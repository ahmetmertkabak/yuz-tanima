"""
Tenant (multi-school) request middleware.

Responsibilities
----------------
1. **Resolve the tenant.** For each incoming request we inspect the hostname
   and attach the corresponding `School` to `flask.g`. The result lives in
   `g.tenant_context` (a `TenantContext` instance).

2. **Auto-filter ORM queries.** Every SELECT touching a tenant-scoped model
   (listed in `app.models.base.TENANT_MODELS`) gets an implicit
   `school_id == g.tenant_context.school_id` predicate injected via SQLAlchemy
   `with_loader_criteria`.

   Super-admins can opt out with `g.bypass_tenant_filter = True`.

3. **Guard helpers.** `@require_school_context` rejects requests that reached
   a school-scoped route without a resolved tenant.

Subdomain conventions (see [`app/config.py`](../config.py:1)):
    - `<SUPER_ADMIN_SUBDOMAIN>.<BASE_DOMAIN>`  → super-admin, no tenant
    - `api.<BASE_DOMAIN>`                      → device API, no tenant (HMAC
      middleware resolves device/school separately)
    - `<school>.<BASE_DOMAIN>`                 → school admin panel
    - `localhost` / dev hostnames              → tenant comes from the
      `X-Tenant-Subdomain` header or `?tenant=` query param
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Optional

from flask import Flask, Response, abort, current_app, g, jsonify, request
from sqlalchemy import event
from sqlalchemy.orm import Query, Session, with_loader_criteria

from app.extensions import db
from app.models.base import TENANT_MODELS
from app.models.school import School


# ---------------------------------------------------------------------------
# Context object
# ---------------------------------------------------------------------------
@dataclass
class TenantContext:
    """Resolved tenant info for the current request."""

    subdomain: Optional[str]          # e.g. "ali-pasa-lisesi" (None for super/api/dev-root)
    school: Optional[School]          # SQLAlchemy instance, None for super-admin routes
    is_super_admin_host: bool         # True when host == admin.<BASE_DOMAIN>
    is_api_host: bool                 # True when host == api.<BASE_DOMAIN>
    # Cache the primary key at resolution time so we never trigger a lazy-load
    # inside the `do_orm_execute` event handler (would cause infinite recursion).
    school_id: Optional[int] = None


def get_tenant_context() -> TenantContext:
    """Return the resolved tenant context (never raises — may be empty)."""
    ctx = getattr(g, "tenant_context", None)
    if ctx is None:
        ctx = TenantContext(
            subdomain=None,
            school=None,
            is_super_admin_host=False,
            is_api_host=False,
        )
        g.tenant_context = ctx
    return ctx


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_tenant_middleware(app: Flask) -> None:
    """Install `before_request` hooks + the SQLAlchemy auto-filter."""
    app.before_request(_resolve_tenant)
    _install_auto_filter()


# ---------------------------------------------------------------------------
# Host / subdomain parsing
# ---------------------------------------------------------------------------
_RESERVED_SUBDOMAINS = {"www", "api", "cdn", "static"}


def _resolve_tenant() -> Optional[Response]:
    """Populate `g.tenant_context` for the current request."""
    base_domain = current_app.config["BASE_DOMAIN"].lower()
    super_sub = current_app.config["SUPER_ADMIN_SUBDOMAIN"].lower()
    host = (request.host or "").split(":")[0].lower().strip()

    ctx = TenantContext(
        subdomain=None,
        school=None,
        is_super_admin_host=False,
        is_api_host=False,
    )

    # --- Super-admin host ---
    if host == f"{super_sub}.{base_domain}":
        ctx.is_super_admin_host = True
        g.tenant_context = ctx
        return None

    # --- Device API host (tenant resolved later via api_key) ---
    if host == f"api.{base_domain}" or request.path.startswith("/api/"):
        ctx.is_api_host = True
        g.tenant_context = ctx
        return None

    # --- School subdomain ---
    subdomain: Optional[str] = None
    if host.endswith(f".{base_domain}"):
        candidate = host[: -(len(base_domain) + 1)]
        if candidate and candidate not in _RESERVED_SUBDOMAINS:
            subdomain = candidate

    # --- Dev / localhost fallback: header or query param ---
    if subdomain is None and (
        host in ("localhost", "127.0.0.1", "0.0.0.0") or host == base_domain
    ):
        subdomain = (
            request.headers.get("X-Tenant-Subdomain")
            or request.args.get("tenant")
        )
        if subdomain:
            subdomain = subdomain.lower()

    ctx.subdomain = subdomain
    if subdomain:
        ctx.school = _fetch_school(subdomain)
        if ctx.school is None:
            current_app.logger.warning("tenant_not_found subdomain=%s", subdomain)
            g.tenant_context = ctx
            return _tenant_not_found_response(subdomain)
        if not ctx.school.is_active:
            g.tenant_context = ctx
            return _tenant_inactive_response(ctx.school)
        ctx.school_id = ctx.school.id

    g.tenant_context = ctx
    return None


def _fetch_school(subdomain: str) -> Optional[School]:
    """Bypass the tenant filter when looking up the tenant itself."""
    g.bypass_tenant_filter = True
    try:
        return (
            db.session.query(School)
            .filter(School.subdomain == subdomain)
            .first()
        )
    finally:
        g.bypass_tenant_filter = False


def _tenant_not_found_response(subdomain: str):
    if _wants_json():
        return jsonify(error="tenant_not_found", subdomain=subdomain), 404
    return (f"Okul bulunamadı: {subdomain}", 404)


def _tenant_inactive_response(school: School):
    if _wants_json():
        return (
            jsonify(
                error="tenant_inactive",
                subdomain=school.subdomain,
                subscription_status=school.subscription_status,
            ),
            403,
        )
    return ("Okul hesabı aktif değil.", 403)


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    return "application/json" in (request.accept_mimetypes.best or "")


# ---------------------------------------------------------------------------
# Route decorator
# ---------------------------------------------------------------------------
def require_school_context(view):
    """Deny access if the request has no resolved school tenant."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        ctx = get_tenant_context()
        if ctx.school is None:
            if _wants_json():
                return jsonify(error="tenant_required"), 400
            abort(400)
        return view(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# SQLAlchemy auto-filter
# ---------------------------------------------------------------------------
_AUTO_FILTER_INSTALLED = False


def _install_auto_filter() -> None:
    """Attach a `do_orm_execute` event listener once per process."""
    global _AUTO_FILTER_INSTALLED
    if _AUTO_FILTER_INSTALLED:
        return
    event.listen(Session, "do_orm_execute", _apply_tenant_filter)
    _AUTO_FILTER_INSTALLED = True


def _apply_tenant_filter(state) -> None:
    """Inject `school_id == g.tenant_context.school_id` into SELECT queries."""
    # Only SELECTs (never INSERT/UPDATE/DELETE).
    if not state.is_select:
        return

    # Caller explicitly opted out (e.g. super-admin, device auth pre-resolution).
    if getattr(g, "bypass_tenant_filter", False):
        return

    # Prevent re-entry when SQLAlchemy re-compiles the same statement internally.
    if state.execution_options.get("_tenant_filter_applied"):
        return

    ctx = getattr(g, "tenant_context", None)
    if ctx is None or ctx.school is None:
        return

    sid = ctx.school_id
    for model in TENANT_MODELS:
        state.statement = state.statement.options(
            with_loader_criteria(
                model,
                lambda cls, _sid=sid: cls.school_id == _sid,
                include_aliases=True,
                track_closure_variables=False,
            )
        )

    # Mark this statement so recursive compiles don't re-apply the same options
    state.statement = state.statement.execution_options(_tenant_filter_applied=True)


# ---------------------------------------------------------------------------
# Convenience helper used by services that need a tenant-scoped query
# ---------------------------------------------------------------------------
def tenant_scoped_query(model) -> Query:
    """Shortcut: `Person.query` with the school_id filter made explicit."""
    ctx = get_tenant_context()
    q = db.session.query(model)
    if ctx.school_id is not None and hasattr(model, "school_id"):
        q = q.filter(model.school_id == ctx.school_id)
    return q