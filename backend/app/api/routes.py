"""Route listing REST API blueprint."""

from flask import Blueprint, jsonify

from app.services.booking_service import list_routes

routes_bp = Blueprint("routes", __name__, url_prefix="/api/routes")


@routes_bp.get("")
def get_routes():
    """List available bus routes and their ordered intermediate stops."""
    routes = list_routes()
    return jsonify({"routes": routes, "count": len(routes)}), 200
