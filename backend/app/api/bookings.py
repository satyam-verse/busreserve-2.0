"""Seat booking, PNR retrieval, and cancellation REST API blueprint."""

from flask import Blueprint, Response, jsonify, request

from app.extensions import limiter
from app.models import User
from app.services.booking_service import cancel_booking, create_booking, get_booking_by_pnr
from app.services.ticket_service import generate_ticket_pdf
from app.utils.auth import load_current_auth
from app.utils.errors import ForbiddenError, UnauthorizedError, ValidationAPIError
from app.utils.schemas import BookingCreateSchema

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")
_booking_create_schema = BookingCreateSchema()


def _mask_contact(value: str | None, is_email: bool = False) -> str | None:
    if not value:
        return value
    if is_email:
        if "@" not in value:
            return "****"
        name, domain = value.split("@", 1)
        if len(name) <= 2:
            masked = name[0] + "*"
        else:
            masked = name[0] + "*" * (len(name) - 2) + name[-1]
        return f"{masked}@{domain}"

    cleaned = value.strip()
    if len(cleaned) <= 4:
        return "****"
    return cleaned[:3] + "*" * (len(cleaned) - 5) + cleaned[-2:]


def _is_verified_caller(booking, user, verification_payload: dict | None = None) -> bool:
    if user:
        if user.role == User.ROLE_ADMIN:
            return True
        if booking.user_id is not None and user.id == booking.user_id:
            return True
        if (
            booking.passenger_email
            and user.email
            and user.email.strip().lower() == booking.passenger_email.strip().lower()
        ):
            return True

    if not verification_payload:
        verification_payload = {}

    cand_email = (
        verification_payload.get("passenger_email")
        or verification_payload.get("email")
        or request.args.get("email")
        or request.args.get("passenger_email")
    )
    if cand_email and cand_email.strip().lower() == (booking.passenger_email or "").strip().lower():
        return True

    cand_phone = (
        verification_payload.get("passenger_phone")
        or verification_payload.get("phone")
        or request.args.get("phone")
        or request.args.get("passenger_phone")
    )
    if cand_phone and cand_phone.strip() == (booking.passenger_phone or "").strip():
        return True

    return False


def _enforce_booking_access(booking, action: str = "view") -> bool:
    """Enforce authorization on booking operations.

    Returns True if caller is verified, False if public view with masked contact info.
    Raises UnauthorizedError or ForbiddenError if access is completely disallowed.
    """
    user, _ = load_current_auth(optional=True)

    # 1. User-owned booking: strictly enforce owner or admin
    if booking.user_id is not None:
        if user is None:
            raise UnauthorizedError("Sign in to view or manage this reservation.")
        if user.id != booking.user_id and user.role != User.ROLE_ADMIN:
            raise ForbiddenError("You do not have permission to access this reservation.")
        return True

    # 2. Guest/unowned booking
    body = request.get_json(silent=True) if request.is_json else {}
    if not isinstance(body, dict):
        body = {}
    verified = _is_verified_caller(booking, user, body)

    if action == "cancel":
        if not verified:
            raise ForbiddenError(
                "Passenger verification required: Provide matching passenger_email or "
                "passenger_phone to cancel this guest reservation."
            )
        return True

    return verified


@bookings_bp.post("")
@limiter.limit("10 per minute")
def create_reservation():
    """Atomically reserve an available seat; associates user_id when authenticated."""
    raw_body = request.get_json(silent=True)
    if not isinstance(raw_body, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")

    validated = _booking_create_schema.load(raw_body)
    user, _ = load_current_auth(optional=True)
    booking = create_booking(validated, user_id=user.id if user else None)
    return jsonify({"booking": booking.to_dict()}), 201


@bookings_bp.get("/<string:pnr>")
@limiter.limit("20 per minute")
def get_reservation(pnr: str):
    """Retrieve booking and ticket details by PNR."""
    booking = get_booking_by_pnr(pnr)
    is_verified = _enforce_booking_access(booking, action="view")
    data = booking.to_dict()
    if not is_verified:
        data["passenger_email"] = _mask_contact(data.get("passenger_email"), is_email=True)
        data["passenger_phone"] = _mask_contact(data.get("passenger_phone"), is_email=False)
        data["is_masked"] = True
    return jsonify({"booking": data}), 200


@bookings_bp.post("/<string:pnr>/cancel")
@limiter.limit("10 per minute")
def cancel_reservation(pnr: str):
    """Cancel an existing confirmed booking and release its seat."""
    existing = get_booking_by_pnr(pnr)
    _enforce_booking_access(existing, action="cancel")
    booking = cancel_booking(pnr)
    return jsonify(
        {
            "message": f"Booking {booking.pnr} has been cancelled.",
            "booking": booking.to_dict(),
        }
    ), 200


@bookings_bp.get("/<string:pnr>/pdf")
@limiter.limit("20 per minute")
def download_ticket_pdf(pnr: str):
    """Generate and download a high-resolution printable PDF boarding pass."""
    booking = get_booking_by_pnr(pnr)
    _enforce_booking_access(booking, action="view")
    pdf_data = generate_ticket_pdf(booking)
    clean_pnr = booking.pnr.upper()
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="BusReserve_Ticket_{clean_pnr}.pdf"',
            "Content-Type": "application/pdf",
        },
    )
