"""Health check endpoints for container liveness and database readiness."""

from flask import Blueprint, current_app, g, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.get("/live")
def liveness():
    """Return application liveness without querying external dependencies."""
    return jsonify(
        {
            "status": "alive",
            "service": "busreserve-api",
            "request_id": getattr(g, "request_id", None),
        }
    ), 200


@health_bp.get("/ready")
def readiness():
    """Verify live PostgreSQL connectivity before marking container ready."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(
            {
                "status": "ready",
                "database": "connected",
                "request_id": getattr(g, "request_id", None),
            }
        ), 200
    except Exception as exc:
        current_app.logger.error(
            "readiness_check_failed",
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )
        db.session.remove()
        return jsonify(
            {
                "status": "not_ready",
                "database": "disconnected",
                "request_id": getattr(g, "request_id", None),
            }
        ), 503
