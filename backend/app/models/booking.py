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

    REFUND_NONE = "NONE"
    REFUND_PENDING = "PENDING"
    REFUND_PROCESSED = "PROCESSED"
    REFUND_NOT_APPLICABLE = "NOT_APPLICABLE"

    id = db.Column(db.Integer, primary_key=True)
    pnr = db.Column(db.String(16), nullable=False, unique=True, index=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", name="fk_bookings_user_id_users", ondelete="SET NULL"),
        nullable=True,
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
    refund_status = db.Column(
        db.String(30),
        nullable=False,
        default=REFUND_NONE,
        server_default=REFUND_NONE,
    )
    refund_amount = db.Column(db.Numeric(10, 2), nullable=True)
    refunded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancellation_reason = db.Column(db.String(255), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )

    user = db.relationship("User", back_populates="bookings", lazy="select")
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
    payment_transactions = db.relationship(
        "PaymentTransaction",
        back_populates="booking",
        lazy="select",
        order_by="PaymentTransaction.id.desc()",
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
        CheckConstraint(
            "refund_status IN ('NONE', 'PENDING', 'PROCESSED', 'NOT_APPLICABLE')",
            name="ck_bookings_valid_refund_status",
        ),
        CheckConstraint(
            "refund_amount IS NULL OR refund_amount >= 0",
            name="ck_bookings_non_negative_refund",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pnr": self.pnr,
            "trip_id": self.trip_id,
            "user_id": self.user_id,
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
            "refund_status": self.refund_status,
            "refund_amount": float(self.refund_amount) if self.refund_amount is not None else None,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
            "cancellation_reason": self.cancellation_reason,
            "is_demo_payment": len(self.payment_transactions) == 0,
            "payment": (
                self.payment_transactions[0].to_dict() if self.payment_transactions else None
            ),
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "trip": self.trip.to_dict() if self.trip else None,
        }
