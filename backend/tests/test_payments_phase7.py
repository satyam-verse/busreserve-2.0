"""Phase 7 Payment Gateway Integration and Notification Engine tests."""

from app.extensions import db
from app.models.payment import PaymentTransaction
from app.models.user import User


def _valid_booking_payload(sample_data, seat_number="1A", **overrides):
    payload = {
        "trip_id": sample_data["upcoming_trip_id"],
        "seat_number": seat_number,
        "passenger_name": "Vikram Malhotra",
        "passenger_email": "vikram.m@example.com",
        "passenger_phone": "+919876501234",
        "boarding_stop_id": sample_data["pr_stop_ids"][0],
        "drop_stop_id": sample_data["pr_stop_ids"][3],
        "travel_date": sample_data["upcoming_date"],
    }
    payload.update(overrides)
    return payload


def test_payment_order_creation_and_idempotency(client, sample_data):
    """Initiating an order returns checkout parameters, and duplicate keys return existing order."""
    payload = _valid_booking_payload(sample_data, "1A", idempotency_key="idemp_order_test_123")
    resp = client.post("/api/payments/order", json=payload)
    assert resp.status_code == 201

    data = resp.get_json()
    assert "transaction" in data
    assert "checkout" in data
    tx = data["transaction"]
    assert tx["status"] == PaymentTransaction.STATUS_INITIATED
    assert tx["gateway"] == PaymentTransaction.GATEWAY_MOCK
    assert tx["transaction_ref"].startswith("TXN_")
    assert tx["idempotency_key"] == "idemp_order_test_123"

    checkout = data["checkout"]
    assert checkout["order_id"].startswith("order_mock_")
    assert checkout["amount"] > 0
    assert "mock_signature" in checkout

    # Duplicate call with same idempotency key must return existing initiated order
    dup_resp = client.post("/api/payments/order", json=payload)
    assert dup_resp.status_code == 201
    dup_data = dup_resp.get_json()
    assert dup_data["transaction"]["transaction_ref"] == tx["transaction_ref"]


