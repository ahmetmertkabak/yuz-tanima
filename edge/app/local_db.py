"""
Local SQLite cache on the Pi.

Holds:
- `persons`      — synced face encodings (for offline recognition)
- `access_logs`  — pending events awaiting upload to the VPS
- `snapshots`    — pending snapshot uploads
- `meta`         — key/value (last_sync_at, encoding_version, ...)

Skeleton only — full CRUD helpers arrive in T6.8.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
    id              INTEGER PRIMARY KEY,
    server_id       INTEGER UNIQUE NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL,       -- student / teacher / staff
    class_name      TEXT,
    encoding        BLOB NOT NULL,       -- numpy.ndarray serialized
    is_active       INTEGER NOT NULL DEFAULT 1,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_persons_active ON persons(is_active);

CREATE TABLE IF NOT EXISTS access_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    person_server_id INTEGER,
    event_at        TEXT NOT NULL,
    direction       TEXT NOT NULL,       -- entry / exit
    confidence      REAL,
    outcome         TEXT NOT NULL,       -- granted / denied / unknown
    snapshot_path   TEXT,
    synced          INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_access_logs_synced ON access_logs(synced);

CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL,
    event_at    TEXT NOT NULL,
    uploaded    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""


def init_db(db_path: Path | None = None) -> None:
    """Create schema if it does not yet exist."""
    path = db_path or settings.local_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_conn(db_path: Path | None = None):
    """Context-managed SQLite connection with row-as-dict access."""
    path = db_path or settings.local_db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()