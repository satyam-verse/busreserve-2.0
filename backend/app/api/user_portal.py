"""Protected passenger profile, session management, and My Bookings REST API."""

from flask import Blueprint, g, jsonify, request

from app.services.admin_service import list_user_bookings
from app.services.auth_service import (
    change_user_password,
    list_user_sessions,
    update_user_profile,
)
from app.services.booking_service import cancel_booking, get_booking_by_pnr
from app.utils.auth import require_auth
from app.utils.errors import ForbiddenError, ValidationAPIError
from app.utils.schemas import ChangePasswordSchema, ProfileUpdateSchema

user_bp = Blueprint("user_portal", __name__, url_prefix="/api/user")

_profile_schema = ProfileUpdateSchema()
_password_schema = ChangePasswordSchema()


def _json_body() -> dict:
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")
    return raw


@user_bp.get("/profile")
@require_auth
def get_profile():
    """Return the authenticated user's profile."""
    return jsonify({"user": g.current_user.to_dict()}), 200


@user_bp.patch("/profile")
@require_auth
def patch_profile():
    """Update authenticated user's name or phone number."""
    data = _profile_schema.load(_json_body())
    updated = update_user_profile(g.current_user, data)
    return jsonify({"message": "Profile updated.", "user": updated.to_dict()}), 200


@user_bp.post("/change-password")
@require_auth
def change_password():
    """Change authenticated user's password and revoke other active sessions."""
    data = _password_schema.load(_json_body())
    change_user_password(
        user=g.current_user,
        current_password=data["current_password"],
        new_password=data["new_password"],
        current_session_jti=g.current_session.jti,
    )
    return jsonify({"message": "Password updated and other active sessions signed out."}), 200


@user_bp.get("/sessions")
@require_auth
def get_sessions():
    """List active and recent authentication sessions for the current user."""
    sessions = list_user_sessions(g.current_user.id, current_jti=g.current_session.jti)
    return jsonify({"sessions": sessions, "count": len(sessions)}), 200


@user_bp.get("/bookings")
@require_auth
def get_my_bookings():
    """Return all bookings owned by the authenticated user."""
    status = request.args.get("status")
    bookings = list_user_bookings(g.current_user.id, status=status)
    return jsonify({"bookings": bookings, "count": len(bookings)}), 200


@user_bp.post("/bookings/<string:pnr>/cancel")
@require_auth
def cancel_my_booking(pnr: str):
    """Cancel a booking owned by the authenticated user."""
    existing = get_booking_by_pnr(pnr)
    if existing.user_id != g.current_user.id:
        raise ForbiddenError("You can only cancel reservations linked to your account.")
    booking = cancel_booking(pnr)
    return jsonify(
        {
            "message": f"Booking {booking.pnr} has been cancelled.",
            "booking": booking.to_dict(),
        }
    ), 200
