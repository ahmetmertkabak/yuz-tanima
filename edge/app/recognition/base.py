"""
Abstract recognizer interface.

Concrete implementations in:
- [`dlib_recognizer.py`](dlib_recognizer.py:1)       — Phase 1 (face_recognition)
- [`insightface_recognizer.py`](insightface_recognizer.py:1) — Phase 2 (ArcFace)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class RecognitionResult:
    """Outcome of a single recognition attempt on a frame."""

    person_server_id: int | None  # None = unknown face
    confidence: float             # 0.0–1.0, higher = more certain
    distance: float               # raw backend distance (smaller = better)
    bbox: tuple[int, int, int, int] | None  # x, y, w, h in frame coordinates


class Recognizer(ABC):
    """Strategy interface for a face recognition backend."""

    @abstractmethod
    def load_persons(self, persons: Sequence[dict]) -> None:
        """Load persons + encodings into the backend.

        Each dict: {"server_id": int, "encoding": np.ndarray, "is_active": bool}
        """

    @abstractmethod
    def identify(self, frame: np.ndarray) -> list[RecognitionResult]:
        """Run detection + identification on a BGR frame."""

    @abstractmethod
    def encode_face(self, frame: np.ndarray) -> np.ndarray | None:
        """Return the face encoding for a single face in the frame, or None."""