"""API blueprint registration."""

from flask import Flask

from app.api.admin import admin_bp
from app.api.ai import ai_bp
from app.api.auth import auth_bp
from app.api.bookings import bookings_bp
from app.api.cities import cities_bp
from app.api.driver import driver_bp
from app.api.health import health_bp
from app.api.metrics import metrics_bp
from app.api.operator import operator_bp
from app.api.payments import payments_bp
from app.api.routes import routes_bp
from app.api.tracking import tracking_bp
from app.api.trips import trips_bp
from app.api.user_portal import user_bp


def register_blueprints(app: Flask) -> None:
    """Register all HTTP API and health blueprints."""
    app.register_blueprint(health_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(cities_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(operator_bp)
