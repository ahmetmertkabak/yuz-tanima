"""
Device model — a Raspberry Pi edge node at a school gate.

Each device belongs to exactly one school, is identified by a UUID
(`device_id`) and authenticated by an API key used in HMAC-signed requests
(see [`edge/app/hmac_signer.py`](../../../edge/app/hmac_signer.py:1)).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import validates

from app.extensions import db
from app.models.base import TimestampMixin, register_tenant_model, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class DeviceDirectionMode(str, Enum):
    IN_ONLY = "in_only"
    OUT_ONLY = "out_only"
    BIDIRECTIONAL = "bidirectional"

    @classmethod
    def values(cls) -> list[str]:
        return [v.value for v in cls]


class DeviceStatus(str, Enum):
    PROVISIONING = "provisioning"   # created, API key not yet used
    ONLINE = "online"
    OFFLINE = "offline"
    DISABLED = "disabled"


# Heartbeat: ≥ this many seconds without heartbeat => offline
DEFAULT_OFFLINE_THRESHOLD_SECONDS = 120


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
@register_tenant_model
class Device(db.Model, TimestampMixin):
    """A Pi at a school gate."""

    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Identity ---
    device_uuid = db.Column(
        db.String(36),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    device_name = db.Column(db.String(100), nullable=False)  # e.g. "Ana Giriş"
    location = db.Column(db.String(200))
    description = db.Column(db.Text)

    # --- Auth: API key ---
    # Fernet-encrypted plaintext of the API key. We need to recompute HMAC
    # server-side to verify device requests, so bcrypt is not an option here.
    # The encryption key lives only in the server .env (FACE_ENCRYPTION_KEY).
    api_key_encrypted = db.Column(db.LargeBinary, nullable=False)
    api_key_prefix = db.Column(db.String(12), nullable=False, index=True)
    # prefix stored in plain for quick "key starts with…" display

    # --- Configuration ---
    direction_mode = db.Column(
        db.String(20),
        nullable=False,
        default=DeviceDirectionMode.BIDIRECTIONAL.value,
    )
    turnstile_pulse_ms = db.Column(db.Integer, nullable=False, default=500)
    recognition_tolerance = db.Column(db.Float)
    # If NULL, fall back to School.recognition_tolerance

    # --- Status / telemetry ---
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_heartbeat_at = db.Column(db.DateTime, index=True)
    last_ip = db.Column(db.String(45))
    firmware_version = db.Column(db.String(32))
    last_error = db.Column(db.Text)
    last_error_at = db.Column(db.DateTime)

    # Hardware stats reported in heartbeat
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    cpu_temp_c = db.Column(db.Float)
    uptime_seconds = db.Column(db.Integer)

    # --- Encoding sync ---
    last_encoding_sync_at = db.Column(db.DateTime)
    persons_cached = db.Column(db.Integer, default=0)

    # --- Lifecycle ---
    provisioned_at = db.Column(db.DateTime)
    installed_at = db.Column(db.DateTime)
    installed_by = db.Column(db.String(120))

    # --- Relationships ---
    school = db.relationship("School", back_populates="devices")
    access_logs = db.relationship("AccessLog", back_populates="device")

    __table_args__ = (
        UniqueConstraint("school_id", "device_name", name="uq_devices_school_name"),
        Index("ix_devices_school_active", "school_id", "is_active"),
    )

    # ---- validators ----
    @validates("direction_mode")
    def _validate_direction(self, _key, value):
        if value not in DeviceDirectionMode.values():
            raise ValueError(f"Invalid direction_mode: {value}")
        return value

    @validates("turnstile_pulse_ms")
    def _validate_pulse(self, _key, value):
        if value is not None and (value < 50 or value > 5000):
            raise ValueError("turnstile_pulse_ms must be 50..5000")
        return value

    # ---- API key lifecycle ----
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Return (prefix, full_key) — plaintext. Caller encrypts via set_api_key."""
        full = secrets.token_urlsafe(48)
        prefix = full[:12]
        return prefix, full

    def set_api_key(self, plain: str | None = None) -> str:
        """Rotate the API key. Returns the plaintext (show once at creation)."""
        from app.services.face_crypto import FaceCrypto  # lazy — Flask ctx needed

        if plain is None:
            self.api_key_prefix, plain = self.generate_api_key()
        else:
            self.api_key_prefix = plain[:12]
        self.api_key_encrypted = FaceCrypto.encrypt(plain.encode("utf-8"))
        return plain

    def reveal_api_key(self) -> str | None:
        """Decrypt and return the plaintext API key (device auth server-side)."""
        if not self.api_key_encrypted:
            return None
        try:
            from app.services.face_crypto import FaceCrypto

            return FaceCrypto.decrypt(self.api_key_encrypted).decode("utf-8")
        except Exception:
            return None

    def check_api_key(self, plain: str) -> bool:
        """Constant-time comparison against the decrypted key."""
        stored = self.reveal_api_key()
        if not stored or not plain:
            return False
        return secrets.compare_digest(stored, plain)

    # ---- heartbeat / status ----
    def touch_heartbeat(
        self,
        ip: str | None = None,
        firmware: str | None = None,
        stats: dict | None = None,
    ) -> None:
        """Record a heartbeat + optional telemetry."""
        self.last_heartbeat_at = utc_now()
        if ip:
            self.last_ip = ip[:45]
        if firmware:
            self.firmware_version = firmware[:32]
        if stats:
            self.cpu_percent = stats.get("cpu_percent")
            self.memory_percent = stats.get("memory_percent")
            self.disk_percent = stats.get("disk_percent")
            self.cpu_temp_c = stats.get("cpu_temp_c")
            self.uptime_seconds = stats.get("uptime_seconds")

    def record_error(self, message: str) -> None:
        self.last_error = (message or "")[:4000]
        self.last_error_at = utc_now()

    @property
    def status(self) -> str:
        if not self.is_active:
            return DeviceStatus.DISABLED.value
        if self.last_heartbeat_at is None:
            return DeviceStatus.PROVISIONING.value
        if self.is_online():
            return DeviceStatus.ONLINE.value
        return DeviceStatus.OFFLINE.value

    def is_online(self, threshold_seconds: int = DEFAULT_OFFLINE_THRESHOLD_SECONDS) -> bool:
        if not self.last_heartbeat_at:
            return False
        delta = utc_now() - self.last_heartbeat_at
        return delta.total_seconds() <= threshold_seconds

    # ---- repr / serialization ----
    def __repr__(self) -> str:
        return (
            f"<Device id={self.id} uuid={self.device_uuid} "
            f"school_id={self.school_id} status={self.status}>"
        )

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "school_id": self.school_id,
            "device_uuid": self.device_uuid,
            "device_name": self.device_name,
            "location": self.location,
            "description": self.description,
            "direction_mode": self.direction_mode,
            "turnstile_pulse_ms": self.turnstile_pulse_ms,
            "recognition_tolerance": self.recognition_tolerance,
            "is_active": self.is_active,
            "status": self.status,
            "last_heartbeat_at": (
                self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None
            ),
            "firmware_version": self.firmware_version,
            "persons_cached": self.persons_cached,
            "api_key_prefix": self.api_key_prefix,
            "created_at": self.created_at.isoformat() if self.created_at else None}
        if include_sensitive:
            data.update(
                last_ip=self.last_ip,
                cpu_percent=self.cpu_percent,
                memory_percent=self.memory_percent,
                disk_percent=self.disk_percent,
                cpu_temp_c=self.cpu_temp_c,
                uptime_seconds=self.uptime_seconds,
                last_error=self.last_error,
                last_error_at=(
                    self.last_error_at.isoformat() if self.last_error_at else None
                ),
            )
        return data


# ---------------------------------------------------------------------------
# Lookup helper — used by the HMAC auth middleware
# ---------------------------------------------------------------------------
def find_device_by_uuid(device_uuid: str) -> Optional[Device]:
    """Bypass tenant middleware for device auth (no tenant context yet)."""
    return db.session.query(Device).filter_by(device_uuid=device_uuid).first()