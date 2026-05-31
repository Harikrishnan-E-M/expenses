from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template
from flask_login import current_user
from pymongo.errors import PyMongoError

from app.extensions import csrf, limiter, login_manager, mongo, get_db
from app.models.user import User
from config.settings import Config


def _ensure_indexes(app: Flask) -> None:
    with app.app_context():
        db = get_db()
        db.users.create_index("email", unique=True)
        db.otp_verifications.create_index("expires_at", expireAfterSeconds=0)
        db.wallets.create_index([("user_id", 1), ("created_at", -1)])
        db.expenses.create_index([("user_id", 1), ("date", -1)])
        db.income.create_index([("user_id", 1), ("date", -1)])
        db.expense_categories.create_index([("user_id", 1), ("name", 1)], unique=True)
        db.income_categories.create_index([("user_id", 1), ("name", 1)], unique=True)


def create_app(config_object: type[Config] = Config) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config.from_object(config_object)

    mongo.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.from_id(user_id)

    @app.after_request
    def apply_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.context_processor
    def inject_globals():
        return {"now_utc": datetime.now(timezone.utc), "current_user": current_user}

    from app.routes.auth import auth_bp
    from app.routes.categories import categories_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.expenses import expenses_bp
    from app.routes.income import income_bp
    from app.routes.profile import profile_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.wallets import wallets_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(wallets_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("errors/500.html"), 500

    with app.app_context():
        if app.config.get("CREATE_INDEXES_ON_STARTUP", True):
            try:
                _ensure_indexes(app)
            except PyMongoError:
                app.logger.warning("MongoDB is unavailable during startup; skipping index creation until the database is reachable.")

    return app
