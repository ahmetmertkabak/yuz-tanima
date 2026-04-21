"""
USB webcam wrapper (OpenCV VideoCapture).

Skeleton — implementation is finished in T6.1–T6.2.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import cv2  # type: ignore[import-not-found]
import numpy as np
import structlog

from app.config import settings


log = structlog.get_logger(__name__)


class Camera:
    """Threaded frame grabber. Always keeps the latest frame in memory."""

    def __init__(
        self,
        index: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        self._index = index if index is not None else settings.camera_index
        self._width = width or settings.camera_width
        self._height = height or settings.camera_height
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._cap = cv2.VideoCapture(self._index)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, settings.camera_fps)

        if not self._cap.isOpened():
            raise RuntimeError(f"Unable to open camera index {self._index}")

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("camera_started", index=self._index, width=self._width, height=self._height)

    def _loop(self) -> None:
        assert self._cap is not None
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if ok:
                with self._lock:
                    self._frame = frame
            else:
                log.warning("camera_read_failed")
                time.sleep(0.1)

    def read(self) -> Optional[np.ndarray]:
        """Return a copy of the latest captured frame, or None if unavailable."""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
        log.info("camera_stopped")