"""GPS Live Tracking, Fleet Operators, Driver Assignments, and Journey Sharing models."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Index, UniqueConstraint

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Operator(db.Model):
    """Bus fleet operating company or private agency."""

    __tablename__ = "operators"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    contact_email = db.Column(db.String(160), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    buses = db.relationship("Bus", back_populates="operator", lazy="select")
    trips = db.relationship("Trip", back_populates="operator", lazy="select")
    users = db.relationship("User", lazy="select")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TripLiveLocation(db.Model):
    """Singleton live location record per trip with atomic source management and dual sequences."""

    __tablename__ = "trip_live_locations"

    SOURCE_DRIVER = "DRIVER"
    SOURCE_OPERATOR = "OPERATOR"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    bus_id = db.Column(
        db.Integer,
        db.ForeignKey("buses.id", ondelete="SET NULL"),
        nullable=True,
    )
    driver_sequence_number = db.Column(BigInteger, nullable=True)
    operator_sequence_number = db.Column(BigInteger, nullable=True)
    driver_server_received_at = db.Column(db.DateTime(timezone=True), nullable=True)
    operator_server_received_at = db.Column(db.DateTime(timezone=True), nullable=True)
    driver_client_timestamp = db.Column(db.DateTime(timezone=True), nullable=True)
    operator_client_timestamp = db.Column(db.DateTime(timezone=True), nullable=True)
    driver_latitude = db.Column(db.Float, nullable=True)
    driver_longitude = db.Column(db.Float, nullable=True)
    driver_speed = db.Column(db.Float, nullable=True)
    driver_heading = db.Column(db.Float, nullable=True)
    driver_accuracy = db.Column(db.Float, nullable=True)
    operator_latitude = db.Column(db.Float, nullable=True)
    operator_longitude = db.Column(db.Float, nullable=True)
    operator_speed = db.Column(db.Float, nullable=True)
    operator_heading = db.Column(db.Float, nullable=True)
    operator_accuracy = db.Column(db.Float, nullable=True)
    operator_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    speed = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)
    active_source = db.Column(db.String(20), nullable=False, default=SOURCE_DRIVER)
    server_received_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    trip = db.relationship("Trip", back_populates="live_location")

    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_trip_live_location_trip_id"),
        CheckConstraint(
            "active_source IN ('DRIVER', 'OPERATOR')",
            name="ck_trip_live_locations_source",
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "speed": self.speed,
            "heading": self.heading,
            "active_source": self.active_source,
            "driver_sequence_number": self.driver_sequence_number,
            "operator_sequence_number": self.operator_sequence_number,
            "driver_server_received_at": self.driver_server_received_at.isoformat() if self.driver_server_received_at else None,
            "operator_server_received_at": self.operator_server_received_at.isoformat() if self.operator_server_received_at else None,
            "server_received_at": self.server_received_at.isoformat() if self.server_received_at else None,
            "is_active": self.is_active,
        }


class TripLocationHistory(db.Model):
    """Immutable breadcrumb audit log of recorded vehicle coordinates."""

    __tablename__ = "trip_location_history"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float, nullable=True)
    heading = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(20), nullable=False, default="DRIVER")
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    trip = db.relationship("Trip")

    __table_args__ = (
        Index("ix_trip_location_history_trip_time", "trip_id", "recorded_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed": self.speed,
            "heading": self.heading,
            "source": self.source,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class TripDriverAssignment(db.Model):
    """Driver assignment record mapping a authenticated user with ROLE_DRIVER to a trip."""

    __tablename__ = "trip_driver_assignments"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer,
        db.ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operator_id = db.Column(
        db.Integer,
        db.ForeignKey("operators.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    trip = db.relationship("Trip", back_populates="driver_assignments")
    driver = db.relationship("User", foreign_keys=[driver_id])
    operator = db.relationship("Operator", foreign_keys=[operator_id])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trip_id": self.trip_id,
            "driver_id": self.driver_id,
            "driver_name": self.driver.full_name if self.driver else None,
            "operator_id": self.operator_id,
            "operator_name": self.operator.name if self.operator else None,
            "is_active": self.is_active,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }


class JourneyShare(db.Model):
    """Hashed secure public tracking token for safe passenger journey sharing."""

    __tablename__ = "journey_shares"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    booking = db.relationship("Booking")
    user = db.relationship("User")

    def is_valid(self, now: datetime | None = None) -> bool:
        check_now = now or _utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.is_active and self.revoked_at is None and expires > check_now

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "user_id": self.user_id,
            "is_active": self.is_valid(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
