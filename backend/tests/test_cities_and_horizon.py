"""Tests for dynamic Indian city search, 90-day horizon, stop matching, and admin schedules."""

from datetime import time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Route, RouteStop, Trip, TripSeat
from app.services.schedule_service import (
    create_city,
    create_route_with_stops,
    create_schedule_with_horizon,
)
from app.utils.timezone import get_app_today
from scripts.seed import run_seed


def test_dynamic_city_autocomplete_and_alias_resolution(client, app):
    with app.app_context():
        run_seed(horizon_days=5)

    resp = client.get("/api/cities?q=pat")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["booking_horizon_days"] == 90
    assert data["cities"][0]["name"] == "Patna"
    assert data["cities"][0]["has_routes"] is True

    # Alias lookup ("Bangalore" -> "Bengaluru")
    alias_resp = client.get("/api/cities?q=bangalore")
    assert alias_resp.status_code == 200
    alias_data = alias_resp.get_json()
    assert alias_data["cities"][0]["name"] == "Bengaluru"
    assert alias_data["cities"][0]["matched_alias"] == "Bangalore"


def test_manual_unknown_city_allowed_in_search(client, sample_data):
    resp = client.get("/api/trips?source=Darjeeling&destination=Gangtok")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 0
    assert data["trips"] == []


def test_bidirectional_intermediate_stop_and_alias_search(client, app):
    with app.app_context():
        run_seed(horizon_days=10)

    target_date = (get_app_today() + timedelta(days=7)).isoformat()

    # Reverse direction (Ranchi -> Patna) works on day +7
    rev_resp = client.get(f"/api/trips?source=Ranchi&destination=Patna&travel_date={target_date}")
    assert rev_resp.status_code == 200
    assert rev_resp.get_json()["count"] == 2

    # Intermediate stop-to-stop segment (Patna -> Jehanabad along Patna-Ranchi & Patna-Gaya)
    seg_resp = client.get(
        f"/api/trips?source=Patna&destination=Jehanabad&travel_date={target_date}"
    )
    assert seg_resp.status_code == 200
    seg_data = seg_resp.get_json()
    assert seg_data["count"] >= 2
    assert seg_data["trips"][0]["matched_boarding_stop_id"] is not None
    assert seg_data["trips"][0]["matched_drop_stop_id"] is not None

    # Alias search ("Bangalore" -> "Mysore")
    alias_trip_resp = client.get(
        f"/api/trips?source=Bangalore&destination=Mysore&travel_date={target_date}"
    )
    assert alias_trip_resp.status_code == 200
    assert alias_trip_resp.get_json()["count"] == 2


