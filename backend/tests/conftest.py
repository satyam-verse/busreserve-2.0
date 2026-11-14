"""Pytest fixtures wired to a real PostgreSQL test database."""

import os

os.environ.setdefault("SEED_DEMO_ADMIN_PASSWORD", "TestAdminPass999!")
os.environ.setdefault("SEED_DEMO_USER_PASSWORD", "TestUserPass999!")

from datetime import time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Route, RouteStop, Trip, TripSeat
from app.utils.timezone import get_app_today


@pytest.fixture(scope="session")
def app():
    """Create a Flask application configured for PostgreSQL testing."""
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://busreserve:busreserve_dev@localhost:5432/busreserve_test",
        ),
    )
    if not test_db_url.startswith("postgresql"):
        raise RuntimeError(f"Tests require PostgreSQL, got: {test_db_url}")

    flask_app = create_app(
        "testing",
        config_overrides={"SQLALCHEMY_DATABASE_URI": test_db_url},
    )

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        db.session.remove()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(app):
    """Reset PostgreSQL tables between tests so multi-connection tests stay isolated."""
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "TRUNCATE TABLE notifications, payment_transactions, "
                    "ai_usage_daily, ai_conversation_messages, bookings, "
                    "trip_seats, trips, bus_schedules, buses, route_stops, routes, cities, "
                    "auth_sessions, users RESTART IDENTITY CASCADE"
                )
            )
    yield
    with app.app_context():
        db.session.remove()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def sample_data(app):
    """Seed two routes, ordered stops, an upcoming trip, a past trip, and seats."""
    with app.app_context():
        route_pr = Route(
            name="Patna to Ranchi Express",
            source="Patna",
            destination="Ranchi",
        )
        route_pg = Route(
            name="Patna to Gaya Intercity",
            source="Patna",
            destination="Gaya",
        )
        db.session.add_all([route_pr, route_pg])
        db.session.flush()

        pr_stops = [
            RouteStop(route_id=route_pr.id, stop_name="Patna (ISBT)", stop_order=1),
            RouteStop(route_id=route_pr.id, stop_name="Jehanabad", stop_order=2),
            RouteStop(route_id=route_pr.id, stop_name="Hazaribagh", stop_order=3),
            RouteStop(route_id=route_pr.id, stop_name="Ranchi (Khadgarha)", stop_order=4),
        ]
        pg_stops = [
            RouteStop(route_id=route_pg.id, stop_name="Patna (ISBT)", stop_order=1),
            RouteStop(route_id=route_pg.id, stop_name="Masaurhi", stop_order=2),
            RouteStop(route_id=route_pg.id, stop_name="Gaya (Gandhi Maidan)", stop_order=3),
        ]
        db.session.add_all(pr_stops + pg_stops)
        db.session.flush()

        today_ist = get_app_today()
        upcoming_date = today_ist + timedelta(days=2)
        past_date = today_ist - timedelta(days=2)

        upcoming_trip = Trip(
            route_id=route_pr.id,
            operator_name="Bihar State Volvo Express",
            bus_number="BR-01-PA-4821",
            departure_time=time(7, 30),
            arrival_time=time(14, 15),
            travel_date=upcoming_date,
            base_fare=Decimal("680.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        past_trip = Trip(
            route_id=route_pr.id,
            operator_name="Bihar State Volvo Express",
            bus_number="BR-01-PA-4822",
            departure_time=time(7, 30),
            arrival_time=time(14, 15),
            travel_date=past_date,
            base_fare=Decimal("680.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        other_trip = Trip(
            route_id=route_pg.id,
            operator_name="Magadh Deluxe Travels",
            bus_number="BR-02-GA-1104",
            departure_time=time(9, 0),
            arrival_time=time(12, 0),
            travel_date=upcoming_date,
            base_fare=Decimal("260.00"),
            status=Trip.STATUS_SCHEDULED,
        )
        db.session.add_all([upcoming_trip, past_trip, other_trip])
        db.session.flush()

        seats_upcoming = [
            TripSeat(
                trip_id=upcoming_trip.id,
                seat_number=sn,
                seat_type=TripSeat.SEAT_WINDOW if sn.endswith(("A", "D")) else TripSeat.SEAT_AISLE,
            )
            for sn in ["1A", "1B", "1C", "1D", "2A", "2B"]
        ]
        seats_past = [
            TripSeat(trip_id=past_trip.id, seat_number="1A", seat_type=TripSeat.SEAT_WINDOW)
        ]
        seats_other = [
            TripSeat(trip_id=other_trip.id, seat_number="1A", seat_type=TripSeat.SEAT_WINDOW)
        ]
        db.session.add_all(seats_upcoming + seats_past + seats_other)
        db.session.flush()

        payload = {
            "route_pr_id": route_pr.id,
            "route_pg_id": route_pg.id,
            "pr_stop_ids": [s.id for s in pr_stops],
            "pg_stop_ids": [s.id for s in pg_stops],
            "upcoming_trip_id": upcoming_trip.id,
            "upcoming_date": upcoming_date.isoformat(),
            "past_trip_id": past_trip.id,
            "past_date": past_date.isoformat(),
            "other_trip_id": other_trip.id,
            "first_seat_id": seats_upcoming[0].id,
        }
        db.session.commit()
        db.session.remove()
        return payload
