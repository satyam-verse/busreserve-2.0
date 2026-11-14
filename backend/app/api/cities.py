"""Dynamic Indian city autocomplete and booking horizon metadata API."""

from flask import Blueprint, jsonify, request

from app.services.booking_service import list_cities
from app.services.schedule_service import get_booking_horizon_bounds
from app.utils.schemas import CitySearchSchema
from app.utils.timezone import get_app_timezone_name

cities_bp = Blueprint("cities", __name__, url_prefix="/api/cities")
_city_search_schema = CitySearchSchema()


@cities_bp.get("")
def search_cities():
    """Return matching searchable cities merged from City catalog and active routes/stops."""
    params = _city_search_schema.load(request.args.to_dict())
    cities = list_cities(
        query=params.get("q"),
        limit=params.get("limit", 15),
    )
    min_date, max_date, horizon_days = get_booking_horizon_bounds()
    return jsonify(
        {
            "cities": cities,
            "count": len(cities),
            "timezone": get_app_timezone_name(),
            "booking_horizon_days": horizon_days,
            "min_date": min_date.isoformat(),
            "max_date": max_date.isoformat(),
        }
    ), 200
