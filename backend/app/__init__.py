"""Flask application factory (modular monolith).

Routes handle HTTP → Services handle business logic → Models handle structure.
"""

import logging
import os

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from app.config import FRONTEND_DIR, INSTANCE_DIR, config_by_name
from app.extensions import db, migrate
from app.middleware.auth import load_current_user
from app.middleware.security import init_csrf
from app.models.enums import ApplicationStatus
from app.utils.errors import ApiError

logger = logging.getLogger(__name__)


def create_app(config_name=None):
    config_name = config_name or os.environ.get("APP_ENV", "default")
    app = Flask(
        __name__,
        instance_path=INSTANCE_DIR,
        instance_relative_config=True,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
    )
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    config_by_name["default"].init_app(app)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    # --- middleware ---
    init_csrf(app)

    @app.before_request
    def _load_user():
        load_current_user()

    # --- blueprints ---
    from app.routes import register_blueprints

    register_blueprints(app)

    # --- template globals & filters ---
    from app.services.notification_service import unread_count

    @app.context_processor
    def inject_globals():
        return {
            "current_user": getattr(g, "current_user", None),
            "csrf_token": lambda: session.get("csrf_token", ""),
            "unread_count": (
                unread_count(g.current_user.id) if getattr(g, "current_user", None) else 0
            ),
            "app_name": app.config["APP_NAME"],
            "status_label": lambda s: ApplicationStatus.LABELS.get(s, s or ""),
        }

    @app.template_filter("datetime")
    def fmt_datetime(value, fmt="%d %b %Y, %I:%M %p"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("date")
    def fmt_date(value, fmt="%d %b %Y"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("time")
    def fmt_time(value, fmt="%I:%M %p"):
        return value.strftime(fmt) if value else "—"

    @app.template_filter("filesize")
    def fmt_filesize(size):
        if size is None:
            return "—"
        for unit in ("B", "KB", "MB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    # --- error handlers ---
    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        if request.path.startswith("/api/") or request.is_json or request.headers.get("X-Requested-With") == "fetch":
            return (
                jsonify({"success": False, "error": exc.to_dict()}),
                exc.status_code,
            )
        return render_template("errors/error.html", error=exc), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": exc.name.replace(" ", "_").upper(),
                            "message": exc.description,
                        },
                    }
                ),
                exc.code or 500,
            )
        return render_template("errors/error.html", error=exc), (exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        logger.exception("Unhandled error")
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "INTERNAL_ERROR", "message": "Something went wrong on our side."},
                    }
                ),
                500,
            )
        return render_template("errors/error.html", error=exc), 500

    # --- CLI commands ---
    from app.cli import register_cli

    register_cli(app)

    return app
