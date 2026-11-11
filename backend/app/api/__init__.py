"""API blueprint registration."""

from flask import Flask

from app.api.admin import admin_bp
from app.api.bookings import bookings_bp
from app.api.health import health_bp
from app.api.routes import routes_bp
from app.api.trips import trips_bp


def register_blueprints(app: Flask) -> None:
    """Register all HTTP API and health blueprints."""
    app.register_blueprint(health_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(admin_bp)
