"""
Migrate data from the legacy RFID yemekhane SQLite DB into the new
multi-tenant PostgreSQL schema.

Usage:
    cd server
    python -m scripts.migrate_legacy_sqlite \\
        --sqlite /path/to/legacy/instance/app.db \\
        --school-name "Legacy İlkokulu" \\
        --school-subdomain "legacy" \\
        [--dry-run]

What it does
------------
1. Creates a single `School` row ("Legacy School") if one with the chosen
   subdomain does not already exist. All migrated rows are attached to it.
2. Walks the legacy `students` table and inserts `persons` rows (role=student,
   class_name copied over, RFID data discarded — face_encoding is NULL).
3. Walks the legacy `attendances` table and inserts `access_logs` rows
   (outcome=granted, direction=in, person_id mapped).
4. Skips rows that already have an id in a per-run mapping (safe to re-run).
5. Legacy `transactions` and balances are dropped entirely (bakiye sistemi
   kaldırıldı — see plan/00_GENEL_BAKIS.md).

The script is **idempotent on School+Person** level: if a `person_no`
already exists under that school it is skipped. AccessLog rows are always
inserted fresh — re-running duplicates logs, so use `--dry-run` first.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Allow running with `python -m scripts.migrate_legacy_sqlite` when executed
# from `server/`.
SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    AccessDirection,
    AccessLog,
    AccessOutcome,
    ConsentStatus,
    Person,
    PersonRole,
    School,
    SubscriptionStatus,
)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", required=True, help="Path to the legacy SQLite DB")
    ap.add_argument("--school-name", default="Legacy Okulu")
    ap.add_argument("--school-subdomain", default="legacy")
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Roll back at the end instead of committing.",
    )
    return ap.parse_args()


# ---------------------------------------------------------------------------
# Legacy schema access — read-only
# ---------------------------------------------------------------------------
def _open_legacy(path: str) -> sqlite3.Connection:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Legacy SQLite DB not found: {p}")
    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _legacy_table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# School
# ---------------------------------------------------------------------------
def _get_or_create_legacy_school(name: str, subdomain: str) -> School:
    school = db.session.query(School).filter_by(subdomain=subdomain).first()
    if school:
        print(f"↺ Reusing existing school (id={school.id}, subdomain={subdomain})")
        return school

    school = School(
        name=name,
        subdomain=School.normalize_subdomain(subdomain),
        subscription_status=SubscriptionStatus.ACTIVE.value,
        is_active=True,
        max_devices=5,
        max_persons=2000,
    )
    db.session.add(school)
    db.session.flush()
    print(f"✓ Created school id={school.id} subdomain={school.subdomain!r}")
    return school


# ---------------------------------------------------------------------------
# Students → Persons
# ---------------------------------------------------------------------------
def _migrate_students(
    legacy: sqlite3.Connection,
    school: School,
    batch_size: int,
) -> dict[int, int]:
    """Return a {legacy_student_id: new_person_id} map."""
    mapping: dict[int, int] = {}

    if not _legacy_table_exists(legacy, "students"):
        print("⚠  'students' table not found in legacy DB — skipping person migration.")
        return mapping

    cur = legacy.execute(
        """
        SELECT id, student_no, name, class_name, parent_phone, is_active, created_at
        FROM students
        ORDER BY id
        """
    )
    seen_person_nos: set[str] = {
        row[0]
        for row in db.session.query(Person.person_no)
        .filter_by(school_id=school.id)
        .all()
    }
    inserted = 0
    skipped_existing = 0

    for i, row in enumerate(cur, start=1):
        person_no = (row["student_no"] or "").strip()
        if not person_no:
            continue
        if person_no in seen_person_nos:
            skipped_existing += 1
            # We still need to look up the existing Person's id for log mapping
            existing = (
                db.session.query(Person.id)
                .filter_by(school_id=school.id, person_no=person_no)
                .scalar()
            )
            if existing:
                mapping[row["id"]] = existing
            continue

        person = Person(
            school_id=school.id,
            person_no=person_no,
            full_name=row["name"] or person_no,
            role=PersonRole.STUDENT.value,
            class_name=(row["class_name"] or None),
            parent_phone=(row["parent_phone"] or None),
            is_active=bool(row["is_active"]) if row["is_active"] is not None else True,
            consent_status=ConsentStatus.PENDING.value,
            access_granted=True,
        )
        db.session.add(person)
        db.session.flush()
        mapping[row["id"]] = person.id
        seen_person_nos.add(person_no)
        inserted += 1

        if i % batch_size == 0:
            print(f"   … processed {i} student rows")

    print(
        f"✓ Students → Persons: inserted={inserted}, skipped_existing={skipped_existing}, "
        f"mapped={len(mapping)}"
    )
    return mapping


# ---------------------------------------------------------------------------
# Attendance → AccessLog
# ---------------------------------------------------------------------------
def _migrate_attendance(
    legacy: sqlite3.Connection,
    school: School,
    person_map: dict[int, int],
    batch_size: int,
) -> int:
    if not _legacy_table_exists(legacy, "attendances"):
        print("⚠  'attendances' table not found in legacy DB — skipping access log migration.")
        return 0

    # Some legacy schemas used `attendance_time`, others `created_at`.
    cols = {row[1] for row in legacy.execute("PRAGMA table_info(attendances)").fetchall()}
    ts_col = (
        "attendance_time" if "attendance_time" in cols
        else "created_at" if "created_at" in cols
        else None
    )
    if ts_col is None:
        print("⚠  Could not find a timestamp column in 'attendances' — skipping.")
        return 0

    cur = legacy.execute(
        f"SELECT id, student_id, {ts_col} AS ts FROM attendances ORDER BY id"
    )
    inserted = 0
    unmapped = 0
    buffer: list[AccessLog] = []

    for row in cur:
        person_id = person_map.get(row["student_id"])
        if person_id is None:
            unmapped += 1
            continue

        ts = row["ts"]
        if isinstance(ts, str):
            try:
                ts_dt = datetime.fromisoformat(ts)
            except ValueError:
                ts_dt = datetime.utcnow()
        elif isinstance(ts, datetime):
            ts_dt = ts
        else:
            ts_dt = datetime.utcnow()

        buffer.append(
            AccessLog(
                school_id=school.id,
                person_id=person_id,
                device_id=None,
                event_at=ts_dt,
                direction=AccessDirection.IN.value,
                outcome=AccessOutcome.GRANTED.value,
                confidence=None,
                details={"legacy_attendance_id": row["id"]},
            )
        )
        inserted += 1

        if len(buffer) >= batch_size:
            db.session.bulk_save_objects(buffer)
            buffer.clear()
            print(f"   … migrated {inserted} attendance rows")

    if buffer:
        db.session.bulk_save_objects(buffer)
        buffer.clear()

    print(f"✓ Attendances → AccessLogs: inserted={inserted}, unmapped={unmapped}")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = _parse_args()
    app = create_app()

    with app.app_context():
        # Bypass tenant middleware (we are the migration)
        from flask import g

        g.bypass_tenant_filter = True

        with _open_legacy(args.sqlite) as legacy:
            print(f"→ Opening legacy DB: {args.sqlite}")
            school = _get_or_create_legacy_school(
                args.school_name, args.school_subdomain
            )
            person_map = _migrate_students(legacy, school, args.batch_size)
            _migrate_attendance(legacy, school, person_map, args.batch_size)

        if args.dry_run:
            db.session.rollback()
            print("🏁 Dry-run: all changes rolled back.")
        else:
            db.session.commit()
            print("🏁 Committed. Legacy migration complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())