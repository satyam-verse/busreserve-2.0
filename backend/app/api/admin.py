"""Demo-only operational overview endpoint for the local admin dashboard."""

from flask import Blueprint, jsonify

from app.services.booking_service import get_admin_overview

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/overview")
def admin_overview():
    """Return aggregated trip, occupancy, and PII-masked booking summaries."""
    return jsonify(get_admin_overview()), 200
