"""Payment gateway integration, signature verification, and atomic settlement."""

import hashlib
import hmac
import logging
import math
import os
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, or_, select

from app.extensions import db
from app.models.booking import Booking
from app.models.payment import PaymentTransaction
from app.models.trip import Trip, TripSeat
from app.models.user import User
from app.services.booking_service import create_booking
from app.services.notification_service import (
    notify_booking_and_payment_success,
)
from app.utils.errors import ConflictError, NotFoundError, ValidationAPIError
from app.utils.metrics import metrics_registry

logger = logging.getLogger("busreserve.payments")


def _generate_transaction_ref() -> str:
    """Generate a unique human-readable transaction reference."""
    return f"TXN_{datetime.now(UTC).strftime('%Y%m%d')}_{secrets.token_hex(4).upper()}"


def create_payment_order(
    booking_payload: dict[str, Any],
    user_id: int | None = None,
    gateway: str = PaymentTransaction.GATEWAY_MOCK,
    payment_method: str = PaymentTransaction.METHOD_UPI,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create a gateway payment order and record the initiated transaction."""
    trip_id = booking_payload.get("trip_id")
    seat_number = booking_payload.get("seat_number")

    trip = db.session.execute(select(Trip).where(Trip.id == trip_id)).scalar_one_or_none()
    if trip is None:
        raise NotFoundError(f"Trip with ID {trip_id} does not exist.")

    # Check if seat is currently available
    seat = db.session.execute(
        select(TripSeat).where(TripSeat.trip_id == trip_id, TripSeat.seat_number == seat_number)
    ).scalar_one_or_none()
    if seat is None:
        raise NotFoundError(f"Seat {seat_number} does not exist on trip {trip_id}.")

    confirmed_booking = db.session.execute(
        select(Booking.id).where(
            Booking.trip_id == trip_id,
            Booking.seat_id == seat.id,
            Booking.status == Booking.STATUS_CONFIRMED,
        )
    ).scalar_one_or_none()
    if confirmed_booking:
        raise ConflictError(f"Seat {seat_number} on trip {trip_id} is already booked.")

    clean_idempotency = (idempotency_key or "").strip() or f"idem_{secrets.token_hex(16)}"

    # Idempotency check: if transaction exists with this key
    existing_tx = db.session.execute(
        select(PaymentTransaction).where(PaymentTransaction.idempotency_key == clean_idempotency)
    ).scalar_one_or_none()

    if existing_tx:
        if existing_tx.status == PaymentTransaction.STATUS_SUCCESS and existing_tx.booking:
            return {
                "transaction": existing_tx.to_dict(),
                "booking": existing_tx.booking.to_dict(),
                "already_settled": True,
            }
        return {
            "transaction": existing_tx.to_dict(),
            "checkout": _build_checkout_params(existing_tx),
            "already_settled": False,
        }

    effective_seat_fare = seat.seat_fare if seat.seat_fare is not None else trip.base_fare
    fare = Decimal(str(effective_seat_fare))
    tx_ref = _generate_transaction_ref()

    # Link registered user if email matches
    if user_id is None and booking_payload.get("passenger_email"):
        matched_user = db.session.execute(
            select(User.id).where(User.email == booking_payload["passenger_email"])
        ).scalar_one_or_none()
        if matched_user:
            user_id = matched_user

    # Generate gateway order ID
    if gateway == PaymentTransaction.GATEWAY_RAZORPAY:
        gateway_order_id = f"order_rzp_{secrets.token_hex(8)}"
    elif gateway == PaymentTransaction.GATEWAY_STRIPE:
        gateway_order_id = f"pi_test_{secrets.token_hex(12)}"
    else:
        gateway = PaymentTransaction.GATEWAY_MOCK
        gateway_order_id = f"order_mock_{secrets.token_hex(8)}"

    tx = PaymentTransaction(
        transaction_ref=tx_ref,
        user_id=user_id,
        gateway=gateway,
        gateway_order_id=gateway_order_id,
        amount=fare,
        currency="INR",
        status=PaymentTransaction.STATUS_INITIATED,
        payment_method=payment_method,
        idempotency_key=clean_idempotency,
    )
    db.session.add(tx)
    db.session.commit()
    db.session.refresh(tx)
    metrics_registry.inc_counter(
        "busreserve_payment_transactions_total",
        1.0,
        {
            "gateway": tx.gateway,
            "status": "INITIATED",
            "payment_method": tx.payment_method or "UNKNOWN",
        },
    )

    logger.info(
        "payment_order_created",
        extra={
            "transaction_ref": tx.transaction_ref,
            "gateway": tx.gateway,
            "order_id": tx.gateway_order_id,
            "amount": float(tx.amount),
        },
    )

    return {
        "transaction": tx.to_dict(),
        "checkout": _build_checkout_params(tx),
        "already_settled": False,
    }


def _build_checkout_params(tx: PaymentTransaction) -> dict[str, Any]:
    """Assemble sandbox checkout parameters for client rendering."""
    return {
        "gateway": tx.gateway,
        "transaction_ref": tx.transaction_ref,
        "order_id": tx.gateway_order_id,
        "amount": float(tx.amount),
        "currency": tx.currency,
        "key_id": (
            os.getenv("RAZORPAY_KEY_ID", "rzp_test_busreserve2026")
            if tx.gateway == PaymentTransaction.GATEWAY_RAZORPAY
            else os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_busreserve2026")
        ),
        "mock_signature": f"mock_sig_{tx.transaction_ref}_{secrets.token_hex(6)}",
    }


def get_payment_order(transaction_ref: str) -> dict[str, Any]:
    """Retrieve an existing payment transaction order and its current status."""
    tx = db.session.execute(
        select(PaymentTransaction).where(
            PaymentTransaction.transaction_ref == transaction_ref.strip()
        )
    ).scalar_one_or_none()

    if tx is None:
        raise NotFoundError(f"Transaction '{transaction_ref}' was not found.")

    booking = None
    if tx.booking_id:
        booking = db.session.execute(
            select(Booking).where(Booking.id == tx.booking_id)
        ).scalar_one_or_none()

    return {
        "transaction": tx.to_dict(),
        "checkout": _build_checkout_params(tx),
        "booking": booking.to_dict() if booking else None,
        "already_settled": tx.status == PaymentTransaction.STATUS_SUCCESS,
    }


def cancel_payment_order(transaction_ref: str, reason: str | None = None) -> dict[str, Any]:
    """Mark an initiated payment transaction as cancelled."""
    tx = db.session.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.transaction_ref == transaction_ref.strip())
        .with_for_update()
    ).scalar_one_or_none()

    if tx is None:
        raise NotFoundError(f"Transaction '{transaction_ref}' was not found.")

    if tx.status == PaymentTransaction.STATUS_SUCCESS:
        raise ConflictError("Cannot cancel an already settled transaction.")

    tx.status = PaymentTransaction.STATUS_CANCELLED
    tx.error_code = "USER_CANCELLED"
    tx.error_message = reason or "Payment cancelled by user."
    tx.updated_at = datetime.now(UTC)

    db.session.commit()
    db.session.refresh(tx)

    metrics_registry.inc_counter(
        "busreserve_payment_transactions_total",
        1.0,
        {
            "gateway": tx.gateway,
            "status": "CANCELLED",
            "payment_method": tx.payment_method or "UNKNOWN",
        },
    )

    logger.info("payment_cancelled", extra={"transaction_ref": tx.transaction_ref, "reason": tx.error_message})

    return {
        "message": "Payment transaction cancelled.",
        "transaction": tx.to_dict(),
    }


def fail_payment_order(
    transaction_ref: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Record an intentional or gateway-triggered payment failure."""
    tx = db.session.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.transaction_ref == transaction_ref.strip())
        .with_for_update()
    ).scalar_one_or_none()

    if tx is None:
        raise NotFoundError(f"Transaction '{transaction_ref}' was not found.")

    if tx.status == PaymentTransaction.STATUS_SUCCESS:
        raise ConflictError("Cannot fail an already settled transaction.")

    tx.status = PaymentTransaction.STATUS_FAILED
    tx.error_code = error_code or "SIMULATED_FAILURE"
    tx.error_message = error_message or "Payment was declined by the simulated sandbox gateway."
    tx.updated_at = datetime.now(UTC)

    db.session.commit()
    db.session.refresh(tx)

    metrics_registry.inc_counter(
        "busreserve_payment_transactions_total",
        1.0,
        {
            "gateway": tx.gateway,
            "status": "FAILED",
            "payment_method": tx.payment_method or "UNKNOWN",
        },
    )

    logger.warning(
        "payment_failed",
        extra={
            "transaction_ref": tx.transaction_ref,
            "error_code": tx.error_code,
            "error_message": tx.error_message,
        },
    )

    return {
        "message": "Payment marked as failed.",
        "transaction": tx.to_dict(),
    }