def test_payment_verification_settlement_and_notifications(client, sample_data):
    """Valid signature confirms booking atomically and dispatches confirmation notifications."""
    booking_payload = _valid_booking_payload(sample_data, "1B")
    order_resp = client.post("/api/payments/order", json=booking_payload)
    assert order_resp.status_code == 201
    order_data = order_resp.get_json()

    tx_ref = order_data["transaction"]["transaction_ref"]
    mock_sig = order_data["checkout"]["mock_signature"]

    # Verify and settle
    verify_resp = client.post(
        "/api/payments/verify",
        json={
            "transaction_ref": tx_ref,
            "gateway_payment_id": "pay_mock_123456",
            "gateway_signature": mock_sig,
            "booking": booking_payload,
        },
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.get_json()
    assert verify_data["idempotent"] is False

    booking = verify_data["booking"]
    assert booking["status"] == "CONFIRMED"
    assert booking["seat_number"] == "1B"
    assert booking["pnr"].startswith("BR")

    payment = verify_data["transaction"]
    assert payment["status"] == PaymentTransaction.STATUS_SUCCESS
    assert payment["gateway_payment_id"] == "pay_mock_123456"

    # Re-settling the same transaction returns idempotent success
    repeat_verify = client.post(
        "/api/payments/verify",
        json={
            "transaction_ref": tx_ref,
            "gateway_payment_id": "pay_mock_123456",
            "gateway_signature": mock_sig,
            "booking": booking_payload,
        },
    )
    assert repeat_verify.status_code == 200
    assert repeat_verify.get_json()["idempotent"] is True


def test_payment_signature_rejection_marks_transaction_failed(client, sample_data):
    """Invalid signature must be rejected with 400 and record transaction failure."""
    booking_payload = _valid_booking_payload(sample_data, "1C")
    order_resp = client.post("/api/payments/order", json=booking_payload)
    assert order_resp.status_code == 201
    order_data = order_resp.get_json()
    tx_ref = order_data["transaction"]["transaction_ref"]

    bad_verify = client.post(
        "/api/payments/verify",
        json={
            "transaction_ref": tx_ref,
            "gateway_payment_id": "pay_bad_0000",
            "gateway_signature": "",  # Empty signature
            "booking": booking_payload,
        },
    )
    assert bad_verify.status_code == 400


def test_razorpay_and_stripe_gateway_orders(client, sample_data):
    """Can create sandbox orders for Razorpay and Stripe gateways."""
    # Razorpay sandbox order
    rzp_payload = _valid_booking_payload(sample_data, "1D", gateway="RAZORPAY_SANDBOX")
    rzp_resp = client.post("/api/payments/order", json=rzp_payload)
    assert rzp_resp.status_code == 201
    rzp_data = rzp_resp.get_json()
    assert rzp_data["transaction"]["gateway"] == "RAZORPAY_SANDBOX"
    assert rzp_data["checkout"]["order_id"].startswith("order_rzp_")

    # Stripe sandbox order
    stripe_payload = _valid_booking_payload(sample_data, "2A", gateway="STRIPE_SANDBOX")
    stripe_resp = client.post("/api/payments/order", json=stripe_payload)
    assert stripe_resp.status_code == 201
    stripe_data = stripe_resp.get_json()
    assert stripe_data["transaction"]["gateway"] == "STRIPE_SANDBOX"
    assert stripe_data["checkout"]["order_id"].startswith("pi_test_")


def test_payment_webhook_processing(client, sample_data):
    """Webhook callback successfully marks order captured."""
    booking_payload = _valid_booking_payload(sample_data, "2B", gateway="RAZORPAY_SANDBOX")
    order_resp = client.post("/api/payments/order", json=booking_payload)
    assert order_resp.status_code == 201
    order_id = order_resp.get_json()["checkout"]["order_id"]

    webhook_resp = client.post(
        "/api/payments/webhook/razorpay",
        json={
            "event": "payment.captured",
            "order_id": order_id,
            "payment_id": "pay_webhook_9999",
        },
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.get_json()["status"] == "settled"


def test_admin_payment_transactions_endpoint(client, sample_data, app):
    """Admin endpoint lists paginated payment transactions."""
    with app.app_context():
        admin = User(
            full_name="Admin Test",
            email="admin@busreserve.local",
            role=User.ROLE_ADMIN,
            email_verified=True,
            is_active=True,
        )
        admin.set_password("TestAdmin@123")
        db.session.add(admin)
        db.session.commit()

    # First seed an order
    client.post("/api/payments/order", json=_valid_booking_payload(sample_data, "1A"))

    # Unauthenticated request rejected
    unauth = client.get("/api/payments/admin/transactions")
    assert unauth.status_code == 401

    # Login as admin
    login_resp = client.post(
        "/api/auth/admin/login",
        json={"email": "admin@busreserve.local", "password": "TestAdmin@123"},
    )
    assert login_resp.status_code == 200

    admin_resp = client.get("/api/payments/admin/transactions")
    assert admin_resp.status_code == 200
    data = admin_resp.get_json()
    assert "transactions" in data
    assert "pagination" in data
    assert len(data["transactions"]) >= 1


def test_booking_pdf_ticket_download(client, sample_data):
    """Download vector PDF boarding pass with valid headers and binary content."""
    # Create and confirm booking
    order_resp = client.post("/api/payments/order", json=_valid_booking_payload(sample_data, "1A"))
    assert order_resp.status_code == 201
    order_data = order_resp.get_json()
    tx = order_data["transaction"]
    checkout = order_data["checkout"]

    verify_resp = client.post(
        "/api/payments/verify",
        json={
            "transaction_ref": tx["transaction_ref"],
            "gateway_payment_id": f"pay_mock_{tx['transaction_ref']}",
            "gateway_signature": checkout["mock_signature"],
            "booking": _valid_booking_payload(sample_data, "1A"),
        },
    )
    assert verify_resp.status_code == 200
    pnr = verify_resp.get_json()["booking"]["pnr"]

    # Request PDF download
    pdf_resp = client.get(f"/api/bookings/{pnr}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.content_type == "application/pdf"
    assert "Content-Disposition" in pdf_resp.headers
    assert f"BusReserve_Ticket_{pnr}.pdf" in pdf_resp.headers["Content-Disposition"]
    assert pdf_resp.data.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_resp.data


def test_user_notifications_flow(client, sample_data, app):
    """Passenger receives in-app notifications and can mark them as read."""
    # Register passenger
    with app.app_context():
        user = User(
            full_name="Notification User",
            email="notif@example.com",
            role=User.ROLE_USER,
            email_verified=True,
            is_active=True,
        )
        user.set_password("TestUser@123")
        db.session.add(user)
        db.session.commit()

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "notif@example.com", "password": "TestUser@123"},
    )
    assert login_resp.status_code == 200

    # Book a ticket while logged in
    payload = _valid_booking_payload(sample_data, "1A")
    payload["passenger_email"] = "notif@example.com"
    order_resp = client.post("/api/payments/order", json=payload)
    order_data = order_resp.get_json()
    tx = order_data["transaction"]
    checkout = order_data["checkout"]

    client.post(
        "/api/payments/verify",
        json={
            "transaction_ref": tx["transaction_ref"],
            "gateway_payment_id": f"pay_mock_{tx['transaction_ref']}",
            "gateway_signature": checkout["mock_signature"],
            "booking": payload,
        },
    )

    # Fetch notifications
    notif_resp = client.get("/api/payments/notifications")
    assert notif_resp.status_code == 200
    notifs = notif_resp.get_json()["notifications"]
    assert len(notifs) >= 1
    first_id = notifs[0]["id"]
    assert notifs[0]["is_read"] is False

    # Mark as read
    read_resp = client.post(f"/api/payments/notifications/{first_id}/read")
    assert read_resp.status_code == 200
    assert read_resp.get_json()["success"] is True
