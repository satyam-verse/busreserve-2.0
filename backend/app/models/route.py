"""Route and RouteStop database models."""

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.extensions import db


class Route(db.Model):
    """Bus route between a primary source and destination city."""

    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    source = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    distance_km = db.Column(db.Integer, nullable=True)
    estimated_duration_minutes = db.Column(db.Integer, nullable=True)

    stops = db.relationship(
        "RouteStop",
        back_populates="route",
        order_by="RouteStop.stop_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    trips = db.relationship("Trip", back_populates="route", lazy="select")

    __table_args__ = (
        Index("ix_routes_source_destination", "source", "destination"),
        CheckConstraint("source <> destination", name="ck_routes_distinct_endpoints"),
        CheckConstraint(
            "distance_km IS NULL OR distance_km > 0",
            name="ck_routes_positive_distance",
        ),
        CheckConstraint(
            "estimated_duration_minutes IS NULL OR estimated_duration_minutes > 0",
            name="ck_routes_positive_duration",
        ),
    )

    def to_dict(self, include_stops: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "destination": self.destination,
            "distance_km": self.distance_km,
            "estimated_duration_minutes": self.estimated_duration_minutes,
        }
        if include_stops:
            data["stops"] = [stop.to_dict() for stop in self.stops]
        return data


class RouteStop(db.Model):
    """Ordered boarding/drop stop along a bus route."""

    __tablename__ = "route_stops"

    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(
        db.Integer,
        db.ForeignKey("routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stop_name = db.Column(db.String(120), nullable=False)
    city_name = db.Column(db.String(100), nullable=True, index=True)
    stop_order = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    route = db.relationship("Route", back_populates="stops")

    __table_args__ = (
        UniqueConstraint("route_id", "stop_order", name="uq_route_stop_order"),
        UniqueConstraint("route_id", "stop_name", name="uq_route_stop_name"),
        CheckConstraint("stop_order >= 1", name="ck_route_stops_positive_order"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "route_id": self.route_id,
            "stop_name": self.stop_name,
            "city_name": self.city_name or self.stop_name.split("(")[0].strip(),
            "stop_order": self.stop_order,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