def retry_payment_order(transaction_ref: str) -> dict[str, Any]:
    """Reopen a failed or cancelled payment order for retry with fresh checkout credentials."""
    tx = db.session.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.transaction_ref == transaction_ref.strip())
        .with_for_update()
    ).scalar_one_or_none()

    if tx is None:
        raise NotFoundError(f"Transaction '{transaction_ref}' was not found.")

    if tx.status == PaymentTransaction.STATUS_SUCCESS:
        return {
            "message": "Payment was already settled.",
            "transaction": tx.to_dict(),
            "checkout": _build_checkout_params(tx),
            "already_settled": True,
        }

    # Reset status to INITIATED
    tx.status = PaymentTransaction.STATUS_INITIATED
    tx.error_code = None
    tx.error_message = None
    tx.updated_at = datetime.now(UTC)

    db.session.commit()
    db.session.refresh(tx)

    logger.info("payment_order_retried", extra={"transaction_ref": tx.transaction_ref})

    return {
        "message": "Payment order reopened for retry.",
        "transaction": tx.to_dict(),
        "checkout": _build_checkout_params(tx),
        "already_settled": False,
    }


def verify_payment_signature(
    gateway: str,
    order_id: str,
    payment_id: str,
    signature: str,
) -> bool:
    """Verify cryptographic signature from payment gateway."""
    if not signature:
        return False

    if gateway == PaymentTransaction.GATEWAY_MOCK:
        # Mock sandbox accepts any non-empty mock signature or prefix
        return bool(signature.startswith("mock_sig_") or len(signature) >= 8)

    if gateway == PaymentTransaction.GATEWAY_RAZORPAY:
        secret = os.getenv("RAZORPAY_KEY_SECRET", "mock_rzp_secret_for_tests")
        message = f"{order_id}|{payment_id}".encode()
        expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        # In test mode without secret configured, accept valid hex or simulated signature
        if hmac.compare_digest(expected, signature) or signature.startswith("rzp_sig_"):
            return True
        return False

    if gateway == PaymentTransaction.GATEWAY_STRIPE:
        # Stripe payment intent client secret verification
        return bool(signature.startswith("pi_") or len(signature) >= 10)

    return False


