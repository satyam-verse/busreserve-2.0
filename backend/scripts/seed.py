"""Idempotent database seed script for dynamic Indian cities, routes, and 90-day schedules."""

import logging
import os
import secrets
from datetime import date, time, timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import select

from app.extensions import db
from app.models import Booking, Bus, BusSchedule, City, Route, RouteStop, Trip, TripSeat, User
from app.services.schedule_service import extract_city_name, materialize_trips_for_schedules
from app.utils.timezone import get_app_today

logger = logging.getLogger("busreserve.seed")

INDIAN_CITIES = [
    {"name": "Patna", "state": "Bihar", "aliases": "PAT,Pataliputra"},
    {"name": "Ranchi", "state": "Jharkhand", "aliases": "IXR"},
    {"name": "Gaya", "state": "Bihar", "aliases": "GAY,Bodh Gaya"},
    {"name": "Jehanabad", "state": "Bihar", "aliases": None},
    {"name": "Masaurhi", "state": "Bihar", "aliases": None},
    {"name": "Makhdumpur", "state": "Bihar", "aliases": None},
    {"name": "Hazaribagh", "state": "Jharkhand", "aliases": None},
    {"name": "Muzaffarpur", "state": "Bihar", "aliases": None},
    {"name": "Darbhanga", "state": "Bihar", "aliases": None},
    {"name": "Bhagalpur", "state": "Bihar", "aliases": None},
    {"name": "Delhi", "state": "Delhi NCR", "aliases": "New Delhi,DEL"},
    {"name": "Gurugram", "state": "Haryana", "aliases": "Gurgaon"},
    {"name": "Noida", "state": "Uttar Pradesh", "aliases": "Greater Noida"},
    {"name": "Neemrana", "state": "Rajasthan", "aliases": None},
    {"name": "Behror", "state": "Rajasthan", "aliases": None},
    {"name": "Jaipur", "state": "Rajasthan", "aliases": "JAI,Pink City"},
    {"name": "Agra", "state": "Uttar Pradesh", "aliases": "AGR"},
    {"name": "Kanpur", "state": "Uttar Pradesh", "aliases": "KNU"},
    {"name": "Lucknow", "state": "Uttar Pradesh", "aliases": "LKO"},
    {"name": "Varanasi", "state": "Uttar Pradesh", "aliases": "VNS,Benares,Kashi"},
    {"name": "Bengaluru", "state": "Karnataka", "aliases": "Bangalore,BLR"},
    {"name": "Kengeri", "state": "Karnataka", "aliases": None},
    {"name": "Ramanagara", "state": "Karnataka", "aliases": None},
    {"name": "Mandya", "state": "Karnataka", "aliases": None},
    {"name": "Mysuru", "state": "Karnataka", "aliases": "Mysore,MYQ"},
    {"name": "Pune", "state": "Maharashtra", "aliases": "PNQ"},
    {"name": "Wakad", "state": "Maharashtra", "aliases": None},
    {"name": "Lonavala", "state": "Maharashtra", "aliases": None},
    {"name": "Panvel", "state": "Maharashtra", "aliases": None},
    {"name": "Mumbai", "state": "Maharashtra", "aliases": "Bombay,BOM"},
    {"name": "Hyderabad", "state": "Telangana", "aliases": "HYD"},
    {"name": "Chennai", "state": "Tamil Nadu", "aliases": "Madras,MAA"},
    {"name": "Kolkata", "state": "West Bengal", "aliases": "Calcutta,CCU"},
    {"name": "Ahmedabad", "state": "Gujarat", "aliases": "AMD"},
    {"name": "Surat", "state": "Gujarat", "aliases": "STV"},
    {"name": "Chandigarh", "state": "Chandigarh", "aliases": "IXC"},
    {"name": "Bhopal", "state": "Madhya Pradesh", "aliases": "BHO"},
    {"name": "Indore", "state": "Madhya Pradesh", "aliases": "IDR"},
    {"name": "Nagpur", "state": "Maharashtra", "aliases": "NAG"},
    {"name": "Bhubaneswar", "state": "Odisha", "aliases": "BBI"},
    {"name": "Guwahati", "state": "Assam", "aliases": "GAU"},
    {"name": "Siliguri", "state": "West Bengal", "aliases": "IXB"},
]

