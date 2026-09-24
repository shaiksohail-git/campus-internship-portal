"""Application configuration.

All secrets come from environment variables (see .env.example). The app runs on
SQLite locally and can point at PostgreSQL in production by setting DATABASE_URL.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# backend/ contains the Python package; frontend/ (templates + static) sits
# beside it at the repository root, so resolve paths from two levels up.
BACKEND_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
BASE_DIR = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INSTANCE_DIR = os.path.join(BACKEND_DIR, "instance")


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Database: SQLite locally, PostgreSQL in production via DATABASE_URL.
    # SQLAlchemy resolves a relative sqlite path against the Flask instance dir.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///portal.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Sessions ---
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # --- Email ---
    # MAIL_MODE = "smtp" (real emails) | "console" (dev mailbox + terminal output)
    MAIL_MODE = os.environ.get("MAIL_MODE", "console")
    MAIL_FROM = os.environ.get("MAIL_FROM", "Placement Portal <no-reply@campusportal.local>")
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

    # --- Resume storage ---
    # Storage is abstracted in services.storage. "local" writes under instance/uploads.
    STORAGE_MODE = os.environ.get("STORAGE_MODE", "local")
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads", "resumes")
    ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
    MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB
    # Max request body size (file uploads) — Flask aborts > this.
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    # --- Security ---
    CSRF_ENABLED = os.environ.get("CSRF_ENABLED", "true").lower() == "true"
    # Rate limiting on auth endpoints: (requests, per_seconds)
    RATE_LIMIT_LOGIN = (10, 300)
    RATE_LIMIT_REGISTER = (5, 600)
    RATE_LIMIT_EMAIL = (5, 300)

    # --- Misc ---
    APP_NAME = "Campus Placement Portal"
    PER_PAGE = 12

    # Verification / password-reset tokens live for N hours
    TOKEN_TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "24"))

    @staticmethod
    def init_app(app):
        pass


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CSRF_ENABLED = False
    MAIL_MODE = "console"
    STORAGE_MODE = "local"
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "test-uploads", "resumes")
    SERVER_NAME = "localhost"
    RATE_LIMIT_LOGIN = (10000, 1)
    RATE_LIMIT_REGISTER = (10000, 1)
    RATE_LIMIT_EMAIL = (10000, 1)


config_by_name = {"default": Config, "test": TestConfig}
