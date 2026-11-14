"""Notification event model for persistent passenger & admin alert tracking."""

from datetime import UTC, datetime
from typing import Any

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Notification(db.Model):
    """Persistent notification record across Email, SMS, and In-App channels."""

    __tablename__ = "notifications"

    CHANNEL_EMAIL = "EMAIL"
    CHANNEL_SMS = "SMS"
    CHANNEL_WHATSAPP = "WHATSAPP"
    CHANNEL_IN_APP = "IN_APP"

    EVENT_BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    EVENT_PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    EVENT_PAYMENT_FAILED = "PAYMENT_FAILED"
    EVENT_BOOKING_CANCELLED = "BOOKING_CANCELLED"
    EVENT_REFUND_PROCESSED = "REFUND_PROCESSED"
    EVENT_ADMIN_ALERT = "ADMIN_ALERT"
    EVENT_BUS_DEPARTED = "BUS_DEPARTED"
    EVENT_JOURNEY_STARTED = "JOURNEY_STARTED"
    EVENT_UPCOMING_STOP = "UPCOMING_STOP"
    EVENT_DELAY_ALERT = "DELAY_ALERT"
    EVENT_ARRIVAL = "ARRIVAL"
    EVENT_JOURNEY_SHARED = "JOURNEY_SHARED"

    STATUS_PENDING = "PENDING"
    STATUS_SENT = "SENT"
    STATUS_FAILED = "FAILED"
    STATUS_MOCK = "MOCK"
    STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", name="fk_notifications_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", name="fk_notifications_booking_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel = db.Column(db.String(20), nullable=False, default=CHANNEL_IN_APP)
    recipient = db.Column(db.String(160), nullable=False)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SENT)
    is_read = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false(), index=True
    )
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    user = db.relationship("User", backref="notifications", lazy="select")
    booking = db.relationship("Booking", backref="notifications", lazy="select")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "booking_id": self.booking_id,
            "channel": self.channel,
            "recipient": self.recipient,
            "event_type": self.event_type,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "is_read": self.is_read,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
