"""Comprehensive tests for Phase 3 Admin Control Centre CRUD, analytics, and RBAC."""

import os

from sqlalchemy import select

from app.extensions import db
from app.models import Bus, User
from app.utils.timezone import get_app_today
from scripts.seed import run_seed

ADMIN_TEST_PW = os.getenv("SEED_DEMO_ADMIN_PASSWORD", "TestAdminPass999!")
USER_TEST_PW = os.getenv("SEED_DEMO_USER_PASSWORD", "TestUserPass999!")


def _login_as_seeded_admin(app):
    admin_client = app.test_client()
    resp = admin_client.post(
        "/api/auth/admin/login",
        json={"email": "admin@busreserve.local", "password": ADMIN_TEST_PW},
    )
    assert resp.status_code == 200
    return admin_client


def _login_as_seeded_user(app):
    user_client = app.test_client()
    resp = user_client.post(
        "/api/auth/login",
        json={"email": "passenger@busreserve.local", "password": USER_TEST_PW},
    )
    assert resp.status_code == 200
    return user_client


def test_all_admin_endpoints_enforce_authentication_and_admin_role(client, app):
    with app.app_context():
        run_seed(horizon_days=2)

    user_client = _login_as_seeded_user(app)
    admin_only_endpoints = [
        ("GET", "/api/admin/analytics", None),
        ("GET", "/api/admin/buses", None),
        (
            "POST",
            "/api/admin/buses",
            {
                "operator_name": "Unauthorized Bus",
                "registration_number": "XX-01-AA-0001",
                "bus_type": "AC_SEATER",
                "seat_layout": "2+2",
                "total_seats": 32,
            },
        ),
        ("PATCH", "/api/admin/buses/1", {"total_seats": 36}),
        ("DELETE", "/api/admin/buses/1", None),
        ("PATCH", "/api/admin/cities/1", {"state": "Updated"}),
        ("PATCH", "/api/admin/routes/1", {"distance_km": 400}),
        ("PATCH", "/api/admin/schedules/1", {"base_fare": 999}),
        ("DELETE", "/api/admin/schedules/1", None),
        ("GET", "/api/admin/bookings/BRSEED0001", None),
        ("POST", "/api/admin/bookings/BRSEED0001/refund", {}),
    ]

    for method, path, body in admin_only_endpoints:
        unauth = getattr(client, method.lower())(path, json=body)
        assert unauth.status_code == 401, f"{method} {path} returned {unauth.status_code}"
        forbidden = getattr(user_client, method.lower())(path, json=body)
        assert forbidden.status_code == 403, f"{method} {path} returned {forbidden.status_code}"


