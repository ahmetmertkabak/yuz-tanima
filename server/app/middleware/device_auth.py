"""
Device REST API — HMAC-SHA256 authentication.

Expected request headers (set by the Pi via
[`edge/app/hmac_signer.py`](../../../edge/app/hmac_signer.py:1)):

    X-Device-Id:  <uuid>
    X-Timestamp:  <unix seconds>
    X-Nonce:      <random hex, 16 bytes>
    X-Signature:  hex( HMAC-SHA256( api_key,
                   f"{method}\\n{path}\\n{timestamp}\\n{nonce}\\n{body_sha256_hex}" ) )

Security checks
---------------
1. All four headers present.
2. `X-Timestamp` within ±tolerance seconds of server clock.
3. `X-Nonce` not used in the last `NONCE_TTL_SECONDS` (replay protection).
4. Device exists, `is_active=True`, belongs to an active School.
5. HMAC signature matches using that device's stored api_key.

The Pi's API key is stored **encrypted-at-rest** (Fernet) on the `Device`
row so the server can recompute the HMAC. Anyone with DB read access alone
cannot impersonate a device because they need the `FACE_ENCRYPTION_KEY` /
the dedicated DEVICE_KEY_ENCRYPTION_KEY (reused for simplicity) from
`/etc/yuz-tanima/server.env`.

On success: `g.device`, `g.school` are attached; tenant middleware is
bypassed so the view can filter explicitly.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from functools import wraps

from flask import current_app, g, jsonify, request

from app.extensions import db
from app.models import School, find_device_by_uuid


NONCE_TTL_SECONDS = 300  # 5 min — server-side memory for replay guard
NONCE_CACHE_MAX = 50_000

# In-memory nonce cache. For multi-worker deployments this moves to Redis
# (replace with a Redis-backed SETNX + EXPIRE when scaling out).
_nonce_cache: dict[str, float] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json_error(status: int, code: str, message: str):
    resp = jsonify(error=code, message=message)
    resp.status_code = status
    return resp


def _gc_nonces(now: float) -> None:
    expired = [k for k, ts in _nonce_cache.items() if now - ts > NONCE_TTL_SECONDS]
    for k in expired:
        _nonce_cache.pop(k, None)


def _check_and_store_nonce(nonce: str, now: float) -> bool:
    """Return True iff the nonce is fresh; False if reused within TTL."""
    if not nonce or not (8 <= len(nonce) <= 64):
        return False
    prev = _nonce_cache.get(nonce)
    if prev is not None and (now - prev) < NONCE_TTL_SECONDS:
        return False
    _nonce_cache[nonce] = now
    if len(_nonce_cache) > NONCE_CACHE_MAX:
        _gc_nonces(now)
    return True


def compute_signature(
    api_key: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> str:
    """Canonical HMAC computation — mirrored by edge/app/hmac_signer.py."""
    body_digest = hashlib.sha256(body or b"").hexdigest()
    canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_digest}"
    return hmac.new(
        api_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------
def device_auth_required(view):
    """Decorator: validate HMAC headers before calling the view."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        device_uuid = request.headers.get("X-Device-Id")
        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        signature = request.headers.get("X-Signature")

        if not (device_uuid and timestamp and nonce and signature):
            return _json_error(401, "missing_auth", "HMAC headers missing")

        try:
            ts = int(timestamp)
        except ValueError:
            return _json_error(401, "bad_timestamp", "X-Timestamp must be int")

        now = time.time()
        tolerance = int(current_app.config.get("DEVICE_API_TIMESTAMP_TOLERANCE", 60))
        if abs(now - ts) > tolerance:
            return _json_error(401, "stale_timestamp", "timestamp out of tolerance")

        if not _check_and_store_nonce(nonce, now):
            return _json_error(401, "replay_detected", "nonce reused")

        # --- Device + school lookup (bypass tenant middleware) ---
        g.bypass_tenant_filter = True
        device = find_device_by_uuid(device_uuid)
        if device is None or not device.is_active:
            return _json_error(
                401, "device_not_found_or_disabled", "unknown/disabled device"
            )

        school = db.session.get(School, device.school_id)
        if school is None or not school.is_active:
            return _json_error(403, "school_inactive", "tenant inactive")

        # --- Recover the plaintext API key ---
        api_key_plain = device.reveal_api_key()
        if not api_key_plain:
            current_app.logger.error(
                "device %s has no decryptable api_key", device.device_uuid
            )
            return _json_error(500, "key_unavailable", "server-side key issue")

        expected = compute_signature(
            api_key=api_key_plain,
            method=request.method,
            path=request.path,
            timestamp=timestamp,
            nonce=nonce,
            body=request.get_data(cache=True),
        )
        if not hmac.compare_digest(expected, signature):
            return _json_error(401, "bad_signature", "HMAC mismatch")

        g.device = device
        g.school = school

        return view(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Test helper — clear the nonce cache between unit tests
# ---------------------------------------------------------------------------
def _reset_nonce_cache_for_tests() -> None:  # pragma: no cover
    _nonce_cache.clear()