"""
Person model — students, teachers, staff, managers.

Replaces the legacy `Student` model. Added fields:
- role (student/teacher/staff/manager)
- class_name
- face_encoding + face_photo_path (encrypted biometric data)
- KVKK consent bookkeeping
- access_granted + access_schedule (per-person ACL)
"""
from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from typing import Optional

import numpy as np
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import validates

from app.extensions import db
from app.models.base import AuditableMixin, TimestampMixin, register_tenant_model
from app.services.face_crypto import FaceCrypto, FaceCryptoError


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PersonRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    STAFF = "staff"
    MANAGER = "manager"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]


class ConsentStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"

    @classmethod
    def values(cls) -> list[str]:
        return [s.value for s in cls]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
@register_tenant_model
class Person(db.Model, TimestampMixin, AuditableMixin):
    """A person enrolled in a school (student, teacher, staff, manager)."""

    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Identity ---
    person_no = db.Column(db.String(30), nullable=False)  # öğrenci no / sicil no
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    class_name = db.Column(db.String(30))  # e.g. "9-A"
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    parent_phone = db.Column(db.String(20))  # for students
    parent_name = db.Column(db.String(120))
    notes = db.Column(db.Text)

    # --- Biometric (encrypted at rest) ---
    face_encoding_encrypted = db.Column(db.LargeBinary)  # Fernet ciphertext
    face_encoding_version = db.Column(db.Integer, default=1)
    # Bump when we re-train / upgrade the recognizer backend
    face_photo_path = db.Column(db.String(255))  # S3/MinIO key
    face_updated_at = db.Column(db.DateTime)

    # --- Access control ---
    access_granted = db.Column(db.Boolean, nullable=False, default=True, index=True)
    # False = temporarily denied access (discipline, lost ID card, etc.)
    access_schedule = db.Column(db.JSON)
    # Example: {"mon": ["07:30-18:00"], "tue": ["07:30-18:00"], ...}
    # Empty list = forbidden that day; missing key = default allow all day

    # --- KVKK / consent ---
    consent_status = db.Column(
        db.String(20),
        nullable=False,
        default=ConsentStatus.PENDING.value,
        index=True,
    )
    consent_granted_at = db.Column(db.DateTime)
    consent_revoked_at = db.Column(db.DateTime)
    consent_document_path = db.Column(db.String(255))
    # signed PDF from parent, stored in private bucket

    # --- Status ---
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # --- Relationships ---
    school = db.relationship("School", back_populates="persons")
    access_logs = db.relationship(
        "AccessLog",
        back_populates="person",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint("school_id", "person_no", name="uq_persons_school_person_no"),
        Index("ix_persons_school_active", "school_id", "is_active"),
        Index("ix_persons_school_role", "school_id", "role"),
        Index(
            "ix_persons_school_class",
            "school_id",
            "class_name",
            postgresql_where=(db.text("class_name IS NOT NULL")),
        ),
    )

    # ---- validators ----
    @validates("role")
    def _validate_role(self, _key, value):
        if value not in PersonRole.values():
            raise ValueError(f"Invalid person role: {value}")
        return value

    @validates("consent_status")
    def _validate_consent(self, _key, value):
        if value not in ConsentStatus.values():
            raise ValueError(f"Invalid consent status: {value}")
        return value

    @validates("email")
    def _norm_email(self, _key, value):
        return value.strip().lower() if value else value

    @validates("person_no")
    def _norm_person_no(self, _key, value):
        if not value:
            raise ValueError("person_no is required")
        return value.strip()

    # ---- biometric helpers ----
    @property
    def has_face(self) -> bool:
        return self.face_encoding_encrypted is not None

    def set_face_encoding(self, encoding: np.ndarray) -> None:
        """Encrypt & store a numpy encoding vector."""
        if encoding is None:
            raise ValueError("encoding must not be None")
        self.face_encoding_encrypted = FaceCrypto.encrypt_array(encoding)
        self.face_updated_at = datetime.utcnow()

    def get_face_encoding(self) -> Optional[np.ndarray]:
        """Decrypt & return the numpy encoding, or None if not set."""
        if not self.face_encoding_encrypted:
            return None
        try:
            return FaceCrypto.decrypt_array(self.face_encoding_encrypted)
        except FaceCryptoError:
            return None

    def clear_face_encoding(self) -> None:
        self.face_encoding_encrypted = None
        self.face_photo_path = None
        self.face_updated_at = None

    # ---- consent helpers ----
    def grant_consent(self, document_path: str | None = None) -> None:
        self.consent_status = ConsentStatus.GRANTED.value
        self.consent_granted_at = datetime.utcnow()
        self.consent_revoked_at = None
        if document_path:
            self.consent_document_path = document_path

    def revoke_consent(self) -> None:
        self.consent_status = ConsentStatus.REVOKED.value
        self.consent_revoked_at = datetime.utcnow()
        self.clear_face_encoding()  # KVKK: revoke => remove biometric data

    # ---- access control ----
    def is_access_allowed_now(self, now: datetime | None = None) -> bool:
        """Whether this person is allowed through a turnstile right now."""
        if not (self.is_active and self.access_granted):
            return False
        if self.consent_status != ConsentStatus.GRANTED.value:
            return False
        if not self.access_schedule:
            return True

        now = now or datetime.utcnow()
        day_key = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][now.weekday()]
        windows = self.access_schedule.get(day_key)
        if windows is None:
            return True  # no rule for today → allow
        if not windows:
            return False  # explicit empty list → forbidden that day

        current = now.time()
        for window in windows:
            try:
                start_s, end_s = window.split("-")
                start = _parse_hhmm(start_s)
                end = _parse_hhmm(end_s)
            except (ValueError, AttributeError):
                continue
            if start <= current <= end:
                return True
        return False

    # ---- repr / serialization ----
    def __repr__(self) -> str:
        return (
            f"<Person id={self.id} school_id={self.school_id} "
            f"no={self.person_no!r} role={self.role}>"
        )

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Serializer — sensitive fields behind a flag."""
        data = {
            "id": self.id,
            "school_id": self.school_id,
            "person_no": self.person_no,
            "full_name": self.full_name,
            "role": self.role,
            "class_name": self.class_name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "access_granted": self.access_granted,
            "has_face": self.has_face,
            "consent_status": self.consent_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "face_updated_at": (
                self.face_updated_at.isoformat() if self.face_updated_at else None
            )}
        if include_sensitive:
            data.update(
                parent_phone=self.parent_phone,
                parent_name=self.parent_name,
                access_schedule=self.access_schedule,
                notes=self.notes,
                consent_granted_at=(
                    self.consent_granted_at.isoformat()
                    if self.consent_granted_at
                    else None
                ),
            )
        return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_hhmm(text: str) -> time:
    h, m = text.strip().split(":")
    return time(hour=int(h), minute=int(m))