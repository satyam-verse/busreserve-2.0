"""Idempotent database seed script for BusReserve Indian bus routes and trips."""

import logging
from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Booking, Route, RouteStop, Trip, TripSeat

logger = logging.getLogger("busreserve.seed")

ROUTE_CATALOG = [
    {
        "name": "Patna to Ranchi Express",
        "source": "Patna",
        "destination": "Ranchi",
        "stops": [
            "Patna (ISBT Bariya)",
            "Jehanabad",
            "Gaya Bypass",
            "Hazaribagh",
            "Ranchi (Khadgarha)",
        ],
        "trips": [
            {
                "operator_name": "Bihar State Volvo Express",
                "bus_number": "BR-01-PA-4821",
                "departure_time": time(6, 30),
                "arrival_time": time(13, 45),
                "base_fare": Decimal("680.00"),
                "day_offsets": [0, 1, 2, 3, 5],
            },
            {
                "operator_name": "Chotanagpur Royal Coach",
                "bus_number": "JH-01-EB-2190",
                "departure_time": time(21, 30),
                "arrival_time": time(4, 45),
                "base_fare": Decimal("740.00"),
                "day_offsets": [1, 2, 4],
            },
        ],
    },
    {
        "name": "Patna to Gaya Intercity",
        "source": "Patna",
        "destination": "Gaya",
        "stops": [
            "Patna (ISBT Bariya)",
            "Masaurhi",
            "Jehanabad",
            "Makhdumpur",
            "Gaya (Gandhi Maidan)",
        ],
        "trips": [
            {
                "operator_name": "Magadh Deluxe Travels",
                "bus_number": "BR-02-GA-1104",
                "departure_time": time(7, 15),
                "arrival_time": time(10, 15),
                "base_fare": Decimal("260.00"),
                "day_offsets": [0, 1, 2, 3],
            },
            {
                "operator_name": "Bodh Gaya AC Cruiser",
                "bus_number": "BR-02-GB-5592",
                "departure_time": time(15, 30),
                "arrival_time": time(18, 30),
                "base_fare": Decimal("310.00"),
                "day_offsets": [1, 2, 4, 5],
            },
        ],
    },
    {
        "name": "Delhi to Jaipur PinkCity Line",
        "source": "Delhi",
        "destination": "Jaipur",
        "stops": [
            "Delhi (Kashmere Gate)",
            "Gurugram (IFFCO Chowk)",
            "Neemrana",
            "Behror",
            "Jaipur (Sindhi Camp)",
        ],
        "trips": [
            {
                "operator_name": "Rajputana GoldLine",
                "bus_number": "DL-01-PC-9204",
                "departure_time": time(7, 0),
                "arrival_time": time(12, 30),
                "base_fare": Decimal("790.00"),
                "day_offsets": [0, 1, 2, 3, 5],
            },
            {
                "operator_name": "Aravalli Prime Sleeper",
                "bus_number": "RJ-14-TD-6402",
                "departure_time": time(22, 15),
                "arrival_time": time(4, 0),
                "base_fare": Decimal("920.00"),
                "day_offsets": [1, 2, 3, 4],
            },
        ],
    },
    {
        "name": "Bengaluru to Mysuru Heritage",
        "source": "Bengaluru",
        "destination": "Mysuru",
        "stops": [
            "Bengaluru (Majestic)",
            "Kengeri",
            "Ramanagara",
            "Mandya",
            "Mysuru (Suburban)",
        ],
        "trips": [
            {
                "operator_name": "Kaveri Airavat Club",
                "bus_number": "KA-01-F-3318",
                "departure_time": time(8, 0),
                "arrival_time": time(11, 15),
                "base_fare": Decimal("440.00"),
                "day_offsets": [0, 1, 2, 3, 5],
            },
            {
                "operator_name": "Nandi Express Shuttle",
                "bus_number": "KA-09-FA-7081",
                "departure_time": time(17, 45),
                "arrival_time": time(21, 0),
                "base_fare": Decimal("410.00"),
                "day_offsets": [1, 2, 4],
            },
        ],
    },
    {
        "name": "Pune to Mumbai Expressway",
        "source": "Pune",
        "destination": "Mumbai",
        "stops": [
            "Pune (Swargate)",
            "Wakad",
            "Lonavala",
            "Panvel",
            "Mumbai (Dadar East)",
        ],
        "trips": [
            {
                "operator_name": "Sahyadri Shivneri AC",
                "bus_number": "MH-12-PQ-7740",
                "departure_time": time(6, 45),
                "arrival_time": time(10, 15),
                "base_fare": Decimal("520.00"),
                "day_offsets": [0, 1, 2, 3, 5],
            },
            {
                "operator_name": "Deccan Queen Coach",
                "bus_number": "MH-14-BT-3019",
                "departure_time": time(18, 30),
                "arrival_time": time(22, 0),
                "base_fare": Decimal("560.00"),
                "day_offsets": [1, 2, 3, 4],
            },
        ],
    },
]

DEMO_BOOKINGS = [
    {
        "pnr": "BRSEED0001",
        "route_name": "Patna to Ranchi Express",
        "bus_number": "BR-01-PA-4821",
        "day_offset": 1,
        "seat_number": "1A",
        "passenger_name": "Aarav Sharma",
        "passenger_email": "aarav.sharma@example.com",
        "passenger_phone": "9876501001",
    },
    {
        "pnr": "BRSEED0002",
        "route_name": "Delhi to Jaipur PinkCity Line",
        "bus_number": "DL-01-PC-9204",
        "day_offset": 1,
        "seat_number": "2D",
        "passenger_name": "Priya Verma",
        "passenger_email": "priya.verma@example.com",
        "passenger_phone": "9876501002",
    },
    {
        "pnr": "BRSEED0003",
        "route_name": "Pune to Mumbai Expressway",
        "bus_number": "MH-12-PQ-7740",
        "day_offset": 2,
        "seat_number": "3B",
        "passenger_name": "Rohan Kulkarni",
        "passenger_email": "rohan.kulkarni@example.com",
        "passenger_phone": "9876501003",
    },
]