def test_city_route_bus_and_schedule_full_crud_with_booking_integration(client, app):
    with app.app_context():
        run_seed(horizon_days=2)

    admin_client = _login_as_seeded_admin(app)

    # 1. City CRUD: create unlimited cities, edit + cascade, filter & paginate, duplicate block
    c1 = admin_client.post(
        "/api/admin/cities",
        json={"name": "Kochi", "state": "Kerala", "aliases": "Cochin,COK"},
    )
    c2 = admin_client.post(
        "/api/admin/cities",
        json={"name": "Munnar", "state": "Kerala", "aliases": "MNR"},
    )
    c3 = admin_client.post(
        "/api/admin/cities",
        json={"name": "Thrissur", "state": "Kerala"},
    )
    assert c1.status_code == 201 and c2.status_code == 201 and c3.status_code == 201
    kochi_id = c1.get_json()["city"]["id"]
    thrissur_id = c3.get_json()["city"]["id"]

    # Duplicate city blocked
    dup_city = admin_client.post("/api/admin/cities", json={"name": "kochi", "state": "Kerala"})
    assert dup_city.status_code == 409

    # Edit & filter cities with pagination
    filtered_cities = admin_client.get("/api/admin/cities?state=Kerala&page=1&per_page=2")
    assert filtered_cities.status_code == 200
    f_data = filtered_cities.get_json()
    assert f_data["pagination"]["total"] == 3
    assert f_data["pagination"]["pages"] == 2
    assert len(f_data["cities"]) == 2

    # Delete unused city succeeds
    assert admin_client.delete(f"/api/admin/cities/{thrissur_id}").status_code == 200

    # 2. Route CRUD: validate city relationships, distance/duration, invalid/dup guards
    bad_route = admin_client.post(
        "/api/admin/routes",
        json={"name": "Same Place", "source": "Kochi", "destination": "Kochi", "stops": ["A", "B"]},
    )
    assert bad_route.status_code == 400

    missing_city_route = admin_client.post(
        "/api/admin/routes",
        json={
            "name": "Ghost City Route",
            "source": "NonExistentCity999",
            "destination": "Kochi",
            "stops": ["Ghost Stop", "Kochi"],
        },
    )
    assert missing_city_route.status_code == 400

    r_create = admin_client.post(
        "/api/admin/routes",
        json={
            "name": "Kochi to Munnar Hill Express",
            "source": "Kochi",
            "destination": "Munnar",
            "distance_km": 130,
            "estimated_duration_minutes": 240,
            "stops": ["Kochi (Vyttila)", "Aluva", "Adimali", "Munnar Town"],
        },
    )
    assert r_create.status_code == 201
    route = r_create.get_json()["route"]
    assert route["distance_km"] == 130
    assert route["estimated_duration_minutes"] == 240

    # Duplicate route (same stops & endpoints) rejected even with different name
    dup_route = admin_client.post(
        "/api/admin/routes",
        json={
            "name": "Another Kochi Munnar Name",
            "source": "Kochi",
            "destination": "Munnar",
            "stops": ["Kochi (Vyttila)", "Aluva", "Adimali", "Munnar Town"],
        },
    )
    assert dup_route.status_code == 409

    # Edit route stops and distance
    r_upd = admin_client.patch(
        f"/api/admin/routes/{route['id']}",
        json={
            "distance_km": 135,
            "estimated_duration_minutes": 250,
            "stops": ["Kochi (Vyttila)", "Perumbavoor", "Adimali", "Munnar Town"],
        },
    )
    assert r_upd.status_code == 200
    assert r_upd.get_json()["route"]["distance_km"] == 135
    assert r_upd.get_json()["route"]["stops"][1]["stop_name"] == "Perumbavoor"

    # City deletion blocked once referenced by a route
    assert admin_client.delete(f"/api/admin/cities/{kochi_id}").status_code == 409

    # 3. Bus Fleet CRUD: 2+1 sleeper coach, edit metadata, duplicate registration guard
    b1 = admin_client.post(
        "/api/admin/buses",
        json={
            "operator_name": "Malabar Luxury Coach",
            "registration_number": "kl-07-pa-7788",
            "bus_type": "AC_SLEEPER",
            "seat_layout": "2+1",
            "total_seats": 18,
            "amenities": "AC, Reading Light, Charging Point",
        },
    )
    assert b1.status_code == 201
    bus = b1.get_json()["bus"]
    assert bus["registration_number"] == "KL-07-PA-7788"

    dup_bus = admin_client.post(
        "/api/admin/buses",
        json={"operator_name": "Other", "registration_number": "KL-07-PA-7788"},
    )
    assert dup_bus.status_code == 409

    b_list = admin_client.get("/api/admin/buses?bus_type=AC_SLEEPER&q=KL-07-PA")
    assert b_list.status_code == 200
    assert b_list.get_json()["pagination"]["total"] == 1

    # 4. Schedule CRUD: link Bus via bus_id -> generates 90-day horizon trips with 2+1 sleeper seats
    s1 = admin_client.post(
        "/api/admin/schedules",
        json={
            "route_id": route["id"],
            "bus_id": bus["id"],
            "departure_time": "06:15",
            "arrival_time": "10:25",
            "base_fare": 640,
            "horizon_days": 5,
        },
    )
    assert s1.status_code == 201
    sched = s1.get_json()["schedule"]
    assert sched["seat_layout"] == "2+1"
    assert sched["bus_type"] == "AC_SLEEPER"
    assert s1.get_json()["generated"]["trips_created"] == 6

    # Edit bus operator -> reflects on linked schedule & trips
    assert (
        admin_client.patch(
            f"/api/admin/buses/{bus['id']}",
            json={"operator_name": "Malabar Crown Sleeper"},
        ).status_code
        == 200
    )

    # Edit schedule fare & propagate to future trips
    upd_sched = admin_client.patch(
        f"/api/admin/schedules/{sched['id']}",
        json={"base_fare": 720, "apply_to_future_trips": True},
    )
    assert upd_sched.status_code == 200
    assert upd_sched.get_json()["schedule"]["base_fare"] == 720.0

    # Verify newly created bus/route/schedule is searchable publicly & preserves 2+1 seat layout
    today_iso = get_app_today().isoformat()
    pub_search = client.get(f"/api/trips?source=Kochi&destination=Munnar&travel_date={today_iso}")
    assert pub_search.status_code == 200
    trips = pub_search.get_json()["trips"]
    assert len(trips) == 1
    trip = trips[0]
    assert trip["operator_name"] == "Malabar Crown Sleeper"
    assert trip["base_fare"] == 720.0
    assert trip["seat_layout"] == "2+1"

    seat_map = client.get(f"/api/trips/{trip['id']}/seats").get_json()
    assert len(seat_map["seats"]) == 18
    assert seat_map["seats"][0]["seat_type"] in ("SLEEPER_LOWER", "SLEEPER_UPPER")
    # 2+1 uses A, B, D (skips C)
    seat_nums = {s["seat_number"] for s in seat_map["seats"]}
    assert "1C" not in seat_nums and {"1A", "1B", "1D"}.issubset(seat_nums)

    # Book seat 6D (row 6 of 18-seat 2+1 coach) -> verify capacity shrink guard
    stops = seat_map["stops"]
    user_client = _login_as_seeded_user(app)
    booking = user_client.post(
        "/api/bookings",
        json={
            "trip_id": trip["id"],
            "seat_number": "6D",
            "passenger_name": "Ananya Menon",
            "passenger_email": "ananya@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": stops[0]["id"],
            "drop_stop_id": stops[-1]["id"],
        },
    )
    assert booking.status_code == 201
    pnr = booking.get_json()["booking"]["pnr"]

    # Reducing bus capacity below occupied seat 6D fails cleanly (409)
    cap_shrink_err = admin_client.patch(
        f"/api/admin/buses/{bus['id']}",
        json={"total_seats": 12},
    )
    assert cap_shrink_err.status_code == 409

    # Booked stops/resources guard deletion cleanly
    assert admin_client.delete(f"/api/admin/buses/{bus['id']}").status_code == 409
    assert admin_client.delete(f"/api/admin/schedules/{sched['id']}").status_code == 409
    assert admin_client.delete(f"/api/admin/routes/{route['id']}").status_code == 409
    shrink_err = admin_client.patch(
        f"/api/admin/routes/{route['id']}",
        json={"stops": ["Kochi (Vyttila)", "Adimali"]},
    )
    assert shrink_err.status_code == 409

    # Create secondary unbooked bus & schedule -> verify clean delete succeeds
    b2 = admin_client.post(
        "/api/admin/buses",
        json={"operator_name": "Temp Bus", "registration_number": "KL-99-TMP-001"},
    ).get_json()["bus"]
    s2 = admin_client.post(
        "/api/admin/schedules",
        json={
            "route_id": route["id"],
            "bus_id": b2["id"],
            "departure_time": "15:00",
            "arrival_time": "19:00",
            "base_fare": 500,
            "horizon_days": 2,
        },
    ).get_json()["schedule"]
    # Unbooked bus capacity change syncs cleanly before delete
    b2_upd = admin_client.patch(f"/api/admin/buses/{b2['id']}", json={"total_seats": 24})
    assert b2_upd.status_code == 200 and b2_upd.get_json()["bus"]["total_seats"] == 24
    assert admin_client.delete(f"/api/admin/schedules/{s2['id']}").status_code == 200
    assert admin_client.delete(f"/api/admin/buses/{b2['id']}").status_code == 200

    # 5. Booking search by date & demo refund workflow
    b_search = admin_client.get(f"/api/admin/bookings?travel_date={today_iso}&q={pnr}")
    assert b_search.status_code == 200
    assert b_search.get_json()["pagination"]["total"] == 1
    assert admin_client.get(f"/api/admin/bookings/{pnr}").status_code == 200

    # Refund before cancellation fails (409)
    assert admin_client.post(f"/api/admin/bookings/{pnr}/refund", json={}).status_code == 409

    # Cancel leaving refund PENDING, then process demo refund cleanly
    cancel_resp = admin_client.post(
        f"/api/admin/bookings/{pnr}/cancel",
        json={"reason": "Weather disruption", "process_refund": False},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.get_json()["booking"]["refund_status"] == "PENDING"

    refund_resp = admin_client.post(
        f"/api/admin/bookings/{pnr}/refund",
        json={"amount": 720, "note": "Full demo refund issued"},
    )
    assert refund_resp.status_code == 200
    r_bk = refund_resp.get_json()["booking"]
    assert r_bk["refund_status"] == "PROCESSED"
    assert r_bk["refund_amount"] == 720.0
    assert r_bk["is_demo_payment"] is True

    # Duplicate refund blocked (409)
    assert admin_client.post(f"/api/admin/bookings/{pnr}/refund", json={}).status_code == 409

    # Released seat is immediately bookable again
    rebook = user_client.post(
        "/api/bookings",
        json={
            "trip_id": trip["id"],
            "seat_number": "6D",
            "passenger_name": "Rebook User",
            "passenger_email": "rebook@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": stops[0]["id"],
            "drop_stop_id": stops[-1]["id"],
        },
    )
    assert rebook.status_code == 201


def test_user_management_last_admin_protection_and_analytics(app):
    with app.app_context():
        run_seed(horizon_days=2)

    admin_client = _login_as_seeded_admin(app)

    users_resp = admin_client.get("/api/admin/users?page=1&per_page=10")
    assert users_resp.status_code == 200
    users = users_resp.get_json()["users"]
    admin_row = next(u for u in users if u["email"] == "admin@busreserve.local")
    passenger_row = next(u for u in users if u["email"] == "passenger@busreserve.local")

    # Self-demote and self-deactivate blocked (409)
    assert (
        admin_client.patch(f"/api/admin/users/{admin_row['id']}", json={"role": "USER"}).status_code
        == 409
    )
    assert (
        admin_client.patch(
            f"/api/admin/users/{admin_row['id']}", json={"is_active": False}
        ).status_code
        == 409
    )

    # Promote passenger to second ADMIN -> last active admin cannot lose admin access
    assert (
        admin_client.patch(
            f"/api/admin/users/{passenger_row['id']}", json={"role": "ADMIN"}
        ).status_code
        == 200
    )

    # Second admin logs in cleanly and can manage another admin while active admin remains
    second_admin_client = app.test_client()
    assert (
        second_admin_client.post(
            "/api/auth/admin/login",
            json={"email": "passenger@busreserve.local", "password": USER_TEST_PW},
        ).status_code
        == 200
    )
    # Second admin can demote admin_row back to USER (because second_admin stays active)
    assert (
        second_admin_client.patch(
            f"/api/admin/users/{admin_row['id']}", json={"role": "USER"}
        ).status_code
        == 200
    )
    # Now second_admin is the LAST active admin -> cannot demote or deactivate self!
    assert (
        second_admin_client.patch(
            f"/api/admin/users/{passenger_row['id']}", json={"role": "USER"}
        ).status_code
        == 409
    )

    # Restore original roles cleanly
    assert (
        second_admin_client.patch(
            f"/api/admin/users/{admin_row['id']}", json={"role": "ADMIN"}
        ).status_code
        == 200
    )
    assert (
        admin_client.post(
            "/api/auth/admin/login",
            json={"email": "admin@busreserve.local", "password": ADMIN_TEST_PW},
        ).status_code
        == 200
    )
    assert (
        admin_client.patch(
            f"/api/admin/users/{passenger_row['id']}", json={"role": "USER"}
        ).status_code
        == 200
    )

    # Analytics & overview accuracy
    analytics = admin_client.get("/api/admin/analytics")
    assert analytics.status_code == 200
    data = analytics.get_json()
    summary = data["summary"]
    assert summary["confirmed_bookings"] == 3
    assert summary["demo_net_revenue"] > 0
    assert "Demo revenue" in summary["revenue_disclaimer"]
    assert summary["total_buses"] == 24
    assert len(data["popular_routes"]) >= 1
    assert len(data["booking_trends"]) == 14
    with app.app_context():
        bus_count = len(db.session.execute(select(Bus)).scalars().all())
        assert bus_count == 24
        adm = db.session.get(User, admin_row["id"])
        assert adm.role == "ADMIN"
