"""
Thin wrapper around `AuditLog.record()` that auto-picks up request context
(current_user, IP, user-agent, request ID) when present.
"""
from __future__ import annotations

from typing import Any, Optional

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import AuditAction, AuditLog


def record_audit(
    action: str | AuditAction,
    *,
    user: Any = None,
    school_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Any = None,
    resource_label: Optional[str] = None,
    details: Optional[dict] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    commit: bool = False,
) -> AuditLog:
    """Record an audit event, auto-filling from Flask context where possible."""
    # Resolve user
    if user is None and has_request_context():
        if getattr(current_user, "is_authenticated", False):
            user = current_user

    # Resolve request metadata
    if has_request_context():
        ip = ip or request.remote_addr
        user_agent = user_agent or request.headers.get("User-Agent", "")
        request_id = request.headers.get("X-Request-Id")
    else:
        request_id = None

    return AuditLog.record(
        action,
        user=user,
        school_id=school_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_label=resource_label,
        details=details,
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
        commit=commit,
    )