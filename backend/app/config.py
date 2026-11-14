"""Environment-based application configuration."""

import os


def _parse_cors_origins(raw_value: str | None) -> list[str] | str:
    if not raw_value:
        return ["http://localhost:5173", "http://localhost:8080", "http://localhost"]
    if raw_value.strip() == "*":
        return "*"
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    """Shared base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key-change-in-production-32b")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = max(
        5, int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "480"))
    )
    JWT_COOKIE_NAME = os.getenv("JWT_COOKIE_NAME", "busreserve_access_token")
    _is_prod = os.getenv("FLASK_ENV") == "production" or os.getenv("ENV") == "production"
    COOKIE_SECURE = _parse_bool(os.getenv("COOKIE_SECURE"), _is_prod)
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

    EMAIL_TOKEN_EXPIRES_MINUTES = max(5, int(os.getenv("EMAIL_TOKEN_EXPIRES_MINUTES", "60")))
    RESET_TOKEN_EXPIRES_MINUTES = max(5, int(os.getenv("RESET_TOKEN_EXPIRES_MINUTES", "30")))
    ALLOW_LOCAL_MAIL_PREVIEW = _parse_bool(os.getenv("ALLOW_LOCAL_MAIL_PREVIEW"), False)
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:8080")
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "")
    ALLOWED_PUBLIC_HOSTS = os.getenv("ALLOWED_PUBLIC_HOSTS", "")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@busreserve.local")
    SMTP_USE_TLS = _parse_bool(os.getenv("SMTP_USE_TLS"), True)

    RATELIMIT_ENABLED = _parse_bool(os.getenv("RATELIMIT_ENABLED"), True)
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": 1800,
    }
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    CORS_ORIGINS = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    BOOKING_HORIZON_DAYS = max(1, int(os.getenv("BOOKING_HORIZON_DAYS", "90")))
    JSON_SORT_KEYS = False

    # Phase 4: Google Gemini AI & deterministic local fallback configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-3.8-flash").strip()
    GEMINI_FALLBACK_MODEL = (os.getenv("GEMINI_FALLBACK_MODEL") or "").strip()
    GEMINI_ENABLED = _parse_bool(os.getenv("GEMINI_ENABLED"), True)
    AI_PROVIDER = (os.getenv("AI_PROVIDER") or "auto").strip().lower()
    AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "15"))
    AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
    AI_DAILY_REQUEST_LIMIT = int(os.getenv("AI_DAILY_REQUEST_LIMIT", "200"))
    AI_USER_DAILY_LIMIT = int(os.getenv("AI_USER_DAILY_LIMIT", "50"))
    AI_MAX_INPUT_LENGTH = int(os.getenv("AI_MAX_INPUT_LENGTH", "1000"))
    AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "600"))
    AI_HISTORY_LIMIT = int(os.getenv("AI_HISTORY_LIMIT", "20"))
    AI_RECOVERY_COOLDOWN_SECONDS = int(os.getenv("AI_RECOVERY_COOLDOWN_SECONDS", "60"))


def validate_ai_config(app) -> None:
    """Validate Phase 4 AI configuration on application startup without logging secrets."""
    provider = str(app.config.get("AI_PROVIDER", "auto")).strip().lower()
    if provider not in {"auto", "gemini", "local_fallback"}:
        raise ValueError(
            f"Invalid AI_PROVIDER '{provider}'. Expected 'auto', 'gemini', or 'local_fallback'."
        )
    app.config["AI_PROVIDER"] = provider

    model_name = str(app.config.get("GEMINI_MODEL", "")).strip()
    if not model_name:
        raise ValueError("GEMINI_MODEL must be a non-empty model identifier.")
    if model_name.startswith(("gemini-1.", "gemini-2.0", "gemini-2.5")):
        app.logger.warning(
            "deprecated_gemini_model_overridden",
            extra={"configured_model": model_name, "active_model": "gemini-3.8-flash"},
        )
        app.config["GEMINI_MODEL"] = "gemini-3.8-flash"
    else:
        app.config["GEMINI_MODEL"] = model_name

    fallback_model = str(app.config.get("GEMINI_FALLBACK_MODEL") or "").strip()
    if fallback_model.startswith(("gemini-1.", "gemini-2.0", "gemini-2.5")):
        app.logger.warning(
            "deprecated_gemini_fallback_model_overridden",
            extra={"configured_model": fallback_model, "active_model": "gemini-3.5-flash-lite"},
        )
        fallback_model = "gemini-3.5-flash-lite"
    if fallback_model == app.config["GEMINI_MODEL"]:
        fallback_model = ""
    app.config["GEMINI_FALLBACK_MODEL"] = fallback_model

    numeric_bounds = {
        "AI_TIMEOUT_SECONDS": (1.0, 60.0),
        "AI_MAX_RETRIES": (0, 5),
        "AI_DAILY_REQUEST_LIMIT": (1, 100000),
        "AI_USER_DAILY_LIMIT": (1, 10000),
        "AI_MAX_INPUT_LENGTH": (20, 4000),
        "AI_MAX_OUTPUT_TOKENS": (32, 4096),
        "AI_HISTORY_LIMIT": (2, 100),
        "AI_RECOVERY_COOLDOWN_SECONDS": (1, 3600),
    }
    for key, (min_val, max_val) in numeric_bounds.items():
        val = app.config.get(key)
        if not isinstance(val, int | float) or val < min_val or val > max_val:
            raise ValueError(f"{key} must be between {min_val} and {max_val}, got {val!r}.")

    api_key = str(app.config.get("GEMINI_API_KEY") or "").strip()
    if api_key in {"your-gemini-api-key-here", "REPLACE_ME", "changeme"}:
        api_key = ""
    app.config["GEMINI_API_KEY"] = api_key


class DevelopmentConfig(BaseConfig):
    """Local development configuration."""

    DEBUG = True
    ALLOW_LOCAL_MAIL_PREVIEW = _parse_bool(os.getenv("ALLOW_LOCAL_MAIL_PREVIEW"), True)
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "https://localhost:8443")
    ALLOWED_PUBLIC_HOSTS = os.getenv("ALLOWED_PUBLIC_HOSTS", "localhost,127.0.0.1")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://busreserve:busreserve_dev@localhost:5432/busreserve",
    )


class TestingConfig(BaseConfig):
    """Automated testing configuration (PostgreSQL)."""

    TESTING = True
    RATELIMIT_ENABLED = False
    ALLOW_LOCAL_MAIL_PREVIEW = _parse_bool(os.getenv("ALLOW_LOCAL_MAIL_PREVIEW"), True)
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "https://test.busreserve.local")
    ALLOWED_PUBLIC_HOSTS = os.getenv("ALLOWED_PUBLIC_HOSTS", "test.busreserve.local")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://busreserve:busreserve_dev@localhost:5432/busreserve_test",
        ),
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 20,
    }


class ProductionConfig(BaseConfig):
    """Production configuration for Gunicorn container runtime."""

    DEBUG = False
    TESTING = False
    COOKIE_SECURE = _parse_bool(os.getenv("COOKIE_SECURE"), True)
    ALLOW_LOCAL_MAIL_PREVIEW = _parse_bool(os.getenv("ALLOW_LOCAL_MAIL_PREVIEW"), False)
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "https://busreserve.in")
    ALLOWED_PUBLIC_HOSTS = os.getenv("ALLOWED_PUBLIC_HOSTS", "busreserve.in")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
