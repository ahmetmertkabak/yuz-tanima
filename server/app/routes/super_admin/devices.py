"""Super-admin → Devices (global list, detail, remote commands)."""
from datetime import datetime, timedelta

from flask import (
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.forms import DeviceCreateForm, DeviceEditForm
from app.middleware.auth import super_admin_required
from app.models import (
    AccessLog,
    AuditAction,
    DEFAULT_OFFLINE_THRESHOLD_SECONDS,
    Device,
    DeviceCommand,
    DeviceCommandStatus,
    DeviceCommandType,
    DeviceStatus,
    School,
)
from app.routes.super_admin import bp
from app.services.audit import record_audit


@bp.route("/devices")
@login_required
@super_admin_required
def devices_list():
    q = (request.args.get("q") or "").strip()
    school_id = request.args.get("school_id", type=int)
    status_filter = request.args.get("status") or ""
    page = max(int(request.args.get("page") or 1), 1)
    per_page = 25

    query = db.session.query(Device).join(School, Device.school_id == School.id)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Device.device_name.ilike(like),
                Device.location.ilike(like),
                Device.device_uuid.ilike(like),
                School.name.ilike(like),
                School.subdomain.ilike(like),
            )
        )
    if school_id:
        query = query.filter(Device.school_id == school_id)

    total = query.count()
    devices = (
        query.order_by(Device.last_heartbeat_at.desc().nulls_last())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Python-side status filter (derived)
    if status_filter:
        devices = [d for d in devices if d.status == status_filter]

    schools = db.session.query(School).order_by(School.name).all()

    return render_template(
        "super_admin/devices/list.html",
        devices=devices,
        schools=schools,
        q=q,
        school_id=school_id,
        status=status_filter,
        statuses=[s.value for s in DeviceStatus],
        page=page,
        per_page=per_page,
        total=total,
    )


@bp.route("/devices/new", methods=["GET", "POST"])
@login_required
@super_admin_required
def devices_new():
    form = DeviceCreateForm()
    form.school_id.choices = [
        (s.id, f"{s.name} ({s.subdomain})")
        for s in db.session.query(School)
        .filter(School.is_active.is_(True))
        .order_by(School.name)
        .all()
    ]

    if form.validate_on_submit():
        school = db.session.get(School, form.school_id.data) or abort(400)
        device = Device(
            school_id=school.id,
            device_name=form.device_name.data.strip(),
            location=form.location.data or None,
            description=form.description.data or None,
            direction_mode=form.direction_mode.data,
            turnstile_pulse_ms=form.turnstile_pulse_ms.data,
            recognition_tolerance=form.recognition_tolerance.data or None,
            is_active=True,
        )
        plaintext = device.set_api_key()
        db.session.add(device)
        db.session.flush()

        record_audit(
            AuditAction.DEVICE_CREATED,
            user=current_user,
            school_id=school.id,
            resource_type="device",
            resource_id=device.id,
            resource_label=device.device_name,
            details={"device_uuid": device.device_uuid},
        )
        db.session.commit()

        flash(
            "Cihaz oluşturuldu. API key'i aşağıdan kopyalayın — bir daha "
            "gösterilmeyecek.",
            "success",
        )
        # Show one-time API key page
        return render_template(
            "super_admin/devices/created.html",
            device=device,
            api_key=plaintext,
        )

    return render_template("super_admin/devices/new.html", form=form)


@bp.route("/devices/<int:device_id>")
@login_required
@super_admin_required
def device_detail(device_id: int):
    device = db.session.get(Device, device_id) or abort(404)

    # Last 24h access counters
    since = datetime.utcnow() - timedelta(hours=24)
    access_24h = (
        db.session.query(AccessLog)
        .filter(AccessLog.device_id == device_id, AccessLog.event_at >= since)
        .count()
    )
    last_accesses = (
        db.session.query(AccessLog)
        .filter(AccessLog.device_id == device_id)
        .order_by(AccessLog.event_at.desc())
        .limit(20)
        .all()
    )
    pending_commands = (
        db.session.query(DeviceCommand)
        .filter(
            DeviceCommand.device_id == device_id,
            DeviceCommand.status.in_(
                [
                    DeviceCommandStatus.PENDING.value,
                    DeviceCommandStatus.SENT.value]
            ),
        )
        .order_by(DeviceCommand.created_at.desc())
        .all()
    )
    recent_commands = (
        db.session.query(DeviceCommand)
        .filter(DeviceCommand.device_id == device_id)
        .order_by(DeviceCommand.created_at.desc())
        .limit(15)
        .all()
    )

    return render_template(
        "super_admin/devices/detail.html",
        device=device,
        access_24h=access_24h,
        last_accesses=last_accesses,
        pending_commands=pending_commands,
        recent_commands=recent_commands,
        command_types=DeviceCommandType.values(),
    )


@bp.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
@login_required
@super_admin_required
def device_edit(device_id: int):
    device = db.session.get(Device, device_id) or abort(404)
    form = DeviceEditForm(obj=device)
    if form.validate_on_submit():
        form.populate_obj(device)
        record_audit(
            AuditAction.DEVICE_UPDATED,
            user=current_user,
            school_id=device.school_id,
            resource_type="device",
            resource_id=device.id,
            resource_label=device.device_name,
        )
        db.session.commit()
        flash("Cihaz güncellendi.", "success")
        return redirect(url_for("super_admin.device_detail", device_id=device.id))

    return render_template(
        "super_admin/devices/edit.html", form=form, device=device
    )


@bp.route("/devices/<int:device_id>/rotate-key", methods=["POST"])
@login_required
@super_admin_required
def device_rotate_key(device_id: int):
    device = db.session.get(Device, device_id) or abort(404)
    plaintext = device.set_api_key()
    record_audit(
        AuditAction.DEVICE_API_KEY_ROTATED,
        user=current_user,
        school_id=device.school_id,
        resource_type="device",
        resource_id=device.id,
        resource_label=device.device_name,
    )
    db.session.commit()
    flash("Yeni API key üretildi. Bu ekrandan kopyalayın.", "warning")
    return render_template(
        "super_admin/devices/created.html",
        device=device,
        api_key=plaintext,
    )


@bp.route("/devices/<int:device_id>/commands", methods=["POST"])
@login_required
@super_admin_required
def device_command_enqueue(device_id: int):
    device = db.session.get(Device, device_id) or abort(404)
    command_type = request.form.get("command_type")
    if command_type not in DeviceCommandType.values():
        flash("Geçersiz komut türü.", "danger")
        return redirect(url_for("super_admin.device_detail", device_id=device.id))

    cmd = DeviceCommand(
        school_id=device.school_id,
        device_id=device.id,
        issued_by_user_id=current_user.id,
        command_type=command_type,
        payload=None,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.session.add(cmd)

    action_map = {
        DeviceCommandType.REBOOT.value: AuditAction.DEVICE_REBOOTED,
        DeviceCommandType.UPDATE_FIRMWARE.value: AuditAction.DEVICE_UPDATE_PUSHED}
    record_audit(
        action_map.get(command_type, AuditAction.DEVICE_UPDATED),
        user=current_user,
        school_id=device.school_id,
        resource_type="device_command",
        resource_id=None,
        resource_label=f"{device.device_name} / {command_type}",
        details={"command_type": command_type},
    )
    db.session.commit()
    flash(f"“{command_type}” komutu kuyruğa alındı.", "info")
    return redirect(url_for("super_admin.device_detail", device_id=device.id))


@bp.route("/devices/<int:device_id>/disable", methods=["POST"])
@login_required
@super_admin_required
def device_disable(device_id: int):
    device = db.session.get(Device, device_id) or abort(404)
    device.is_active = False
    record_audit(
        AuditAction.DEVICE_UPDATED,
        user=current_user,
        school_id=device.school_id,
        resource_type="device",
        resource_id=device.id,
        resource_label=device.device_name,
        details={"action": "disable"},
    )
    db.session.commit()
    flash("Cihaz devre dışı bırakıldı.", "warning")
    return redirect(url_for("super_admin.device_detail", device_id=device.id))