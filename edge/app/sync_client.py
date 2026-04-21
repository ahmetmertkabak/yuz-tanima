"""
Sync client — talks to the VPS REST API.

Full implementation in T6.9. This stub provides the public interface so
other modules (main orchestrator, scheduler) can already import it.
"""
from __future__ import annotations

import json
from typing import Any

import requests
import structlog

from app.config import settings
from app.hmac_signer import build_signed_headers


log = structlog.get_logger(__name__)


class SyncClient:
    """Thin HTTP client wrapping the device REST API."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._base = settings.server_url.rstrip("/")

    # ---- low-level ----
    def _request(
        self,
        method: str,
        path: str,
        json_body: Any | None = None,
    ) -> requests.Response:
        url = f"{self._base}{path}"
        body_bytes = (
            json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            if json_body is not None
            else b""
        )
        headers = dict(build_signed_headers(method, path, body_bytes))

        log.debug("sync_request", method=method, path=path, body_size=len(body_bytes))
        resp = self._session.request(
            method,
            url,
            data=body_bytes,
            headers=headers,
            timeout=settings.api_timeout,
        )
        return resp

    # ---- high-level (stubs, filled in T6.9) ----
    def send_heartbeat(self, payload: dict) -> bool:
        """POST /api/v1/device/heartbeat"""
        try:
            resp = self._request("POST", "/api/v1/device/heartbeat", payload)
            return resp.ok
        except requests.RequestException as exc:
            log.warning("heartbeat_failed", error=str(exc))
            return False

    def fetch_encodings(self, since: str | None = None) -> list[dict] | None:
        """GET /api/v1/device/encodings?since=<iso8601>"""
        path = "/api/v1/device/encodings"
        if since:
            path += f"?since={since}"
        try:
            resp = self._request("GET", path)
            if resp.ok:
                return resp.json().get("encodings", [])
        except requests.RequestException as exc:
            log.warning("fetch_encodings_failed", error=str(exc))
        return None

    def submit_access_logs(self, batch: list[dict]) -> bool:
        """POST /api/v1/device/access_log (batched)"""
        try:
            resp = self._request("POST", "/api/v1/device/access_log", {"logs": batch})
            return resp.ok
        except requests.RequestException as exc:
            log.warning("submit_logs_failed", error=str(exc))
            return False


sync_client = SyncClient()