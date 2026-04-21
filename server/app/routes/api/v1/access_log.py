"""
Batched access log ingestion.

Pi posts a JSON payload:
    {
      "logs": [
        {
          "event_at": "2026-04-21T10:30:00",
          "person_server_id": 42,        # null for unknown
          "direction": "in",
          "outcome": "granted",
          "confidence": 0.93,
          "distance": 0.41,
          "recognizer_backend": "dlib",
          "details": {...}               # optional
        },
        ...
      ]
    }

Server:
  - Validates each entry
  - Creates AccessLog rows
  - Broadcasts each row via Socket.IO to school_<id>
  - Returns per-entry status so the Pi can mark only accepted entries as synced
"""
from __future__ import annotations

from datetime import datetime

from flask import g, jsonify, request

from app.extensions import db, limiter
from app.middleware import device_auth_required
from app.models import (
    AccessDirection,
    AccessLog,
    AccessOutcome,
    Person,
)
from app.routes.api.v1 import bp
from app.services.realtime import broadcast_access_log


MAX_BATCH_SIZE = 500


def _parse_event_at(value) -> datetime:
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


@bp.route("/device/access_log", methods=["POST"])
@limiter.limit("60 per minute")
@device_auth_required
def submit_access_logs():
    payload = request.get_json(silent=True) or {}
    entries = payload.get("logs") or []

    if not isinstance(entries, list) or not entries:
        return jsonify(error="empty_batch"), 400
    if len(entries) > MAX_BATCH_SIZE:
        return jsonify(error="batch_too_large", max=MAX_BATCH_SIZE), 413

    device = g.device
    school_id = g.school.id

    # Resolve all referenced person_ids once (one query, belongs to this school)
    person_ids = [
        e.get("person_server_id")
        for e in entries
        if isinstance(e.get("person_server_id"), int)
    ]
    persons_by_id: dict[int, Person] = {}
    if person_ids:
        persons = (
            db.session.query(Person)
            .filter(Person.school_id == school_id, Person.id.in_(person_ids))
            .all()
        )
        persons_by_id = {p.id: p for p in persons}

    accepted = []
    rejected = []
    created_logs: list[AccessLog] = []

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            rejected.append({"index": idx, "error": "bad_shape"})
            continue

        direction = entry.get("direction") or AccessDirection.UNKNOWN.value
        outcome = entry.get("outcome")
        if direction not in AccessDirection.values():
            rejected.append({"index": idx, "error": "bad_direction"})
            continue
        if outcome not in AccessOutcome.values():
            rejected.append({"index": idx, "error": "bad_outcome"})
            continue

        person = persons_by_id.get(entry.get("person_server_id"))

        log = AccessLog(
            school_id=school_id,
            person_id=person.id if person else None,
            device_id=device.id,
            event_at=_parse_event_at(entry.get("event_at")),
            direction=direction,
            outcome=outcome,
            confidence=entry.get("confidence"),
            distance=entry.get("distance"),
            recognizer_backend=entry.get("recognizer_backend"),
            snapshot_path=entry.get("snapshot_path"),
            details=entry.get("details"),
        )
        db.session.add(log)
        created_logs.append(log)
        accepted.append({"index": idx, "client_id": entry.get("client_id")})

    db.session.flush()
    db.session.commit()

    # Broadcast after commit so IDs are assigned
    for log in created_logs:
        broadcast_access_log(log)

    return jsonify(
        accepted=accepted,
        rejected=rejected,
        server_time=datetime.utcnow().isoformat(),
    )