"""Database models package export for SQLAlchemy and Flask-Migrate discovery."""

from app.models.ai import AIConversationMessage, AIUsageDaily
from app.models.booking import Booking
from app.models.bus import Bus
from app.models.city import City
from app.models.notification import Notification
from app.models.payment import PaymentTransaction
from app.models.route import Route, RouteStop
from app.models.tracking import (
    JourneyShare,
    Operator,
    TripDriverAssignment,
    TripLiveLocation,
    TripLocationHistory,
)
from app.models.trip import BusSchedule, Trip, TripSeat
from app.models.user import AuthSession, User

__all__ = [
    "User",
    "AuthSession",
    "Bus",
    "City",
    "Route",
    "RouteStop",
    "BusSchedule",
    "Trip",
    "TripSeat",
    "Booking",
    "AIConversationMessage",
    "AIUsageDaily",
    "PaymentTransaction",
    "Notification",
    "Operator",
    "TripLiveLocation",
    "TripLocationHistory",
    "TripDriverAssignment",
    "JourneyShare",
]
