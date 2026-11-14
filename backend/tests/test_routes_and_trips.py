"""Tests for route listing, trip search, seat maps, admin summary, and idempotent seeding."""

import os
from scripts.seed import run_seed

ADMIN_TEST_PW = os.getenv("SEED_DEMO_ADMIN_PASSWORD", "TestAdminPass999!")
USER_TEST_PW = os.getenv("SEED_DEMO_USER_PASSWORD", "TestUserPass999!")


def test_list_routes(client, sample_data):
    response = client.get("/api/routes")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2
    names = [r["name"] for r in data["routes"]]
    assert "Patna to Ranchi Express" in names
    assert len(data["routes"][0]["stops"]) >= 3


def test_search_trips_filters_and_sorting(client, sample_data):
    response = client.get(
        f"/api/trips?source=Patna&destination=Ranchi&travel_date={sample_data['upcoming_date']}"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    trip = data["trips"][0]
    assert trip["id"] == sample_data["upcoming_trip_id"]
    assert trip["available_seats"] == 6
    assert trip["total_seats"] == 6
    assert trip["duration_display"] == "6h 45m"


def test_search_trips_invalid_date_returns_400(client, sample_data):
    response = client.get("/api/trips?travel_date=2026-99-99")
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


def test_trip_seat_map_and_not_found(client, sample_data):
    response = client.get(f"/api/trips/{sample_data['upcoming_trip_id']}/seats")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["seats"]) == 6
    assert all(seat["is_available"] is True for seat in data["seats"])
    assert len(data["stops"]) == 4

    missing = client.get("/api/trips/999999/seats")
    assert missing.status_code == 404


def test_seed_script_is_idempotent(app):
    with app.app_context():
        first = run_seed()
        assert first["users_created"] == 2
        assert first["cities_created"] >= 30
        assert first["routes_created"] == 12
        assert first["schedules_created"] == 24
        assert first["trips_created"] >= 2000
        assert first["seats_created"] > 0
        assert first["bookings_created"] == 3

        second = run_seed()
        assert second == {
            "users_created": 0,
            "cities_created": 0,
            "routes_created": 0,
            "stops_created": 0,
            "schedules_created": 0,
            "trips_created": 0,
            "seats_created": 0,
            "bookings_created": 0,
        }


def test_admin_overview_requires_admin_auth(client, app):
    with app.app_context():
        run_seed(horizon_days=5)

    # Unauthenticated request rejected (401)
    unauth = client.get("/api/admin/overview")
    assert unauth.status_code == 401

    # Regular USER cannot access admin overview (403)
    user_client = app.test_client()
    assert (
        user_client.post(
            "/api/auth/login",
            json={"email": "passenger@busreserve.local", "password": USER_TEST_PW},
        ).status_code
        == 200
    )
    assert user_client.get("/api/admin/overview").status_code == 403

    # Authenticated ADMIN succeeds (200)
    admin_client = app.test_client()
    assert (
        admin_client.post(
            "/api/auth/admin/login",
            json={"email": "admin@busreserve.local", "password": ADMIN_TEST_PW},
        ).status_code
        == 200
    )
    response = admin_client.get("/api/admin/overview")
    assert response.status_code == 200
    data = response.get_json()
    assert data["summary"]["confirmed_bookings"] == 3
    assert len(data["recent_bookings"]) == 3
