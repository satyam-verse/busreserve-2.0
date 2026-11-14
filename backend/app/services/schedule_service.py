"""Database-driven city, route, and rolling 90-day schedule generation services."""

from datetime import date, time, timedelta
from decimal import Decimal

from flask import current_app
from psycopg2.extras import execute_values
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import BusSchedule, City, Route, RouteStop, Trip, TripSeat
from app.utils.timezone import get_app_today


def get_booking_horizon_bounds(base_date: date | None = None) -> tuple[date, date, int]:
    """Return (min_date, max_date, horizon_days) in APP_TIMEZONE (Asia/Kolkata)."""
    horizon = max(1, int(current_app.config.get("BOOKING_HORIZON_DAYS", 90)))
    min_date = base_date or get_app_today()
    max_date = min_date + timedelta(days=horizon)
    return min_date, max_date, horizon


def extract_city_name(stop_name: str) -> str:
    """Derive a clean city name from a boarding/drop stop label."""
    return stop_name.split("(")[0].strip()


def build_seat_specs(
    seat_count: int = 32,
    seat_layout: str = "2+2",
    bus_type: str = "AC_SEATER",
) -> list[tuple[str, str]]:
    """Build deterministic seat specifications matching coach layout and bus type."""
    if seat_layout == "2+1":
        cols = [
            ("A", TripSeat.SEAT_WINDOW),
            ("B", TripSeat.SEAT_AISLE),
            ("D", TripSeat.SEAT_WINDOW),
        ]
    elif seat_layout == "1+2":
        cols = [
            ("A", TripSeat.SEAT_WINDOW),
            ("C", TripSeat.SEAT_AISLE),
            ("D", TripSeat.SEAT_WINDOW),
        ]
    else:
        cols = [
            ("A", TripSeat.SEAT_WINDOW),
            ("B", TripSeat.SEAT_AISLE),
            ("C", TripSeat.SEAT_AISLE),
            ("D", TripSeat.SEAT_WINDOW),
        ]

    specs: list[tuple[str, str]] = []
    row = 1
    while len(specs) < seat_count:
        for col_label, base_type in cols:
            if len(specs) >= seat_count:
                break
            if bus_type == "AC_SLEEPER":
                seat_type = (
                    TripSeat.SEAT_SLEEPER_LOWER if row % 2 == 1 else TripSeat.SEAT_SLEEPER_UPPER
                )
            elif bus_type == "SEATER_SLEEPER" and len(specs) >= seat_count // 2:
                seat_type = TripSeat.SEAT_SLEEPER_UPPER
            else:
                seat_type = base_type
            specs.append((f"{row}{col_label}", seat_type))
        row += 1
    return specs


def materialize_trips_for_schedules(
    schedules: list[BusSchedule],
    start_date: date,
    end_date: date,
) -> dict[str, int]:
    """Idempotently bulk-create Trip and TripSeat rows across [start_date, end_date]."""
    if not schedules or end_date < start_date:
        return {"trips_created": 0, "seats_created": 0}

    total_days = (end_date - start_date).days + 1
    trip_rows = []
    schedule_meta_map: dict[tuple[int, str, date, time], tuple[int, str, str]] = {}

    for sched in schedules:
        if not sched.is_active:
            continue
        layout = getattr(sched, "seat_layout", None) or "2+2"
        btype = getattr(sched, "bus_type", None) or "AC_SEATER"
        for day_offset in range(total_days):
            travel_dt = start_date + timedelta(days=day_offset)
            key = (sched.route_id, sched.bus_number, travel_dt, sched.departure_time)
            schedule_meta_map[key] = (sched.seat_count, layout, btype)
            trip_rows.append(
                {
                    "route_id": sched.route_id,
                    "bus_id": getattr(sched, "bus_id", None),
                    "operator_name": sched.operator_name,
                    "bus_number": sched.bus_number,
                    "bus_type": btype,
                    "seat_layout": layout,
                    "departure_time": sched.departure_time,
                    "arrival_time": sched.arrival_time,
                    "travel_date": travel_dt,
                    "base_fare": sched.base_fare,
                    "status": Trip.STATUS_SCHEDULED,
                }
            )

    if not trip_rows:
        return {"trips_created": 0, "seats_created": 0}

    inserted_trip_ids: list[tuple[int, tuple[int, str, date, time]]] = []
    batch_size = 500
    for idx in range(0, len(trip_rows), batch_size):
        batch = trip_rows[idx : idx + batch_size]
        stmt = (
            pg_insert(Trip)
            .values(batch)
            .on_conflict_do_nothing(constraint="uq_trip_schedule")
            .returning(
                Trip.id,
                Trip.route_id,
                Trip.bus_number,
                Trip.travel_date,
                Trip.departure_time,
            )
        )
        for row in db.session.execute(stmt).all():
            inserted_trip_ids.append((row[0], (row[1], row[2], row[3], row[4])))

    seat_tuples: list[tuple[int, str, str]] = []
    for trip_id, key in inserted_trip_ids:
        seat_count, layout, btype = schedule_meta_map.get(key, (32, "2+2", "AC_SEATER"))
        for seat_number, seat_type in build_seat_specs(
            seat_count, seat_layout=layout, bus_type=btype
        ):
            seat_tuples.append((trip_id, seat_number, seat_type))

    if seat_tuples:
        sa_conn = db.session.connection()
        raw_conn = getattr(sa_conn.connection, "driver_connection", sa_conn.connection)
        if hasattr(raw_conn, "cursor"):
            with raw_conn.cursor() as cur:
                execute_values(
                    cur,
                    "INSERT INTO trip_seats (trip_id, seat_number, seat_type) "
                    "VALUES %s ON CONFLICT ON CONSTRAINT uq_trip_seat_number DO NOTHING",
                    seat_tuples,
                    page_size=5000,
                )
        else:
            seat_dicts = [
                {"trip_id": tid, "seat_number": sn, "seat_type": st} for tid, sn, st in seat_tuples
            ]
            db.session.execute(insert(TripSeat), seat_dicts)

    return {
        "trips_created": len(inserted_trip_ids),
        "seats_created": len(seat_tuples),
    }


