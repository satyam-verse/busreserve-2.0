"""Tests verifying Asia/Kolkata (IST) standardization and 00:00-05:30 IST boundary safety."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Route, RouteStop, Trip, TripSeat
from app.utils import timezone as tz_utils
from scripts.seed import run_seed


def test_app_timezone_defaults_to_asia_kolkata(app):
    assert app.config["APP_TIMEZONE"] == "Asia/Kolkata"
    assert str(tz_utils.get_app_timezone()) == "Asia/Kolkata"


def test_ist_midnight_to_0530_boundary_consistent_between_utc_and_ist(client, app, monkeypatch):
    """Simulate UTC instants spanning 23:59:59 IST, 00:00:00 IST, and 05:29:59 IST."""
    # 18:29:59 UTC on 2026-11-11 == 23:59:59 IST on 2026-11-11
    before_ist_midnight = datetime(2026, 11, 11, 18, 29, 59, tzinfo=UTC)
    monkeypatch.setattr(tz_utils, "get_utc_now", lambda: before_ist_midnight)
    assert tz_utils.get_app_today() == date(2026, 11, 11)

    # 18:30:00 UTC on 2026-11-11 == 00:00:00 IST on 2026-11-12 (UTC is still Nov 11!)
    at_ist_midnight = datetime(2026, 11, 11, 18, 30, 0, tzinfo=UTC)
    monkeypatch.setattr(tz_utils, "get_utc_now", lambda: at_ist_midnight)
    assert tz_utils.get_app_today() == date(2026, 11, 12)

    # 23:59:59 UTC on 2026-11-11 == 05:29:59 IST on 2026-11-12 (UTC is still Nov 11!)
    at_0529_ist = datetime(2026, 11, 11, 23, 59, 59, tzinfo=UTC)
    monkeypatch.setattr(tz_utils, "get_utc_now", lambda: at_0529_ist)
    assert tz_utils.get_app_today() == date(2026, 11, 12)

    cities_resp = client.get("/api/cities")
    assert cities_resp.status_code == 200
    cities_data = cities_resp.get_json()
    assert cities_data["timezone"] == "Asia/Kolkata"
    assert cities_data["min_date"] == "2026-11-12"
    assert cities_data["max_date"] == (date(2026, 11, 12) + timedelta(days=90)).isoformat()

    # Seed route & trips anchored at 2026-11-12 IST (while UTC clock is still 2026-11-11)
    with app.app_context():
        route = Route(name="Patna to Ranchi IST Test", source="Patna", destination="Ranchi")
        db.session.add(route)
        db.session.flush()
        stops = [
            RouteStop(route_id=route.id, stop_name="Patna ISBT", city_name="Patna", stop_order=1),
            RouteStop(
                route_id=route.id, stop_name="Ranchi Khadgarha", city_name="Ranchi", stop_order=2
            ),
        ]
        db.session.add_all(stops)
        db.session.flush()

        trip_yesterday_ist = Trip(
            route_id=route.id,
            operator_name="IST Express",
            bus_number="BR-01-IST-01",
            departure_time=time(8, 0),
            arrival_time=time(14, 0),
            travel_date=date(2026, 11, 11),
            base_fare=Decimal("650.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        trip_today_ist = Trip(
            route_id=route.id,
            operator_name="IST Express",
            bus_number="BR-01-IST-02",
            departure_time=time(8, 0),
            arrival_time=time(14, 0),
            travel_date=date(2026, 11, 12),
            base_fare=Decimal("650.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        trip_day90_ist = Trip(
            route_id=route.id,
            operator_name="IST Express",
            bus_number="BR-01-IST-90",
            departure_time=time(8, 0),
            arrival_time=time(14, 0),
            travel_date=date(2026, 11, 12) + timedelta(days=90),
            base_fare=Decimal("650.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        db.session.add_all([trip_yesterday_ist, trip_today_ist, trip_day90_ist])
        db.session.flush()
        db.session.add_all(
            [
                TripSeat(trip_id=t.id, seat_number="1A", seat_type=TripSeat.SEAT_WINDOW)
                for t in (trip_yesterday_ist, trip_today_ist, trip_day90_ist)
            ]
        )
        db.session.commit()
        past_trip_id = trip_yesterday_ist.id
        today_trip_id = trip_today_ist.id
        day90_trip_id = trip_day90_ist.id
        stop_ids = [s.id for s in stops]

    # At 05:29:59 IST (2026-11-12), 2026-11-11 (still UTC date!) MUST be rejected as past
    assert client.get("/api/trips?travel_date=2026-11-11").status_code == 400
    past_booking = client.post(
        "/api/bookings",
        json={
            "trip_id": past_trip_id,
            "seat_number": "1A",
            "passenger_name": "IST User",
            "passenger_email": "ist@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": stop_ids[0],
            "drop_stop_id": stop_ids[1],
        },
    )
    assert past_booking.status_code == 400

    # Day 0 (2026-11-12 IST) and Day 90 (2027-02-10 IST) succeed cleanly
    today_search = client.get("/api/trips?source=Patna&destination=Ranchi&travel_date=2026-11-12")
    assert today_search.status_code == 200
    assert today_search.get_json()["count"] == 1
    assert today_search.get_json()["timezone"] == "Asia/Kolkata"

    day90_iso = (date(2026, 11, 12) + timedelta(days=90)).isoformat()
    day90_search = client.get(f"/api/trips?source=Patna&destination=Ranchi&travel_date={day90_iso}")
    assert day90_search.status_code == 200
    assert day90_search.get_json()["count"] == 1

    day91_iso = (date(2026, 11, 12) + timedelta(days=91)).isoformat()
    assert client.get(f"/api/trips?travel_date={day91_iso}").status_code == 400

    for tid in (today_trip_id, day90_trip_id):
        bk = client.post(
            "/api/bookings",
            json={
                "trip_id": tid,
                "seat_number": "1A",
                "passenger_name": "IST Passenger",
                "passenger_email": "ist.pass@example.com",
                "passenger_phone": "9876543211",
                "boarding_stop_id": stop_ids[0],
                "drop_stop_id": stop_ids[1],
            },
        )
        assert bk.status_code == 201


def test_complete_90_day_seeded_window_searchable_and_bookable(client, app):
    with app.app_context():
        run_seed()
        today_ist = tz_utils.get_app_today()

    for offset in (0, 1, 30, 60, 89, 90):
        target_iso = (today_ist + timedelta(days=offset)).isoformat()
        resp = client.get(f"/api/trips?source=Patna&destination=Ranchi&travel_date={target_iso}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2
        assert data["trips"][0]["travel_date"] == target_iso

    # Book on day +90 and verify seat lock prevents duplicate
    day90_iso = (today_ist + timedelta(days=90)).isoformat()
    trips_90 = client.get(
        f"/api/trips?source=Patna&destination=Ranchi&travel_date={day90_iso}"
    ).get_json()["trips"]
    chosen = trips_90[0]
    stops = chosen["stops"]

    bk1 = client.post(
        "/api/bookings",
        json={
            "trip_id": chosen["id"],
            "seat_number": "2A",
            "passenger_name": "Ninety Day Traveler",
            "passenger_email": "ninety@example.com",
            "passenger_phone": "9876543212",
            "boarding_stop_id": stops[0]["id"],
            "drop_stop_id": stops[-1]["id"],
        },
    )
    assert bk1.status_code == 201

    bk_dup = client.post(
        "/api/bookings",
        json={
            "trip_id": chosen["id"],
            "seat_number": "2A",
            "passenger_name": "Duplicate Traveler",
            "passenger_email": "dup@example.com",
            "passenger_phone": "9876543213",
            "boarding_stop_id": stops[0]["id"],
            "drop_stop_id": stops[-1]["id"],
        },
    )
    assert bk_dup.status_code == 409
