"""
Shared model base classes + mixins.

- `TimestampMixin`   — adds created_at / updated_at columns
- `TenantMixin`      — adds school_id (FK to schools) + composite index helpers
- `AuditableMixin`   — adds created_by / updated_by user FKs (used by admin-touched rows)

All concrete models should inherit from `db.Model` + whatever mixins apply.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import declared_attr

from app.extensions import db


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class TimestampMixin:
    """Adds `created_at` and `updated_at` columns."""

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class TenantMixin:
    """Adds `school_id` (NOT NULL FK) used by every tenant-scoped model."""

    @declared_attr
    def school_id(cls):  # noqa: N805
        return Column(
            Integer,
            ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class AuditableMixin:
    """Tracks which admin user created / last modified a row."""

    @declared_attr
    def created_by_user_id(cls):  # noqa: N805
        return Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def updated_by_user_id(cls):  # noqa: N805
        return Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def utc_now() -> datetime:
    """Single source of truth for timestamps — always UTC naive."""
    return datetime.utcnow()


# Registry of tenant-scoped models. The tenant middleware (T1.7) consults this
# list to know where to inject a `school_id == g.school_id` predicate.
TENANT_MODELS: list[type[db.Model]] = []


def register_tenant_model(cls):
    """Decorator: marks a model as tenant-scoped."""
    TENANT_MODELS.append(cls)
    return cls