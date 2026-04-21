# Device REST API — v1

Base URL (production): `https://<base-domain>/api/v1`
Base URL (dev):        `http://localhost:5000/api/v1`

All device endpoints (everything except `/ping`) require HMAC authentication.

---

## 🔐 Authentication — HMAC-SHA256

Every authenticated request MUST include these headers:

| Header         | Description |
|----------------|-------------|
| `X-Device-Id`  | UUID issued by the SuperAdmin when the device was provisioned |
| `X-Timestamp`  | Unix epoch seconds at request time; server tolerates ±60 s |
| `X-Nonce`      | Random 16-byte hex string (32 chars); must be unique for 5 min |
| `X-Signature`  | `hex(HMAC-SHA256(api_key, canonical))` |

Canonical string:

```
<METHOD>\n<PATH>\n<TIMESTAMP>\n<NONCE>\n<SHA256_HEX(body)>
```

- `METHOD` is uppercase (`POST`, `GET`, …)
- `PATH` is the request path **without** query string (e.g. `/api/v1/device/heartbeat`)
- `SHA256_HEX(body)` is `sha256("")` = `e3b0c4…` for empty bodies

Reference implementation in [`edge/app/hmac_signer.py`](../edge/app/hmac_signer.py:1).

### Replay protection

Nonces are remembered server-side for 5 minutes. A nonce that is reused
within that window causes HTTP 401 `replay_detected`.

### Error responses

All authentication errors return JSON:

```json
{ "error": "<code>", "message": "<human readable>" }
```

Possible codes: `missing_auth`, `bad_timestamp`, `stale_timestamp`,
`replay_detected`, `device_not_found_or_disabled`, `school_inactive`,
`bad_signature`, `key_unavailable`.

---

## Endpoints

### `GET /ping`

Liveness. No authentication.

```json
{ "status": "ok", "api_version": "v1" }
```

---

### `POST /device/heartbeat`

Must be called every ~30 s. Returns server time + current config + count
of pending remote commands.

Request body (optional):

```json
{
  "firmware_version": "0.1.0",
  "persons_cached": 412,
  "stats": {
    "cpu_percent": 12.3,
    "memory_percent": 48.1,
    "disk_percent": 14.7,
    "cpu_temp_c": 55.2,
    "uptime_seconds": 86400
  }
}
```

Response:

```json
{
  "ok": true,
  "server_time": "2026-04-21T10:30:00",
  "pending_commands": 0,
  "config": {
    "recognition_tolerance": 0.55,
    "turnstile_pulse_ms": 500,
    "direction_mode": "bidirectional"
  }
}
```

Rate limit: 120/min.

---

### `GET /device/config`

Standalone config fetch (same data as heartbeat response, no state update).

Response:

```json
{
  "recognition_tolerance": 0.55,
  "turnstile_pulse_ms": 500,
  "direction_mode": "bidirectional",
  "timezone": "Europe/Istanbul",
  "firmware_target": null
}
```

Rate limit: 30/min.

---

### `GET /device/encodings?since=<ISO>&limit=500&cursor=<id>`

Incremental sync of face encodings.

- `since`  (optional) — only persons whose `face_updated_at >= since`
- `limit`  (default 500, max 1000)
- `cursor` — paginate by passing the last `server_id` seen

Response:

```json
{
  "encodings": [
    {
      "server_id": 42,
      "person_no": "STU0001",
      "full_name": "Ali Veli",
      "role": "student",
      "class_name": "9-A",
      "is_active": true,
      "encoding_b64": "<base64 of raw float32 bytes>",
      "encoding_dim": 128,
      "encoding_dtype": "float32",
      "face_updated_at": "2026-04-20T12:00:00"
    }
  ],
  "deletions": [15, 22],
  "has_more": false,
  "next_cursor": null,
  "server_time": "2026-04-21T10:30:00"
}
```

- `deletions` — persons that **lost** their encoding since `since`
  (deactivated, consent revoked, or face cleared). Pi must remove them
  from its local cache.
- When `has_more=true`, call again with `cursor=next_cursor`.

Rate limit: 60/min.

---

### `POST /device/access_log`

Batched ingestion of turnstile events.

