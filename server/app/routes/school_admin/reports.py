"""
Reports — daily, monthly, absentees, late arrivals.

All queries are tenant-scoped by the middleware.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.middleware.auth import school_staff_required
from app.middleware.tenant import require_school_context
from app.models import AccessLog, AccessOutcome, Person, PersonRole
from app.routes.school_admin import bp


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------
@bp.route("/reports")
@login_required
@require_school_context
@school_staff_required
def reports_index():
    return render_template("school_admin/reports/index.html")


# ---------------------------------------------------------------------------
# Daily
# ---------------------------------------------------------------------------
@bp.route("/reports/daily")
@login_required
@require_school_context
@school_staff_required
def report_daily():
    date_str = request.args.get("date")
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
    except ValueError:
        day = None
    if day is None:
        now = datetime.utcnow()
        day = datetime(now.year, now.month, now.day)

    day_end = day + timedelta(days=1)

    first_entry_q = (
        db.session.query(
            AccessLog.person_id.label("person_id"),
            func.min(AccessLog.event_at).label("first_entry"),
            func.max(AccessLog.event_at).label("last_entry"),
            func.count(AccessLog.id).label("event_count"),
        )
        .filter(
            AccessLog.event_at >= day,
            AccessLog.event_at < day_end,
            AccessLog.outcome == AccessOutcome.GRANTED.value,
            AccessLog.person_id.isnot(None),
        )
        .group_by(AccessLog.person_id)
        .subquery()
    )

    present_rows = (
        db.session.query(Person, first_entry_q)
        .join(first_entry_q, first_entry_q.c.person_id == Person.id)
        .order_by(first_entry_q.c.first_entry)
        .all()
    )

    # Late threshold (default 08:30)
    late_after = time(8, 30)
    late = [r for r in present_rows if r.first_entry.time() > late_after]

    total_active = (
        db.session.query(func.count(Person.id))
        .filter(Person.is_active.is_(True))
        .scalar()
        or 0
    )
    total_present = len(present_rows)
    total_absent = max(total_active - total_present, 0)

    return render_template(
        "school_admin/reports/daily.html",
        day=day,
        rows=present_rows,
        late=late,
        totals={
            "active": total_active,
            "present": total_present,
            "absent": total_absent},
    )


# ---------------------------------------------------------------------------
# Absent today
# ---------------------------------------------------------------------------
@bp.route("/reports/absent")
@login_required
@require_school_context
@school_staff_required
def report_absent():
    date_str = request.args.get("date")
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
    except ValueError:
        day = None
    if day is None:
        now = datetime.utcnow()
        day = datetime(now.year, now.month, now.day)
    day_end = day + timedelta(days=1)

    role = request.args.get("role") or ""
    class_name = request.args.get("class_name") or ""

    present_ids = (
        db.session.query(AccessLog.person_id)
        .filter(
            AccessLog.event_at >= day,
            AccessLog.event_at < day_end,
            AccessLog.outcome == AccessOutcome.GRANTED.value,
            AccessLog.person_id.isnot(None),
        )
        .distinct()
        .subquery()
    )

    absent_q = db.session.query(Person).filter(
        Person.is_active.is_(True),
        ~Person.id.in_(present_ids),
    )
    if role in PersonRole.values():
        absent_q = absent_q.filter(Person.role == role)
    else:
        # Default to students for absentee lists
        absent_q = absent_q.filter(Person.role == PersonRole.STUDENT.value)
    if class_name:
        absent_q = absent_q.filter(Person.class_name == class_name)

    absent_q = absent_q.order_by(Person.class_name, Person.full_name)
    absent = absent_q.all()

    classes = [
        c[0]
        for c in db.session.query(Person.class_name)
        .filter(Person.class_name.isnot(None))
        .distinct()
        .order_by(Person.class_name)
        .all()
    ]

    return render_template(
        "school_admin/reports/absent.html",
        day=day,
        absent=absent,
        classes=classes,
        role=role,
        class_name=class_name,
    )


# ---------------------------------------------------------------------------
# Monthly summary (per person, how many days they came in)
# ---------------------------------------------------------------------------
@bp.route("/reports/monthly")
@login_required
@require_school_context
@school_staff_required
def report_monthly():
    month_str = request.args.get("month")
    try:
        if month_str:
            year, month = (int(x) for x in month_str.split("-"))
        else:
            now = datetime.utcnow()
            year, month = now.year, now.month
    except ValueError:
        now = datetime.utcnow()
        year, month = now.year, now.month

    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    rows = (
        db.session.query(
            Person,
            func.count(func.distinct(func.date(AccessLog.event_at))).label("days_attended"),
            func.count(AccessLog.id).label("event_count"),
        )
        .outerjoin(
            AccessLog,
            (AccessLog.person_id == Person.id)
            & (AccessLog.event_at >= start)
            & (AccessLog.event_at < end)
            & (AccessLog.outcome == AccessOutcome.GRANTED.value),
        )
        .filter(Person.is_active.is_(True))
        .group_by(Person.id)
        .order_by(Person.class_name, Person.full_name)
        .all()
    )

    return render_template(
        "school_admin/reports/monthly.html",
        year=year,
        month=month,
        start=start,
        rows=rows,
    )