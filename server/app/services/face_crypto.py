"""
Biometric data encryption helpers.

Face encodings are stored **encrypted at rest** in the DB using Fernet
(AES-128-CBC + HMAC-SHA256). The key is loaded from `FACE_ENCRYPTION_KEY`
config value, which itself comes from the environment.

Encodings travel between server ↔ edge as raw `numpy` float arrays
(128-dim for dlib, 512-dim for ArcFace). We convert to bytes for storage.

Usage:
    ciphertext = FaceCrypto.encrypt_array(encoding_array)
    arr = FaceCrypto.decrypt_array(ciphertext)
"""
from __future__ import annotations

import io
from functools import lru_cache

import numpy as np
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


class FaceCryptoError(Exception):
    """Raised when encryption / decryption of a face encoding fails."""


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = current_app.config.get("FACE_ENCRYPTION_KEY")
    if not key:
        raise FaceCryptoError(
            "FACE_ENCRYPTION_KEY is not configured. Generate one with:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:  # pragma: no cover — invalid key format
        raise FaceCryptoError(f"Invalid FACE_ENCRYPTION_KEY: {exc}")


class FaceCrypto:
    """Stateless helper class (static-style)."""

    # ---- numpy ↔ bytes ----
    @staticmethod
    def array_to_bytes(arr: np.ndarray) -> bytes:
        """Serialize a float encoding vector to compact bytes."""
        if arr is None:
            raise FaceCryptoError("Cannot serialize a None encoding")
        arr = np.ascontiguousarray(arr, dtype=np.float32)
        buf = io.BytesIO()
        np.save(buf, arr, allow_pickle=False)
        return buf.getvalue()

    @staticmethod
    def bytes_to_array(data: bytes) -> np.ndarray:
        buf = io.BytesIO(data)
        arr = np.load(buf, allow_pickle=False)
        return arr.astype(np.float32)

    # ---- encrypt / decrypt bytes ----
    @staticmethod
    def encrypt(plaintext: bytes) -> bytes:
        return _get_fernet().encrypt(plaintext)

    @staticmethod
    def decrypt(ciphertext: bytes) -> bytes:
        try:
            return _get_fernet().decrypt(ciphertext)
        except InvalidToken as exc:
            raise FaceCryptoError("Face encoding decryption failed") from exc

    # ---- high-level: array ↔ ciphertext ----
    @classmethod
    def encrypt_array(cls, arr: np.ndarray) -> bytes:
        return cls.encrypt(cls.array_to_bytes(arr))

    @classmethod
    def decrypt_array(cls, ciphertext: bytes) -> np.ndarray:
        return cls.bytes_to_array(cls.decrypt(ciphertext))