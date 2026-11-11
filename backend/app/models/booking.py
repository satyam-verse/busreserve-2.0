"""Booking database model with PostgreSQL partial unique index against double-booking."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Index, text

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Booking(db.Model):
    """Passenger seat reservation linked to a Trip, TripSeat, and boarding/drop stops."""

    __tablename__ = "bookings"

    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"

    id = db.Column(db.Integer, primary_key=True)
    pnr = db.Column(db.String(16), nullable=False, unique=True, index=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    seat_id = db.Column(
        db.Integer,
        db.ForeignKey("trip_seats.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    passenger_name = db.Column(db.String(120), nullable=False)
    passenger_email = db.Column(db.String(160), nullable=False)
    passenger_phone = db.Column(db.String(20), nullable=False)
    boarding_stop_id = db.Column(
        db.Integer,
        db.ForeignKey("route_stops.id", ondelete="RESTRICT"),
        nullable=False,
    )
    drop_stop_id = db.Column(
        db.Integer,
        db.ForeignKey("route_stops.id", ondelete="RESTRICT"),
        nullable=False,
    )
    total_fare = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_CONFIRMED)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )

    trip = db.relationship("Trip", back_populates="bookings", lazy="joined")
    seat = db.relationship("TripSeat", back_populates="bookings", lazy="joined")
    boarding_stop = db.relationship(
        "RouteStop",
        foreign_keys=[boarding_stop_id],
        lazy="joined",
    )
    drop_stop = db.relationship(
        "RouteStop",
        foreign_keys=[drop_stop_id],
        lazy="joined",
    )

    __table_args__ = (
        # Database-level guarantee: only one CONFIRMED reservation per (trip_id, seat_id).
        # Cancelled bookings remain in history while immediately releasing the seat for rebooking.
        Index(
            "uq_active_booking_trip_seat",
            "trip_id",
            "seat_id",
            unique=True,
            postgresql_where=text("status = 'CONFIRMED'"),
        ),
        Index("ix_bookings_trip_status", "trip_id", "status"),
        CheckConstraint("boarding_stop_id <> drop_stop_id", name="ck_bookings_different_stops"),
        CheckConstraint("total_fare >= 0", name="ck_bookings_non_negative_fare"),
        CheckConstraint("status IN ('CONFIRMED', 'CANCELLED')", name="ck_bookings_valid_status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pnr": self.pnr,
            "trip_id": self.trip_id,
            "seat_id": self.seat_id,
            "seat_number": self.seat.seat_number if self.seat else None,
            "seat_type": self.seat.seat_type if self.seat else None,
            "passenger_name": self.passenger_name,
            "passenger_email": self.passenger_email,
            "passenger_phone": self.passenger_phone,
            "boarding_stop": self.boarding_stop.to_dict() if self.boarding_stop else None,
            "drop_stop": self.drop_stop.to_dict() if self.drop_stop else None,
            "total_fare": float(self.total_fare),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "trip": self.trip.to_dict() if self.trip else None,
        }
