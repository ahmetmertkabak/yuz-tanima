"""Request-time middleware (tenant resolution, auth/RBAC, rate-limit)."""
from app.middleware.auth import (
    can_manage_devices,
    can_manage_persons,
    has_any_role,
    must_belong_to_current_school,
    roles_required,
    school_admin_required,
    school_staff_required,
    super_admin_required,
)
from app.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    register_tenant_middleware,
    require_school_context,
    tenant_scoped_query,
)

__all__ = [
    # tenant
    "TenantContext",
    "get_tenant_context",
    "register_tenant_middleware",
    "require_school_context",
    "tenant_scoped_query",
    # auth / RBAC
    "roles_required",
    "super_admin_required",
    "school_admin_required",
    "school_staff_required",
    "must_belong_to_current_school",
    "can_manage_persons",
    "can_manage_devices",
    "has_any_role"]