"""Device sync + control endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import g, jsonify, request

from app.extensions import db, limiter
from app.middleware import device_auth_required
from app.models import DeviceCommand, DeviceCommandStatus
from app.routes.api.v1 import bp
from app.services.realtime import broadcast_device_status


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------
@bp.route("/device/heartbeat", methods=["POST"])
@limiter.limit("120 per minute")
@device_auth_required
def heartbeat():
    payload = request.get_json(silent=True) or {}

    device = g.device
    device.touch_heartbeat(
        ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        firmware=payload.get("firmware_version"),
        stats=payload.get("stats") or {},
    )
    persons_cached = payload.get("persons_cached")
    if isinstance(persons_cached, int):
        device.persons_cached = persons_cached

    db.session.commit()

    broadcast_device_status(device)

    # Let the Pi know whether there are commands waiting for it.
    pending_count = (
        db.session.query(DeviceCommand)
        .filter(
            DeviceCommand.device_id == device.id,
            DeviceCommand.status.in_(
                [
                    DeviceCommandStatus.PENDING.value,
                    DeviceCommandStatus.SENT.value]
            ),
        )
        .count()
    )

    return jsonify(
        ok=True,
        server_time=datetime.utcnow().isoformat(),
        pending_commands=pending_count,
        config={
            "recognition_tolerance": (
                device.recognition_tolerance or g.school.recognition_tolerance
            ),
            "turnstile_pulse_ms": device.turnstile_pulse_ms,
            "direction_mode": device.direction_mode},
    )


# ---------------------------------------------------------------------------
# Config (same info as heartbeat response, but standalone)
# ---------------------------------------------------------------------------
@bp.route("/device/config", methods=["GET"])
@limiter.limit("30 per minute")
@device_auth_required
def device_config():
    device = g.device
    school = g.school
    return jsonify(
        recognition_tolerance=device.recognition_tolerance or school.recognition_tolerance,
        turnstile_pulse_ms=device.turnstile_pulse_ms,
        direction_mode=device.direction_mode,
        timezone=school.timezone,
        firmware_target=None,  # set when OTA rollout is active (T7.x)
    )


# ---------------------------------------------------------------------------
# Commands: pull + ack
# ---------------------------------------------------------------------------
@bp.route("/device/commands", methods=["GET"])
@limiter.limit("60 per minute")
@device_auth_required
def list_pending_commands():
    device = g.device
    now = datetime.utcnow()

    commands = (
        db.session.query(DeviceCommand)
        .filter(
            DeviceCommand.device_id == device.id,
            DeviceCommand.status.in_(
                [
                    DeviceCommandStatus.PENDING.value,
                    DeviceCommandStatus.SENT.value]
            ),
        )
        .order_by(DeviceCommand.created_at)
        .limit(20)
        .all()
    )

    serialized = []
    for cmd in commands:
        # Expire stale commands so we don't re-queue reboots from last week
        if cmd.expires_at and cmd.expires_at < now:
            cmd.status = DeviceCommandStatus.EXPIRED.value
            cmd.completed_at = now
            continue
        if cmd.status == DeviceCommandStatus.PENDING.value:
            cmd.mark_sent()
        serialized.append(cmd.to_dict())
    db.session.commit()

    return jsonify(commands=serialized)


@bp.route("/device/commands/<int:command_id>/ack", methods=["POST"])
@limiter.limit("120 per minute")
@device_auth_required
def ack_command(command_id: int):
    device = g.device
    cmd = (
        db.session.query(DeviceCommand)
        .filter(
            DeviceCommand.id == command_id,
            DeviceCommand.device_id == device.id,
        )
        .first()
    )
    if cmd is None:
        return jsonify(error="not_found"), 404

    body = request.get_json(silent=True) or {}
    status = body.get("status", "completed")
    response = body.get("response")
    error_message = body.get("error")

    if status == "failed":
        cmd.mark_failed(error_message or "device reported failure")
    else:
        cmd.mark_completed(response)

    db.session.commit()
    return jsonify(ok=True)