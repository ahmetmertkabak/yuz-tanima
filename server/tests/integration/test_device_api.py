"""
End-to-end tests for the device REST API.

Covers:
- HMAC auth: accepts valid signatures, rejects missing/bad/stale/replayed
- Heartbeat updates device state
- Encoding sync returns only granted + active persons
- Access log ingestion persists rows and returns accepted/rejected breakdown
- Commands flow (pending → sent → ack)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime

import numpy as np
import pytest

from app.extensions import db
from app.middleware.device_auth import _reset_nonce_cache_for_tests
from app.models import (
    AccessDirection,
    AccessLog,
    AccessOutcome,
    ConsentStatus,
    Device,
    DeviceCommand,
    DeviceCommandStatus,
    DeviceCommandType,
)


# ---------------------------------------------------------------------------
# HMAC signing helper (mirrors edge/app/hmac_signer.py)
# ---------------------------------------------------------------------------
def _sign(
    api_key: str,
    method: str,
    path: str,
    body: bytes = b"",
    device_uuid: str = "",
    ts_offset: int = 0,
    nonce: str = None,
) -> dict:
    ts = str(int(time.time()) + ts_offset)
    nonce = nonce or hashlib.sha256(f"{ts}{path}".encode()).hexdigest()[:32]
    body_hex = hashlib.sha256(body).hexdigest()
    canonical = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{body_hex}"
    sig = hmac.new(api_key.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Device-Id": device_uuid,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "Content-Type": "application/json"}


@pytest.fixture(autouse=True)
def _reset_nonces():
    _reset_nonce_cache_for_tests()
    yield
    _reset_nonce_cache_for_tests()


@pytest.fixture()
def device_with_key(db, make_device):
    """Provision a device and return (device, plaintext_key)."""
    device, plain = make_device()
    db.session.commit()
    return device, plain


# ---------------------------------------------------------------------------
# HMAC auth — negative paths
# ---------------------------------------------------------------------------
class TestHmacAuth:
    def test_missing_headers(self, client):
        res = client.post("/api/v1/device/heartbeat", json={})
        assert res.status_code == 401
        assert res.get_json()["error"] == "missing_auth"

    def test_stale_timestamp(self, client, device_with_key):
        device, key = device_with_key
        headers = _sign(
            key,
            "POST",
            "/api/v1/device/heartbeat",
            b"{}",
            device_uuid=device.device_uuid,
            ts_offset=-500,  # 500 s in the past
        )
        res = client.post("/api/v1/device/heartbeat", data="{}", headers=headers)
        assert res.status_code == 401
        assert res.get_json()["error"] == "stale_timestamp"

    def test_bad_signature(self, client, device_with_key):
        device, _ = device_with_key
        headers = _sign(
            "wrong-key",
            "POST",
            "/api/v1/device/heartbeat",
            b"{}",
            device_uuid=device.device_uuid,
        )
        res = client.post("/api/v1/device/heartbeat", data="{}", headers=headers)
        assert res.status_code == 401
        assert res.get_json()["error"] == "bad_signature"

    def test_unknown_device(self, client, device_with_key):
        _, key = device_with_key
        headers = _sign(
            key,
            "POST",
            "/api/v1/device/heartbeat",
            b"{}",
            device_uuid="00000000-0000-0000-0000-000000000000",
        )
        res = client.post("/api/v1/device/heartbeat", data="{}", headers=headers)
        assert res.status_code == 401
        assert res.get_json()["error"] == "device_not_found_or_disabled"

    def test_replay_blocked(self, client, device_with_key):
        device, key = device_with_key
        body = b"{}"
        headers = _sign(
            key, "POST", "/api/v1/device/heartbeat", body,
            device_uuid=device.device_uuid,
            nonce="a" * 32,
        )
        first = client.post("/api/v1/device/heartbeat", data=body, headers=headers)
        assert first.status_code == 200

        # Re-use the exact same headers
        second = client.post("/api/v1/device/heartbeat", data=body, headers=headers)
        assert second.status_code == 401
        assert second.get_json()["error"] == "replay_detected"


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------
class TestHeartbeat:
    def test_updates_device_state(self, client, db, device_with_key):
        device, key = device_with_key
        body = json.dumps(
            {
                "firmware_version": "0.2.0",
                "persons_cached": 123,
                "stats": {"cpu_percent": 10.0}}
        ).encode()
        headers = _sign(
            key, "POST", "/api/v1/device/heartbeat", body,
            device_uuid=device.device_uuid,
        )
        res = client.post("/api/v1/device/heartbeat", data=body, headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["ok"] is True
        assert "config" in data
        assert data["config"]["turnstile_pulse_ms"] == device.turnstile_pulse_ms

        db.session.refresh(device)
        assert device.firmware_version == "0.2.0"
        assert device.persons_cached == 123
        assert device.is_online()


# ---------------------------------------------------------------------------
# Encodings sync
# ---------------------------------------------------------------------------
class TestEncodings:
    def test_returns_only_granted_active(self, client, db, device_with_key, make_person):
        device, key = device_with_key

        # Three persons in the same school
        enrolled = make_person(
            school=device.school,
            full_name="Has Face",
            consent_status=ConsentStatus.GRANTED.value,
            is_active=True,
        )
        enrolled.set_face_encoding(np.zeros(128, dtype=np.float32))

        _pending = make_person(
            school=device.school,
            full_name="Pending Consent",
            consent_status=ConsentStatus.PENDING.value,
        )

        _inactive = make_person(
            school=device.school,
            full_name="Inactive",
            consent_status=ConsentStatus.GRANTED.value,
            is_active=False,
        )
        db.session.commit()

        headers = _sign(
            key, "GET", "/api/v1/device/encodings", b"",
            device_uuid=device.device_uuid,
        )
        res = client.get("/api/v1/device/encodings", headers=headers)
        assert res.status_code == 200
        data = res.get_json()

        ids = [e["server_id"] for e in data["encodings"]]
        assert enrolled.id in ids
        assert len(ids) == 1  # only the enrolled+granted+active one


# ---------------------------------------------------------------------------
# Access log ingestion
# ---------------------------------------------------------------------------
class TestAccessLogs:
    def test_happy_path(self, client, db, device_with_key, make_person):
        device, key = device_with_key
        person = make_person(school=device.school)
        db.session.commit()

        payload = {
            "logs": [
                {
                    "client_id": "l-1",
                    "event_at": datetime.utcnow().isoformat(),
                    "person_server_id": person.id,
                    "direction": AccessDirection.IN.value,
                    "outcome": AccessOutcome.GRANTED.value,
                    "confidence": 0.91,
                    "recognizer_backend": "dlib"},
                {
                    "client_id": "l-2",
                    "person_server_id": None,
                    "direction": AccessDirection.UNKNOWN.value,
                    "outcome": AccessOutcome.DENIED_UNKNOWN.value}]
        }
        body = json.dumps(payload).encode()
        headers = _sign(
            key, "POST", "/api/v1/device/access_log", body,
            device_uuid=device.device_uuid,
        )
        res = client.post("/api/v1/device/access_log", data=body, headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["accepted"]) == 2
        assert data["rejected"] == []

        logs = db.session.query(AccessLog).filter_by(device_id=device.id).all()
        assert len(logs) == 2
        granted = [log for log in logs if log.is_granted]
        assert len(granted) == 1
        assert granted[0].person_id == person.id

    def test_invalid_direction_rejected(self, client, device_with_key):
        device, key = device_with_key
        payload = {"logs": [{"direction": "sideways", "outcome": "granted"}]}
        body = json.dumps(payload).encode()
        headers = _sign(
            key, "POST", "/api/v1/device/access_log", body,
            device_uuid=device.device_uuid,
        )
        res = client.post("/api/v1/device/access_log", data=body, headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["accepted"] == []
        assert data["rejected"][0]["error"] == "bad_direction"


# ---------------------------------------------------------------------------
# Commands pull + ack
# ---------------------------------------------------------------------------
class TestCommands:
    def test_pull_marks_sent(self, client, db, device_with_key):
        device, key = device_with_key
        cmd = DeviceCommand(
            school_id=device.school_id,
            device_id=device.id,
            command_type=DeviceCommandType.REBOOT.value,
        )
        db.session.add(cmd)
        db.session.commit()

        headers = _sign(
            key, "GET", "/api/v1/device/commands", b"",
            device_uuid=device.device_uuid,
        )
        res = client.get("/api/v1/device/commands", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["commands"]) == 1

        db.session.refresh(cmd)
        assert cmd.status == DeviceCommandStatus.SENT.value
        assert cmd.attempts == 1

    def test_ack_completes(self, client, db, device_with_key):
        device, key = device_with_key
        cmd = DeviceCommand(
            school_id=device.school_id,
            device_id=device.id,
            command_type=DeviceCommandType.RELOAD_ENCODINGS.value,
            status=DeviceCommandStatus.SENT.value,
        )
        db.session.add(cmd)
        db.session.commit()

        path = f"/api/v1/device/commands/{cmd.id}/ack"
        body = json.dumps({"status": "completed", "response": {"ok": True}}).encode()
        headers = _sign(
            key, "POST", path, body, device_uuid=device.device_uuid
        )
        res = client.post(path, data=body, headers=headers)
        assert res.status_code == 200

        db.session.refresh(cmd)
        assert cmd.status == DeviceCommandStatus.COMPLETED.value
        assert cmd.completed_at is not None