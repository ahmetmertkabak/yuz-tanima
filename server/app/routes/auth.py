"""
Shared auth routes — used by both super-admin and school-admin hosts.

Flow
----
1. POST /auth/login → password check.
2. If user has TOTP enabled → session["pending_2fa_user_id"] set, redirect to /auth/2fa.
3. POST /auth/2fa → verify code → log user in (Flask-Login).
4. GET /auth/logout → clear session.

Tenant rules
------------
- Super-admin **must** log in from the super-admin host.
- School users **must** log in from their own school's subdomain.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pyotp
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.forms import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    TwoFactorForm,
    TwoFactorSetupForm,
)
from app.middleware.tenant import get_tenant_context
from app.models import AuditAction, AuditLog, User, UserRole
from app.services.audit import record_audit


bp = Blueprint("auth", __name__, url_prefix="/auth")

PENDING_USER_KEY = "pending_2fa_user_id"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _find_user(username: str) -> Optional[User]:
    """Resolve (username|email) against the current tenant context."""
    ctx = get_tenant_context()
    username = (username or "").strip().lower()

    if ctx.is_super_admin_host:
        # Only super-admins live at admin.<base-domain>
        return (
            db.session.query(User)
            .filter(
                User.role == UserRole.SUPER_ADMIN.value,
                db.or_(User.username == username, User.email == username),
            )
            .first()
        )

    if ctx.school_id is None:
        # Dev fallback: no tenant resolved — only allow super-admin
        return (
            db.session.query(User)
            .filter(
                User.role == UserRole.SUPER_ADMIN.value,
                db.or_(User.username == username, User.email == username),
            )
            .first()
        )

    return (
        db.session.query(User)
        .filter(
            User.school_id == ctx.school_id,
            db.or_(User.username == username, User.email == username),
        )
        .first()
    )


def _safe_next() -> Optional[str]:
    """Return `?next=` URL only if it's relative (prevent open redirect)."""
    nxt = request.args.get("next") or request.form.get("next")
    if not nxt:
        return None
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return None


def _post_login_redirect(user: User) -> str:
    if user.is_super_admin():
        return url_for("super_admin.dashboard")
    # school_admin / staff / viewer → school admin dashboard
    return url_for("school_admin.dashboard")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = _find_user(form.username.data)
        ip = request.remote_addr
        ua = request.headers.get("User-Agent", "")

        if user is None or not user.check_password(form.password.data):
            record_audit(
                AuditAction.LOGIN_FAILED,
                user=user,
                details={"username_attempt": form.username.data},
                ip=ip,
                user_agent=ua,
            )
            if user:
                user.register_failed_login()
            db.session.commit()
            flash("Kullanıcı adı veya şifre hatalı.", "danger")
            return render_template("shared/auth/login.html", form=form), 401

        if not user.is_active_account:
            flash(
                "Hesabınız kilitli veya pasif. Lütfen yöneticinize başvurun.",
                "warning",
            )
            return render_template("shared/auth/login.html", form=form), 403

        # --- 2FA branch ---
        if user.totp_enabled:
            session[PENDING_USER_KEY] = user.id
            session["pending_2fa_remember"] = form.remember_me.data
            session["pending_2fa_next"] = _safe_next()
            return redirect(url_for("auth.two_factor"))

        # --- straight login ---
        return _finalize_login(user, form.remember_me.data, _safe_next())

    return render_template("shared/auth/login.html", form=form)