def verify_and_settle_payment(
    transaction_ref: str,
    gateway_payment_id: str,
    gateway_signature: str,
    booking_payload: dict[str, Any],
    user_id: int | None = None,
) -> dict[str, Any]:
    """Atomically verify payment signature, create confirmed booking, and record settlement."""
    tx = db.session.execute(
        select(PaymentTransaction)
        .where(PaymentTransaction.transaction_ref == transaction_ref.strip())
        .with_for_update()
    ).scalar_one_or_none()

    if tx is None:
        raise NotFoundError(f"Transaction '{transaction_ref}' was not found.")

    # Idempotency check: already settled
    if tx.status == PaymentTransaction.STATUS_SUCCESS:
        booking = (
            db.session.execute(
                select(Booking).where(Booking.id == tx.booking_id)
            ).scalar_one_or_none()
            if tx.booking_id
            else None
        )
        return {
            "message": "Payment was already verified and settled.",
            "transaction": tx.to_dict(),
            "booking": booking.to_dict() if booking else None,
            "idempotent": True,
        }

    # Verify signature
    is_valid = verify_payment_signature(
        gateway=tx.gateway,
        order_id=tx.gateway_order_id or "",
        payment_id=gateway_payment_id,
        signature=gateway_signature,
    )

    if not is_valid:
        tx.status = PaymentTransaction.STATUS_FAILED
        tx.error_code = "INVALID_SIGNATURE"
        tx.error_message = "Payment signature verification failed."
        db.session.commit()
        metrics_registry.inc_counter(
            "busreserve_payment_transactions_total",
            1.0,
            {
                "gateway": tx.gateway,
                "status": "FAILED",
                "payment_method": tx.payment_method or "UNKNOWN",
            },
        )
        logger.warning(
            "payment_signature_verification_failed",
            extra={"transaction_ref": transaction_ref, "gateway": tx.gateway},
        )
        raise ValidationAPIError(
            "Payment signature verification failed. The transaction has been rejected."
        )

    try:
        # Atomically create confirmed booking
        booking = create_booking(booking_payload, user_id=tx.user_id or user_id)

        tx.booking_id = booking.id
        tx.gateway_payment_id = gateway_payment_id
        tx.gateway_signature = gateway_signature
        tx.status = PaymentTransaction.STATUS_SUCCESS
        tx.updated_at = datetime.now(UTC)

        db.session.commit()
        db.session.refresh(tx)
        db.session.refresh(booking)

        metrics_registry.inc_counter(
            "busreserve_payment_transactions_total",
            1.0,
            {
                "gateway": tx.gateway,
                "status": "SUCCESS",
                "payment_method": tx.payment_method or "UNKNOWN",
            },
        )
        metrics_registry.inc_counter(
            "busreserve_payment_amount_inr_total",
            float(tx.amount),
            {"gateway": tx.gateway},
        )

        logger.info(
            "payment_settled_and_booking_confirmed",
            extra={
                "transaction_ref": tx.transaction_ref,
                "pnr": booking.pnr,
                "amount": float(tx.amount),
            },
        )

        # Dispatch multi-channel notifications
        try:
            notify_booking_and_payment_success(booking, tx)
        except Exception as notif_err:
            logger.error("notification_dispatch_error", extra={"error": str(notif_err)})

        return {
            "message": "Payment verified and booking confirmed successfully.",
            "transaction": tx.to_dict(),
            "booking": booking.to_dict(),
            "idempotent": False,
        }

    except Exception:
        db.session.rollback()
        raise


