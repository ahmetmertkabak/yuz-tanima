"""
Flask application factory.

Creates and configures the multi-tenant SaaS face recognition application.

Subdomains:
  - admin.yuztanima.com   → Super Admin panel
  - <school>.yuztanima.com → School Admin / Staff panel
  - api.yuztanima.com (or any) → Device REST API (/api/v1/...)
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, jsonify

from app.config import get_config
from app.extensions import (
    csrf,
    db,
    limiter,
    login_manager,
    migrate,
    socketio,
)


def create_app(config_name: str | None = None) -> Flask:
    """Application factory.

    Args:
        config_name: One of "development", "testing", "production".
                     If None, read from FLASK_ENV environment variable.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    _configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_middleware(app)
    _register_cli_commands(app)

    app.logger.info(
        "%s started in %s mode",
        app.config["APP_NAME"],
        config_class.__name__,
    )

    return app


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------
def _configure_logging(app: Flask) -> None:
    """Configure app-wide logging (file + stdout)."""
    log_level = app.config.get("LOG_LEVEL", "INFO")
    app.logger.setLevel(log_level)

    if app.debug or app.testing:
        return

    log_dir = Path(app.root_path).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s "
            "[in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(log_level)
    app.logger.addHandler(file_handler)

    # Sentry
    dsn = app.config.get("SENTRY_DSN")
    if dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            sentry_sdk.init(
                dsn=dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,
                environment=app.config.get("FLASK_ENV", "production"),
                release=app.config.get("APP_VERSION"),
            )
            app.logger.info("Sentry initialized")
        except Exception as exc:  # pragma: no cover
            app.logger.warning("Sentry init failed: %s", exc)


def _init_extensions(app: Flask) -> None:
    """Wire up Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    socketio.init_app(
        app,
        message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"),
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "eventlet"),
        cors_allowed_origins="*",
    )

    # Import models so Flask-Migrate can discover them
    from app import models  # noqa: F401


def _register_blueprints(app: Flask) -> None:
    """Register all route blueprints.

    NOTE: Blueprint modules will be created in Phase 2 (T2.1+). For now only
    health check is wired up.
    """
    from app.routes.api.v1 import bp as api_v1_bp

    # CSRF is disabled for the device API (uses HMAC signatures instead)
    csrf.exempt(api_v1_bp)
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # Placeholder root health endpoint (not on a blueprint)
    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            app=app.config["APP_NAME"],
            version=app.config["APP_VERSION"],
        )


def _register_error_handlers(app: Flask) -> None:
    """JSON API error handlers + HTML fallbacks."""
    from flask import request

    def _wants_json() -> bool:
        if request.path.startswith("/api/"):
            return True
        return "application/json" in (request.accept_mimetypes.best or "")

    @app.errorhandler(400)
    def _bad_request(e):
        if _wants_json():
            return jsonify(error="bad_request", message=str(e)), 400
        return "Bad Request", 400

    @app.errorhandler(401)
    def _unauthorized(e):
        if _wants_json():
            return jsonify(error="unauthorized", message=str(e)), 401
        return "Unauthorized", 401

    @app.errorhandler(403)
    def _forbidden(e):
        if _wants_json():
            return jsonify(error="forbidden", message=str(e)), 403
        return "Forbidden", 403

    @app.errorhandler(404)
    def _not_found(e):
        if _wants_json():
            return jsonify(error="not_found", message=str(e)), 404
        return "Not Found", 404

    @app.errorhandler(429)
    def _ratelimited(e):
        return jsonify(error="rate_limited", message=str(e)), 429

    @app.errorhandler(500)
    def _server_error(e):
        app.logger.exception("Internal server error")
        if _wants_json():
            return jsonify(error="internal_server_error"), 500
        return "Internal Server Error", 500


def _register_middleware(app: Flask) -> None:
    """Register request hooks (tenant resolution, etc.)."""
    from app.middleware.tenant import register_tenant_middleware

    register_tenant_middleware(app)


def _register_cli_commands(app: Flask) -> None:
    """Register custom `flask ...` CLI commands."""
    import click

    @app.cli.command("create-super-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    )
    def create_super_admin(username: str, email: str, password: str):
        """Create a platform-level super admin user."""
        from app.extensions import db
        from app.models import User, UserRole

        existing = (
            db.session.query(User)
            .filter(
                User.school_id.is_(None),
                db.or_(User.username == username.lower(), User.email == email.lower()),
            )
            .first()
        )
        if existing:
            click.echo(f"User with that username or email already exists (id={existing.id}).")
            return

        user = User(
            username=username,
            email=email,
            role=UserRole.SUPER_ADMIN.value,
            is_active=True,
            school_id=None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"✅ Super admin created (id={user.id}).")

    @app.cli.command("routes-list")
    def routes_list():
        """List all registered routes."""
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            click.echo(f"{methods:20s} {rule.rule:50s} -> {rule.endpoint}")

    @app.cli.command("dev-reset-db")
    def dev_reset_db():
        """DROP and recreate every table (dev only — refuses in production)."""
        if app.config.get("FLASK_ENV") == "production" or not app.config.get("DEBUG"):
            click.echo("❌ Refusing to run in non-debug / production environment.")
            return
        from app.extensions import db

        click.confirm("This will DROP ALL TABLES. Continue?", abort=True)
        db.drop_all()
        db.create_all()
        click.echo("✅ Schema recreated from models.")