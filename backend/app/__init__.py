"""Modular Flask application factory for BusReserve."""

import os
from typing import Any

import click
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app import models  # noqa: F401  Ensure SQLAlchemy models register with metadata
from app.ai import AIProviderManager
from app.api import register_blueprints
from app.config import CONFIG_MAP, validate_ai_config
from app.extensions import cors, db, limiter, migrate
from app.utils.errors import register_error_handlers
from app.utils.logging import configure_logging
from app.utils.metrics import init_metrics_middleware


def create_app(
    config_name: str | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> Flask:
    """Create and configure a BusReserve Flask application instance."""
    app = Flask(__name__)

    env_name = (config_name or os.getenv("FLASK_ENV", "development")).lower()
    config_cls = CONFIG_MAP.get(env_name, CONFIG_MAP["development"])
    app.config.from_object(config_cls)

    if config_overrides:
        app.config.update(config_overrides)

    if env_name == "production" and not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL environment variable must be set in production.")

    configure_logging(app)
    validate_ai_config(app)
    app.extensions["busreserve_ai_manager"] = AIProviderManager()

    if not app.config.get("TESTING"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        expose_headers=["X-Request-ID"],
    )

    register_blueprints(app)
    register_error_handlers(app)
    init_metrics_middleware(app)
    _register_cli(app)

    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    def seed_command() -> None:
        """Populate idempotent sample cities, routes, 90-day trips, seats, and demo bookings."""
        from scripts.seed import run_seed

        summary = run_seed()
        click.echo(
            f"Seed complete: users+{summary['users_created']}, "
            f"cities+{summary['cities_created']}, "
            f"routes+{summary['routes_created']}, "
            f"schedules+{summary['schedules_created']}, "
            f"trips+{summary['trips_created']}, "
            f"seats+{summary['seats_created']}, "
            f"bookings+{summary['bookings_created']}"
        )

    @app.cli.command("ensure-horizon")
    def ensure_horizon_command() -> None:
        """Materialize upcoming trips across the configured BOOKING_HORIZON_DAYS window."""
        from app.services.schedule_service import ensure_horizon_trips

        summary = ensure_horizon_trips()
        click.echo(
            f"Horizon sync complete: trips+{summary['trips_created']}, "
            f"seats+{summary['seats_created']}"
        )
