"""
Edge node entry point.

Orchestrates:
- camera capture
- face recognition loop (T6.3)
- turnstile control (T6.5)
- background sync (heartbeat / encodings / logs) via APScheduler (T6.9)
- OTA update checks (T7)

Run via systemd — see [`../systemd/yuz-tanima-edge.service`](../systemd/yuz-tanima-edge.service:1).
"""
from __future__ import annotations

import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.camera import Camera
from app.config import settings
from app.local_db import init_db
from app.logging_setup import configure_logging
from app.sync_client import sync_client
from app.turnstile import Turnstile


log = configure_logging()


class EdgeApp:
    """Top-level orchestrator."""

    def __init__(self) -> None:
        self.camera = Camera()
        self.turnstile = Turnstile()
        self.scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
        self._stopping = False

    # ---- lifecycle ----
    def start(self) -> None:
        log.info("edge_starting", device_id=settings.device_id, version="0.1.0")
        init_db()

        self.camera.start()
        self._install_scheduled_jobs()
        self.scheduler.start()
        self._install_signal_handlers()

        log.info("edge_started")
        self._recognition_loop()

    def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        log.info("edge_stopping")
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
        self.camera.stop()
        self.turnstile.shutdown()
        log.info("edge_stopped")

    # ---- loops ----
    def _recognition_loop(self) -> None:
        """Placeholder — real implementation comes in T6.3–T6.4."""
        while not self._stopping:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.05)
                continue
            # TODO (T6.3): run recognizer.identify(frame) and act on results
            time.sleep(0.1)

    def _install_scheduled_jobs(self) -> None:
        self.scheduler.add_job(
            self._heartbeat_job,
            "interval",
            seconds=settings.heartbeat_interval,
            id="heartbeat",
            max_instances=1,
        )
        self.scheduler.add_job(
            self._encoding_sync_job,
            "interval",
            seconds=settings.encoding_sync_interval,
            id="encoding_sync",
            max_instances=1,
        )
        self.scheduler.add_job(
            self._log_sync_job,
            "interval",
            seconds=settings.log_sync_interval,
            id="log_sync",
            max_instances=1,
        )

    # ---- scheduled jobs (stubs) ----
    def _heartbeat_job(self) -> None:
        payload = {
            "device_id": settings.device_id,
            "school_id": settings.school_id,
            "ts": int(time.time())}
        ok = sync_client.send_heartbeat(payload)
        log.debug("heartbeat_result", ok=ok)

    def _encoding_sync_job(self) -> None:
        log.debug("encoding_sync_placeholder")  # T6.9

    def _log_sync_job(self) -> None:
        log.debug("log_sync_placeholder")  # T6.9

    # ---- signals ----
    def _install_signal_handlers(self) -> None:
        def _handle(signum, _frame):
            log.info("signal_received", signum=signum)
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, _handle)
        signal.signal(signal.SIGINT, _handle)


def main() -> None:
    app = EdgeApp()
    try:
        app.start()
    except Exception:
        log.exception("edge_fatal_error")
        app.stop()
        raise


if __name__ == "__main__":
    main()