"""
Snapshot — a face image captured by a device, most often for denied /
unrecognized events.

KVKK compliance:
- `expires_at` defaults to `created_at + SNAPSHOT_RETENTION_DAYS`.
- A nightly Celery task deletes expired snapshots (file + row).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import Index
from sqlalchemy.orm import validates

from app.extensions import db
from app.models.base import register_tenant_model, utc_now


DEFAULT_RETENTION_DAYS = 30


@register_tenant_model
class Snapshot(db.Model):
    """Captured face image (denied events, review queue, audit)."""

    __tablename__ = "snapshots"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="SET NULL"),
    )

    # --- Storage ---
    image_path = db.Column(db.String(255), nullable=False)
    # Relative key in the private S3/MinIO bucket
    image_content_type = db.Column(db.String(32), default="image/jpeg")
    image_size_bytes = db.Column(db.Integer)

    # --- Recognition hints (optional) ---
    face_encoding_encrypted = db.Column(db.LargeBinary)
    # Stored only if we need to re-run matching later; nullable.
    best_match_person_id = db.Column(
        db.Integer,
        db.ForeignKey("persons.id", ondelete="SET NULL"),
    )
    best_match_confidence = db.Column(db.Float)

    # --- Review workflow ---
    reviewed = db.Column(db.Boolean, nullable=False, default=False, index=True)
    review_note = db.Column(db.Text)
    reviewed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
    )
    reviewed_at = db.Column(db.DateTime)

    # --- Timestamps / retention ---
    captured_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime, index=True)

    __table_args__ = (
        Index("ix_snapshots_school_captured", "school_id", "captured_at"),
        Index("ix_snapshots_review_state", "school_id", "reviewed", "captured_at"),
    )

    # ---- validators ----
    @validates("best_match_confidence")
    def _validate_conf(self, _key, value):
        if value is None:
            return value
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError("best_match_confidence must be in [0, 1]")
        return float(value)

    # ---- helpers ----
    def set_expiry(self, days: int | None = None) -> None:
        days = days or self._retention_days()
        self.expires_at = (self.captured_at or utc_now()) + timedelta(days=days)

    @staticmethod
    def _retention_days() -> int:
        try:
            return int(current_app.config.get("SNAPSHOT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
        except Exception:
            return DEFAULT_RETENTION_DAYS

    def mark_reviewed(self, user_id: int, note: str | None = None) -> None:
        self.reviewed = True
        self.reviewed_by_user_id = user_id
        self.reviewed_at = utc_now()
        if note:
            self.review_note = note

    # ---- repr / serialization ----
    def __repr__(self) -> str:
        return (
            f"<Snapshot id={self.id} school={self.school_id} "
            f"captured_at={self.captured_at} reviewed={self.reviewed}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "school_id": self.school_id,
            "device_id": self.device_id,
            "image_path": self.image_path,
            "image_size_bytes": self.image_size_bytes,
            "best_match_person_id": self.best_match_person_id,
            "best_match_confidence": self.best_match_confidence,
            "reviewed": self.reviewed,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None}


# ---------------------------------------------------------------------------
# Auto-populate expires_at if the caller forgot to set it
# ---------------------------------------------------------------------------
@db.event.listens_for(Snapshot, "before_insert")
def _set_expiry_on_insert(_mapper, _connection, target: Snapshot) -> None:
    if target.expires_at is None:
        # Outside an app context (e.g. bulk imports) we fall back to the default.
        try:
            target.set_expiry()
        except RuntimeError:
            target.expires_at = (target.captured_at or utc_now()) + timedelta(
                days=DEFAULT_RETENTION_DAYS
            )