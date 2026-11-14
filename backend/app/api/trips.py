"""Trip search and seat map REST API blueprint."""

from flask import Blueprint, jsonify, request

from app.extensions import limiter
from app.services.booking_service import get_trip_seats, search_trips
from app.services.schedule_service import get_booking_horizon_bounds
from app.utils.schemas import TripSearchSchema
from app.utils.timezone import get_app_timezone_name

trips_bp = Blueprint("trips", __name__, url_prefix="/api/trips")
_trip_search_schema = TripSearchSchema()


@trips_bp.get("")
@limiter.limit("60 per minute")
def find_trips():
    """Search scheduled bus trips by source, destination, and travel date."""
    params = _trip_search_schema.load(request.args.to_dict())
    trips = search_trips(
        source=params.get("source"),
        destination=params.get("destination"),
        travel_date=params.get("travel_date"),
        sort_by=params.get("sort_by", "departure_asc"),
        min_seats=params.get("min_seats"),
        featured=params.get("featured", False),
    )
    min_date, max_date, horizon_days = get_booking_horizon_bounds()
    return jsonify(
        {
            "trips": trips,
            "count": len(trips),
            "timezone": get_app_timezone_name(),
            "booking_horizon_days": horizon_days,
            "min_date": min_date.isoformat(),
            "max_date": max_date.isoformat(),
        }
    ), 200


@trips_bp.get("/<int:trip_id>/seats")
@limiter.limit("60 per minute")
def trip_seat_map(trip_id: int):
    """Return the seat layout and real-time availability for a trip with optional tier/position filtering."""
    tier = request.args.get("tier")
    position = request.args.get("position")
    max_fare = request.args.get("max_fare", type=float)
    available_only = request.args.get("available_only", "").lower() in ("true", "1", "yes")

    payload = get_trip_seats(
        trip_id,
        tier=tier,
        position=position,
        max_fare=max_fare,
        available_only=available_only,
    )
    return jsonify(payload), 200


@trips_bp.get("/<int:trip_id>/cheapest-seats")
@limiter.limit("60 per minute")
def trip_cheapest_seats(trip_id: int):
    """Find the cheapest available seats across tiers for a trip."""
    from app.services.booking_service import find_cheapest_seats

    payload = find_cheapest_seats(trip_id)
    return jsonify(payload), 200