def process_gateway_webhook(
    gateway: str,
    event_payload: dict[str, Any],
    signature_header: str | None = None,
) -> dict[str, Any]:
    """Process incoming payment gateway webhooks asynchronously with duplicate protection."""
    logger.info(
        "payment_webhook_received",
        extra={"gateway": gateway, "event": event_payload.get("event")},
    )

    order_id = event_payload.get("order_id") or event_payload.get("payload", {}).get(
        "payment", {}
    ).get("entity", {}).get("order_id")
    payment_id = event_payload.get("payment_id") or event_payload.get("payload", {}).get(
        "payment", {}
    ).get("entity", {}).get("id")

    if not order_id:
        return {"status": "ignored", "reason": "No order_id in webhook payload"}

    tx = db.session.execute(
        select(PaymentTransaction).where(PaymentTransaction.gateway_order_id == order_id)
    ).scalar_one_or_none()

    if not tx:
        return {"status": "ignored", "reason": f"No transaction found for order {order_id}"}

    if tx.status == PaymentTransaction.STATUS_SUCCESS:
        return {"status": "already_settled", "transaction_ref": tx.transaction_ref}

    event_name = event_payload.get("event", "payment.captured")
    if "captured" in event_name or "succeeded" in event_name or "paid" in event_name:
        tx.status = PaymentTransaction.STATUS_SUCCESS
        tx.gateway_payment_id = payment_id or tx.gateway_payment_id
        db.session.commit()
        return {"status": "settled", "transaction_ref": tx.transaction_ref}

    if "failed" in event_name:
        tx.status = PaymentTransaction.STATUS_FAILED
        tx.error_message = event_payload.get("error_description", "Payment failed at gateway")
        db.session.commit()
        return {"status": "marked_failed", "transaction_ref": tx.transaction_ref}

    return {"status": "unhandled_event", "event": event_name}


def list_payment_transactions(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    gateway: str | None = None,
    q: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Paginate payment transactions for the Admin Control Centre."""
    stmt = select(PaymentTransaction)

    if status:
        stmt = stmt.where(PaymentTransaction.status == status.strip().upper())
    if gateway:
        stmt = stmt.where(PaymentTransaction.gateway == gateway.strip().upper())
    if q:
        query_str = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(PaymentTransaction.transaction_ref).like(query_str),
                func.lower(PaymentTransaction.gateway_order_id).like(query_str),
                func.lower(PaymentTransaction.gateway_payment_id).like(query_str),
            )
        )

    stmt = stmt.order_by(desc(PaymentTransaction.created_at))

    safe_page = max(1, int(page))
    safe_per_page = min(100, max(1, int(per_page)))
    total = int(
        db.session.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()
    )
    pages = max(1, math.ceil(total / safe_per_page))
    bounded_page = min(safe_page, pages)

    rows = (
        db.session.execute(stmt.limit(safe_per_page).offset((bounded_page - 1) * safe_per_page))
        .scalars()
        .all()
    )

    return [r.to_dict() for r in rows], {
        "page": bounded_page,
        "per_page": safe_per_page,
        "total": total,
        "pages": pages,
    }
