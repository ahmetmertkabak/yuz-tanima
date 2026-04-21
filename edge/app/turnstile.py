"""
Turnstile relay controller.

Default behaviour is **fail-safe**: on any error, the relay stays de-energized
(turnstile locked). Full implementation in T6.5.
"""
from __future__ import annotations

import threading
import time

import structlog

from app.config import settings


log = structlog.get_logger(__name__)


try:  # pragma: no cover — only available on the Pi
    from gpiozero import LED  # type: ignore
    _HAS_GPIO = True
except Exception:
    _HAS_GPIO = False


class Turnstile:
    """Controls the relay wired to the turnstile unlock input."""

    def __init__(self, pin: int | None = None, pulse_ms: int | None = None) -> None:
        self._pin = pin or settings.gpio_relay_pin
        self._pulse_ms = pulse_ms or settings.relay_pulse_ms
        self._lock = threading.Lock()
        self._relay = LED(self._pin) if _HAS_GPIO else None
        if not _HAS_GPIO:
            log.warning("gpio_unavailable_simulation_mode", pin=self._pin)

    def open_briefly(self) -> None:
        """Pulse the relay for `pulse_ms` milliseconds (non-blocking)."""
        threading.Thread(target=self._pulse, daemon=True).start()

    def _pulse(self) -> None:
        with self._lock:
            try:
                if self._relay:
                    self._relay.on()
                log.info("turnstile_pulse_on", pin=self._pin, pulse_ms=self._pulse_ms)
                time.sleep(self._pulse_ms / 1000.0)
            except Exception as exc:
                log.error("turnstile_pulse_error", error=str(exc))
            finally:
                if self._relay:
                    try:
                        self._relay.off()
                    except Exception:  # pragma: no cover
                        pass
                log.info("turnstile_pulse_off")

    def shutdown(self) -> None:
        if self._relay:
            try:
                self._relay.off()
                self._relay.close()
            except Exception:  # pragma: no cover
                pass