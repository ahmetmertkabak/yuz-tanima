"""Super-admin → Schools CRUD."""
from datetime import datetime

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
from sqlalchemy import func, or_

from app.extensions import db
from app.forms import SchoolCreateForm, SchoolEditForm
from app.middleware.auth import super_admin_required
from app.models import (
    AuditAction,
    Device,
    Person,
    School,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.routes.super_admin import bp
from app.services.audit import record_audit


@bp.before_request
def _bypass_tenant_for_super_admin_routes():
    """Super-admins see every school; never filter by tenant."""
    g.bypass_tenant_filter = True


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@bp.route("/schools")
@login_required
@super_admin_required
def schools_list():
    q = (request.args.get("q") or "").strip()
    status = request.args.get("status") or ""
    page = max(int(request.args.get("page") or 1), 1)
    per_page = 25

    query = db.session.query(School)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(School.name).like(like),
                func.lower(School.subdomain).like(like),
                func.lower(School.contact_email).like(like),
            )
        )
    if status and status in SubscriptionStatus.values():
        query = query.filter(School.subscription_status == status)

    total = query.count()
    schools = (
        query.order_by(School.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Stat bubbles per school (single query, aggregated)
    stats = {}
    if schools:
        ids = [s.id for s in schools]
        person_counts = dict(
            db.session.query(Person.school_id, func.count(Person.id))
            .filter(Person.school_id.in_(ids))
            .group_by(Person.school_id)
            .all()
        )
        device_counts = dict(
            db.session.query(Device.school_id, func.count(Device.id))
            .filter(Device.school_id.in_(ids))
            .group_by(Device.school_id)
            .all()
        )
        for sid in ids:
            stats[sid] = {
                "persons": person_counts.get(sid, 0),
                "devices": device_counts.get(sid, 0)}

    return render_template(
        "super_admin/schools/list.html",
        schools=schools,
        stats=stats,
        q=q,
        status=status,
        page=page,
        per_page=per_page,
        total=total,
        statuses=SubscriptionStatus.values(),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@bp.route("/schools/new", methods=["GET", "POST"])
@login_required
@super_admin_required
def schools_new():
    form = SchoolCreateForm()
    if form.validate_on_submit():
        subdomain = School.normalize_subdomain(form.subdomain.data)
        if db.session.query(School).filter_by(subdomain=subdomain).first():
            flash("Bu subdomain zaten kullanılıyor.", "danger")
            return render_template("super_admin/schools/new.html", form=form), 409

        school = School(
            name=form.name.data.strip(),
            subdomain=subdomain,
            contact_name=form.contact_name.data or None,
            contact_email=form.contact_email.data.strip().lower(),
            phone=form.phone.data or None,
            address=form.address.data or None,
            max_devices=form.max_devices.data,
            max_persons=form.max_persons.data,
        )
        if form.trial_days.data and form.trial_days.data > 0:
            school.start_trial(days=form.trial_days.data)
        else:
            school.subscription_status = SubscriptionStatus.ACTIVE.value
            school.subscription_started_at = datetime.utcnow()

        db.session.add(school)
        db.session.flush()

        # First school-admin user
        admin = User(
            school_id=school.id,
            username=form.admin_username.data.strip().lower(),
            email=form.admin_email.data.strip().lower(),
            full_name=form.admin_full_name.data or None,
            role=UserRole.SCHOOL_ADMIN.value,
            is_active=True,
        )
        admin.set_password(form.admin_password.data)
        db.session.add(admin)

        record_audit(
            AuditAction.SCHOOL_CREATED,
            user=current_user,
            school_id=school.id,
            resource_type="school",
            resource_id=school.id,
            resource_label=school.name,
            details={"subdomain": school.subdomain, "trial_days": form.trial_days.data},
        )
        record_audit(
            AuditAction.USER_CREATED,
            user=current_user,
            school_id=school.id,
            resource_type="user",
            resource_id=admin.id,
            resource_label=admin.email,
            details={"role": admin.role, "initial_admin": True},
        )

        db.session.commit()
        flash(f"“{school.name}” okulu oluşturuldu.", "success")
        return redirect(url_for("super_admin.school_detail", school_id=school.id))

    return render_template("super_admin/schools/new.html", form=form)


# ---------------------------------------------------------------------------
# Detail / edit
# ---------------------------------------------------------------------------
@bp.route("/schools/<int:school_id>", methods=["GET"])
@login_required
@super_admin_required
def school_detail(school_id: int):
    school = db.session.get(School, school_id) or abort(404)

    person_count = (
        db.session.query(func.count(Person.id)).filter_by(school_id=school_id).scalar()
        or 0
    )
    device_count = (
        db.session.query(func.count(Device.id)).filter_by(school_id=school_id).scalar()
        or 0
    )
    user_count = (
        db.session.query(func.count(User.id)).filter_by(school_id=school_id).scalar()
        or 0
    )

    devices = (
        db.session.query(Device)
        .filter_by(school_id=school_id)
        .order_by(Device.device_name)
        .all()
    )
    users = (
        db.session.query(User)
        .filter_by(school_id=school_id)
        .order_by(User.role, User.username)
        .all()
    )

    return render_template(
        "super_admin/schools/detail.html",
        school=school,
        devices=devices,
        users=users,
        counts={
            "persons": person_count,
            "devices": device_count,
            "users": user_count},
    )


@bp.route("/schools/<int:school_id>/edit", methods=["GET", "POST"])
@login_required
@super_admin_required
def school_edit(school_id: int):
    school = db.session.get(School, school_id) or abort(404)
    form = SchoolEditForm(obj=school)
    if form.validate_on_submit():
        form.populate_obj(school)
        record_audit(
            AuditAction.SCHOOL_UPDATED,
            user=current_user,
            school_id=school.id,
            resource_type="school",
            resource_id=school.id,
            resource_label=school.name,
        )
        db.session.commit()
        flash("Okul bilgileri güncellendi.", "success")
        return redirect(url_for("super_admin.school_detail", school_id=school.id))

    return render_template(
        "super_admin/schools/edit.html", form=form, school=school
    )


@bp.route("/schools/<int:school_id>/suspend", methods=["POST"])
@login_required
@super_admin_required
def school_suspend(school_id: int):
    school = db.session.get(School, school_id) or abort(404)
    school.subscription_status = SubscriptionStatus.SUSPENDED.value
    school.is_active = False
    record_audit(
        AuditAction.SCHOOL_SUSPENDED,
        user=current_user,
        school_id=school.id,
        resource_type="school",
        resource_id=school.id,
        resource_label=school.name,
    )
    db.session.commit()
    flash(f"“{school.name}” askıya alındı.", "warning")
    return redirect(url_for("super_admin.school_detail", school_id=school.id))


@bp.route("/schools/<int:school_id>/reactivate", methods=["POST"])
@login_required
@super_admin_required
def school_reactivate(school_id: int):
    school = db.session.get(School, school_id) or abort(404)
    school.subscription_status = SubscriptionStatus.ACTIVE.value
    school.is_active = True
    record_audit(
        AuditAction.SCHOOL_UPDATED,
        user=current_user,
        school_id=school.id,
        resource_type="school",
        resource_id=school.id,
        resource_label=school.name,
        details={"action": "reactivate"},
    )
    db.session.commit()
    flash(f"“{school.name}” tekrar aktif.", "success")
    return redirect(url_for("super_admin.school_detail", school_id=school.id))