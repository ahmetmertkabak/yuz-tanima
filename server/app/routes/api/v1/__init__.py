"""
Device-facing REST API, version 1.

Base URL: /api/v1
Auth: HMAC-SHA256 signed requests (see T5.1).
"""
from flask import Blueprint, jsonify

bp = Blueprint("api_v1", __name__)


@bp.get("/ping")
def ping():
    """Liveness check for devices / monitoring."""
    return jsonify(status="ok", api_version="v1")


# Sub-route modules will be wired in T5.1–T5.6:
# from app.routes.api.v1 import device, encodings, access_log  # noqa