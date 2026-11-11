"""Seat booking, PNR retrieval, and cancellation REST API blueprint."""

from flask import Blueprint, jsonify, request

from app.services.booking_service import cancel_booking, create_booking, get_booking_by_pnr
from app.utils.errors import ValidationAPIError
from app.utils.schemas import BookingCreateSchema

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")
_booking_create_schema = BookingCreateSchema()


@bookings_bp.post("")
def create_reservation():
    """Atomically reserve an available seat for a scheduled bus trip."""
    raw_body = request.get_json(silent=True)
    if not isinstance(raw_body, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")

    validated = _booking_create_schema.load(raw_body)
    booking = create_booking(validated)
    return jsonify({"booking": booking.to_dict()}), 201


@bookings_bp.get("/<string:pnr>")
def get_reservation(pnr: str):
    """Retrieve booking and ticket details by PNR."""
    booking = get_booking_by_pnr(pnr)
    return jsonify({"booking": booking.to_dict()}), 200


@bookings_bp.post("/<string:pnr>/cancel")
def cancel_reservation(pnr: str):
    """Cancel an existing confirmed booking and release its seat."""
    booking = cancel_booking(pnr)
    return jsonify(
        {
            "message": f"Booking {booking.pnr} has been cancelled.",
            "booking": booking.to_dict(),
        }
    ), 200