Request body:

```json
{
  "logs": [
    {
      "client_id": "local-42",
      "event_at": "2026-04-21T10:30:05",
      "person_server_id": 42,
      "direction": "in",
      "outcome": "granted",
      "confidence": 0.92,
      "distance": 0.33,
      "recognizer_backend": "dlib",
      "snapshot_path": null,
      "details": {}
    }
  ]
}
```

- Direction: `in` / `out` / `unknown`
- Outcome: `granted` / `denied_unknown` / `denied_access` /
  `denied_schedule` / `denied_inactive` / `denied_no_consent` / `error`
- `person_server_id`: integer from `GET /device/encodings`, or `null`
  for unknown faces.
- `client_id` (optional): opaque string returned in the response so the
  Pi can mark only accepted rows as synced.

Response:

```json
{
  "accepted": [{"index": 0, "client_id": "local-42"}],
  "rejected": [],
  "server_time": "2026-04-21T10:30:06"
}
```

Max batch size: 500. Rate limit: 60/min.

Every accepted row is **broadcast in real-time** to the school's
Socket.IO room.

---

### `POST /device/snapshot`

`multipart/form-data` upload.

Form fields:

| Field              | Type   | Notes |
|--------------------|--------|-------|
| `file`             | file   | JPEG/PNG, max 6 MB |
| `captured_at`      | string | ISO-8601; defaults to now |
| `access_log_id`    | int    | optional link back to an AccessLog |
| `best_match_person`| int    | optional `person.id` guess |
| `best_match_conf`  | float  | 0.0–1.0 |

Response:

```json
{
  "ok": true,
  "snapshot_id": 73,
  "image_path": "ali-pasa-lisesi/snapshots/2026/04/21/9f3a....jpg",
  "size": 23456
}
```

Rate limit: 30/min.

---

### `GET /device/commands`

Return up to 20 pending commands, marking them as `sent`.

Response:

```json
{
  "commands": [
    {
      "id": 17,
      "school_id": 1,
      "device_id": 3,
      "command_type": "reload_encodings",
      "payload": null,
      "status": "sent",
      "attempts": 1,
      "response": null,
      "error_message": null,
      "created_at": "2026-04-21T10:25:00",
      "sent_at": "2026-04-21T10:30:05",
      "completed_at": null
    }
  ]
}
```

Command types: `reboot`, `reload_encodings`, `force_sync`,
`update_firmware`, `disable`, `enable`, `test_turnstile`.

Rate limit: 60/min.

---

### `POST /device/commands/<id>/ack`

Report the outcome of a command.

Request body:

```json
{
  "status": "completed",       // or "failed"
  "response": { "note": "OK" },
  "error": null
}
```

Response:

```json
{ "ok": true }
```

---

## 📋 Error Codes (business level)

| HTTP | Code | When |
|------|------|------|
| 400  | `bad_shape`         | Malformed body item |
| 400  | `empty_batch`       | `logs` array missing or empty |
| 400  | `bad_direction`     | Invalid `direction` |
| 400  | `bad_outcome`       | Invalid `outcome` |
| 400  | `missing_file`      | Snapshot upload without file |
| 401  | (see auth section)  | HMAC failures |
| 403  | `school_inactive`   | Tenant disabled |
| 404  | `not_found`         | Command ID unknown |
| 413  | `batch_too_large`   | > 500 logs in one batch |
| 413  | `file_too_large`    | Snapshot > 6 MB |
| 429  | `rate_limited`      | Per-minute limit hit |
| 500  | `key_unavailable`   | Server cannot decrypt device API key |
| 502  | `storage_failed`    | S3/MinIO upload failed |

---

## 🧪 Testing

Use [`edge/app/hmac_signer.build_signed_headers()`](../edge/app/hmac_signer.py:31)
during local development:

```python
from edge.app.hmac_signer import build_signed_headers
headers = build_signed_headers("POST", "/api/v1/device/heartbeat", b'{}')
requests.post("http://localhost:5000/api/v1/device/heartbeat",
              headers=headers, data="{}")
```

A minimal Postman collection and integration tests will be published in
`docs/api-postman.json` during Phase 5 (T5.11).