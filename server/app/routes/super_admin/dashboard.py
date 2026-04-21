"""Super-admin dashboard."""
from datetime import datetime, timedelta

from flask import g, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.middleware.auth import super_admin_required
from app.models import (
    AccessLog,
    AuditLog,
    DEFAULT_OFFLINE_THRESHOLD_SECONDS,
    Device,
    Person,
    School,
    SubscriptionStatus,
)
from app.routes.super_admin import bp


@bp.route("/")
@bp.route("/dashboard")
@login_required
@super_admin_required
def dashboard():
    g.bypass_tenant_filter = True  # we need to see everyone

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    online_cutoff = now - timedelta(seconds=DEFAULT_OFFLINE_THRESHOLD_SECONDS)

    # ---- Totals ----
    total_schools = db.session.query(func.count(School.id)).scalar() or 0
    active_schools = (
        db.session.query(func.count(School.id))
        .filter(School.is_active.is_(True))
        .scalar()
        or 0
    )
    total_persons = db.session.query(func.count(Person.id)).scalar() or 0
    total_devices = db.session.query(func.count(Device.id)).scalar() or 0

    online_devices = (
        db.session.query(func.count(Device.id))
        .filter(
            Device.is_active.is_(True),
            Device.last_heartbeat_at.isnot(None),
            Device.last_heartbeat_at >= online_cutoff,
        )
        .scalar()
        or 0
    )
    offline_devices = max(total_devices - online_devices, 0)

    # ---- Today's access count ----
    access_today = (
        db.session.query(func.count(AccessLog.id))
        .filter(AccessLog.event_at >= today_start)
        .scalar()
        or 0
    )

    # ---- Devices offline > threshold ----
    stale_devices = (
        db.session.query(Device)
        .filter(
            Device.is_active.is_(True),
            (
                (Device.last_heartbeat_at.is_(None))
                | (Device.last_heartbeat_at < online_cutoff)
            ),
        )
        .order_by(Device.last_heartbeat_at.asc().nulls_first())
        .limit(10)
        .all()
    )

    # ---- Subscriptions expiring in the next 14 days ----
    expiring_soon_cutoff = now + timedelta(days=14)
    expiring_schools = (
        db.session.query(School)
        .filter(
            School.is_active.is_(True),
            School.subscription_status.in_(
                [
                    SubscriptionStatus.TRIAL.value,
                    SubscriptionStatus.ACTIVE.value]
            ),
            (
                (School.subscription_expires_at.isnot(None))
                & (School.subscription_expires_at <= expiring_soon_cutoff)
            )
            | (
                (School.trial_expires_at.isnot(None))
                & (School.trial_expires_at <= expiring_soon_cutoff)
            ),
        )
        .order_by(
            School.subscription_expires_at.asc().nulls_last(),
            School.trial_expires_at.asc().nulls_last(),
        )
        .limit(10)
        .all()
    )

    # ---- Recent audit events (top-level) ----
    recent_audit = (
        db.session.query(AuditLog)
        .order_by(AuditLog.event_at.desc())
        .limit(15)
        .all()
    )

    return render_template(
        "super_admin/dashboard.html",
        stats={
            "total_schools": total_schools,
            "active_schools": active_schools,
            "total_persons": total_persons,
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "access_today": access_today},
        stale_devices=stale_devices,
        expiring_schools=expiring_schools,
        recent_audit=recent_audit,
    )