"""
Queued remote commands sent from SuperAdmin to Pi devices.

Pi polls `/api/v1/device/commands` periodically and reports back the outcome.
"""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Index

from app.extensions import db
from app.models.base import register_tenant_model, utc_now


class DeviceCommandType(str, Enum):
    REBOOT = "reboot"
    RELOAD_ENCODINGS = "reload_encodings"
    FORCE_SYNC = "force_sync"
    UPDATE_FIRMWARE = "update_firmware"
    DISABLE = "disable"
    ENABLE = "enable"
    TEST_TURNSTILE = "test_turnstile"

    @classmethod
    def values(cls) -> list[str]:
        return [v.value for v in cls]


class DeviceCommandStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@register_tenant_model
class DeviceCommand(db.Model):
    """One queued command for a specific device."""

    __tablename__ = "device_commands"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
    )

    command_type = db.Column(db.String(30), nullable=False)
    payload = db.Column(db.JSON)  # Optional command parameters

    status = db.Column(
        db.String(20),
        nullable=False,
        default=DeviceCommandStatus.PENDING.value,
        index=True,
    )
    attempts = db.Column(db.Integer, nullable=False, default=0)
    response = db.Column(db.JSON)
    error_message = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    sent_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)

    __table_args__ = (
        Index("ix_device_commands_device_status", "device_id", "status"),
        Index("ix_device_commands_school_created", "school_id", "created_at"),
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            DeviceCommandStatus.COMPLETED.value,
            DeviceCommandStatus.FAILED.value,
            DeviceCommandStatus.CANCELLED.value,
            DeviceCommandStatus.EXPIRED.value,
        )

    def mark_sent(self) -> None:
        self.status = DeviceCommandStatus.SENT.value
        self.sent_at = utc_now()
        self.attempts = (self.attempts or 0) + 1

    def mark_completed(self, response: dict | None = None) -> None:
        self.status = DeviceCommandStatus.COMPLETED.value
        self.completed_at = utc_now()
        if response is not None:
            self.response = response

    def mark_failed(self, error: str) -> None:
        self.status = DeviceCommandStatus.FAILED.value
        self.completed_at = utc_now()
        self.error_message = error[:4000]

    def __repr__(self) -> str:
        return (
            f"<DeviceCommand id={self.id} device={self.device_id} "
            f"type={self.command_type} status={self.status}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "school_id": self.school_id,
            "device_id": self.device_id,
            "command_type": self.command_type,
            "payload": self.payload,
            "status": self.status,
            "attempts": self.attempts,
            "response": self.response,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            )}