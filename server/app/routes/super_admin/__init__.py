"""
Super Admin blueprint.

Mounted at `/super/...` URL prefix **and** on the `admin.<BASE_DOMAIN>` host.
Every route enforces `@login_required` + `@super_admin_required`.

Sub-modules:
- dashboard  — overview / stats
- schools    — tenant CRUD
- devices    — global device list + detail + commands
"""
from flask import Blueprint

bp = Blueprint(
    "super_admin",
    __name__,
    template_folder="../../templates/super_admin",
)

# Import sub-modules so their routes are registered on `bp`.
from app.routes.super_admin import dashboard, schools, devices  # noqa: E402, F401