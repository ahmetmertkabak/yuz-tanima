"""
Model package.

Importing from `app.models` exposes every concrete model class, so SQLAlchemy
metadata + Flask-Migrate can discover them without per-file imports elsewhere.
"""
from app.models.base import (
    AuditableMixin,
    TENANT_MODELS,
    TenantMixin,
    TimestampMixin,
    register_tenant_model,
    utc_now,
)
from app.models.access_log import AccessDirection, AccessLog, AccessOutcome
from app.models.audit_log import AuditAction, AuditLog
from app.models.device import (
    DEFAULT_OFFLINE_THRESHOLD_SECONDS,
    Device,
    DeviceDirectionMode,
    DeviceStatus,
    find_device_by_uuid,
)
from app.models.device_command import (
    DeviceCommand,
    DeviceCommandStatus,
    DeviceCommandType,
)
from app.models.person import ConsentStatus, Person, PersonRole
from app.models.school import School, SubscriptionStatus
from app.models.snapshot import Snapshot
from app.models.user import User, UserRole, count_users_by_school

__all__ = [
    # Mixins / base
    "TimestampMixin",
    "TenantMixin",
    "AuditableMixin",
    "TENANT_MODELS",
    "register_tenant_model",
    "utc_now",
    # School
    "School",
    "SubscriptionStatus",
    # User
    "User",
    "UserRole",
    "count_users_by_school",
    # Person
    "Person",
    "PersonRole",
    "ConsentStatus",
    # Device
    "Device",
    "DeviceDirectionMode",
    "DeviceStatus",
    "DEFAULT_OFFLINE_THRESHOLD_SECONDS",
    "find_device_by_uuid",
    "DeviceCommand",
    "DeviceCommandStatus",
    "DeviceCommandType",
    # AccessLog
    "AccessLog",
    "AccessDirection",
    "AccessOutcome",
    # Snapshot
    "Snapshot",
    # AuditLog
    "AuditLog",
    "AuditAction"]