def ensure_horizon_trips(
    horizon_days: int | None = None,
    base_date: date | None = None,
) -> dict[str, int]:
    """Ensure all active BusSchedule templates are materialized across the booking horizon."""
    min_date, default_max, _ = get_booking_horizon_bounds(base_date=base_date)
    max_date = min_date + timedelta(days=horizon_days) if horizon_days is not None else default_max

    schedules = (
        db.session.execute(select(BusSchedule).where(BusSchedule.is_active.is_(True)))
        .scalars()
        .all()
    )
    summary = materialize_trips_for_schedules(schedules, min_date, max_date)
    db.session.commit()
    return summary


def create_city(name: str, state: str | None = None, aliases: str | None = None) -> City:
    """Create or activate a city in the searchable directory."""
    clean_name = name.strip()
    city = db.session.execute(select(City).where(City.name.ilike(clean_name))).scalar_one_or_none()
    if city is None:
        city = City(name=clean_name, state=state, aliases=aliases, is_active=True)
        db.session.add(city)
    else:
        city.is_active = True
        if state:
            city.state = state
        if aliases:
            city.aliases = aliases
    db.session.commit()
    return city


def create_route_with_stops(
    name: str,
    source: str,
    destination: str,
    stops: list[dict[str, str]] | list[str],
    distance_km: int | None = None,
    estimated_duration_minutes: int | None = None,
) -> Route:
    """Create a route with ordered stops and auto-populated city_name values."""
    route = Route(
        name=name.strip(),
        source=source.strip(),
        destination=destination.strip(),
        distance_km=distance_km,
        estimated_duration_minutes=estimated_duration_minutes,
    )
    db.session.add(route)
    db.session.flush()

    for order_idx, stop in enumerate(stops, start=1):
        if isinstance(stop, str):
            stop_name = stop.strip()
            city_name = extract_city_name(stop_name)
        else:
            stop_name = stop["stop_name"].strip()
            city_name = (stop.get("city_name") or extract_city_name(stop_name)).strip()

        db.session.add(
            RouteStop(
                route_id=route.id,
                stop_name=stop_name,
                city_name=city_name,
                stop_order=order_idx,
            )
        )

    db.session.commit()
    db.session.refresh(route)
    return route


def create_schedule_with_horizon(
    route_id: int,
    operator_name: str,
    bus_number: str,
    departure_time: time,
    arrival_time: time,
    base_fare: Decimal,
    seat_count: int = 32,
    horizon_days: int | None = None,
    bus_id: int | None = None,
    bus_type: str = "AC_SEATER",
    seat_layout: str = "2+2",
) -> tuple[BusSchedule, dict[str, int]]:
    """Persist a BusSchedule and materialize trips across the configured booking window."""
    schedule = BusSchedule(
        route_id=route_id,
        bus_id=bus_id,
        operator_name=operator_name.strip(),
        bus_number=bus_number.strip(),
        bus_type=bus_type,
        seat_layout=seat_layout,
        departure_time=departure_time,
        arrival_time=arrival_time,
        base_fare=base_fare,
        seat_count=seat_count,
        is_active=True,
    )
    db.session.add(schedule)
    db.session.flush()

    min_date, default_max, _ = get_booking_horizon_bounds()
    max_date = min_date + timedelta(days=horizon_days) if horizon_days is not None else default_max
    counts = materialize_trips_for_schedules([schedule], min_date, max_date)
    db.session.commit()
    db.session.refresh(schedule)
    return schedule, counts
