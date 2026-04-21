"""
RBAC decorators + helpers.

These compose with Flask-Login's `@login_required`. Apply after it, e.g.:

    @bp.route("/some-protected-thing")
    @login_required
    @super_admin_required
    def view(): ...
"""
from __future__ import annotations

from functools import wraps
from typing import Iterable

from flask import abort, jsonify, redirect, request, url_for
from flask_login import current_user

from app.models import UserRole


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    return "application/json" in (request.accept_mimetypes.best or "")


def _deny(code: int, message: str):
    if _wants_json():
        return jsonify(error="forbidden", message=message), code
    abort(code)


# ---------------------------------------------------------------------------
# Basic role decorators
# ---------------------------------------------------------------------------
def roles_required(*roles: str):
    """Allow access only if `current_user.role` is in `roles`."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))
            if current_user.role not in roles:
                return _deny(403, "insufficient role")
            return view(*args, **kwargs)

        return wrapper

    return decorator


def super_admin_required(view):
    return roles_required(UserRole.SUPER_ADMIN.value)(view)


def school_admin_required(view):
    return roles_required(
        UserRole.SCHOOL_ADMIN.value,
        UserRole.SUPER_ADMIN.value,
    )(view)


def school_staff_required(view):
    """Any authenticated user with a school context."""
    return roles_required(
        UserRole.SCHOOL_ADMIN.value,
        UserRole.SCHOOL_STAFF.value,
        UserRole.VIEWER.value,
        UserRole.SUPER_ADMIN.value,
    )(view)


# ---------------------------------------------------------------------------
# Composite guard: role + same-tenant check
# ---------------------------------------------------------------------------
def must_belong_to_current_school(view):
    """Reject if the logged-in user's school_id differs from the request tenant."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

        from app.middleware.tenant import get_tenant_context

        ctx = get_tenant_context()
        # super_admin passes through
        if current_user.is_super_admin():
            return view(*args, **kwargs)

        if ctx.school_id != current_user.school_id:
            return _deny(403, "cross-tenant access denied")
        return view(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Permission helpers (mirror helpers on User)
# ---------------------------------------------------------------------------
def can_manage_persons() -> bool:
    return current_user.is_authenticated and current_user.can_manage_persons()


def can_manage_devices() -> bool:
    return current_user.is_authenticated and current_user.can_manage_devices()


def has_any_role(*roles: Iterable[str]) -> bool:
    return current_user.is_authenticated and current_user.role in roles