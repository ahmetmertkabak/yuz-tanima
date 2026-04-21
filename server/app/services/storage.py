"""
Object storage helper (S3 / MinIO).

Snapshots are stored under a per-school prefix:
    s3://<bucket>/<school_subdomain>/snapshots/YYYY/MM/DD/<uuid>.jpg

If `S3_ENDPOINT_URL` is empty (= no S3 configured), a filesystem fallback
under `UPLOAD_FOLDER/<school>/snapshots/...` is used so dev works without
MinIO.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path

from flask import current_app


class StorageError(Exception):
    pass


def _make_key(school_subdomain: str, prefix: str, ext: str = "jpg") -> str:
    now = datetime.utcnow()
    return (
        f"{school_subdomain}/{prefix}/{now:%Y/%m/%d}/"
        f"{uuid.uuid4().hex}.{ext}"
    )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def store_snapshot(
    school_subdomain: str,
    file_bytes: bytes,
    content_type: str = "image/jpeg",
) -> tuple[str, int]:
    """Store snapshot bytes; return (storage_key, size)."""
    key = _make_key(school_subdomain, "snapshots", _ext_for(content_type))
    if current_app.config.get("S3_ENDPOINT_URL"):
        _upload_to_s3(key, file_bytes, content_type)
    else:
        _write_local(key, file_bytes)
    return key, len(file_bytes)


def _ext_for(content_type: str) -> str:
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    return "jpg"


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def _upload_to_s3(key: str, data: bytes, content_type: str) -> None:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:  # pragma: no cover
        raise StorageError("boto3 missing") from exc

    cfg = current_app.config
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=cfg.get("S3_ACCESS_KEY"),
        aws_secret_access_key=cfg.get("S3_SECRET_KEY"),
        region_name=cfg.get("S3_REGION"),
    )
    bucket = cfg["S3_BUCKET_NAME"]
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError(f"S3 put_object failed: {exc}") from exc


def _write_local(key: str, data: bytes) -> None:
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    target = upload_root / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)