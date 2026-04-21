"""
Structured logging for the edge node — JSON-formatted, file + stdout.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

import structlog

from app.config import settings


def configure_logging() -> structlog.BoundLogger:
    """Install handlers + structlog processors. Call once at startup."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # ---- stdlib logging ----
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)

    file_handler = RotatingFileHandler(
        settings.log_dir / "edge.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(log_level)

    formatter = logging.Formatter("%(message)s")
    stdout_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root.addHandler(stdout_handler)
    root.addHandler(file_handler)

    # ---- structlog ----
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("edge")
    logger.info(
        "logging_configured",
        device_id=settings.device_id,
        school_id=settings.school_id,
        log_level=settings.log_level,
    )
    return logger