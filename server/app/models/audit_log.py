"""
AuditLog — immutable record of every administrative action.

Required by KVKK for accountability: who did what, when, from where, with
what payload.

NOTE: AuditLog rows are tenant-scoped (school_id can be set for school-admin
actions) but super-admin actions have school_id NULL, so this model is NOT
listed in `TENANT_MODELS` — queries must be written explicitly.
"""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Index

from app.extensions import db
from app.models.base import utc_now


class AuditAction(str, Enum):
    # Auth
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILED = "login.failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password.changed"
    PASSWORD_RESET_REQUESTED = "password.reset_requested"
    TOTP_ENABLED = "totp.enabled"
    TOTP_DISABLED = "totp.disabled"

    # Schools (super admin)
    SCHOOL_CREATED = "school.created"
    SCHOOL_UPDATED = "school.updated"
    SCHOOL_SUSPENDED = "school.suspended"
    SCHOOL_DELETED = "school.deleted"

    # Users
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOCKED = "user.locked"
    USER_UNLOCKED = "user.unlocked"

    # Persons
    PERSON_CREATED = "person.created"
    PERSON_UPDATED = "person.updated"
    PERSON_DELETED = "person.deleted"
    PERSON_BULK_IMPORT = "person.bulk_import"
    FACE_ENROLLED = "face.enrolled"
    FACE_DELETED = "face.deleted"

    # Consent
    CONSENT_GRANTED = "consent.granted"
    CONSENT_REVOKED = "consent.revoked"

    # Devices
    DEVICE_CREATED = "device.created"
    DEVICE_UPDATED = "device.updated"
    DEVICE_API_KEY_ROTATED = "device.api_key_rotated"
    DEVICE_DELETED = "device.deleted"
    DEVICE_REBOOTED = "device.rebooted"
    DEVICE_UPDATE_PUSHED = "device.update_pushed"

    # Data export / KVKK rights
    DATA_EXPORT_REQUESTED = "data.export_requested"
    DATA_EXPORT_COMPLETED = "data.export_completed"
    DATA_DELETION_REQUESTED = "data.deletion_requested"
    DATA_DELETION_COMPLETED = "data.deletion_completed"

    @classmethod
    def values(cls) -> list[str]:
        return [a.value for a in cls]


class AuditLog(db.Model):
    """Append-only audit trail — never UPDATE, never DELETE."""

    __tablename__ = "audit_logs"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # --- Who ---
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
    )
    user_role_cached = db.Column(db.String(20))
    user_email_cached = db.Column(db.String(120))

    # --- Tenant scope (NULL for super-admin global actions) ---
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # --- What ---
    action = db.Column(db.String(50), nullable=False, index=True)
    resource_type = db.Column(db.String(40))
    resource_id = db.Column(db.String(64))  # string to handle UUIDs / composite ids
    resource_label = db.Column(db.String(200))  # human-readable label at the time
    details = db.Column(db.JSON)

    # --- How / from where ---
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    request_id = db.Column(db.String(40))  # correlation ID

    # --- When ---
    event_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)

    __table_args__ = (
        Index("ix_audit_logs_school_event", "school_id", "event_at"),
        Index("ix_audit_logs_user_event", "user_id", "event_at"),
        Index("ix_audit_logs_action_event", "action", "event_at"),
    )

    # ---- helpers ----
    @classmethod
    def record(
        cls,
        action: str | AuditAction,
        *,
        user=None,
        school_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        resource_label: str | None = None,
        details: dict | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        commit: bool = False,
    ) -> "AuditLog":
        """Convenience constructor that picks up user/school context."""
        if isinstance(action, AuditAction):
            action = action.value

        entry = cls(
            action=action,
            school_id=school_id if school_id is not None else getattr(user, "school_id", None),
            user_id=getattr(user, "id", None),
            user_role_cached=getattr(user, "role", None),
            user_email_cached=getattr(user, "email", None),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            resource_label=resource_label,
            details=details,
            ip_address=ip[:45] if ip else None,
            user_agent=user_agent[:255] if user_agent else None,
            request_id=request_id,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
        return entry

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"user_id={self.user_id} school_id={self.school_id} "
            f"event_at={self.event_at}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email_cached,
            "user_role": self.user_role_cached,
            "school_id": self.school_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_label": self.resource_label,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "event_at": self.event_at.isoformat() if self.event_at else None}


# ---------------------------------------------------------------------------
# Prevent UPDATE / DELETE at the ORM level
# ---------------------------------------------------------------------------
@db.event.listens_for(AuditLog, "before_update")
def _block_update(_mapper, _connection, _target):  # pragma: no cover
    raise RuntimeError("audit_logs rows are immutable (UPDATE blocked)")


@db.event.listens_for(AuditLog, "before_delete")
def _block_delete(_mapper, _connection, _target):  # pragma: no cover
    raise RuntimeError("audit_logs rows are immutable (DELETE blocked)")