def test_90_day_booking_window_enforced_in_search_and_booking(client, app, sample_data):
    today_ist = get_app_today()
    day_90 = (today_ist + timedelta(days=90)).isoformat()
    day_91 = (today_ist + timedelta(days=91)).isoformat()
    yesterday = (today_ist - timedelta(days=1)).isoformat()

    # Search rejects past and >90-day dates
    assert client.get(f"/api/trips?travel_date={yesterday}").status_code == 400
    assert client.get(f"/api/trips?travel_date={day_91}").status_code == 400
    assert client.get(f"/api/trips?travel_date={day_90}").status_code == 200

    # Create a trip on day +90 (allowed) and day +91 (blocked from booking)
    with app.app_context():
        trip_90 = Trip(
            route_id=sample_data["route_pr_id"],
            operator_name="Horizon Express",
            bus_number="BR-90-DAY-0090",
            departure_time=time(10, 0),
            arrival_time=time(16, 0),
            travel_date=today_ist + timedelta(days=90),
            base_fare=Decimal("700.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        trip_91 = Trip(
            route_id=sample_data["route_pr_id"],
            operator_name="Horizon Express",
            bus_number="BR-90-DAY-0091",
            departure_time=time(10, 0),
            arrival_time=time(16, 0),
            travel_date=today_ist + timedelta(days=91),
            base_fare=Decimal("700.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        db.session.add_all([trip_90, trip_91])
        db.session.flush()
        db.session.add_all(
            [
                TripSeat(trip_id=trip_90.id, seat_number="1A", seat_type=TripSeat.SEAT_WINDOW),
                TripSeat(trip_id=trip_91.id, seat_number="1A", seat_type=TripSeat.SEAT_WINDOW),
            ]
        )
        db.session.commit()
        trip_90_id = trip_90.id
        trip_91_id = trip_91.id

    ok_booking = client.post(
        "/api/bookings",
        json={
            "trip_id": trip_90_id,
            "seat_number": "1A",
            "passenger_name": "Horizon Passenger",
            "passenger_email": "horizon@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": sample_data["pr_stop_ids"][0],
            "drop_stop_id": sample_data["pr_stop_ids"][3],
        },
    )
    assert ok_booking.status_code == 201

    too_far_booking = client.post(
        "/api/bookings",
        json={
            "trip_id": trip_91_id,
            "seat_number": "1A",
            "passenger_name": "Horizon Passenger",
            "passenger_email": "horizon@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": sample_data["pr_stop_ids"][0],
            "drop_stop_id": sample_data["pr_stop_ids"][3],
        },
    )
    assert too_far_booking.status_code == 400

    # Configurable horizon respects runtime config override
    original_horizon = app.config["BOOKING_HORIZON_DAYS"]
    try:
        app.config["BOOKING_HORIZON_DAYS"] = 30
        day_31 = (get_app_today() + timedelta(days=31)).isoformat()
        assert client.get(f"/api/trips?travel_date={day_31}").status_code == 400
    finally:
        app.config["BOOKING_HORIZON_DAYS"] = original_horizon


def test_admin_created_cities_routes_and_schedules_become_searchable(client, app):
    with app.app_context():
        create_city("Siliguri", state="West Bengal", aliases="IXB")
        create_city("Guwahati", state="Assam", aliases="GAU")
        route = create_route_with_stops(
            name="Siliguri to Guwahati Himalayan Line",
            source="Siliguri",
            destination="Guwahati",
            stops=["Siliguri (Tenzing Norgay)", "Alipurduar", "Bongaigaon", "Guwahati (ISBT)"],
        )
        _, gen_counts = create_schedule_with_horizon(
            route_id=route.id,
            operator_name="NorthEast Royal Volvo",
            bus_number="WB-73-NE-4001",
            departure_time=time(6, 0),
            arrival_time=time(14, 30),
            base_fare=Decimal("820.00"),
            seat_count=24,
        )
        assert gen_counts["trips_created"] == 91
        assert gen_counts["seats_created"] == 91 * 24

        # Also test direct RouteStop insertion without explicit City row
        direct_route = Route(name="Bhopal to Indore Express", source="Bhopal", destination="Indore")
        db.session.add(direct_route)
        db.session.flush()
        db.session.add_all(
            [
                RouteStop(route_id=direct_route.id, stop_name="Bhopal ISBT", stop_order=1),
                RouteStop(route_id=direct_route.id, stop_name="Indore Sarwate", stop_order=2),
            ]
        )
        db.session.commit()
        stop_ids = [s.id for s in route.stops]

    # Newly created cities appear immediately in autocomplete
    sil_cities = client.get("/api/cities?q=sil").get_json()["cities"]
    assert any(c["name"] == "Siliguri" and c["has_routes"] is True for c in sil_cities)
    bho_cities = client.get("/api/cities?q=bho").get_json()["cities"]
    assert any(c["name"] == "Bhopal" and c["has_routes"] is True for c in bho_cities)

    # Search works at day +45 across intermediate stop (Alipurduar -> Guwahati)
    day_45 = (get_app_today() + timedelta(days=45)).isoformat()
    trips_resp = client.get(
        f"/api/trips?source=Alipurduar&destination=Guwahati&travel_date={day_45}"
    )
    assert trips_resp.status_code == 200
    trips_data = trips_resp.get_json()
    assert trips_data["count"] == 1
    trip = trips_data["trips"][0]
    assert trip["available_seats"] == 24

    # And booking on day +45 succeeds atomically
    bk_resp = client.post(
        "/api/bookings",
        json={
            "trip_id": trip["id"],
            "seat_number": "1A",
            "passenger_name": "Kalyan Roy",
            "passenger_email": "kalyan.roy@example.com",
            "passenger_phone": "9876543218",
            "boarding_stop_id": stop_ids[1],
            "drop_stop_id": stop_ids[3],
        },
    )
    assert bk_resp.status_code == 201
