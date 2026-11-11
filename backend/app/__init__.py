"""Modular Flask application factory for BusReserve."""

import os
from typing import Any

import click
from flask import Flask

from app import models  # noqa: F401  Ensure SQLAlchemy models register with metadata
from app.api import register_blueprints
from app.config import CONFIG_MAP
from app.extensions import cors, db, migrate
from app.utils.errors import register_error_handlers
from app.utils.logging import configure_logging


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

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        expose_headers=["X-Request-ID"],
    )

    register_blueprints(app)
    register_error_handlers(app)
    _register_cli(app)

    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    def seed_command() -> None:
        """Populate idempotent sample routes, trips, seats, and demo bookings."""
        from scripts.seed import run_seed

        summary = run_seed()
        click.echo(
            f"Seed complete: routes+{summary['routes_created']}, "
            f"trips+{summary['trips_created']}, "
            f"seats+{summary['seats_created']}, "
            f"bookings+{summary['bookings_created']}"
        )
