"""
Incremental encoding sync.

Pi requests `GET /api/v1/device/encodings?since=<iso>`; server returns every
Person whose `face_updated_at` >= since AND `consent_status=granted` AND
`is_active=true` scoped to the device's school.

Encodings travel over TLS but **in plaintext numpy bytes**, base64-encoded.
The server decrypts Fernet on the way out; the Pi does not hold the
FACE_ENCRYPTION_KEY.
"""
from __future__ import annotations

import base64
from datetime import datetime

from flask import g, jsonify, request

from app.extensions import db, limiter
from app.middleware import device_auth_required
from app.models import ConsentStatus, Person
from app.routes.api.v1 import bp


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


@bp.route("/device/encodings", methods=["GET"])
@limiter.limit("60 per minute")
@device_auth_required
def list_encodings():
    since = _parse_since(request.args.get("since"))
    limit = min(int(request.args.get("limit", 500)), 1000)
    cursor = request.args.get("cursor", type=int)

    school_id = g.school.id
    query = (
        db.session.query(Person)
        .filter(
            Person.school_id == school_id,
            Person.is_active.is_(True),
            Person.consent_status == ConsentStatus.GRANTED.value,
            Person.face_encoding_encrypted.isnot(None),
        )
    )
    if since:
        query = query.filter(Person.face_updated_at >= since)
    if cursor:
        query = query.filter(Person.id > cursor)

    query = query.order_by(Person.id).limit(limit + 1)
    rows = query.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    # Also find IDs that have been deactivated / consent-revoked since `since`
    # so the Pi can remove them from its local cache.
    deletions_query = db.session.query(Person.id).filter(
        Person.school_id == school_id,
        (Person.is_active.is_(False))
        | (Person.consent_status != ConsentStatus.GRANTED.value)
        | (Person.face_encoding_encrypted.is_(None)),
    )
    if since:
        # Only recently touched rows matter for the delete list
        deletions_query = deletions_query.filter(Person.updated_at >= since)
    deletions = [r[0] for r in deletions_query.all()]

    encodings = []
    for person in rows:
        encoding = person.get_face_encoding()
        if encoding is None:
            continue
        encodings.append(
            {
                "server_id": person.id,
                "person_no": person.person_no,
                "full_name": person.full_name,
                "role": person.role,
                "class_name": person.class_name,
                "is_active": person.is_active,
                "encoding_b64": base64.b64encode(encoding.tobytes()).decode("ascii"),
                "encoding_dim": int(encoding.shape[0]),
                "encoding_dtype": str(encoding.dtype),
                "face_updated_at": (
                    person.face_updated_at.isoformat()
                    if person.face_updated_at
                    else None
                )}
        )

    return jsonify(
        encodings=encodings,
        deletions=deletions,
        has_more=has_more,
        next_cursor=(rows[-1].id if has_more and rows else None),
        server_time=datetime.utcnow().isoformat(),
    )