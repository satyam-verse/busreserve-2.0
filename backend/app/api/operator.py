"""Operator REST API blueprint: fleet oversight, active trip management, and driver assignment."""

from flask import Blueprint, g, jsonify, request

from app.extensions import db, limiter
from app.models.bus import Bus
from app.models.tracking import Operator, TripDriverAssignment, TripLiveLocation
from app.models.trip import Trip
from app.models.user import User
from app.services.tracking_service import get_active_trip_location
from app.utils.auth import require_roles
from app.utils.errors import ForbiddenError, NotFoundError, ValidationAPIError
from app.utils.schemas import DriverAssignSchema

operator_bp = Blueprint("operator", __name__, url_prefix="/api/operator")
_assign_schema = DriverAssignSchema()


@operator_bp.get("/fleet")
@limiter.limit("60 per minute")
@require_roles(User.ROLE_OPERATOR, User.ROLE_ADMIN)
def get_fleet_status():
    """Retrieve all buses belonging to the operator with real-time GPS health."""
    operator_id = g.current_user.operator_id
    if g.current_user.role == User.ROLE_ADMIN and not operator_id:
        buses = Bus.query.filter_by(is_active=True).all()
    else:
        if not operator_id:
            raise ForbiddenError("User is not affiliated with any active operator.")
        buses = Bus.query.filter_by(operator_id=operator_id, is_active=True).all()

    fleet_data = []
    for bus in buses:
        # Find today's active or next scheduled trip
        active_trip = (
            Trip.query.filter_by(bus_id=bus.id, status=Trip.STATUS_SCHEDULED)
            .order_by(Trip.travel_date.asc(), Trip.departure_time.asc())
            .first()
        )
        tracking_info = get_active_trip_location(active_trip.id) if active_trip else None
        fleet_data.append(
            {
                "bus": bus.to_dict(),
                "active_trip": active_trip.to_dict() if active_trip else None,
                "tracking": tracking_info,
            }
        )

    return jsonify({"fleet": fleet_data, "count": len(fleet_data)}), 200


@operator_bp.get("/trips")
@limiter.limit("60 per minute")
@require_roles(User.ROLE_OPERATOR, User.ROLE_ADMIN)
def get_operator_trips():
    """List scheduled trips for the operator's fleet."""
    operator_id = g.current_user.operator_id
    if g.current_user.role == User.ROLE_ADMIN and not operator_id:
        trips = Trip.query.filter_by(status=Trip.STATUS_SCHEDULED).limit(50).all()
    else:
        if not operator_id:
            raise ForbiddenError("User is not affiliated with any active operator.")
        trips = (
            Trip.query.filter_by(operator_id=operator_id, status=Trip.STATUS_SCHEDULED)
            .limit(50)
            .all()
        )

    results = []
    for trip in trips:
        assignment = (
            TripDriverAssignment.query.filter_by(trip_id=trip.id, is_active=True)
            .order_by(TripDriverAssignment.assigned_at.desc())
            .first()
        )
        results.append(
            {
                "trip": trip.to_dict(),
                "assigned_driver": assignment.to_dict() if assignment else None,
            }
        )

    return jsonify({"trips": results, "count": len(results)}), 200


@operator_bp.post("/assign-driver")
@limiter.limit("30 per minute")
@require_roles(User.ROLE_OPERATOR, User.ROLE_ADMIN)
def assign_driver_to_trip():
    """Assign an authenticated driver to a specific trip."""
    payload = _assign_schema.load(request.get_json() or {})
    driver_id = payload["driver_id"]
    trip_id = payload["trip_id"]

    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip {trip_id} was not found.")

    if g.current_user.role != User.ROLE_ADMIN:
        if g.current_user.operator_id != trip.operator_id:
            raise ForbiddenError("You can only assign drivers to your own trips.")

    driver = db.session.get(User, driver_id)
    if not driver or driver.role != User.ROLE_DRIVER:
        raise ValidationAPIError(f"User {driver_id} is not an active driver.")

    # Deactivate existing assignments for this trip
    existing = TripDriverAssignment.query.filter_by(trip_id=trip_id, is_active=True).all()
    for e in existing:
        e.is_active = False

    new_assignment = TripDriverAssignment(
        trip_id=trip_id,
        driver_id=driver_id,
        operator_id=trip.operator_id or g.current_user.operator_id,
        is_active=True,
    )
    db.session.add(new_assignment)
    db.session.commit()
    db.session.refresh(new_assignment)

    return jsonify(
        {
            "message": f"Driver {driver.full_name} assigned to trip {trip_id}.",
            "assignment": new_assignment.to_dict(),
        }
    ), 201
