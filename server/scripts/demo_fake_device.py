"""
Pretend-to-be-a-Pi simulator — sends real HMAC-signed API requests to the
running local server so the school admin dashboard comes alive with fresh
heartbeats and access events.

Usage (in a SECOND terminal, after `python run.py`):

    cd server
    source .venv/bin/activate

    export SERVER_URL=http://localhost:5000
    export DEVICE_UUID=<from demo_seed output>
    export API_KEY=<from demo_seed output>

    # Once
    python -m scripts.demo_fake_device heartbeat

    # Continuous (heartbeat every 15s + random access log every 3-8 s)
    python -m scripts.demo_fake_device live
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import secrets
import sys
import time
from datetime import datetime


BASE_URL = os.getenv("SERVER_URL", "http://localhost:5000").rstrip("/")
DEVICE_UUID = os.getenv("DEVICE_UUID", "")
API_KEY = os.getenv("API_KEY", "")

if not DEVICE_UUID or not API_KEY:
    print("❌ Set DEVICE_UUID and API_KEY environment variables first.")
    print("   See demo_seed output.")
    sys.exit(1)


try:
    import requests
except ImportError:
    print("❌ Run:  pip install requests")
    sys.exit(1)


def _sign(method: str, path: str, body: bytes = b"") -> dict:
    ts = str(int(time.time()))
    nonce = secrets.token_hex(16)
    body_hex = hashlib.sha256(body).hexdigest()
    canonical = f"{method.upper()}\n{path}\n{ts}\n{nonce}\n{body_hex}"
    sig = hmac.new(API_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Device-Id": DEVICE_UUID,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "Content-Type": "application/json"}


def heartbeat():
    body = json.dumps(
        {
            "firmware_version": "demo-0.1",
            "persons_cached": random.randint(30, 60),
            "stats": {
                "cpu_percent": round(random.uniform(5, 25), 1),
                "memory_percent": round(random.uniform(30, 60), 1),
                "disk_percent": round(random.uniform(10, 30), 1),
                "cpu_temp_c": round(random.uniform(45, 62), 1),
                "uptime_seconds": random.randint(3600, 86400)}}
    ).encode()
    path = "/api/v1/device/heartbeat"
    r = requests.post(
        f"{BASE_URL}{path}", data=body, headers=_sign("POST", path, body), timeout=10
    )
    r.raise_for_status()
    data = r.json()
    print(
        f"[{datetime.utcnow():%H:%M:%S}] ♥  heartbeat → ok, "
        f"pending_commands={data.get('pending_commands')}, "
        f"tolerance={data['config']['recognition_tolerance']}"
    )


def fetch_encodings():
    path = "/api/v1/device/encodings"
    r = requests.get(
        f"{BASE_URL}{path}", headers=_sign("GET", path), timeout=10
    )
    r.raise_for_status()
    data = r.json()
    return data.get("encodings", [])


def send_access_log(person_server_id: int | None = None, granted: bool = True):
    """
    Send a single access log. If `person_server_id` is None, send an
    "unknown face" event.
    """
    now = datetime.utcnow().isoformat()
    if granted and person_server_id is None:
        raise ValueError("granted log requires a person_server_id")

    entry = {
        "client_id": secrets.token_hex(4),
        "event_at": now,
        "person_server_id": person_server_id,
        "direction": "in",
        "outcome": "granted" if granted else "denied_unknown",
        "confidence": round(random.uniform(0.82, 0.97), 2) if granted else None,
        "distance": round(random.uniform(0.25, 0.45), 3) if granted else None,
        "recognizer_backend": "dlib"}
    body = json.dumps({"logs": [entry]}).encode()
    path = "/api/v1/device/access_log"
    r = requests.post(
        f"{BASE_URL}{path}", data=body, headers=_sign("POST", path, body), timeout=10
    )
    r.raise_for_status()
    data = r.json()
    label = f"person={person_server_id}" if person_server_id else "unknown"
    print(
        f"[{datetime.utcnow():%H:%M:%S}] → access_log {entry['outcome']} ({label}) "
        f"accepted={len(data['accepted'])}"
    )


def live():
    """Heartbeat every 15 s + random access event every 3-8 s."""
    print("📡 Cached encodings fetching…")
    encodings = fetch_encodings()
    person_ids = [e["server_id"] for e in encodings]
    print(f"✓ {len(person_ids)} encodings cached")

    if not person_ids:
        print("⚠  No encodings yet — granted events will be skipped")

    last_heartbeat = 0.0
    try:
        while True:
            now = time.time()
            if now - last_heartbeat > 15:
                heartbeat()
                last_heartbeat = now

            # 90% granted, 10% unknown
            if person_ids and random.random() > 0.1:
                send_access_log(random.choice(person_ids), granted=True)
            else:
                send_access_log(None, granted=False)

            time.sleep(random.uniform(3, 8))
    except KeyboardInterrupt:
        print("\n👋 stopped")


def pull_commands():
    path = "/api/v1/device/commands"
    r = requests.get(
        f"{BASE_URL}{path}", headers=_sign("GET", path), timeout=10
    )
    r.raise_for_status()
    data = r.json()
    for cmd in data.get("commands", []):
        print(f"  ↘ command id={cmd['id']} type={cmd['command_type']} status={cmd['status']}")
        # Auto-ack immediately as if the Pi executed it
        ack_path = f"/api/v1/device/commands/{cmd['id']}/ack"
        ack_body = json.dumps({"status": "completed", "response": {"note": "simulated"}}).encode()
        r2 = requests.post(
            f"{BASE_URL}{ack_path}",
            data=ack_body,
            headers=_sign("POST", ack_path, ack_body),
            timeout=10,
        )
        r2.raise_for_status()
        print(f"    ✓ acked → completed")


COMMANDS = {
    "heartbeat": heartbeat,
    "live": live,
    "commands": pull_commands,
    "encodings": lambda: print(f"✓ {len(fetch_encodings())} encodings")}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "heartbeat"
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"Usage: python -m scripts.demo_fake_device {{{'|'.join(COMMANDS)}}}")
        sys.exit(1)
    fn()