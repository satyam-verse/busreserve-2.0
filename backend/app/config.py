"""Environment-based application configuration."""

import os


def _parse_cors_origins(raw_value: str | None) -> list[str] | str:
    if not raw_value:
        return ["http://localhost:5173", "http://localhost:8080", "http://localhost"]
    if raw_value.strip() == "*":
        return "*"
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


class BaseConfig:
    """Shared base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": 1800,
    }
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    CORS_ORIGINS = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    """Local development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://busreserve:busreserve_dev@localhost:5432/busreserve",
    )


class TestingConfig(BaseConfig):
    """Automated testing configuration (PostgreSQL)."""

    TESTING = True
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
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
