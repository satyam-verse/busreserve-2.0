"""Driver REST API blueprint: assigned trips, departure dispatch, and arrival confirmation."""

from flask import Blueprint, g, jsonify

from app.extensions import db, limiter
from app.models.notification import Notification
from app.models.tracking import TripDriverAssignment
from app.models.trip import Trip
from app.models.user import User
from app.services.notification_service import notify_arrival, notify_bus_departed
from app.utils.auth import require_driver
from app.utils.errors import ForbiddenError, NotFoundError

driver_bp = Blueprint("driver", __name__, url_prefix="/api/driver")


@driver_bp.get("/trips")
@limiter.limit("60 per minute")
@require_driver
def list_assigned_trips():
    """List all scheduled bus trips assigned to the authenticated driver."""
    driver_id = g.current_user.id

    assignments = (
        db.session.query(TripDriverAssignment)
        .filter(
            TripDriverAssignment.driver_id == driver_id,
            TripDriverAssignment.is_active.is_(True),
        )
        .all()
    )

    trip_ids = [a.trip_id for a in assignments]
    if not trip_ids and g.current_user.role == User.ROLE_ADMIN:
        # For admin testing/demo, list active scheduled trips
        trips = Trip.query.filter_by(status=Trip.STATUS_SCHEDULED).limit(10).all()
    else:
        trips = Trip.query.filter(Trip.id.in_(trip_ids)).all() if trip_ids else []

    return jsonify(
        {
            "driver": g.current_user.to_dict(),
            "trips": [t.to_dict() for t in trips],
            "count": len(trips),
        }
    ), 200


@driver_bp.post("/trip/<int:trip_id>/depart")
@limiter.limit("30 per minute")
@require_driver
def mark_trip_departed(trip_id: int):
    """Mark a scheduled trip as departed and dispatch multi-channel departure notifications."""
    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip {trip_id} was not found.")

    if g.current_user.role != User.ROLE_ADMIN:
        assignment = TripDriverAssignment.query.filter_by(
            trip_id=trip_id,
            driver_id=g.current_user.id,
            is_active=True,
        ).first()
        if not assignment:
            raise ForbiddenError("You are not assigned to this trip.")

    # Dispatch departure alerts
    notifications = notify_bus_departed(trip_id)
    sent_count = len([n for n in notifications if n.status == Notification.STATUS_SENT])
    status_summary = {
        "sent": sent_count,
        "mock": len([n for n in notifications if n.status == Notification.STATUS_MOCK]),
        "not_configured": len([n for n in notifications if n.status == Notification.STATUS_NOT_CONFIGURED]),
        "failed": len([n for n in notifications if n.status == Notification.STATUS_FAILED]),
    }

    return jsonify(
        {
            "message": f"Trip {trip_id} departure recorded.",
            "trip_id": trip_id,
            "notifications_dispatched": sent_count,
            "delivery_status": status_summary,
        }
    ), 200


@driver_bp.post("/trip/<int:trip_id>/arrive")
@limiter.limit("30 per minute")
@require_driver
def mark_trip_arrived(trip_id: int):
    """Mark a trip as arrived/completed at destination and alert passengers."""
    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip {trip_id} was not found.")

    if g.current_user.role != User.ROLE_ADMIN:
        assignment = TripDriverAssignment.query.filter_by(
            trip_id=trip_id,
            driver_id=g.current_user.id,
            is_active=True,
        ).first()
        if not assignment:
            raise ForbiddenError("You are not assigned to this trip.")

    trip.status = Trip.STATUS_COMPLETED
    db.session.commit()

    destination_name = trip.destination or "Destination"
    notifications = notify_arrival(trip_id, destination_name)
    sent_count = len([n for n in notifications if n.status == Notification.STATUS_SENT])
    status_summary = {
        "sent": sent_count,
        "mock": len([n for n in notifications if n.status == Notification.STATUS_MOCK]),
        "not_configured": len([n for n in notifications if n.status == Notification.STATUS_NOT_CONFIGURED]),
        "failed": len([n for n in notifications if n.status == Notification.STATUS_FAILED]),
    }

    return jsonify(
        {
            "message": f"Trip {trip_id} arrival confirmed. Trip status set to COMPLETED.",
            "trip_id": trip_id,
            "status": trip.status,
            "notifications_dispatched": sent_count,
            "delivery_status": status_summary,
        }
    ), 200
