"""Real multi-connection PostgreSQL concurrency tests preventing double-booking."""

import threading
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.extensions import db
from app.models import Booking


def test_concurrent_api_bookings_allow_only_single_winner(app, sample_data):
    """Fire 10 simultaneous POST /api/bookings requests for the same seat via separate threads."""
    worker_count = 10
    barrier = threading.Barrier(worker_count)
    results: list[tuple[int, str | None]] = []
    lock = threading.Lock()

    def _book_seat(idx: int) -> None:
        local_client = app.test_client()
        payload = {
            "trip_id": sample_data["upcoming_trip_id"],
            "seat_number": "1A",
            "passenger_name": f"Passenger {chr(65 + idx)}",
            "passenger_email": f"passenger{idx}@example.com",
            "passenger_phone": f"98765432{idx:02d}",
            "boarding_stop_id": sample_data["pr_stop_ids"][0],
            "drop_stop_id": sample_data["pr_stop_ids"][3],
        }
        barrier.wait(timeout=5)
        resp = local_client.post("/api/bookings", json=payload)
        body = resp.get_json() or {}
        pnr = body.get("booking", {}).get("pnr")
        with lock:
            results.append((resp.status_code, pnr))

    threads = [threading.Thread(target=_book_seat, args=(i,)) for i in range(worker_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert len(results) == worker_count
    statuses = [status for status, _ in results]
    assert statuses.count(201) == 1
    assert statuses.count(409) == worker_count - 1

    with app.app_context():
        confirmed_count = db.session.execute(
            select(func.count(Booking.id)).where(
                Booking.trip_id == sample_data["upcoming_trip_id"],
                Booking.seat_id == sample_data["first_seat_id"],
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        ).scalar_one()
        total_count = db.session.execute(select(func.count(Booking.id))).scalar_one()
        assert confirmed_count == 1
        assert total_count == 1


def test_postgres_partial_unique_index_enforced_across_independent_sessions(app, sample_data):
    """Verify the PostgreSQL partial unique index under concurrent uncommitted transactions."""
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    engine_a = create_engine(db_uri)
    engine_b = create_engine(db_uri)

    SessionA = sessionmaker(bind=engine_a)
    SessionB = sessionmaker(bind=engine_b)

    session_a = SessionA()
    session_b = SessionB()

    a_flushed = threading.Event()
    b_started = threading.Event()
    b_result: dict[str, object] = {}

    def _run_session_b() -> None:
        a_flushed.wait(timeout=5)
        booking_b = Booking(
            pnr="BRCONC0002",
            trip_id=sample_data["upcoming_trip_id"],
            seat_id=sample_data["first_seat_id"],
            passenger_name="Session B User",
            passenger_email="sessionb@example.com",
            passenger_phone="9876543202",
            boarding_stop_id=sample_data["pr_stop_ids"][0],
            drop_stop_id=sample_data["pr_stop_ids"][3],
            total_fare=Decimal("680.00"),
            status=Booking.STATUS_CONFIRMED,
        )
        session_b.add(booking_b)
        b_started.set()
        try:
            # Flush blocks on PostgreSQL unique index lock until Session A commits
            session_b.flush()
            session_b.commit()
            b_result["committed"] = True
        except IntegrityError as exc:
            session_b.rollback()
            b_result["integrity_error"] = str(exc)

    try:
        booking_a = Booking(
            pnr="BRCONC0001",
            trip_id=sample_data["upcoming_trip_id"],
            seat_id=sample_data["first_seat_id"],
            passenger_name="Session A User",
            passenger_email="sessiona@example.com",
            passenger_phone="9876543201",
            boarding_stop_id=sample_data["pr_stop_ids"][0],
            drop_stop_id=sample_data["pr_stop_ids"][3],
            total_fare=Decimal("680.00"),
            status=Booking.STATUS_CONFIRMED,
        )
        thread_b = threading.Thread(target=_run_session_b)
        thread_b.start()

        session_a.add(booking_a)
        session_a.flush()
        a_flushed.set()

        b_started.wait(timeout=5)
        session_a.commit()
        thread_b.join(timeout=10)

        assert "integrity_error" in b_result
        assert "uq_active_booking_trip_seat" in str(b_result["integrity_error"])
        assert b_result.get("committed") is not True

        # Once session_a cancels, session_b can insert a new CONFIRMED booking for the same seat
        booking_a.status = Booking.STATUS_CANCELLED
        session_a.commit()

        booking_b_retry = Booking(
            pnr="BRCONC0003",
            trip_id=sample_data["upcoming_trip_id"],
            seat_id=sample_data["first_seat_id"],
            passenger_name="Session B Retry",
            passenger_email="sessionb@example.com",
            passenger_phone="9876543202",
            boarding_stop_id=sample_data["pr_stop_ids"][0],
            drop_stop_id=sample_data["pr_stop_ids"][3],
            total_fare=Decimal("680.00"),
            status=Booking.STATUS_CONFIRMED,
        )
        session_b.add(booking_b_retry)
        session_b.commit()
        assert booking_b_retry.id is not None
    finally:
        session_a.close()
        session_b.close()
        engine_a.dispose()
        engine_b.dispose()
