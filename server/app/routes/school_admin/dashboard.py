"""School admin dashboard (minimal stub — expanded in T3.1-T3.3)."""
from datetime import datetime, timedelta

from flask import render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.middleware.auth import school_staff_required
from app.middleware.tenant import require_school_context
from app.models import AccessLog, AccessOutcome, Device, Person, PersonRole
from app.routes.school_admin import bp


@bp.route("/")
@bp.route("/dashboard")
@login_required
@require_school_context
@school_staff_required
def dashboard():
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    total_students = (
        db.session.query(func.count(Person.id))
        .filter(
            Person.role == PersonRole.STUDENT.value,
            Person.is_active.is_(True),
        )
        .scalar()
        or 0
    )
    total_staff = (
        db.session.query(func.count(Person.id))
        .filter(
            Person.role.in_(
                [
                    PersonRole.TEACHER.value,
                    PersonRole.STAFF.value,
                    PersonRole.MANAGER.value]
            ),
            Person.is_active.is_(True),
        )
        .scalar()
        or 0
    )

    entered_today = (
        db.session.query(func.count(func.distinct(AccessLog.person_id)))
        .filter(
            AccessLog.event_at >= today_start,
            AccessLog.outcome == AccessOutcome.GRANTED.value,
            AccessLog.person_id.isnot(None),
        )
        .scalar()
        or 0
    )

    recent_logs = (
        db.session.query(AccessLog)
        .order_by(AccessLog.event_at.desc())
        .limit(15)
        .all()
    )

    devices = db.session.query(Device).order_by(Device.device_name).all()

    return render_template(
        "school_admin/dashboard.html",
        stats={
            "total_students": total_students,
            "total_staff": total_staff,
            "entered_today": entered_today},
        recent_logs=recent_logs,
        devices=devices,
    )