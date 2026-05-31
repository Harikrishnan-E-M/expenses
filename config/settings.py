from __future__ import annotations

from datetime import timedelta
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/fintrack_inr")
    MONGO_DBNAME = os.getenv("MONGO_DBNAME", "fintrack_inr")
    EMAIL_DELIVERY_MODE = os.getenv("EMAIL_DELIVERY_MODE", "smtp").lower().strip()
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    REGISTER_LIMIT = os.getenv("REGISTER_LIMIT", "3 per 10 minutes")
    OTP_VERIFY_LIMIT = os.getenv("OTP_VERIFY_LIMIT", "5 per 10 minutes")
    LOGIN_LIMIT = os.getenv("LOGIN_LIMIT", "5 per minute")
    CREATE_INDEXES_ON_STARTUP = os.getenv("CREATE_INDEXES_ON_STARTUP", "1") == "1"

    DEFAULT_FROM_EMAIL = SMTP_EMAIL
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
