"""Tests for route listing, trip search, seat maps, admin summary, and idempotent seeding."""

from scripts.seed import run_seed


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
        assert first["routes_created"] == 5
        assert first["trips_created"] > 0
        assert first["seats_created"] > 0
        assert first["bookings_created"] == 3

        second = run_seed()
        assert second == {
            "routes_created": 0,
            "stops_created": 0,
            "trips_created": 0,
            "seats_created": 0,
            "bookings_created": 0,
        }


def test_admin_overview_masks_passenger_pii(client, app):
    with app.app_context():
        run_seed()

    response = client.get("/api/admin/overview")
    assert response.status_code == 200
    data = response.get_json()
    assert data["demo_only"] is True
    assert data["summary"]["confirmed_bookings"] == 3
    assert len(data["recent_bookings"]) == 3
    for record in data["recent_bookings"]:
        assert "aarav.sharma@example.com" not in record["passenger_email_masked"]
        assert "987650" not in str(record)