def _finalize_login(user: User, remember: bool, next_url: Optional[str]):
    login_user(user, remember=bool(remember))
    user.register_successful_login(ip=request.remote_addr)
    db.session.commit()
    record_audit(
        AuditAction.LOGIN_SUCCESS,
        user=user,
        ip=request.remote_addr,
        user_agent=request.headers.get("User-Agent", ""),
        commit=True,
    )
    return redirect(next_url or _post_login_redirect(user))


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------
@bp.route("/2fa", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def two_factor():
    user_id = session.get(PENDING_USER_KEY)
    if not user_id:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if user is None or not user.totp_enabled or not user.totp_secret:
        session.pop(PENDING_USER_KEY, None)
        return redirect(url_for("auth.login"))

    form = TwoFactorForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(user.totp_secret)
        if totp.verify(form.code.data, valid_window=1):
            session.pop(PENDING_USER_KEY, None)
            remember = bool(session.pop("pending_2fa_remember", False))
            next_url = session.pop("pending_2fa_next", None)
            return _finalize_login(user, remember, next_url)

        user.register_failed_login()
        db.session.commit()
        flash("Doğrulama kodu hatalı.", "danger")
        return render_template("shared/auth/two_factor.html", form=form), 401

    return render_template("shared/auth/two_factor.html", form=form)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    record_audit(
        AuditAction.LOGOUT,
        user=current_user,
        ip=request.remote_addr,
        commit=True,
    )
    logout_user()
    session.pop(PENDING_USER_KEY, None)
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Change password (self-service)
# ---------------------------------------------------------------------------
@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Mevcut şifre hatalı.", "danger")
            return render_template("shared/auth/change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        record_audit(
            AuditAction.PASSWORD_CHANGED,
            user=current_user,
            ip=request.remote_addr,
            commit=True,
        )
        flash("Şifre başarıyla güncellendi.", "success")
        return redirect(_post_login_redirect(current_user))

    return render_template("shared/auth/change_password.html", form=form)


# ---------------------------------------------------------------------------
# 2FA setup (enable / disable)
# ---------------------------------------------------------------------------
@bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def setup_two_factor():
    # Re-use an in-progress secret so the QR code matches the one the user scanned.
    if not current_user.totp_secret or current_user.totp_enabled:
        current_user.totp_secret = pyotp.random_base32()
        db.session.commit()

    issuer = current_app.config.get("APP_NAME", "Yüz Tanıma")
    account = current_user.email or current_user.username
    provisioning_uri = pyotp.TOTP(current_user.totp_secret).provisioning_uri(
        name=account, issuer_name=issuer
    )

    form = TwoFactorSetupForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(current_user.totp_secret)
        if totp.verify(form.code.data, valid_window=1):
            current_user.totp_enabled = True
            db.session.commit()
            record_audit(
                AuditAction.TOTP_ENABLED,
                user=current_user,
                ip=request.remote_addr,
                commit=True,
            )
            flash("İki faktörlü doğrulama etkinleştirildi.", "success")
            return redirect(_post_login_redirect(current_user))
        flash("Doğrulama kodu hatalı.", "danger")

    return render_template(
        "shared/auth/two_factor_setup.html",
        form=form,
        provisioning_uri=provisioning_uri,
        secret=current_user.totp_secret,
    )


@bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_two_factor():
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.session.commit()
    record_audit(
        AuditAction.TOTP_DISABLED,
        user=current_user,
        ip=request.remote_addr,
        commit=True,
    )
    flash("İki faktörlü doğrulama devre dışı bırakıldı.", "info")
    return redirect(_post_login_redirect(current_user))


# ---------------------------------------------------------------------------
# Password reset (stub — email delivery wired in T8.x)
# ---------------------------------------------------------------------------
@bp.route("/password-reset", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def password_reset_request():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        # TODO (T8.x): generate token + send email
        record_audit(
            AuditAction.PASSWORD_RESET_REQUESTED,
            user=None,
            details={"email": form.email.data},
            ip=request.remote_addr,
            commit=True,
        )
        flash(
            "Eğer bu e-posta sistemde kayıtlıysa, kısa süre içinde sıfırlama "
            "bağlantısı gönderilecek.",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("shared/auth/password_reset_request.html", form=form)


@bp.route("/password-reset/<token>", methods=["GET", "POST"])
def password_reset(token: str):
    # TODO (T8.x): verify token, fetch user
    flash("Şifre sıfırlama özelliği henüz aktif değil.", "warning")
    return redirect(url_for("auth.login"))