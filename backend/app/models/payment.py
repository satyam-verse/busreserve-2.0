"""Payment transaction model for multi-gateway transactions and idempotency."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Index

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PaymentTransaction(db.Model):
    """Financial payment transaction linked to a booking and/or user."""

    __tablename__ = "payment_transactions"

    STATUS_INITIATED = "INITIATED"
    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_REFUNDED = "REFUNDED"

    GATEWAY_MOCK = "MOCK_SANDBOX"
    GATEWAY_RAZORPAY = "RAZORPAY_SANDBOX"
    GATEWAY_STRIPE = "STRIPE_SANDBOX"

    METHOD_UPI = "UPI"
    METHOD_CARD = "CARD"
    METHOD_NETBANKING = "NETBANKING"
    METHOD_WALLET = "WALLET"

    id = db.Column(db.Integer, primary_key=True)
    transaction_ref = db.Column(db.String(32), unique=True, nullable=False, index=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "bookings.id", name="fk_payment_transactions_booking_id", ondelete="SET NULL"
        ),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", name="fk_payment_transactions_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gateway = db.Column(db.String(30), nullable=False, default=GATEWAY_MOCK)
    gateway_order_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_payment_id = db.Column(db.String(100), nullable=True, index=True)
    gateway_signature = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR", server_default="INR")
    status = db.Column(db.String(20), nullable=False, default=STATUS_INITIATED, index=True)
    payment_method = db.Column(db.String(30), nullable=True)
    idempotency_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    error_code = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    booking = db.relationship("Booking", back_populates="payment_transactions", lazy="select")
    user = db.relationship("User", backref="payment_transactions", lazy="select")

    __table_args__ = (Index("ix_payment_tx_booking_status", "booking_id", "status"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transaction_ref": self.transaction_ref,
            "booking_id": self.booking_id,
            "user_id": self.user_id,
            "gateway": self.gateway,
            "gateway_order_id": self.gateway_order_id,
            "gateway_payment_id": self.gateway_payment_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status,
            "payment_method": self.payment_method,
            "idempotency_key": self.idempotency_key,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
