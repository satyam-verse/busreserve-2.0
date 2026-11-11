"""Trip search and seat map REST API blueprint."""

from flask import Blueprint, jsonify, request

from app.services.booking_service import get_trip_seats, search_trips
from app.utils.schemas import TripSearchSchema

trips_bp = Blueprint("trips", __name__, url_prefix="/api/trips")
_trip_search_schema = TripSearchSchema()


@trips_bp.get("")
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
    return jsonify({"trips": trips, "count": len(trips)}), 200


@trips_bp.get("/<int:trip_id>/seats")
def trip_seat_map(trip_id: int):
    """Return the seat layout and real-time availability for a trip."""
    payload = get_trip_seats(trip_id)
    return jsonify(payload), 200
