"""Trip and TripSeat database models."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class BusSchedule(db.Model):
    """Recurring daily schedule template used to materialize trips across the booking horizon."""

    __tablename__ = "bus_schedules"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(
        db.Integer,
        db.ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bus_id = db.Column(
        db.Integer,
        db.ForeignKey("buses.id", name="fk_bus_schedules_bus_id_buses", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operator_name = db.Column(db.String(120), nullable=False)
    bus_number = db.Column(db.String(40), nullable=False)
    bus_type = db.Column(
        db.String(40),
        nullable=False,
        default="AC_SEATER",
        server_default="AC_SEATER",
    )
    seat_layout = db.Column(
        db.String(20),
        nullable=False,
        default="2+2",
        server_default="2+2",
    )
    departure_time = db.Column(db.Time, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    base_fare = db.Column(db.Numeric(10, 2), nullable=False)
    seat_count = db.Column(db.Integer, nullable=False, default=32)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    route = db.relationship("Route", lazy="joined")
    bus = db.relationship("Bus", back_populates="schedules", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "bus_number",
            "departure_time",
            name="uq_bus_schedule_template",
        ),
        CheckConstraint("base_fare > 0", name="ck_bus_schedules_positive_fare"),
        CheckConstraint("seat_count >= 4 AND seat_count <= 80", name="ck_bus_schedules_seat_count"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "route_id": self.route_id,
            "route_name": self.route.name if self.route else None,
            "source": self.route.source if self.route else None,
            "destination": self.route.destination if self.route else None,
            "bus_id": self.bus_id,
            "operator_name": self.operator_name,
            "bus_number": self.bus_number,
            "bus_type": self.bus_type,
            "seat_layout": self.seat_layout,
            "departure_time": self.departure_time.strftime("%H:%M"),
            "arrival_time": self.arrival_time.strftime("%H:%M"),
            "base_fare": float(self.base_fare),
            "seat_count": self.seat_count,
            "is_active": self.is_active,
        }


class Trip(db.Model):
    """Scheduled bus trip operating on a route on a specific travel date."""

    __tablename__ = "trips"

    STATUS_SCHEDULED = "SCHEDULED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_COMPLETED = "COMPLETED"

    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(
        db.Integer,
        db.ForeignKey("operators.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    route_id = db.Column(
        db.Integer,
        db.ForeignKey("routes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    bus_id = db.Column(
        db.Integer,
        db.ForeignKey("buses.id", name="fk_trips_bus_id_buses", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operator_name = db.Column(db.String(120), nullable=False)
    bus_number = db.Column(db.String(40), nullable=False)
    bus_type = db.Column(
        db.String(40),
        nullable=False,
        default="AC_SEATER",
        server_default="AC_SEATER",
    )
    seat_layout = db.Column(
        db.String(20),
        nullable=False,
        default="2+2",
        server_default="2+2",
    )
    departure_time = db.Column(db.Time, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    travel_date = db.Column(db.Date, nullable=False, index=True)
    base_fare = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SCHEDULED)

    route = db.relationship("Route", back_populates="trips", lazy="joined")
    bus = db.relationship("Bus", back_populates="trips", lazy="select")
    operator = db.relationship("Operator", back_populates="trips", lazy="select")
    live_location = db.relationship(
        "TripLiveLocation",
        back_populates="trip",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    driver_assignments = db.relationship(
        "TripDriverAssignment",
        back_populates="trip",
        cascade="all, delete-orphan",
        lazy="select",
    )
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
    def source(self) -> str | None:
        return self.route.source if self.route else None

    @property
    def destination(self) -> str | None:
        return self.route.destination if self.route else None

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
            "operator_id": self.operator_id,
            "route_id": self.route_id,
            "route_name": self.route.name if self.route else None,
            "source": self.route.source if self.route else None,
            "destination": self.route.destination if self.route else None,
            "bus_id": self.bus_id,
            "operator_name": self.operator_name,
            "bus_number": self.bus_number,
            "bus_type": self.bus_type,
            "seat_layout": self.seat_layout,
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

    TIER_STANDARD = "STANDARD"
    TIER_PREMIUM = "PREMIUM"
    TIER_SLEEPER = "SLEEPER"

    POSITION_FRONT = "FRONT"
    POSITION_MIDDLE = "MIDDLE"
    POSITION_BACK = "BACK"
    POSITION_SINGLE = "SINGLE"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_number = db.Column(db.String(10), nullable=False)
    seat_type = db.Column(db.String(30), nullable=False, default=SEAT_WINDOW)
    seat_tier = db.Column(
        db.String(30),
        nullable=False,
        default=TIER_STANDARD,
        server_default=TIER_STANDARD,
    )
    seat_fare = db.Column(db.Numeric(10, 2), nullable=True)
    amenities = db.Column(db.String(255), nullable=True)
    position_type = db.Column(
        db.String(30),
        nullable=False,
        default=POSITION_MIDDLE,
        server_default=POSITION_MIDDLE,
    )

    trip = db.relationship("Trip", back_populates="seats")
    bookings = db.relationship("Booking", back_populates="seat", lazy="select")

    __table_args__ = (
        UniqueConstraint("trip_id", "seat_number", name="uq_trip_seat_number"),
        CheckConstraint(
            "seat_type IN ('WINDOW', 'AISLE', 'SLEEPER_LOWER', 'SLEEPER_UPPER')",
            name="ck_trip_seats_valid_type",
        ),
        CheckConstraint(
            "seat_tier IN ('STANDARD', 'PREMIUM', 'SLEEPER')",
            name="ck_trip_seats_valid_tier",
        ),
        CheckConstraint(
            "position_type IN ('FRONT', 'MIDDLE', 'BACK', 'SINGLE')",
            name="ck_trip_seats_valid_position",
        ),
        CheckConstraint(
            "seat_fare IS NULL OR seat_fare > 0",
            name="ck_trip_seats_positive_fare",
        ),
    )

    def amenity_list(self) -> list[str]:
        if not self.amenities:
            return []
        return [item.strip() for item in self.amenities.split(",") if item.strip()]

    def to_dict(self, is_available: bool | None = None, fare: float | None = None) -> dict:
        if self.seat_fare is not None:
            effective_fare = float(self.seat_fare)
        elif fare is not None:
            effective_fare = float(fare)
        elif self.trip and self.trip.base_fare is not None:
            effective_fare = float(self.trip.base_fare)
        else:
            effective_fare = None

        data = {
            "id": self.id,
            "trip_id": self.trip_id,
            "seat_number": self.seat_number,
            "seat_type": self.seat_type,
            "seat_tier": self.seat_tier,
            "seat_fare": float(self.seat_fare) if self.seat_fare is not None else None,
            "amenities": self.amenity_list(),
            "amenities_text": self.amenities or "",
            "position_type": self.position_type,
        }
        if is_available is not None:
            data["is_available"] = is_available
            data["status"] = "AVAILABLE" if is_available else "BOOKED"
        if effective_fare is not None:
            data["fare"] = effective_fare
        return data
