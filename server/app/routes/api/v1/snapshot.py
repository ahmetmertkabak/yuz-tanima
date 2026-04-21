"""
Snapshot upload endpoint.

The Pi sends a multipart/form-data request with:
    file:               JPEG/PNG bytes
    captured_at:        ISO timestamp (optional, defaults to now)
    access_log_id:      optional int — links to a preceding AccessLog
    best_match_person:  optional int — the Pi's best guess
    best_match_conf:    optional float

HMAC signature covers the HTTP method + path + timestamp + nonce +
sha256(body). Flask's `request.get_data(cache=True)` returns the complete
multipart body bytes so the HMAC still matches.
"""
from __future__ import annotations

from datetime import datetime

from flask import g, jsonify, request

from app.extensions import db, limiter
from app.middleware import device_auth_required
from app.models import AccessLog, Snapshot
from app.routes.api.v1 import bp
from app.services.storage import StorageError, store_snapshot


MAX_IMAGE_BYTES = 6 * 1024 * 1024  # 6 MB


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


@bp.route("/device/snapshot", methods=["POST"])
@limiter.limit("30 per minute")
@device_auth_required
def upload_snapshot():
    file = request.files.get("file")
    if file is None:
        return jsonify(error="missing_file"), 400

    payload = file.read(MAX_IMAGE_BYTES + 1)
    if len(payload) > MAX_IMAGE_BYTES:
        return jsonify(error="file_too_large", max=MAX_IMAGE_BYTES), 413

    content_type = file.mimetype or "image/jpeg"
    school = g.school
    device = g.device

    try:
        key, size = store_snapshot(school.subdomain, payload, content_type)
    except StorageError as exc:
        return jsonify(error="storage_failed", message=str(exc)), 502

    access_log_id = request.form.get("access_log_id", type=int)
    best_match_id = request.form.get("best_match_person", type=int)
    best_match_conf = request.form.get("best_match_conf", type=float)

    snapshot = Snapshot(
        school_id=school.id,
        device_id=device.id,
        image_path=key,
        image_content_type=content_type,
        image_size_bytes=size,
        captured_at=_parse_ts(request.form.get("captured_at")),
        best_match_person_id=best_match_id,
        best_match_confidence=best_match_conf,
    )
    db.session.add(snapshot)
    db.session.flush()

    # Optional link back to an AccessLog
    if access_log_id:
        log = (
            db.session.query(AccessLog)
            .filter(
                AccessLog.id == access_log_id,
                AccessLog.school_id == school.id,
            )
            .first()
        )
        if log:
            log.snapshot_id = snapshot.id
            log.snapshot_path = key

    db.session.commit()

    return jsonify(
        ok=True,
        snapshot_id=snapshot.id,
        image_path=key,
        size=size,
    )