def _build_coach_seats(trip_id: int, rows: int = 8) -> list[TripSeat]:
    """Generate a 2+2 coach seat layout (1A..8D = 32 seats)."""
    seat_cols = [
        ("A", TripSeat.SEAT_WINDOW),
        ("B", TripSeat.SEAT_AISLE),
        ("C", TripSeat.SEAT_AISLE),
        ("D", TripSeat.SEAT_WINDOW),
    ]
    seats = []
    for row in range(1, rows + 1):
        for col_label, seat_type in seat_cols:
            seats.append(
                TripSeat(
                    trip_id=trip_id,
                    seat_number=f"{row}{col_label}",
                    seat_type=seat_type,
                )
            )
    return seats


def run_seed(base_date: date | None = None) -> dict[str, int]:
    """Idempotently seed sample Indian routes, stops, trips, seats, and bookings."""
    anchor_date = base_date or date.today()
    counts = {
        "routes_created": 0,
        "stops_created": 0,
        "trips_created": 0,
        "seats_created": 0,
        "bookings_created": 0,
    }

    route_map: dict[str, Route] = {}

    for route_def in ROUTE_CATALOG:
        route = db.session.execute(
            select(Route).where(Route.name == route_def["name"])
        ).scalar_one_or_none()

        if route is None:
            route = Route(
                name=route_def["name"],
                source=route_def["source"],
                destination=route_def["destination"],
            )
            db.session.add(route)
            db.session.flush()
            counts["routes_created"] += 1

        route_map[route.name] = route

        existing_stops = {
            s.stop_order: s
            for s in db.session.execute(select(RouteStop).where(RouteStop.route_id == route.id))
            .scalars()
            .all()
        }
        for order_idx, stop_name in enumerate(route_def["stops"], start=1):
            if order_idx not in existing_stops:
                db.session.add(
                    RouteStop(
                        route_id=route.id,
                        stop_name=stop_name,
                        stop_order=order_idx,
                    )
                )
                counts["stops_created"] += 1
        db.session.flush()

        for trip_def in route_def["trips"]:
            for offset in trip_def["day_offsets"]:
                travel_dt = anchor_date + timedelta(days=offset)
                trip = db.session.execute(
                    select(Trip).where(
                        Trip.route_id == route.id,
                        Trip.bus_number == trip_def["bus_number"],
                        Trip.travel_date == travel_dt,
                        Trip.departure_time == trip_def["departure_time"],
                    )
                ).scalar_one_or_none()

                if trip is None:
                    trip = Trip(
                        route_id=route.id,
                        operator_name=trip_def["operator_name"],
                        bus_number=trip_def["bus_number"],
                        departure_time=trip_def["departure_time"],
                        arrival_time=trip_def["arrival_time"],
                        travel_date=travel_dt,
                        base_fare=trip_def["base_fare"],
                        status=Trip.STATUS_SCHEDULED,
                    )
                    db.session.add(trip)
                    db.session.flush()
                    counts["trips_created"] += 1

                    seats = _build_coach_seats(trip.id)
                    db.session.add_all(seats)
                    db.session.flush()
                    counts["seats_created"] += len(seats)

    for sample in DEMO_BOOKINGS:
        existing_pnr = db.session.execute(
            select(Booking).where(Booking.pnr == sample["pnr"])
        ).scalar_one_or_none()
        if existing_pnr is not None:
            continue

        route = route_map[sample["route_name"]]
        target_date = anchor_date + timedelta(days=sample["day_offset"])
        trip = db.session.execute(
            select(Trip).where(
                Trip.route_id == route.id,
                Trip.bus_number == sample["bus_number"],
                Trip.travel_date == target_date,
            )
        ).scalar_one_or_none()
        if trip is None:
            continue

        seat = db.session.execute(
            select(TripSeat).where(
                TripSeat.trip_id == trip.id,
                TripSeat.seat_number == sample["seat_number"],
            )
        ).scalar_one_or_none()
        if seat is None:
            continue

        already_confirmed = db.session.execute(
            select(Booking.id).where(
                Booking.trip_id == trip.id,
                Booking.seat_id == seat.id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        ).scalar_one_or_none()
        if already_confirmed is not None:
            continue

        stops = (
            db.session.execute(
                select(RouteStop)
                .where(RouteStop.route_id == route.id)
                .order_by(RouteStop.stop_order)
            )
            .scalars()
            .all()
        )
        if len(stops) < 2:
            continue

        db.session.add(
            Booking(
                pnr=sample["pnr"],
                trip_id=trip.id,
                seat_id=seat.id,
                passenger_name=sample["passenger_name"],
                passenger_email=sample["passenger_email"],
                passenger_phone=sample["passenger_phone"],
                boarding_stop_id=stops[0].id,
                drop_stop_id=stops[-1].id,
                total_fare=trip.base_fare,
                status=Booking.STATUS_CONFIRMED,
            )
        )
        counts["bookings_created"] += 1

    db.session.commit()
    logger.info("database_seeded", extra=counts)
    return counts


if __name__ == "__main__":
    from app import create_app

    flask_app = create_app()
    with flask_app.app_context():
        result = run_seed()
        print(f"Seed complete: {result}")
