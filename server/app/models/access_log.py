"""
AccessLog — every turnstile event.

Granted events: person recognized + allowed → relay pulsed.
Denied events:  person not recognized OR access revoked OR out-of-schedule.

This is the highest-volume table in the system. Partitioning (by month or year)
should be added in production once we have multiple schools (see
[`plan/04_VERITABANI_DEGISIKLIKLERI.md`](../../../plan/04_VERITABANI_DEGISIKLIKLERI.md:519)).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Index
from sqlalchemy.orm import validates

from app.extensions import db
from app.models.base import register_tenant_model, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AccessDirection(str, Enum):
    IN = "in"
    OUT = "out"
    UNKNOWN = "unknown"

    @classmethod
    def values(cls) -> list[str]:
        return [v.value for v in cls]


class AccessOutcome(str, Enum):
    GRANTED = "granted"
    DENIED_UNKNOWN = "denied_unknown"        # face not recognized
    DENIED_ACCESS = "denied_access"          # person.access_granted=False
    DENIED_SCHEDULE = "denied_schedule"      # outside access_schedule
    DENIED_INACTIVE = "denied_inactive"      # person or school inactive
    DENIED_NO_CONSENT = "denied_no_consent"  # KVKK consent missing/revoked
    ERROR = "error"                          # system-side error

    @classmethod
    def values(cls) -> list[str]:
        return [v.value for v in cls]

    @property
    def is_granted(self) -> bool:
        return self == AccessOutcome.GRANTED


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
@register_tenant_model
class AccessLog(db.Model):
    """A single attempt to pass through a turnstile."""

    __tablename__ = "access_logs"

    id = db.Column(db.BigInteger, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Who / where ---
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # person_id NULL = unknown face (denied)

    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- When / what ---
    event_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
        index=True,
    )
    direction = db.Column(
        db.String(10),
        nullable=False,
        default=AccessDirection.UNKNOWN.value,
    )
    outcome = db.Column(db.String(30), nullable=False, index=True)

    # --- Recognition details ---
    confidence = db.Column(db.Float)  # 0.0..1.0
    distance = db.Column(db.Float)    # raw backend distance
    recognizer_backend = db.Column(db.String(20))  # "dlib" / "insightface"

    # --- Attached snapshot (for denied / suspicious events) ---
    snapshot_path = db.Column(db.String(255))
    snapshot_id = db.Column(
        db.Integer,
        db.ForeignKey("snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Denormalized fields (survive person deletion, useful for reports) ---
    person_name_cached = db.Column(db.String(120))
    person_no_cached = db.Column(db.String(30))
    person_class_cached = db.Column(db.String(30))

    # --- Free-form ---
    details = db.Column(db.JSON)  # arbitrary backend-specific payload

    # --- Metadata ---
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utc_now,
    )
    # We don't track updated_at — access logs are immutable.

    # --- Relationships ---
    person = db.relationship("Person", back_populates="access_logs")
    device = db.relationship("Device", back_populates="access_logs")
    snapshot = db.relationship(
        "Snapshot",
        foreign_keys=[snapshot_id],
        backref="linked_access_logs",
    )

    __table_args__ = (
        Index("ix_access_logs_school_event_at", "school_id", "event_at"),
        Index(
            "ix_access_logs_school_person_event",
            "school_id",
            "person_id",
            "event_at",
        ),
        Index("ix_access_logs_school_outcome", "school_id", "outcome"),
        Index("ix_access_logs_device_event", "device_id", "event_at"),
    )

    # ---- validators ----
    @validates("direction")
    def _validate_direction(self, _key, value):
        if value not in AccessDirection.values():
            raise ValueError(f"Invalid direction: {value}")
        return value

    @validates("outcome")
    def _validate_outcome(self, _key, value):
        if value not in AccessOutcome.values():
            raise ValueError(f"Invalid outcome: {value}")
        return value

    @validates("confidence")
    def _validate_confidence(self, _key, value):
        if value is None:
            return value
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        return float(value)

    # ---- helpers ----
    @property
    def is_granted(self) -> bool:
        return self.outcome == AccessOutcome.GRANTED.value

    @property
    def is_unknown(self) -> bool:
        return self.person_id is None

    def cache_person_fields(self) -> None:
        """Copy person's display fields for report stability across deletions."""
        if self.person is not None:
            self.person_name_cached = self.person.full_name
            self.person_no_cached = self.person.person_no
            self.person_class_cached = self.person.class_name

    # ---- repr / serialization ----
    def __repr__(self) -> str:
        return (
            f"<AccessLog id={self.id} school={self.school_id} "
            f"person={self.person_id} outcome={self.outcome} at={self.event_at}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "school_id": self.school_id,
            "person_id": self.person_id,
            "person_name": self.person_name_cached,
            "person_no": self.person_no_cached,
            "person_class": self.person_class_cached,
            "device_id": self.device_id,
            "event_at": self.event_at.isoformat() if self.event_at else None,
            "direction": self.direction,
            "outcome": self.outcome,
            "is_granted": self.is_granted,
            "confidence": self.confidence,
            "distance": self.distance,
            "recognizer_backend": self.recognizer_backend,
            "snapshot_path": self.snapshot_path,
            "snapshot_id": self.snapshot_id}


# ---------------------------------------------------------------------------
# Event hooks
# ---------------------------------------------------------------------------
@db.event.listens_for(AccessLog, "before_insert")
def _cache_on_insert(_mapper, _connection, target: AccessLog) -> None:
    """Auto-snapshot the person's display fields."""
    if target.person_id and not target.person_name_cached:
        target.cache_person_fields()