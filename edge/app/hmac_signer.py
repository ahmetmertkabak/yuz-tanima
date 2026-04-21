"""
HMAC-SHA256 request signing for device → VPS API calls.

Header layout (sent with every API request):

    X-Device-Id:       <uuid>
    X-Timestamp:       <unix seconds>
    X-Nonce:           <random hex, 16 bytes>
    X-Signature:       hex( HMAC-SHA256( api_key, canonical_string ) )

    canonical_string = "{method}\n{path}\n{timestamp}\n{nonce}\n{sha256_body_hex}"

The server validates:
  1. Timestamp within ±DEVICE_API_TIMESTAMP_TOLERANCE seconds
  2. Nonce not seen in the last N minutes (replay protection)
  3. Signature matches using the stored api_key for device_id
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Mapping

from app.config import settings


def _body_digest(body: bytes | None) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def build_signed_headers(
    method: str,
    path: str,
    body: bytes | None = None,
) -> Mapping[str, str]:
    """Return headers dict to attach to a requests.Session call."""
    method = method.upper()
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    body_hex = _body_digest(body)

    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hex}"
    signature = hmac.new(
        settings.api_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-Device-Id": settings.device_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json"}