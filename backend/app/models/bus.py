"""Bus fleet database model with operator, registration, type, seat layout, and capacity."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Bus(db.Model):
    """Physical bus fleet unit managed by administrators."""

    __tablename__ = "buses"

    TYPE_AC_SEATER = "AC_SEATER"
    TYPE_NON_AC_SEATER = "NON_AC_SEATER"
    TYPE_AC_SLEEPER = "AC_SLEEPER"
    TYPE_SEATER_SLEEPER = "SEATER_SLEEPER"
    TYPE_VOLVO_MULTI_AXLE = "VOLVO_MULTI_AXLE"

    VALID_TYPES = (
        TYPE_AC_SEATER,
        TYPE_NON_AC_SEATER,
        TYPE_AC_SLEEPER,
        TYPE_SEATER_SLEEPER,
        TYPE_VOLVO_MULTI_AXLE,
    )

    LAYOUT_2_2 = "2+2"
    LAYOUT_2_1 = "2+1"
    LAYOUT_1_2 = "1+2"
    VALID_LAYOUTS = (LAYOUT_2_2, LAYOUT_2_1, LAYOUT_1_2)

    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(
        db.Integer,
        db.ForeignKey("operators.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operator_name = db.Column(db.String(120), nullable=False, index=True)
    registration_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    bus_type = db.Column(db.String(40), nullable=False, default=TYPE_AC_SEATER)
    seat_layout = db.Column(db.String(20), nullable=False, default=LAYOUT_2_2)
    total_seats = db.Column(db.Integer, nullable=False, default=32)
    amenities = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    operator = db.relationship("Operator", back_populates="buses", lazy="select")
    schedules = db.relationship("BusSchedule", back_populates="bus", lazy="select")
    trips = db.relationship("Trip", back_populates="bus", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "bus_type IN ('AC_SEATER', 'NON_AC_SEATER', 'AC_SLEEPER', "
            "'SEATER_SLEEPER', 'VOLVO_MULTI_AXLE')",
            name="ck_buses_valid_type",
        ),
        CheckConstraint(
            "seat_layout IN ('2+2', '2+1', '1+2')",
            name="ck_buses_valid_layout",
        ),
        CheckConstraint(
            "total_seats >= 4 AND total_seats <= 80",
            name="ck_buses_seat_count",
        ),
    )

    def amenity_list(self) -> list[str]:
        if not self.amenities:
            return []
        return [item.strip() for item in self.amenities.split(",") if item.strip()]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "registration_number": self.registration_number,
            "bus_type": self.bus_type,
            "seat_layout": self.seat_layout,
            "total_seats": self.total_seats,
            "amenities": self.amenity_list(),
            "amenities_text": self.amenities or "",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
