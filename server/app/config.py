"""
Configuration objects for different environments.

Loaded via environment variables (`.env` file). See `.env.example` at project root.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (server/)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    """Shared configuration for all environments."""

    # --- Core ---
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    APP_NAME = "Yüz Tanıma SaaS"
    APP_VERSION = "0.1.0"

    # --- Domain / Tenant ---
    BASE_DOMAIN = os.getenv("BASE_DOMAIN", "yuztanima.com")
    SUPER_ADMIN_SUBDOMAIN = os.getenv("SUPER_ADMIN_SUBDOMAIN", "admin")

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/yuz_tanima_dev",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # --- Session / Auth ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True

    # --- Security ---
    BCRYPT_LOG_ROUNDS = 12
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # --- Biometric Encryption ---
    # Fernet key (32 url-safe base64 bytes). Generate via:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FACE_ENCRYPTION_KEY = os.getenv("FACE_ENCRYPTION_KEY", "")

    # --- Device API ---
    DEVICE_API_TIMESTAMP_TOLERANCE = 60  # seconds
    DEVICE_HEARTBEAT_INTERVAL = 30       # seconds (expected)
    DEVICE_OFFLINE_THRESHOLD = 120       # seconds without heartbeat => offline

    # --- Rate Limiting ---
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    RATELIMIT_DEFAULT = "200 per minute"
    RATELIMIT_HEADERS_ENABLED = True

    # --- Celery ---
    CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_TIMEZONE = "Europe/Istanbul"

    # --- Socket.IO ---
    SOCKETIO_MESSAGE_QUEUE = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    SOCKETIO_ASYNC_MODE = "eventlet"

    # --- Object Storage (snapshots, face images) ---
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "yuz-tanima")
    S3_REGION = os.getenv("S3_REGION", "eu-central-1")

    # --- Retention (KVKK) ---
    SNAPSHOT_RETENTION_DAYS = int(os.getenv("SNAPSHOT_RETENTION_DAYS", "30"))
    ACCESS_LOG_RETENTION_DAYS = int(os.getenv("ACCESS_LOG_RETENTION_DAYS", "365"))

    # --- Logging ---
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # --- Uploads ---
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPLOAD_FOLDER = BASE_DIR / "uploads"

    # --- i18n ---
    LANGUAGES = ["tr", "en"]
    BABEL_DEFAULT_LOCALE = "tr"
    BABEL_DEFAULT_TIMEZONE = "Europe/Istanbul"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # makes local API testing easier
    SQLALCHEMY_ECHO = False

    # Allow plain HTTP during local dev
    PREFERRED_URL_SCHEME = "http"


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    # Default to in-memory SQLite so unit tests need zero infrastructure.
    # CI / integration runs can override via TEST_DATABASE_URL.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}  # pool options not valid for sqlite://
    WTF_CSRF_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4  # faster tests
    RATELIMIT_ENABLED = False
    # A stable Fernet key for tests so face_crypto has something to work with.
    # Test-only Fernet key is set by conftest (Fernet.generate_key())
    FACE_ENCRYPTION_KEY = os.getenv("FACE_ENCRYPTION_KEY", "")
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SOCKETIO_MESSAGE_QUEUE = None  # disable redis queue during tests
    SOCKETIO_ASYNC_MODE = "threading"


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    PREFERRED_URL_SCHEME = "https"

    # Stricter session cookies
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"

    # Production must provide these
    @classmethod
    def validate(cls):
        required = ["SECRET_KEY", "DATABASE_URL", "FACE_ENCRYPTION_KEY"]
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables for production: {missing}"
            )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig}


def get_config(name: str | None = None):
    """Resolve config class by name or FLASK_ENV env var."""
    name = name or os.getenv("FLASK_ENV", "development")
    cfg = config_by_name.get(name, DevelopmentConfig)
    if name == "production":
        cfg.validate()
    return cfg