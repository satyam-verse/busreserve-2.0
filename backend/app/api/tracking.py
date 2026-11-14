"""Live GPS Tracking, SSE Streams, Driver/Operator ingestion, and Journey Sharing APIs."""

import json
import time
from typing import Generator

from flask import Blueprint, Response, g, jsonify, request

from app.extensions import db, limiter
from app.models.user import User
from app.services.tracking_service import (
    create_journey_share,
    get_active_trip_location,
    get_shared_journey,
    record_driver_gps,
    record_operator_gps,
    revoke_journey_share,
)
from app.utils.auth import require_auth, require_driver, require_roles
from app.utils.schemas import GPSPingSchema, JourneyShareCreateSchema

tracking_bp = Blueprint("tracking", __name__, url_prefix="/api/tracking")

_gps_ping_schema = GPSPingSchema()
_journey_share_schema = JourneyShareCreateSchema()


@tracking_bp.post("/driver/location")
@limiter.limit("120 per minute")
@require_driver
def driver_location_ping():
    """Ingest real-time GPS coordinates directly from authenticated driver device."""
    payload = _gps_ping_schema.load(request.get_json() or {})
    result = record_driver_gps(g.current_user, payload)
    return jsonify(result), 200


@tracking_bp.post("/operator/location")
@limiter.limit("120 per minute")
@require_roles(User.ROLE_OPERATOR, User.ROLE_ADMIN)
def operator_location_ping():
    """Ingest operator fleet GPS coordinates under verified operator takeover."""
    payload = _gps_ping_schema.load(request.get_json() or {})
    result = record_operator_gps(g.current_user, payload)
    return jsonify(result), 200


@tracking_bp.get("/trip/<int:trip_id>")
@limiter.limit("120 per minute")
def get_trip_tracking(trip_id: int):
    """Retrieve public live location and signal freshness for a scheduled trip."""
    tracking_data = get_active_trip_location(trip_id)
    return jsonify(tracking_data), 200


@tracking_bp.get("/stream/<int:trip_id>")
def stream_trip_tracking(trip_id: int):
    """Server-Sent Events (SSE) stream for real-time trip GPS tracking updates."""
    def generate_events() -> Generator[str, None, None]:
        # Stream location snapshot and heartbeat
        for _ in range(5):
            data = get_active_trip_location(trip_id)
            yield f"event: location\ndata: {json.dumps(data)}\n\n"
            time.sleep(2)
        yield "event: heartbeat\ndata: {\"status\":\"alive\"}\n\n"

    return Response(
        generate_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@tracking_bp.post("/share")
@limiter.limit("30 per minute")
@require_auth
def create_share_link():
    """Generate a secure, hashed live journey tracking link for passenger's booking."""
    payload = _journey_share_schema.load(request.get_json() or {})
    booking_id = payload["booking_id"]
    validity_hours = payload.get("validity_hours", 24)

    share_info = create_journey_share(
        user=g.current_user,
        booking_id=booking_id,
        validity_hours=validity_hours,
    )
    return jsonify(share_info), 201


@tracking_bp.delete("/share/<token>")
@limiter.limit("30 per minute")
@require_auth
def revoke_share_link(token: str):
    """Immediately revoke an active journey sharing link."""
    revoke_journey_share(g.current_user, token)
    return jsonify({"message": "Journey sharing link revoked successfully."}), 200


@tracking_bp.get("/shared/<token>")
@limiter.limit("60 per minute")
def view_shared_journey(token: str):
    """Public tracking view for shared journeys with zero passenger PII."""
    shared_data = get_shared_journey(token)
    return jsonify(shared_data), 200
