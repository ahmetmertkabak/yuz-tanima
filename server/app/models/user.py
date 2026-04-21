"""
User model — platform + school-scoped accounts.

Roles:
  - `super_admin`  — platform owner (us). school_id is NULL.
  - `school_admin` — school-level admin (full access within one school).
  - `school_staff` — limited access (e.g. view reports, no CRUD on persons).
  - `viewer`       — read-only (e.g. principal).

Uniqueness is scoped per-school so two different schools can both have a
`admin@example.com` without collision.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import bcrypt
from flask_login import UserMixin
from sqlalchemy import Index, UniqueConstraint, func
from sqlalchemy.orm import validates

from app.extensions import db, login_manager
from app.models.base import TimestampMixin, utc_now


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    SCHOOL_STAFF = "school_staff"
    VIEWER = "viewer"

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]

    @classmethod
    def school_scoped(cls) -> set[str]:
        """Roles that MUST have a school_id."""
        return {cls.SCHOOL_ADMIN.value, cls.SCHOOL_STAFF.value, cls.VIEWER.value}


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model, TimestampMixin):
    """Authenticated user of one of the web panels."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # NOTE: school_id is nullable because super_admin has no tenant
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Identity
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120))

    # Auth
    password_hash = db.Column(db.String(255), nullable=False)
    password_changed_at = db.Column(db.DateTime)

    # Two-factor auth
    totp_secret = db.Column(db.String(64))
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)

    # Role / permissions
    role = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        default=UserRole.SCHOOL_STAFF.value,
    )

    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)

    # Tracking
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))

    # Relationships
    school = db.relationship("School", back_populates="users")

    __table_args__ = (
        UniqueConstraint("school_id", "username", name="uq_user_school_username"),
        UniqueConstraint("school_id", "email", name="uq_user_school_email"),
        Index("ix_users_role_active", "role", "is_active"),
    )

    # ---- validators ----
    @validates("role")
    def _validate_role(self, _key, value):
        if value not in UserRole.values():
            raise ValueError(f"Invalid role: {value}")
        return value

    @validates("email")
    def _validate_email(self, _key, value):
        if value:
            value = value.strip().lower()
        return value

    @validates("username")
    def _validate_username(self, _key, value):
        if value:
            value = value.strip().lower()
        return value

    # ---- password helpers ----
    def set_password(self, password: str) -> None:
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")
        self.password_changed_at = utc_now()

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password_hash.encode("utf-8"),
            )
        except ValueError:
            return False

    # ---- role helpers ----
    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN.value

    def is_school_admin(self) -> bool:
        return self.role == UserRole.SCHOOL_ADMIN.value

    def can_manage_persons(self) -> bool:
        return self.role in (
            UserRole.SUPER_ADMIN.value,
            UserRole.SCHOOL_ADMIN.value,
        )

    def can_manage_devices(self) -> bool:
        return self.role in (
            UserRole.SUPER_ADMIN.value,
            UserRole.SCHOOL_ADMIN.value,
        )

    def can_view_reports(self) -> bool:
        return self.role in UserRole.values()

    # ---- Flask-Login integration ----
    @property
    def is_active_account(self) -> bool:
        """Flask-Login checks `is_active`. We also check `is_locked` + expiry."""
        if not self.is_active or self.is_locked:
            return False
        if self.locked_until and self.locked_until > utc_now():
            return False
        return True

    def get_id(self) -> str:
        """Flask-Login expects a string."""
        return str(self.id)

    # Override UserMixin.is_active to honor lock state
    @property
    def is_active_flag(self) -> bool:  # pragma: no cover
        return self.is_active_account

    # ---- lockout ----
    def register_failed_login(self, threshold: int = 5, lockout_minutes: int = 15) -> None:
        """Increment failed counter, lock if threshold reached."""
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= threshold:
            self.is_locked = True
            self.locked_until = utc_now() + timedelta(minutes=lockout_minutes)

    def register_successful_login(self, ip: str | None = None) -> None:
        self.failed_login_count = 0
        self.is_locked = False
        self.locked_until = None
        self.last_login_at = utc_now()
        if ip:
            self.last_login_ip = ip[:45]

    # ---- repr / serialization ----
    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role} school_id={self.school_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "school_id": self.school_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "totp_enabled": self.totp_enabled,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None}


# ---------------------------------------------------------------------------
# Validation: school_id vs role consistency
# ---------------------------------------------------------------------------
@db.event.listens_for(User, "before_insert")
@db.event.listens_for(User, "before_update")
def _validate_user_role_tenant(_mapper, _connection, target: User) -> None:
    """Enforce: super_admin MUST have school_id IS NULL, others MUST have one."""
    if target.role == UserRole.SUPER_ADMIN.value and target.school_id is not None:
        raise ValueError("super_admin users cannot be attached to a school")
    if (
        target.role in UserRole.school_scoped()
        and target.school_id is None
    ):
        raise ValueError(f"{target.role} users must have a school_id")


# ---------------------------------------------------------------------------
# Flask-Login user loader
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Convenience queries
# ---------------------------------------------------------------------------
def count_users_by_school(school_id: int) -> int:
    return db.session.query(func.count(User.id)).filter_by(school_id=school_id).scalar() or 0