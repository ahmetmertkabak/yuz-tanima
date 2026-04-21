"""
Real-time broadcasting helpers.

Each school has its own Socket.IO room (`school_<id>`). Clients join their
school room when connecting. Access logs, device state changes, etc. are
emitted to that room so every connected tab updates instantly.

Server-side usage:
    from app.services.realtime import broadcast_access_log
    broadcast_access_log(access_log)

Client-side (in templates):
    const socket = io("/");  # same-origin
    socket.on("connect", () => socket.emit("join_school"));
    socket.on("access_log", data => { ... });
"""
from __future__ import annotations

from flask import current_app

from app.extensions import socketio


def _school_room(school_id: int) -> str:
    return f"school_{school_id}"


def broadcast_access_log(log) -> None:
    """Fire an `access_log` event into the owning school's room."""
    try:
        payload = {
            "id": log.id,
            "person_id": log.person_id,
            "person_name": log.person_name_cached
            or (log.person.full_name if log.person else None),
            "person_class": log.person_class_cached
            or (log.person.class_name if log.person else None),
            "device_id": log.device_id,
            "device_name": log.device.device_name if log.device else None,
            "event_at": log.event_at.isoformat() if log.event_at else None,
            "direction": log.direction,
            "outcome": log.outcome,
            "is_granted": log.is_granted,
            "confidence": log.confidence}
        socketio.emit(
            "access_log",
            payload,
            to=_school_room(log.school_id),
            namespace="/",
        )
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("broadcast_access_log failed: %s", exc)


def broadcast_device_status(device) -> None:
    """Emit device status change to the school room."""
    try:
        socketio.emit(
            "device_status",
            {
                "id": device.id,
                "device_name": device.device_name,
                "status": device.status,
                "last_heartbeat_at": (
                    device.last_heartbeat_at.isoformat()
                    if device.last_heartbeat_at
                    else None
                )},
            to=_school_room(device.school_id),
            namespace="/",
        )
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("broadcast_device_status failed: %s", exc)


# ---------------------------------------------------------------------------
# Socket.IO event handlers (registered via register_socketio_handlers)
# ---------------------------------------------------------------------------
def register_socketio_handlers() -> None:
    """Attach handlers to the default namespace."""
    from flask import request
    from flask_login import current_user
    from flask_socketio import disconnect, join_room

    @socketio.on("connect")
    def _on_connect():
        if not current_user.is_authenticated:
            disconnect()
            return False
        # Auto-join the school room on connect
        if current_user.school_id:
            join_room(_school_room(current_user.school_id))

    @socketio.on("join_school")
    def _on_join_school():
        if current_user.is_authenticated and current_user.school_id:
            join_room(_school_room(current_user.school_id))