"""
Face enrollment endpoint.

Flow
----
Front-end captures 3-5 frames via `getUserMedia`, sends them as base64 JPEGs
in JSON. Backend:
  1. Decodes each frame
  2. Runs face detection + encoding (requires `face_recognition` at import time)
  3. Averages the encodings that passed quality checks
  4. Stores the encrypted encoding on the Person row
  5. Optionally uploads the best-quality frame to S3/MinIO for review

Prerequisites in production:
    pip install face-recognition dlib numpy Pillow

The server-side encoding computation is CPU-intensive. For multi-school
deployments, move this into a Celery task (T4.5 follow-up).
"""
from __future__ import annotations

import base64
import binascii
import io
from typing import Sequence

from flask import (
    abort,
    current_app,
    jsonify,
    request,
)
from flask_login import current_user, login_required

from app.extensions import db
from app.middleware.auth import school_admin_required
from app.middleware.tenant import require_school_context
from app.models import AuditAction, Person
from app.routes.school_admin import bp
from app.services.audit import record_audit


MIN_GOOD_FRAMES = 3
MAX_FRAMES = 8


# ---------------------------------------------------------------------------
# Lazy imports — heavy deps only loaded on first use
# ---------------------------------------------------------------------------
def _load_face_lib():
    """Import numpy + face_recognition on demand (keeps boot light)."""
    try:
        import numpy as np  # noqa: F401
        import face_recognition  # type: ignore

        return face_recognition
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("face_recognition unavailable: %s", exc)
        return None


def _decode_base64_image(data_url: str):
    """Return a PIL.Image or raise ValueError."""
    from PIL import Image

    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    try:
        raw = base64.b64decode(data_url, validate=False)
    except binascii.Error as exc:
        raise ValueError(f"base64 decode failed: {exc}")
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return img


def _pil_to_numpy(img):
    import numpy as np

    return np.asarray(img, dtype=np.uint8)


def _compute_encoding(frame_array) -> tuple[object | None, str | None]:
    """Return (encoding or None, error message or None) for a single frame."""
    face_recognition = _load_face_lib()
    if face_recognition is None:
        return None, "face_recognition library not installed on server"

    locations = face_recognition.face_locations(frame_array, model="hog")
    if not locations:
        return None, "Yüz bulunamadı."
    if len(locations) > 1:
        return None, "Birden fazla yüz var."
    encodings = face_recognition.face_encodings(frame_array, known_face_locations=locations)
    if not encodings:
        return None, "Encoding üretilemedi."
    return encodings[0], None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@bp.route("/persons/<int:person_id>/face", methods=["POST"])
@login_required
@require_school_context
@school_admin_required
def person_enroll_face(person_id: int):
    """Accept JSON `{ "frames": ["data:image/jpeg;base64,..."] }` and store encoding."""
    import numpy as np

    person = db.session.get(Person, person_id) or abort(404)

    payload = request.get_json(silent=True) or {}
    frames: Sequence[str] = payload.get("frames") or []
    if not frames:
        return jsonify(error="no_frames"), 400

    frames = list(frames)[:MAX_FRAMES]

    good_encodings = []
    per_frame_errors = []

    for idx, data_url in enumerate(frames):
        try:
            img = _decode_base64_image(data_url)
        except ValueError as exc:
            per_frame_errors.append({"frame": idx, "error": str(exc)})
            continue
        arr = _pil_to_numpy(img)

        enc, err = _compute_encoding(arr)
        if enc is None:
            per_frame_errors.append({"frame": idx, "error": err})
        else:
            good_encodings.append(enc)

    if len(good_encodings) < MIN_GOOD_FRAMES:
        return (
            jsonify(
                error="insufficient_quality",
                message=(
                    f"En az {MIN_GOOD_FRAMES} temiz kare gerekli — "
                    f"{len(good_encodings)}/{len(frames)} alındı."
                ),
                frame_errors=per_frame_errors,
            ),
            422,
        )

    averaged = np.mean(np.vstack(good_encodings), axis=0).astype(np.float32)
    person.set_face_encoding(averaged)

    record_audit(
        AuditAction.FACE_ENROLLED,
        user=current_user,
        school_id=person.school_id,
        resource_type="person",
        resource_id=person.id,
        resource_label=person.full_name,
        details={"frame_count": len(good_encodings), "dim": int(averaged.shape[0])},
    )
    db.session.commit()

    return jsonify(
        ok=True,
        frames_used=len(good_encodings),
        frame_errors=per_frame_errors,
    )


@bp.route("/persons/<int:person_id>/face", methods=["DELETE"])
@login_required
@require_school_context
@school_admin_required
def person_delete_face(person_id: int):
    person = db.session.get(Person, person_id) or abort(404)
    person.clear_face_encoding()

    record_audit(
        AuditAction.FACE_DELETED,
        user=current_user,
        school_id=person.school_id,
        resource_type="person",
        resource_id=person.id,
        resource_label=person.full_name,
    )
    db.session.commit()
    return jsonify(ok=True)