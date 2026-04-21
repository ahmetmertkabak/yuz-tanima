"""
School model — the tenant in our multi-tenant SaaS.

Every other tenant-scoped table carries a `school_id` FK back to this table.
Deleting a school cascades to all of its users, persons, devices and logs
(SET via `ondelete="CASCADE"` in the FK definitions on those tables).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import Index

from app.extensions import db
from app.models.base import TimestampMixin, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class SubscriptionStatus(str, Enum):
    """Lifecycle states for a school's SaaS subscription."""

    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

    @classmethod
    def values(cls) -> list[str]:
        return [s.value for s in cls]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class School(db.Model, TimestampMixin):
    """A customer tenant (a single school)."""

    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    name = db.Column(db.String(200), nullable=False)
    subdomain = db.Column(db.String(63), unique=True, nullable=False, index=True)
    # e.g. "ali-pasa-lisesi" → ali-pasa-lisesi.yuztanima.com

    # Contact
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    contact_name = db.Column(db.String(120))

    # Subscription
    subscription_status = db.Column(
        db.String(20),
        nullable=False,
        default=SubscriptionStatus.TRIAL.value,
        index=True,
    )
    subscription_started_at = db.Column(db.DateTime)
    subscription_expires_at = db.Column(db.DateTime)
    trial_expires_at = db.Column(db.DateTime)

    # Plan limits
    max_devices = db.Column(db.Integer, nullable=False, default=1)
    max_persons = db.Column(db.Integer, nullable=False, default=500)

    # Operational settings
    timezone = db.Column(db.String(50), nullable=False, default="Europe/Istanbul")
    recognition_tolerance = db.Column(db.Float, nullable=False, default=0.55)
    # lower = stricter; edge-node uses this to reject low-confidence matches

    # Lifecycle flags
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # Relationships (populated by cascaded models)
    users = db.relationship(
        "User",
        back_populates="school",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    persons = db.relationship(
        "Person",
        back_populates="school",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    devices = db.relationship(
        "Device",
        back_populates="school",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_schools_status_active", "subscription_status", "is_active"),
    )

    # ---- validation ----
    @staticmethod
    def normalize_subdomain(value: str) -> str:
        """Lower-case, strip, replace spaces/underscores with hyphens."""
        return (
            (value or "")
            .strip()
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )

    # ---- helpers ----
    @property
    def is_subscription_active(self) -> bool:
        """True if the school may use the service right now."""
        if not self.is_active:
            return False
        if self.subscription_status in (
            SubscriptionStatus.SUSPENDED.value,
            SubscriptionStatus.CANCELLED.value,
            SubscriptionStatus.EXPIRED.value,
        ):
            return False
        now = utc_now()
        if self.subscription_status == SubscriptionStatus.TRIAL.value:
            return bool(self.trial_expires_at and self.trial_expires_at > now)
        if self.subscription_status == SubscriptionStatus.ACTIVE.value:
            return bool(
                self.subscription_expires_at is None
                or self.subscription_expires_at > now
            )
        return False

    @property
    def full_domain(self) -> str:
        """E.g. "ali-pasa-lisesi.yuztanima.com" — for building URLs."""
        # BASE_DOMAIN is pulled at render time from config, not here, to avoid
        # coupling the model to Flask's app context.
        return self.subdomain

    def start_trial(self, days: int = 30) -> None:
        """Mark a freshly-created school as trial and set its expiry."""
        self.subscription_status = SubscriptionStatus.TRIAL.value
        self.subscription_started_at = utc_now()
        self.trial_expires_at = utc_now() + timedelta(days=days)

    def activate_subscription(self, expires_at: datetime | None) -> None:
        """Flip trial → active (called after payment)."""
        self.subscription_status = SubscriptionStatus.ACTIVE.value
        self.subscription_started_at = self.subscription_started_at or utc_now()
        self.subscription_expires_at = expires_at

    # ---- misc ----
    def __repr__(self) -> str:
        return f"<School id={self.id} subdomain={self.subdomain!r}>"

    def to_dict(self) -> dict:
        """Serializer used by the super-admin API."""
        return {
            "id": self.id,
            "name": self.name,
            "subdomain": self.subdomain,
            "is_active": self.is_active,
            "subscription_status": self.subscription_status,
            "subscription_expires_at": (
                self.subscription_expires_at.isoformat()
                if self.subscription_expires_at
                else None
            ),
            "trial_expires_at": (
                self.trial_expires_at.isoformat() if self.trial_expires_at else None
            ),
            "max_devices": self.max_devices,
            "max_persons": self.max_persons,
            "timezone": self.timezone,
            "recognition_tolerance": self.recognition_tolerance,
            "created_at": self.created_at.isoformat() if self.created_at else None}