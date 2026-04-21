"""
Person (student/teacher/staff) management — School Admin panel.

Route map (under school admin blueprint):
  GET  /persons                       list
  GET  /persons/new                   create form
  POST /persons/new                   create submit
  GET  /persons/<id>                  detail
  GET  /persons/<id>/edit             edit form
  POST /persons/<id>/edit             edit submit
  POST /persons/<id>/delete           delete
  POST /persons/bulk                  bulk action (activate/deactivate/delete)
  GET  /persons/export                Excel export
  GET  /persons/import                import form
  POST /persons/import                import submit
"""
from __future__ import annotations

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.forms import PersonBulkImportForm, PersonForm
from app.middleware.auth import (
    must_belong_to_current_school,
    school_admin_required,
    school_staff_required,
)
from app.middleware.tenant import get_tenant_context, require_school_context
from app.models import (
    AuditAction,
    ConsentStatus,
    Person,
    PersonRole,
)
from app.routes.school_admin import bp
from app.services.audit import record_audit
from app.services.person_io import PersonExporter, PersonImporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filtered_query():
    """Build a query already constrained by `filter_*` query-string params.

    Tenant middleware auto-filters by `school_id`.
    """
    q = (request.args.get("q") or "").strip()
    role = (request.args.get("role") or "").strip()
    class_name = (request.args.get("class_name") or "").strip()
    active_filter = request.args.get("active")  # "1", "0", or None
    has_face = request.args.get("has_face")     # "1", "0", or None

    query = db.session.query(Person)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(Person.full_name).like(like),
                func.lower(Person.person_no).like(like),
                func.lower(Person.email).like(like),
            )
        )
    if role in PersonRole.values():
        query = query.filter(Person.role == role)
    if class_name:
        query = query.filter(Person.class_name == class_name)
    if active_filter == "1":
        query = query.filter(Person.is_active.is_(True))
    elif active_filter == "0":
        query = query.filter(Person.is_active.is_(False))
    if has_face == "1":
        query = query.filter(Person.face_encoding_encrypted.isnot(None))
    elif has_face == "0":
        query = query.filter(Person.face_encoding_encrypted.is_(None))

    return query


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@bp.route("/persons")
@login_required
@require_school_context
@school_staff_required
def persons_list():
    page = max(int(request.args.get("page") or 1), 1)
    per_page = min(int(request.args.get("per_page") or 25), 200)
    sort = request.args.get("sort") or "full_name"
    direction = request.args.get("direction") or "asc"

    query = _filtered_query()

    sort_map = {
        "person_no": Person.person_no,
        "full_name": Person.full_name,
        "class_name": Person.class_name,
        "created_at": Person.created_at,
        "role": Person.role}
    order_col = sort_map.get(sort, Person.full_name)
    if direction == "desc":
        order_col = order_col.desc()
    query = query.order_by(order_col)

    total = query.count()
    persons = query.offset((page - 1) * per_page).limit(per_page).all()

    # Class dropdown
    classes = [
        c[0]
        for c in db.session.query(Person.class_name)
        .filter(Person.class_name.isnot(None))
        .distinct()
        .order_by(Person.class_name)
        .all()
    ]

    return render_template(
        "school_admin/persons/list.html",
        persons=persons,
        total=total,
        page=page,
        per_page=per_page,
        classes=classes,
        roles=PersonRole.values(),
        sort=sort,
        direction=direction,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@bp.route("/persons/new", methods=["GET", "POST"])
@login_required
@require_school_context
@school_admin_required
def persons_new():
    form = PersonForm()
    if form.validate_on_submit():
        ctx = get_tenant_context()
        if (
            db.session.query(Person)
            .filter_by(school_id=ctx.school_id, person_no=form.person_no.data.strip())
            .first()
        ):
            flash("Bu kişi numarası zaten kayıtlı.", "danger")
            return render_template("school_admin/persons/form.html", form=form, mode="new"), 409

        person = Person(
            school_id=ctx.school_id,
            person_no=form.person_no.data,
            full_name=form.full_name.data,
            role=form.role.data,
            class_name=form.class_name.data or None,
            email=form.email.data or None,
            phone=form.phone.data or None,
            parent_name=form.parent_name.data or None,
            parent_phone=form.parent_phone.data or None,
            notes=form.notes.data or None,
            is_active=form.is_active.data,
            access_granted=form.access_granted.data,
            consent_status=form.consent_status.data,
            created_by_user_id=current_user.id,
        )
        if form.consent_status.data == ConsentStatus.GRANTED.value:
            person.grant_consent()
        db.session.add(person)
        db.session.flush()

        record_audit(
            AuditAction.PERSON_CREATED,
            user=current_user,
            school_id=ctx.school_id,
            resource_type="person",
            resource_id=person.id,
            resource_label=person.full_name,
        )
        db.session.commit()
        flash("Kişi eklendi. Şimdi yüz kaydı yapabilirsiniz.", "success")
        return redirect(url_for("school_admin.person_detail", person_id=person.id))

    return render_template("school_admin/persons/form.html", form=form, mode="new")


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@bp.route("/persons/<int:person_id>")
@login_required
@require_school_context
@school_staff_required
@must_belong_to_current_school
def person_detail(person_id: int):
    person = db.session.get(Person, person_id) or abort(404)

    from app.models import AccessLog

    recent_logs = (
        db.session.query(AccessLog)
        .filter(AccessLog.person_id == person.id)
        .order_by(AccessLog.event_at.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "school_admin/persons/detail.html",
        person=person,
        recent_logs=recent_logs,
    )


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------
@bp.route("/persons/<int:person_id>/edit", methods=["GET", "POST"])
@login_required
@require_school_context
@school_admin_required
def person_edit(person_id: int):
    person = db.session.get(Person, person_id) or abort(404)

    form = PersonForm(obj=person)
    if form.validate_on_submit():
        # Handle consent transitions explicitly
        new_consent = form.consent_status.data
        old_consent = person.consent_status

        form.populate_obj(person)
        person.updated_by_user_id = current_user.id

        if new_consent != old_consent:
            if new_consent == ConsentStatus.GRANTED.value:
                person.grant_consent()
            elif new_consent == ConsentStatus.REVOKED.value:
                person.revoke_consent()

        record_audit(
            AuditAction.PERSON_UPDATED,
            user=current_user,
            school_id=person.school_id,
            resource_type="person",
            resource_id=person.id,
            resource_label=person.full_name,
        )
        db.session.commit()
        flash("Kişi güncellendi.", "success")
        return redirect(url_for("school_admin.person_detail", person_id=person.id))

    return render_template(
        "school_admin/persons/form.html", form=form, mode="edit", person=person
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@bp.route("/persons/<int:person_id>/delete", methods=["POST"])
@login_required
@require_school_context
@school_admin_required
def person_delete(person_id: int):
    person = db.session.get(Person, person_id) or abort(404)
    label = person.full_name
    school_id = person.school_id

    db.session.delete(person)
    record_audit(
        AuditAction.PERSON_DELETED,
        user=current_user,
        school_id=school_id,
        resource_type="person",
        resource_id=person_id,
        resource_label=label,
    )
    db.session.commit()
    flash(f"“{label}” silindi.", "info")
    return redirect(url_for("school_admin.persons_list"))


# ---------------------------------------------------------------------------
# Bulk action
# ---------------------------------------------------------------------------
@bp.route("/persons/bulk", methods=["POST"])
@login_required
@require_school_context
@school_admin_required
def persons_bulk():
    action = (request.form.get("action") or "").strip()
    ids_str = (request.form.get("ids") or "").strip()
    if not ids_str or action not in ("activate", "deactivate", "delete"):
        flash("Geçersiz toplu işlem.", "danger")
        return redirect(url_for("school_admin.persons_list"))

    try:
        ids = [int(x) for x in ids_str.split(",") if x.strip().isdigit()]
    except ValueError:
        ids = []
    if not ids:
        flash("Seçim boş.", "warning")
        return redirect(url_for("school_admin.persons_list"))

    persons = db.session.query(Person).filter(Person.id.in_(ids)).all()
    affected = 0

    if action == "delete":
        for p in persons:
            record_audit(
                AuditAction.PERSON_DELETED,
                user=current_user,
                school_id=p.school_id,
                resource_type="person",
                resource_id=p.id,
                resource_label=p.full_name,
                details={"via": "bulk"},
            )
            db.session.delete(p)
            affected += 1
        flash(f"{affected} kişi silindi.", "info")
    else:
        new_state = action == "activate"
        for p in persons:
            p.is_active = new_state
            record_audit(
                AuditAction.PERSON_UPDATED,
                user=current_user,
                school_id=p.school_id,
                resource_type="person",
                resource_id=p.id,
                resource_label=p.full_name,
                details={"bulk_action": action},
            )
            affected += 1
        flash(f"{affected} kişi güncellendi.", "success")

    db.session.commit()
    return redirect(url_for("school_admin.persons_list"))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@bp.route("/persons/export")
@login_required
@require_school_context
@school_staff_required
def persons_export():
    persons = _filtered_query().order_by(Person.full_name).all()
    buf = PersonExporter.persons_to_excel(persons)
    ctx = get_tenant_context()

    record_audit(
        AuditAction.DATA_EXPORT_REQUESTED,
        user=current_user,
        school_id=ctx.school_id,
        resource_type="persons",
        resource_label=f"{len(persons)} kişi",
        commit=True,
    )

    return send_file(
        buf,
        as_attachment=True,
        download_name=f"kisiler-{ctx.school.subdomain}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
@bp.route("/persons/import", methods=["GET", "POST"])
@login_required
@require_school_context
@school_admin_required
def persons_import():
    form = PersonBulkImportForm()
    summary = None

    if form.validate_on_submit():
        ctx = get_tenant_context()
        importer = PersonImporter(
            school_id=ctx.school_id,
            default_role=form.default_role.data,
            overwrite=form.overwrite.data,
        )
        try:
            summary = importer.import_file(form.file.data, form.file.data.filename or "")
            if summary.created or summary.updated:
                record_audit(
                    AuditAction.PERSON_BULK_IMPORT,
                    user=current_user,
                    school_id=ctx.school_id,
                    resource_type="persons",
                    resource_label=(
                        f"+{summary.created} yeni, {summary.updated} güncel, "
                        f"{len(summary.errors)} hata"
                    ),
                    details=summary.as_dict(),
                )
                db.session.commit()
            else:
                db.session.rollback()
        except Exception as exc:  # pragma: no cover
            db.session.rollback()
            flash(f"Import başarısız: {exc}", "danger")
            summary = None

        if summary:
            flash(
                f"{summary.created} yeni, {summary.updated} güncel, "
                f"{summary.skipped} atlandı, {len(summary.errors)} hata.",
                "success" if not summary.errors else "warning",
            )

    return render_template(
        "school_admin/persons/import.html", form=form, summary=summary
    )