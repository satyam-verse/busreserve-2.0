"""Tests for booking validation, creation, PNR retrieval, cancellation, and rebooking."""

from sqlalchemy import func, select

from app.extensions import db
from app.models import Booking


def _valid_payload(sample_data, seat_number="1A", **overrides):
    payload = {
        "trip_id": sample_data["upcoming_trip_id"],
        "seat_number": seat_number,
        "passenger_name": "Ananya Singh",
        "passenger_email": "ananya.singh@example.com",
        "passenger_phone": "+919876543210",
        "boarding_stop_id": sample_data["pr_stop_ids"][0],
        "drop_stop_id": sample_data["pr_stop_ids"][3],
        "travel_date": sample_data["upcoming_date"],
    }
    payload.update(overrides)
    return payload


def test_valid_booking_pnr_lookup_cancellation_and_rebooking(client, sample_data):
    create_resp = client.post("/api/bookings", json=_valid_payload(sample_data, seat_number="1A"))
    assert create_resp.status_code == 201
    booking = create_resp.get_json()["booking"]
    pnr = booking["pnr"]
    assert pnr.startswith("BR")
    assert booking["status"] == "CONFIRMED"
    assert booking["seat_number"] == "1A"

    # Seat map now shows 1A unavailable
    seat_map = client.get(f"/api/trips/{sample_data['upcoming_trip_id']}/seats").get_json()
    seat_1a = next(s for s in seat_map["seats"] if s["seat_number"] == "1A")
    assert seat_1a["is_available"] is False

    # Case-insensitive PNR lookup
    lookup_resp = client.get(f"/api/bookings/{pnr.lower()}")
    assert lookup_resp.status_code == 200
    assert lookup_resp.get_json()["booking"]["pnr"] == pnr

    # Duplicate booking attempt must return 409 Conflict
    dup_resp = client.post("/api/bookings", json=_valid_payload(sample_data, seat_number="1A"))
    assert dup_resp.status_code == 409

    # Unauthorized cancel attempt without verification must return 403 Forbidden
    unauth_cancel = client.post(f"/api/bookings/{pnr}/cancel")
    assert unauth_cancel.status_code == 403

    # Wrong email returns 403 Forbidden
    wrong_email_cancel = client.post(
        f"/api/bookings/{pnr}/cancel",
        json={"passenger_email": "wrong@example.com"},
    )
    assert wrong_email_cancel.status_code == 403

    # Cancel booking with matching passenger email -> 200 and releases seat
    cancel_resp = client.post(
        f"/api/bookings/{pnr}/cancel",
        json={"passenger_email": "ananya.singh@example.com"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.get_json()["booking"]["status"] == "CANCELLED"

    # Double cancellation returns 409
    second_cancel = client.post(
        f"/api/bookings/{pnr}/cancel",
        json={"passenger_email": "ananya.singh@example.com"},
    )
    assert second_cancel.status_code == 409

    # Seat 1A is available again and can be rebooked
    seat_map_after = client.get(f"/api/trips/{sample_data['upcoming_trip_id']}/seats").get_json()
    seat_1a_after = next(s for s in seat_map_after["seats"] if s["seat_number"] == "1A")
    assert seat_1a_after["is_available"] is True

    rebook_resp = client.post(
        "/api/bookings",
        json=_valid_payload(
            sample_data,
            seat_number="1A",
            passenger_name="Vikram Kumar",
            passenger_email="vikram.kumar@example.com",
        ),
    )
    assert rebook_resp.status_code == 201
    new_booking = rebook_resp.get_json()["booking"]
    assert new_booking["pnr"] != pnr
    assert new_booking["status"] == "CONFIRMED"


def test_invalid_passenger_fields_rejected(client, sample_data):
    bad_email = client.post(
        "/api/bookings", json=_valid_payload(sample_data, passenger_email="bad")
    )
    assert bad_email.status_code == 400

    bad_phone = client.post(
        "/api/bookings", json=_valid_payload(sample_data, passenger_phone="12345")
    )
    assert bad_phone.status_code == 400

    bad_name = client.post("/api/bookings", json=_valid_payload(sample_data, passenger_name="1234"))
    assert bad_name.status_code == 400

    bad_json = client.post("/api/bookings", data="not json", content_type="application/json")
    assert bad_json.status_code == 400


def test_invalid_travel_date_rejected(client, sample_data):
    past_resp = client.post(
        "/api/bookings",
        json={
            "trip_id": sample_data["past_trip_id"],
            "seat_number": "1A",
            "passenger_name": "Ananya Singh",
            "passenger_email": "ananya@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": sample_data["pr_stop_ids"][0],
            "drop_stop_id": sample_data["pr_stop_ids"][3],
        },
    )
    assert past_resp.status_code == 400

    mismatch_resp = client.post(
        "/api/bookings",
        json=_valid_payload(sample_data, travel_date=sample_data["past_date"]),
    )
    assert mismatch_resp.status_code == 400


def test_invalid_boarding_and_drop_stops_rejected(client, sample_data):
    # Reverse order: boarding after drop
    reverse_resp = client.post(
        "/api/bookings",
        json=_valid_payload(
            sample_data,
            boarding_stop_id=sample_data["pr_stop_ids"][3],
            drop_stop_id=sample_data["pr_stop_ids"][1],
        ),
    )
    assert reverse_resp.status_code == 400

    # Same stop
    same_resp = client.post(
        "/api/bookings",
        json=_valid_payload(
            sample_data,
            boarding_stop_id=sample_data["pr_stop_ids"][1],
            drop_stop_id=sample_data["pr_stop_ids"][1],
        ),
    )
    assert same_resp.status_code == 400

    # Stop belonging to a different route
    foreign_resp = client.post(
        "/api/bookings",
        json=_valid_payload(
            sample_data,
            boarding_stop_id=sample_data["pr_stop_ids"][0],
            drop_stop_id=sample_data["pg_stop_ids"][2],
        ),
    )
    assert foreign_resp.status_code == 400


def test_unknown_pnr_and_seat_return_404_without_orphans(client, app, sample_data):
    bad_seat = client.post("/api/bookings", json=_valid_payload(sample_data, seat_number="99Z"))
    assert bad_seat.status_code == 404

    bad_trip = client.post("/api/bookings", json=_valid_payload(sample_data, trip_id=999999))
    assert bad_trip.status_code == 404

    missing_pnr = client.get("/api/bookings/BRDOESNOT1")
    assert missing_pnr.status_code == 404

    with app.app_context():
        count = db.session.execute(select(func.count(Booking.id))).scalar_one()
        assert count == 0
