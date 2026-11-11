"""Trip and TripSeat database models."""

from datetime import datetime, timedelta

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.extensions import db


class Trip(db.Model):
    """Scheduled bus trip operating on a route on a specific travel date."""

    __tablename__ = "trips"

    STATUS_SCHEDULED = "SCHEDULED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_COMPLETED = "COMPLETED"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(
        db.Integer,
        db.ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    operator_name = db.Column(db.String(120), nullable=False)
    bus_number = db.Column(db.String(40), nullable=False)
    departure_time = db.Column(db.Time, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    travel_date = db.Column(db.Date, nullable=False, index=True)
    base_fare = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SCHEDULED)

    route = db.relationship("Route", back_populates="trips", lazy="joined")
    seats = db.relationship(
        "TripSeat",
        back_populates="trip",
        order_by="TripSeat.id",
        cascade="all, delete-orphan",
        lazy="select",
    )
    bookings = db.relationship("Booking", back_populates="trip", lazy="select")

    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "bus_number",
            "travel_date",
            "departure_time",
            name="uq_trip_schedule",
        ),
        Index("ix_trips_travel_date_status", "travel_date", "status"),
        CheckConstraint("base_fare > 0", name="ck_trips_positive_fare"),
        CheckConstraint(
            "status IN ('SCHEDULED', 'CANCELLED', 'COMPLETED')",
            name="ck_trips_valid_status",
        ),
    )

    @property
    def duration_minutes(self) -> int:
        dep_dt = datetime.combine(self.travel_date, self.departure_time)
        arr_dt = datetime.combine(self.travel_date, self.arrival_time)
        if arr_dt <= dep_dt:
            arr_dt += timedelta(days=1)
        return int((arr_dt - dep_dt).total_seconds() // 60)

    @property
    def duration_display(self) -> str:
        minutes = self.duration_minutes
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins:02d}m"

    def to_dict(self, available_seats: int | None = None, total_seats: int | None = None) -> dict:
        data = {
            "id": self.id,
            "route_id": self.route_id,
            "route_name": self.route.name if self.route else None,
            "source": self.route.source if self.route else None,
            "destination": self.route.destination if self.route else None,
            "operator_name": self.operator_name,
            "bus_number": self.bus_number,
            "departure_time": self.departure_time.strftime("%H:%M"),
            "arrival_time": self.arrival_time.strftime("%H:%M"),
            "travel_date": self.travel_date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "duration_display": self.duration_display,
            "base_fare": float(self.base_fare),
            "status": self.status,
        }
        if available_seats is not None:
            data["available_seats"] = available_seats
        if total_seats is not None:
            data["total_seats"] = total_seats
        return data


class TripSeat(db.Model):
    """Seat inventory item belonging to a specific Trip."""

    __tablename__ = "trip_seats"

    SEAT_WINDOW = "WINDOW"
    SEAT_AISLE = "AISLE"
    SEAT_SLEEPER_LOWER = "SLEEPER_LOWER"
    SEAT_SLEEPER_UPPER = "SLEEPER_UPPER"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_number = db.Column(db.String(10), nullable=False)
    seat_type = db.Column(db.String(30), nullable=False, default=SEAT_WINDOW)

    trip = db.relationship("Trip", back_populates="seats")
    bookings = db.relationship("Booking", back_populates="seat", lazy="select")

    __table_args__ = (
        UniqueConstraint("trip_id", "seat_number", name="uq_trip_seat_number"),
        CheckConstraint(
            "seat_type IN ('WINDOW', 'AISLE', 'SLEEPER_LOWER', 'SLEEPER_UPPER')",
            name="ck_trip_seats_valid_type",
        ),
    )

    def to_dict(self, is_available: bool | None = None, fare: float | None = None) -> dict:
        data = {
            "id": self.id,
            "trip_id": self.trip_id,
            "seat_number": self.seat_number,
            "seat_type": self.seat_type,
        }
        if is_available is not None:
            data["is_available"] = is_available
            data["status"] = "AVAILABLE" if is_available else "BOOKED"
        if fare is not None:
            data["fare"] = fare
        return data
