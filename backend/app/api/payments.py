"""Payments REST API blueprint for order creation, signature verification, and webhooks."""

from flask import Blueprint, jsonify, request

from app.extensions import limiter
from app.models.payment import PaymentTransaction
from app.services.notification_service import list_user_notifications, mark_notification_read
from app.services.payment_service import (
    cancel_payment_order,
    create_payment_order,
    fail_payment_order,
    get_payment_order,
    list_payment_transactions,
    process_gateway_webhook,
    retry_payment_order,
    verify_and_settle_payment,
)
from app.utils.auth import load_current_auth, require_admin, require_auth
from app.utils.errors import NotFoundError, ValidationAPIError
from app.utils.schemas import BookingCreateSchema

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")
_booking_schema = BookingCreateSchema()


@payments_bp.post("/order")
@limiter.limit("20 per minute")
def create_order_endpoint():
    """Initiate a payment order with the selected gateway sandbox."""
    raw_body = request.get_json(silent=True)
    if not isinstance(raw_body, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")

    body_copy = dict(raw_body)
    gateway = body_copy.pop("gateway", PaymentTransaction.GATEWAY_MOCK)
    payment_method = body_copy.pop("payment_method", PaymentTransaction.METHOD_UPI)
    idempotency_key = body_copy.pop("idempotency_key", None)

    booking_payload = _booking_schema.load(body_copy)
    user, _ = load_current_auth(optional=True)
    result = create_payment_order(
        booking_payload=booking_payload,
        user_id=user.id if user else None,
        gateway=gateway,
        payment_method=payment_method,
        idempotency_key=idempotency_key,
    )
    return jsonify(result), 201


@payments_bp.get("/order/<string:transaction_ref>")
@limiter.limit("30 per minute")
def get_order_endpoint(transaction_ref: str):
    """Retrieve an existing payment order session and its status."""
    result = get_payment_order(transaction_ref=transaction_ref)
    return jsonify(result), 200


@payments_bp.post("/cancel")
@limiter.limit("20 per minute")
def cancel_order_endpoint():
    """Cancel an initiated payment session."""
    raw_body = request.get_json(silent=True) or {}
    transaction_ref = raw_body.get("transaction_ref")
    reason = raw_body.get("reason")
    if not transaction_ref:
        raise ValidationAPIError("transaction_ref is required.")
    result = cancel_payment_order(transaction_ref=transaction_ref, reason=reason)
    return jsonify(result), 200


@payments_bp.post("/fail")
@limiter.limit("20 per minute")
def fail_order_endpoint():
    """Record a simulated or gateway failure on an initiated transaction."""
    raw_body = request.get_json(silent=True) or {}
    transaction_ref = raw_body.get("transaction_ref")
    error_code = raw_body.get("error_code")
    error_message = raw_body.get("error_message")
    if not transaction_ref:
        raise ValidationAPIError("transaction_ref is required.")
    result = fail_payment_order(
        transaction_ref=transaction_ref,
        error_code=error_code,
        error_message=error_message,
    )
    return jsonify(result), 200


@payments_bp.post("/retry")
@limiter.limit("20 per minute")
def retry_order_endpoint():
    """Reopen a failed or cancelled transaction for retry."""
    raw_body = request.get_json(silent=True) or {}
    transaction_ref = raw_body.get("transaction_ref")
    if not transaction_ref:
        raise ValidationAPIError("transaction_ref is required.")
    result = retry_payment_order(transaction_ref=transaction_ref)
    return jsonify(result), 200


@payments_bp.post("/verify")
@limiter.limit("20 per minute")
def verify_payment_endpoint():
    """Verify cryptographic payment signature, confirm booking, and settle transaction."""
    raw_body = request.get_json(silent=True)
    if not isinstance(raw_body, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")

    transaction_ref = raw_body.get("transaction_ref")
    gateway_payment_id = raw_body.get("gateway_payment_id")
    gateway_signature = raw_body.get("gateway_signature")
    booking_data = raw_body.get("booking")

    if not transaction_ref or not gateway_payment_id or not gateway_signature:
        raise ValidationAPIError(
            "transaction_ref, gateway_payment_id, and gateway_signature are required."
        )

    if not isinstance(booking_data, dict):
        raise ValidationAPIError("booking object is required for atomic reservation settlement.")

    validated_booking = _booking_schema.load(booking_data)
    user, _ = load_current_auth(optional=True)

    result = verify_and_settle_payment(
        transaction_ref=transaction_ref,
        gateway_payment_id=gateway_payment_id,
        gateway_signature=gateway_signature,
        booking_payload=validated_booking,
        user_id=user.id if user else None,
    )
    return jsonify(result), 200


@payments_bp.post("/webhook/<string:gateway>")
def webhook_endpoint(gateway: str):
    """Receive asynchronous payment callbacks from gateway sandbox."""
    payload = request.get_json(silent=True) or {}
    signature_header = request.headers.get("X-Razorpay-Signature") or request.headers.get(
        "Stripe-Signature"
    )

    result = process_gateway_webhook(
        gateway=gateway.upper(),
        event_payload=payload,
        signature_header=signature_header,
    )
    return jsonify(result), 200


# Passenger in-app notifications
@payments_bp.get("/notifications")
@require_auth
@limiter.limit("30 per minute")
def user_notifications_endpoint():
    """Retrieve passenger in-app notification feed."""
    user, _ = load_current_auth()
    notifs = list_user_notifications(user_id=user.id, limit=30)
    return jsonify({"notifications": notifs, "count": len(notifs)}), 200


@payments_bp.post("/notifications/<int:notification_id>/read")
@require_auth
def mark_read_endpoint(notification_id: int):
    """Mark an in-app notification as read."""
    user, _ = load_current_auth()
    success = mark_notification_read(notification_id=notification_id, user_id=user.id)
    if not success:
        raise NotFoundError("Notification not found or access denied.")
    return jsonify(
        {
            "message": "Notification marked as read.",
            "success": True,
            "notification_id": notification_id,
        }
    ), 200


# Admin payment transaction history
@payments_bp.get("/admin/transactions")
@require_admin
@limiter.limit("30 per minute")
def admin_transactions_endpoint():
    """Paginated list of payment transactions for the Admin Control Centre."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    status = request.args.get("status")
    gateway = request.args.get("gateway")
    q = request.args.get("q")

    transactions, pagination = list_payment_transactions(
        page=page,
        per_page=per_page,
        status=status,
        gateway=gateway,
        q=q,
    )
    return jsonify({"transactions": transactions, "pagination": pagination}), 200