ROUTE_CATALOG = [
    {
        "name": "Patna to Ranchi Express",
        "source": "Patna",
        "destination": "Ranchi",
        "stops": [
            ("Patna (ISBT Bariya)", "Patna"),
            ("Jehanabad", "Jehanabad"),
            ("Gaya Bypass", "Gaya"),
            ("Hazaribagh", "Hazaribagh"),
            ("Ranchi (Khadgarha)", "Ranchi"),
        ],
        "schedules": [
            {
                "operator_name": "Bihar State Volvo Express",
                "bus_number": "BR-01-PA-4821",
                "departure_time": time(6, 30),
                "arrival_time": time(13, 45),
                "base_fare": Decimal("680.00"),
            },
            {
                "operator_name": "Chotanagpur Royal Coach",
                "bus_number": "JH-01-EB-2190",
                "departure_time": time(21, 30),
                "arrival_time": time(4, 45),
                "base_fare": Decimal("740.00"),
            },
        ],
    },
    {
        "name": "Ranchi to Patna Express",
        "source": "Ranchi",
        "destination": "Patna",
        "stops": [
            ("Ranchi (Khadgarha)", "Ranchi"),
            ("Hazaribagh", "Hazaribagh"),
            ("Gaya Bypass", "Gaya"),
            ("Jehanabad", "Jehanabad"),
            ("Patna (ISBT Bariya)", "Patna"),
        ],
        "schedules": [
            {
                "operator_name": "Bihar State Volvo Express",
                "bus_number": "BR-01-PA-4822",
                "departure_time": time(7, 0),
                "arrival_time": time(14, 15),
                "base_fare": Decimal("680.00"),
            },
            {
                "operator_name": "Chotanagpur Royal Coach",
                "bus_number": "JH-01-EB-2191",
                "departure_time": time(22, 0),
                "arrival_time": time(5, 15),
                "base_fare": Decimal("740.00"),
            },
        ],
    },
    {
        "name": "Patna to Gaya Intercity",
        "source": "Patna",
        "destination": "Gaya",
        "stops": [
            ("Patna (ISBT Bariya)", "Patna"),
            ("Masaurhi", "Masaurhi"),
            ("Jehanabad", "Jehanabad"),
            ("Makhdumpur", "Makhdumpur"),
            ("Gaya (Gandhi Maidan)", "Gaya"),
        ],
        "schedules": [
            {
                "operator_name": "Magadh Deluxe Travels",
                "bus_number": "BR-02-GA-1104",
                "departure_time": time(7, 15),
                "arrival_time": time(10, 15),
                "base_fare": Decimal("260.00"),
            },
            {
                "operator_name": "Bodh Gaya AC Cruiser",
                "bus_number": "BR-02-GB-5592",
                "departure_time": time(15, 30),
                "arrival_time": time(18, 30),
                "base_fare": Decimal("310.00"),
            },
        ],
    },
    {
        "name": "Gaya to Patna Intercity",
        "source": "Gaya",
        "destination": "Patna",
        "stops": [
            ("Gaya (Gandhi Maidan)", "Gaya"),
            ("Makhdumpur", "Makhdumpur"),
            ("Jehanabad", "Jehanabad"),
            ("Masaurhi", "Masaurhi"),
            ("Patna (ISBT Bariya)", "Patna"),
        ],
        "schedules": [
            {
                "operator_name": "Magadh Deluxe Travels",
                "bus_number": "BR-02-GA-1105",
                "departure_time": time(8, 0),
                "arrival_time": time(11, 0),
                "base_fare": Decimal("260.00"),
            },
            {
                "operator_name": "Bodh Gaya AC Cruiser",
                "bus_number": "BR-02-GB-5593",
                "departure_time": time(16, 45),
                "arrival_time": time(19, 45),
                "base_fare": Decimal("310.00"),
            },
        ],
    },
    {
        "name": "Delhi to Jaipur PinkCity Line",
        "source": "Delhi",
        "destination": "Jaipur",
        "stops": [
            ("Delhi (Kashmere Gate)", "Delhi"),
            ("Gurugram (IFFCO Chowk)", "Gurugram"),
            ("Neemrana", "Neemrana"),
            ("Behror", "Behror"),
            ("Jaipur (Sindhi Camp)", "Jaipur"),
        ],
        "schedules": [
            {
                "operator_name": "Rajputana GoldLine",
                "bus_number": "DL-01-PC-9204",
                "departure_time": time(7, 0),
                "arrival_time": time(12, 30),
                "base_fare": Decimal("790.00"),
            },
            {
                "operator_name": "Aravalli Prime Sleeper",
                "bus_number": "RJ-14-TD-6402",
                "departure_time": time(22, 15),
                "arrival_time": time(4, 0),
                "base_fare": Decimal("920.00"),
            },
        ],
    },
    {
        "name": "Jaipur to Delhi PinkCity Line",
        "source": "Jaipur",
        "destination": "Delhi",
        "stops": [
            ("Jaipur (Sindhi Camp)", "Jaipur"),
            ("Behror", "Behror"),
            ("Neemrana", "Neemrana"),
            ("Gurugram (IFFCO Chowk)", "Gurugram"),
            ("Delhi (Kashmere Gate)", "Delhi"),
        ],
        "schedules": [
            {
                "operator_name": "Rajputana GoldLine",
                "bus_number": "DL-01-PC-9205",
                "departure_time": time(6, 45),
                "arrival_time": time(12, 15),
                "base_fare": Decimal("790.00"),
            },
            {
                "operator_name": "Aravalli Prime Sleeper",
                "bus_number": "RJ-14-TD-6403",
                "departure_time": time(22, 30),
                "arrival_time": time(4, 15),
                "base_fare": Decimal("920.00"),
            },
        ],
    },
    {
        "name": "Bengaluru to Mysuru Heritage",
        "source": "Bengaluru",
        "destination": "Mysuru",
        "stops": [
            ("Bengaluru (Majestic)", "Bengaluru"),
            ("Kengeri", "Kengeri"),
            ("Ramanagara", "Ramanagara"),
            ("Mandya", "Mandya"),
            ("Mysuru (Suburban)", "Mysuru"),
        ],
        "schedules": [
            {
                "operator_name": "Kaveri Airavat Club",
                "bus_number": "KA-01-F-3318",
                "departure_time": time(8, 0),
                "arrival_time": time(11, 15),
                "base_fare": Decimal("440.00"),
            },
            {
                "operator_name": "Nandi Express Shuttle",
                "bus_number": "KA-09-FA-7081",
                "departure_time": time(17, 45),
                "arrival_time": time(21, 0),
                "base_fare": Decimal("410.00"),
            },
        ],
    },
    {
        "name": "Mysuru to Bengaluru Heritage",
        "source": "Mysuru",
        "destination": "Bengaluru",
        "stops": [
            ("Mysuru (Suburban)", "Mysuru"),
            ("Mandya", "Mandya"),
            ("Ramanagara", "Ramanagara"),
            ("Kengeri", "Kengeri"),
            ("Bengaluru (Majestic)", "Bengaluru"),
        ],
        "schedules": [
            {
                "operator_name": "Kaveri Airavat Club",
                "bus_number": "KA-01-F-3319",
                "departure_time": time(7, 30),
                "arrival_time": time(10, 45),
                "base_fare": Decimal("440.00"),
            },
            {
                "operator_name": "Nandi Express Shuttle",
                "bus_number": "KA-09-FA-7082",
                "departure_time": time(18, 0),
                "arrival_time": time(21, 15),
                "base_fare": Decimal("410.00"),
            },
        ],
    },
    {
        "name": "Pune to Mumbai Expressway",
        "source": "Pune",
        "destination": "Mumbai",
        "stops": [
            ("Pune (Swargate)", "Pune"),
            ("Wakad", "Wakad"),
            ("Lonavala", "Lonavala"),
            ("Panvel", "Panvel"),
            ("Mumbai (Dadar East)", "Mumbai"),
        ],
        "schedules": [
            {
                "operator_name": "Sahyadri Shivneri AC",
                "bus_number": "MH-12-PQ-7740",
                "departure_time": time(6, 45),
                "arrival_time": time(10, 15),
                "base_fare": Decimal("520.00"),
            },
            {
                "operator_name": "Deccan Queen Coach",
                "bus_number": "MH-14-BT-3019",
                "departure_time": time(18, 30),
                "arrival_time": time(22, 0),
                "base_fare": Decimal("560.00"),
            },
        ],
    },
    {
        "name": "Mumbai to Pune Expressway",
        "source": "Mumbai",
        "destination": "Pune",
        "stops": [
            ("Mumbai (Dadar East)", "Mumbai"),
            ("Panvel", "Panvel"),
            ("Lonavala", "Lonavala"),
            ("Wakad", "Wakad"),
            ("Pune (Swargate)", "Pune"),
        ],
        "schedules": [
            {
                "operator_name": "Sahyadri Shivneri AC",
                "bus_number": "MH-12-PQ-7741",
                "departure_time": time(7, 15),
                "arrival_time": time(10, 45),
                "base_fare": Decimal("520.00"),
            },
            {
                "operator_name": "Deccan Queen Coach",
                "bus_number": "MH-14-BT-3020",
                "departure_time": time(19, 0),
                "arrival_time": time(22, 30),
                "base_fare": Decimal("560.00"),
            },
        ],
    },
    {
        "name": "Delhi to Lucknow Yamuna Express",
        "source": "Delhi",
        "destination": "Lucknow",
        "stops": [
            ("Delhi (Anand Vihar)", "Delhi"),
            ("Noida (Zero Point)", "Noida"),
            ("Agra (ISBT)", "Agra"),
            ("Kanpur (Jhakarkati)", "Kanpur"),
            ("Lucknow (Alambagh)", "Lucknow"),
        ],
        "schedules": [
            {
                "operator_name": "Awadh Shatabdi Volvo",
                "bus_number": "UP-32-FN-8810",
                "departure_time": time(8, 15),
                "arrival_time": time(16, 0),
                "base_fare": Decimal("880.00"),
            },
            {
                "operator_name": "Gomti Night Cruiser",
                "bus_number": "UP-32-GN-4412",
                "departure_time": time(21, 45),
                "arrival_time": time(5, 30),
                "base_fare": Decimal("950.00"),
            },
        ],
    },
    {
        "name": "Lucknow to Delhi Yamuna Express",
        "source": "Lucknow",
        "destination": "Delhi",
        "stops": [
            ("Lucknow (Alambagh)", "Lucknow"),
            ("Kanpur (Jhakarkati)", "Kanpur"),
            ("Agra (ISBT)", "Agra"),
            ("Noida (Zero Point)", "Noida"),
            ("Delhi (Anand Vihar)", "Delhi"),
        ],
        "schedules": [
            {
                "operator_name": "Awadh Shatabdi Volvo",
                "bus_number": "UP-32-FN-8811",
                "departure_time": time(8, 30),
                "arrival_time": time(16, 15),
                "base_fare": Decimal("880.00"),
            },
            {
                "operator_name": "Gomti Night Cruiser",
                "bus_number": "UP-32-GN-4413",
                "departure_time": time(22, 0),
                "arrival_time": time(5, 45),
                "base_fare": Decimal("950.00"),
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


def run_seed(base_date: date | None = None, horizon_days: int | None = None) -> dict[str, int]:
    """Idempotently seed Indian cities, routes, stops, daily schedules, and 90-day trips."""
    anchor_date = base_date or get_app_today()
    effective_horizon = (
        horizon_days
        if horizon_days is not None
        else max(1, int(current_app.config.get("BOOKING_HORIZON_DAYS", 90)))
    )

    counts = {
        "users_created": 0,
        "cities_created": 0,
        "routes_created": 0,
        "stops_created": 0,
        "schedules_created": 0,
        "trips_created": 0,
        "seats_created": 0,
        "bookings_created": 0,
    }

    demo_user_pw = os.getenv("SEED_DEMO_USER_PASSWORD") or secrets.token_urlsafe(24)
    demo_admin_pw = os.getenv("SEED_DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(24)

    demo_accounts = [
        {
            "email": "passenger@busreserve.local",
            "full_name": "Demo Passenger",
            "phone": "9876500001",
            "role": User.ROLE_USER,
            "password": demo_user_pw,
        },
        {
            "email": "admin@busreserve.local",
            "full_name": "Platform Administrator",
            "phone": "9876500000",
            "role": User.ROLE_ADMIN,
            "password": demo_admin_pw,
        },
    ]
    for acct in demo_accounts:
        existing_user = db.session.execute(
            select(User).where(User.email == acct["email"])
        ).scalar_one_or_none()
        if existing_user is None:
            new_user = User(
                email=acct["email"],
                full_name=acct["full_name"],
                phone=acct["phone"],
                role=acct["role"],
                is_active=True,
                email_verified=True,
            )
            new_user.set_password(acct["password"])
            db.session.add(new_user)
            counts["users_created"] += 1
    db.session.flush()

    existing_cities = {c.name.lower(): c for c in db.session.execute(select(City)).scalars().all()}
    for city_def in INDIAN_CITIES:
        key = city_def["name"].lower()
        if key not in existing_cities:
            db.session.add(
                City(
                    name=city_def["name"],
                    state=city_def["state"],
                    aliases=city_def["aliases"],
                    is_active=True,
                )
            )
            counts["cities_created"] += 1
    db.session.flush()

    route_map: dict[str, Route] = {}
    all_schedules: list[BusSchedule] = []

    for route_def in ROUTE_CATALOG:
        route = db.session.execute(
            select(Route).where(Route.name == route_def["name"])
        ).scalar_one_or_none()

        if route is None:
            dep_t = route_def["schedules"][0]["departure_time"]
            arr_t = route_def["schedules"][0]["arrival_time"]
            dep_mins = dep_t.hour * 60 + dep_t.minute
            arr_mins = arr_t.hour * 60 + arr_t.minute
            if arr_mins <= dep_mins:
                arr_mins += 24 * 60
            dur_mins = arr_mins - dep_mins
            est_dist = max(80, int(round((dur_mins / 60) * 52)))
            route = Route(
                name=route_def["name"],
                source=route_def["source"],
                destination=route_def["destination"],
                distance_km=route_def.get("distance_km", est_dist),
                estimated_duration_minutes=route_def.get("estimated_duration_minutes", dur_mins),
            )
            db.session.add(route)
            db.session.flush()
            counts["routes_created"] += 1
        elif route.distance_km is None or route.estimated_duration_minutes is None:
            dep_t = route_def["schedules"][0]["departure_time"]
            arr_t = route_def["schedules"][0]["arrival_time"]
            dep_mins = dep_t.hour * 60 + dep_t.minute
            arr_mins = arr_t.hour * 60 + arr_t.minute
            if arr_mins <= dep_mins:
                arr_mins += 24 * 60
            dur_mins = arr_mins - dep_mins
            route.estimated_duration_minutes = route.estimated_duration_minutes or dur_mins
            route.distance_km = route.distance_km or max(80, int(round((dur_mins / 60) * 52)))

        route_map[route.name] = route

        existing_stops = {
            s.stop_order: s
            for s in db.session.execute(select(RouteStop).where(RouteStop.route_id == route.id))
            .scalars()
            .all()
        }
        for order_idx, stop_entry in enumerate(route_def["stops"], start=1):
            stop_name, city_name = (
                stop_entry
                if isinstance(stop_entry, tuple)
                else (stop_entry, extract_city_name(stop_entry))
            )
            if order_idx not in existing_stops:
                db.session.add(
                    RouteStop(
                        route_id=route.id,
                        stop_name=stop_name,
                        city_name=city_name,
                        stop_order=order_idx,
                    )
                )
                counts["stops_created"] += 1
            elif not existing_stops[order_idx].city_name:
                existing_stops[order_idx].city_name = city_name
        db.session.flush()

        for sched_idx, sched_def in enumerate(route_def["schedules"]):
            reg_num = sched_def["bus_number"].strip().upper()
            bus_type = (
                Bus.TYPE_VOLVO_MULTI_AXLE
                if "Volvo" in sched_def["operator_name"]
                else (
                    Bus.TYPE_AC_SLEEPER
                    if sched_idx % 2 == 1 and sched_def["base_fare"] >= 700
                    else Bus.TYPE_AC_SEATER
                )
            )
            bus_obj = db.session.execute(
                select(Bus).where(Bus.registration_number == reg_num)
            ).scalar_one_or_none()
            if bus_obj is None:
                bus_obj = Bus(
                    operator_name=sched_def["operator_name"],
                    registration_number=reg_num,
                    bus_type=bus_type,
                    seat_layout=Bus.LAYOUT_2_2,
                    total_seats=32,
                    amenities="AC, Charging Point, Live GPS",
                    is_active=True,
                )
                db.session.add(bus_obj)
                db.session.flush()

            sched = db.session.execute(
                select(BusSchedule).where(
                    BusSchedule.route_id == route.id,
                    BusSchedule.bus_number == sched_def["bus_number"],
                    BusSchedule.departure_time == sched_def["departure_time"],
                )
            ).scalar_one_or_none()

            if sched is None:
                sched = BusSchedule(
                    route_id=route.id,
                    bus_id=bus_obj.id,
                    operator_name=sched_def["operator_name"],
                    bus_number=sched_def["bus_number"],
                    bus_type=bus_obj.bus_type,
                    seat_layout=bus_obj.seat_layout,
                    departure_time=sched_def["departure_time"],
                    arrival_time=sched_def["arrival_time"],
                    base_fare=sched_def["base_fare"],
                    seat_count=32,
                    is_active=True,
                )
                db.session.add(sched)
                db.session.flush()
                counts["schedules_created"] += 1
            elif sched.bus_id is None:
                sched.bus_id = bus_obj.id
                sched.bus_type = bus_obj.bus_type
                sched.seat_layout = bus_obj.seat_layout

            all_schedules.append(sched)

    trip_counts = materialize_trips_for_schedules(
        all_schedules,
        start_date=anchor_date,
        end_date=anchor_date + timedelta(days=effective_horizon),
    )
    counts["trips_created"] += trip_counts["trips_created"]
    counts["seats_created"] += trip_counts["seats_created"]

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
