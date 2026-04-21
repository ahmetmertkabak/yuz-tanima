"""
School Admin blueprint.

Mounted under the school subdomain (e.g. `ali-pasa-lisesi.yuztanima.com`).
The tenant middleware in [`app/middleware/tenant.py`](../../middleware/tenant.py:1)
resolves the subdomain → `g.tenant_context.school` before each request.

Sub-modules will grow in Phase 3 (T3.*):
- dashboard  (T3.1-T3.3)
- persons    (T3.4-T3.8)
- access_logs (T3.9)
- reports    (T3.10-T3.13)
- devices    (read-only per-school view)
"""
from flask import Blueprint

bp = Blueprint(
    "school_admin",
    __name__,
    template_folder="../../templates/school_admin",
)

from app.routes.school_admin import (  # noqa: E402, F401
    access_logs,
    dashboard,
    face_enroll,
    persons,
    reports,
)