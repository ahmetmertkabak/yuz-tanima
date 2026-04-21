"""
Device-facing REST API, version 1.

Base URL: /api/v1
Auth: HMAC-SHA256 signed requests (see `middleware/device_auth.py`).

Endpoints:
    GET  /ping                             — liveness (no auth)
    POST /device/heartbeat                 — periodic status + telemetry
    GET  /device/config                    — current per-device config
    GET  /device/encodings?since=ISO&...   — incremental face encoding sync
    POST /device/access_log                — batched turnstile events
    POST /device/snapshot                  — multipart image upload
    GET  /device/commands                  — pending remote commands
    POST /device/commands/<id>/ack         — report command result
"""
from flask import Blueprint, jsonify

bp = Blueprint("api_v1", __name__)


@bp.get("/ping")
def ping():
    """Liveness check for devices / monitoring."""
    return jsonify(status="ok", api_version="v1")


# Register sub-route modules
from app.routes.api.v1 import (  # noqa: E402, F401
    access_log,
    device,
    encodings,
    snapshot,
)