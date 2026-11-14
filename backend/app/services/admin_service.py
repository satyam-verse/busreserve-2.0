"""Protected Admin Control Centre domain services."""

import logging
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    AuthSession,
    Booking,
    Bus,
    BusSchedule,
    City,
    Route,
    RouteStop,
    Trip,
    TripSeat,
    User,
)
from app.services.booking_service import cancel_booking, get_booking_by_pnr
from app.services.schedule_service import (
    build_seat_specs,
    create_route_with_stops,
    create_schedule_with_horizon,
    extract_city_name,
    get_booking_horizon_bounds,
)
from app.utils.errors import ConflictError, NotFoundError, ValidationAPIError
from app.utils.timezone import get_app_timezone, get_app_today

logger = logging.getLogger("busreserve.admin_service")


def _paginate_query(stmt, page: int = 1, per_page: int = 20) -> tuple[list[Any], dict[str, int]]:
    safe_page = max(1, int(page))
    safe_per_page = min(100, max(1, int(per_page)))
    total = int(
        db.session.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()
    )
    pages = max(1, math.ceil(total / safe_per_page))
    bounded_page = min(safe_page, pages)
    rows = (
        db.session.execute(stmt.limit(safe_per_page).offset((bounded_page - 1) * safe_per_page))
        .scalars()
        .all()
    )
    return rows, {
        "page": bounded_page,
        "per_page": safe_per_page,
        "total": total,
        "pages": pages,
    }


def _route_stops_signature(stops: list[str]) -> tuple[str, ...]:
    return tuple(s.strip().lower() for s in stops)


def _find_duplicate_route(
    name: str,
    source: str,
    destination: str,
    stops: list[str],
    exclude_route_id: int | None = None,
) -> Route | None:
    stmt = select(Route)
    if exclude_route_id is not None:
        stmt = stmt.where(Route.id != exclude_route_id)
    routes = db.session.execute(stmt).scalars().all()
    clean_name = name.strip().lower()
    src_l = source.strip().lower()
    dst_l = destination.strip().lower()
    target_sig = _route_stops_signature(stops)

    for existing in routes:
        if existing.name.strip().lower() == clean_name:
            return existing
        existing_sig = tuple(s.stop_name.strip().lower() for s in existing.stops)
        if (
            existing.source.strip().lower() == src_l
            and existing.destination.strip().lower() == dst_l
            and existing_sig == target_sig
        ):
            return existing
    return None


def _ensure_bus_for_manual_schedule(
    operator_name: str,
    bus_number: str,
    bus_type: str,
    seat_layout: str,
    seat_count: int,
) -> Bus:
    reg = bus_number.strip().upper()
    bus = db.session.execute(
        select(Bus).where(func.upper(Bus.registration_number) == reg)
    ).scalar_one_or_none()
    if bus is None:
        bus = Bus(
            operator_name=operator_name.strip(),
            registration_number=reg,
            bus_type=bus_type,
            seat_layout=seat_layout,
            total_seats=seat_count,
            is_active=True,
        )
        db.session.add(bus)
        db.session.flush()
    return bus


# ---------------------------------------------------------------------------
# Analytics & Overview
# ---------------------------------------------------------------------------


def get_protected_admin_overview() -> dict[str, Any]:
    """Compute real-time PostgreSQL operational metrics, analytics, and occupancy."""
    min_date, max_date, horizon_days = get_booking_horizon_bounds()
    today_ist = get_app_today()
    tz = get_app_timezone()
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    fourteen_days_ago_ist = today_ist - timedelta(days=13)

    total_users = db.session.execute(
        select(func.count(User.id)).where(User.role == User.ROLE_USER)
    ).scalar_one()
    active_users = db.session.execute(
        select(func.count(User.id)).where(User.role == User.ROLE_USER, User.is_active.is_(True))
    ).scalar_one()
    suspended_users = db.session.execute(
        select(func.count(User.id)).where(User.role == User.ROLE_USER, User.is_active.is_(False))
    ).scalar_one()
    verified_users = db.session.execute(
        select(func.count(User.id)).where(
            User.role == User.ROLE_USER, User.email_verified.is_(True)
        )
    ).scalar_one()
    admin_count = db.session.execute(
        select(func.count(User.id)).where(User.role == User.ROLE_ADMIN, User.is_active.is_(True))
    ).scalar_one()
    new_users_7d = db.session.execute(
        select(func.count(User.id)).where(
            User.role == User.ROLE_USER, User.created_at >= seven_days_ago
        )
    ).scalar_one()

    total_cities = db.session.execute(select(func.count(City.id))).scalar_one()
    active_cities = db.session.execute(
        select(func.count(City.id)).where(City.is_active.is_(True))
    ).scalar_one()
    total_routes = db.session.execute(select(func.count(Route.id))).scalar_one()
    total_buses = db.session.execute(select(func.count(Bus.id))).scalar_one()
    active_buses = db.session.execute(
        select(func.count(Bus.id)).where(Bus.is_active.is_(True))
    ).scalar_one()
    total_schedules = db.session.execute(select(func.count(BusSchedule.id))).scalar_one()
    active_schedules = db.session.execute(
        select(func.count(BusSchedule.id)).where(BusSchedule.is_active.is_(True))
    ).scalar_one()
    total_trips = db.session.execute(select(func.count(Trip.id))).scalar_one()

    total_bookings = db.session.execute(select(func.count(Booking.id))).scalar_one()
    confirmed_bookings = db.session.execute(
        select(func.count(Booking.id)).where(Booking.status == Booking.STATUS_CONFIRMED)
    ).scalar_one()
    cancelled_bookings = db.session.execute(
        select(func.count(Booking.id)).where(Booking.status == Booking.STATUS_CANCELLED)
    ).scalar_one()
    pending_refunds = db.session.execute(
        select(func.count(Booking.id)).where(Booking.refund_status == Booking.REFUND_PENDING)
    ).scalar_one()
    processed_refunds = db.session.execute(
        select(func.count(Booking.id)).where(Booking.refund_status == Booking.REFUND_PROCESSED)
    ).scalar_one()

    demo_confirmed_revenue = (
        db.session.execute(
            select(func.coalesce(func.sum(Booking.total_fare), 0)).where(
                Booking.status == Booking.STATUS_CONFIRMED
            )
        ).scalar_one()
        or 0
    )
    demo_gross_booked = (
        db.session.execute(select(func.coalesce(func.sum(Booking.total_fare), 0))).scalar_one() or 0
    )
    demo_refunded_amount = (
        db.session.execute(
            select(func.coalesce(func.sum(Booking.refund_amount), 0)).where(
                Booking.refund_status == Booking.REFUND_PROCESSED
            )
        ).scalar_one()
        or 0
    )

    total_seats = db.session.execute(select(func.count(TripSeat.id))).scalar_one()
    available_seats = max(int(total_seats) - int(confirmed_bookings), 0)
    occupancy_rate = round((confirmed_bookings / total_seats) * 100, 1) if total_seats else 0.0

    # Popular routes based on real bookings
    pop_rows = db.session.execute(
        select(
            Route.id,
            Route.name,
            Route.source,
            Route.destination,
            Route.distance_km,
            func.count(Booking.id).label("bookings_count"),
            func.coalesce(func.sum(Booking.total_fare), 0).label("demo_revenue"),
        )
        .join(Trip, Trip.route_id == Route.id)
        .join(Booking, Booking.trip_id == Trip.id)
        .where(Booking.status == Booking.STATUS_CONFIRMED)
        .group_by(Route.id, Route.name, Route.source, Route.destination, Route.distance_km)
        .order_by(func.count(Booking.id).desc(), Route.name.asc())
        .limit(8)
    ).all()
    popular_routes = [
        {
            "route_id": row.id,
            "route_name": row.name,
            "source": row.source,
            "destination": row.destination,
            "distance_km": row.distance_km,
            "confirmed_bookings": int(row.bookings_count),
            "demo_revenue": float(row.demo_revenue),
        }
        for row in pop_rows
    ]

    # 14-day booking trend anchored in Asia/Kolkata IST
    trend_map: dict[str, dict[str, Any]] = {}
    for offset in range(14):
        day_iso = (fourteen_days_ago_ist + timedelta(days=offset)).isoformat()
        trend_map[day_iso] = {
            "date": day_iso,
            "confirmed_bookings": 0,
            "cancelled_bookings": 0,
            "demo_revenue": 0.0,
        }

    window_start_utc = datetime.combine(
        fourteen_days_ago_ist, datetime.min.time(), tzinfo=tz
    ).astimezone(UTC)
    trend_bookings = (
        db.session.execute(select(Booking).where(Booking.created_at >= window_start_utc))
        .scalars()
        .all()
    )
    for booking in trend_bookings:
        created = booking.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        ist_date_iso = created.astimezone(tz).date().isoformat()
        bucket = trend_map.get(ist_date_iso)
        if bucket is None:
            continue
        if booking.status == Booking.STATUS_CONFIRMED:
            bucket["confirmed_bookings"] += 1
            bucket["demo_revenue"] = round(bucket["demo_revenue"] + float(booking.total_fare), 2)
        else:
            bucket["cancelled_bookings"] += 1

    # Upcoming trip occupancy
    upcoming_trips = (
        db.session.execute(
            select(Trip)
            .options(joinedload(Trip.route))
            .where(
                Trip.status == Trip.STATUS_SCHEDULED,
                Trip.travel_date >= min_date,
                Trip.travel_date <= max_date,
            )
            .order_by(Trip.travel_date.asc(), Trip.departure_time.asc())
            .limit(15)
        )
        .unique()
        .scalars()
        .all()
    )
    upcoming_ids = [t.id for t in upcoming_trips]
    seat_counts = (
        dict(
            db.session.execute(
                select(TripSeat.trip_id, func.count(TripSeat.id))
                .where(TripSeat.trip_id.in_(upcoming_ids))
                .group_by(TripSeat.trip_id)
            ).all()
        )
        if upcoming_ids
        else {}
    )
    booked_counts = (
        dict(
            db.session.execute(
                select(Booking.trip_id, func.count(Booking.id))
                .where(
                    Booking.trip_id.in_(upcoming_ids),
                    Booking.status == Booking.STATUS_CONFIRMED,
                )
                .group_by(Booking.trip_id)
            ).all()
        )
        if upcoming_ids
        else {}
    )

    trip_occupancy = [
        {
            "trip_id": trip.id,
            "route_name": trip.route.name if trip.route else None,
            "operator_name": trip.operator_name,
            "bus_number": trip.bus_number,
            "bus_type": trip.bus_type,
            "seat_layout": trip.seat_layout,
            "travel_date": trip.travel_date.isoformat(),
            "departure_time": trip.departure_time.strftime("%H:%M"),
            "total_seats": int(seat_counts.get(trip.id, 0)),
            "occupied_seats": int(booked_counts.get(trip.id, 0)),
            "available_seats": max(
                int(seat_counts.get(trip.id, 0)) - int(booked_counts.get(trip.id, 0)), 0
            ),
            "occupancy_rate": round(
                (int(booked_counts.get(trip.id, 0)) / int(seat_counts.get(trip.id, 1))) * 100, 1
            )
            if seat_counts.get(trip.id, 0)
            else 0.0,
        }
        for trip in upcoming_trips
    ]

    recent = (
        db.session.execute(select(Booking).order_by(Booking.created_at.desc()).limit(10))
        .scalars()
        .all()
    )

    return {
        "summary": {
            "total_users": int(total_users),
            "active_users": int(active_users),
            "suspended_users": int(suspended_users),
            "verified_users": int(verified_users),
            "admin_count": int(admin_count),
            "new_users_7d": int(new_users_7d),
            "total_cities": int(total_cities),
            "active_cities": int(active_cities),
            "total_routes": int(total_routes),
            "total_buses": int(total_buses),
            "active_buses": int(active_buses),
            "total_schedules": int(total_schedules),
            "active_schedules": int(active_schedules),
            "total_trips": int(total_trips),
            "booking_horizon_days": horizon_days,
            "total_bookings": int(total_bookings),
            "confirmed_bookings": int(confirmed_bookings),
            "cancelled_bookings": int(cancelled_bookings),
            "pending_refunds_count": int(pending_refunds),
            "processed_refunds_count": int(processed_refunds),
            "demo_gross_revenue": float(demo_gross_booked),
            "demo_net_revenue": float(demo_confirmed_revenue),
            "demo_refunded_amount": float(demo_refunded_amount),
            "revenue_disclaimer": (
                "Demo revenue & refund metrics only — no real payments processed."
            ),
            "total_seats": int(total_seats),
            "occupied_seats": int(confirmed_bookings),
            "available_seats": available_seats,
            "occupancy_rate": occupancy_rate,
        },
        "popular_routes": popular_routes,
        "booking_trends": list(trend_map.values()),
        "trip_occupancy": trip_occupancy,
        "recent_bookings": [b.to_dict() for b in recent],
    }


# ---------------------------------------------------------------------------
# 1. City Management
# ---------------------------------------------------------------------------


def list_admin_cities(
    query: str | None = None,
    state: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(City).order_by(City.name.asc())
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(or_(City.name.ilike(q), City.state.ilike(q), City.aliases.ilike(q)))
    if state and state.strip():
        stmt = stmt.where(City.state.ilike(state.strip()))
    if is_active is not None:
        stmt = stmt.where(City.is_active.is_(is_active))

    cities, pagination = _paginate_query(stmt, page=page, per_page=per_page)

    all_routes = db.session.execute(select(Route)).scalars().all()
    items = []
    for c in cities:
        cname = c.name.strip().lower()
        usage = sum(
            1
            for r in all_routes
            if r.source.strip().lower() == cname
            or r.destination.strip().lower() == cname
            or any((s.city_name or "").strip().lower() == cname for s in r.stops)
        )
        entry = c.to_dict()
        entry["route_count"] = usage
        items.append(entry)

    states = sorted(
        {
            s
            for s in db.session.execute(
                select(City.state).where(City.state.is_not(None)).distinct()
            ).scalars()
            if s and s.strip()
        }
    )
    return {
        "cities": items,
        "items": items,
        "count": len(items),
        "states": states,
        "pagination": pagination,
    }


def admin_create_city(payload: dict[str, Any]) -> City:
    clean_name = payload["name"].strip()
    existing = db.session.execute(
        select(City).where(func.lower(City.name) == clean_name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"City '{clean_name}' already exists.")

    city = City(
        name=clean_name,
        state=payload.get("state").strip() if payload.get("state") else None,
        aliases=payload.get("aliases").strip() if payload.get("aliases") else None,
        is_active=True,
    )
    db.session.add(city)
    db.session.commit()
    db.session.refresh(city)
    return city


def admin_update_city(city_id: int, payload: dict[str, Any]) -> City:
    city = db.session.get(City, city_id)
    if city is None:
        raise NotFoundError(f"City {city_id} was not found.")

    old_name = city.name
    if "name" in payload:
        new_name = payload["name"].strip()
        conflict = db.session.execute(
            select(City).where(func.lower(City.name) == new_name.lower(), City.id != city_id)
        ).scalar_one_or_none()
        if conflict is not None:
            raise ConflictError(f"Another city named '{new_name}' already exists.")
        city.name = new_name
        if new_name.lower() != old_name.lower():
            db.session.execute(
                update(Route)
                .where(func.lower(Route.source) == old_name.lower())
                .values(source=new_name)
            )
            db.session.execute(
                update(Route)
                .where(func.lower(Route.destination) == old_name.lower())
                .values(destination=new_name)
            )
            db.session.execute(
                update(RouteStop)
                .where(func.lower(RouteStop.city_name) == old_name.lower())
                .values(city_name=new_name)
            )

    if "state" in payload:
        city.state = payload["state"].strip() if payload["state"] else None
    if "aliases" in payload:
        city.aliases = payload["aliases"].strip() if payload["aliases"] else None
    if "is_active" in payload:
        city.is_active = bool(payload["is_active"])

    db.session.commit()
    db.session.refresh(city)
    return city


def admin_delete_city(city_id: int) -> None:
    city = db.session.get(City, city_id)
    if city is None:
        raise NotFoundError(f"City {city_id} was not found.")

    cname = city.name.strip().lower()
    linked_route = db.session.execute(
        select(Route.id).where(
            or_(func.lower(Route.source) == cname, func.lower(Route.destination) == cname)
        )
    ).scalar_one_or_none()
    linked_stop = db.session.execute(
        select(RouteStop.id).where(func.lower(RouteStop.city_name) == cname).limit(1)
    ).scalar_one_or_none()

    if linked_route is not None or linked_stop is not None:
        raise ConflictError(
            f"Cannot delete city '{city.name}' because routes or stops reference it. "
            "Pause/deactivate it instead."
        )
    db.session.delete(city)
    db.session.commit()


# ---------------------------------------------------------------------------
# 2. Route Management
# ---------------------------------------------------------------------------


def list_admin_routes(
    query: str | None = None,
    source: str | None = None,
    destination: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(Route).order_by(Route.name.asc())
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(Route.name.ilike(q), Route.source.ilike(q), Route.destination.ilike(q))
        )
    if source and source.strip():
        stmt = stmt.where(Route.source.ilike(f"%{source.strip()}%"))
    if destination and destination.strip():
        stmt = stmt.where(Route.destination.ilike(f"%{destination.strip()}%"))

    routes, pagination = _paginate_query(stmt, page=page, per_page=per_page)
    route_ids = [r.id for r in routes]

    sched_counts = (
        dict(
            db.session.execute(
                select(BusSchedule.route_id, func.count(BusSchedule.id))
                .where(BusSchedule.route_id.in_(route_ids))
                .group_by(BusSchedule.route_id)
            ).all()
        )
        if route_ids
        else {}
    )
    trip_counts = (
        dict(
            db.session.execute(
                select(Trip.route_id, func.count(Trip.id))
                .where(Trip.route_id.in_(route_ids))
                .group_by(Trip.route_id)
            ).all()
        )
        if route_ids
        else {}
    )

    items = []
    for r in routes:
        d = r.to_dict(include_stops=True)
        d["schedule_count"] = int(sched_counts.get(r.id, 0))
        d["trip_count"] = int(trip_counts.get(r.id, 0))
        items.append(d)

    return {
        "routes": items,
        "items": items,
        "count": len(items),
        "pagination": pagination,
    }


def _resolve_active_city(raw_name: str, field_name: str) -> str:
    """Resolve and validate that a route endpoint exists as an active city in PostgreSQL."""
    term = raw_name.strip()
    term_lower = term.lower()
    active_cities = db.session.execute(select(City).where(City.is_active.is_(True))).scalars().all()
    for city in active_cities:
        if city.name.strip().lower() == term_lower:
            return city.name
        if term_lower in {a.lower() for a in city.alias_list()}:
            return city.name
    raise ValidationAPIError(
        f"{field_name.title()} city '{term}' must exist as an active city in the directory.",
        details={field_name: [f"City '{term}' is missing or inactive."]},
    )


def admin_create_route(payload: dict[str, Any]) -> Route:
    source_city = _resolve_active_city(payload["source"], "source")
    dest_city = _resolve_active_city(payload["destination"], "destination")
    if source_city.lower() == dest_city.lower():
        raise ValidationAPIError(
            "Destination must differ from source.",
            details={"destination": ["Destination must differ from source."]},
        )

    dup = _find_duplicate_route(
        name=payload["name"],
        source=source_city,
        destination=dest_city,
        stops=payload["stops"],
    )
    if dup is not None:
        raise ConflictError(
            f"Duplicate route detected matching '{dup.name}' ({dup.source} -> {dup.destination})."
        )

    stops = payload["stops"]
    if len(stops) < 2:
        raise ValidationAPIError("A route must contain at least 2 ordered stops.")

    return create_route_with_stops(
        name=payload["name"],
        source=source_city,
        destination=dest_city,
        stops=stops,
        distance_km=payload.get("distance_km"),
        estimated_duration_minutes=payload.get("estimated_duration_minutes"),
    )


def admin_update_route(route_id: int, payload: dict[str, Any]) -> Route:
    route = db.session.get(Route, route_id)
    if route is None:
        raise NotFoundError(f"Route {route_id} was not found.")

    new_name = payload.get("name", route.name).strip()
    new_source = (
        _resolve_active_city(payload["source"], "source") if "source" in payload else route.source
    )
    new_dest = (
        _resolve_active_city(payload["destination"], "destination")
        if "destination" in payload
        else route.destination
    )
    if new_source.lower() == new_dest.lower():
        raise ValidationAPIError(
            "Destination must differ from source.",
            details={"destination": ["Destination must differ from source."]},
        )

    new_stops = payload.get("stops")
    stop_names_for_dup = new_stops if new_stops is not None else [s.stop_name for s in route.stops]
    dup = _find_duplicate_route(
        name=new_name,
        source=new_source,
        destination=new_dest,
        stops=stop_names_for_dup,
        exclude_route_id=route.id,
    )
    if dup is not None:
        raise ConflictError(
            f"Update conflicts with route '{dup.name}' ({dup.source} -> {dup.destination})."
        )

    route.name = new_name
    route.source = new_source
    route.destination = new_dest
    if "distance_km" in payload:
        route.distance_km = payload["distance_km"]
    if "estimated_duration_minutes" in payload:
        route.estimated_duration_minutes = payload["estimated_duration_minutes"]

    if new_stops is not None:
        existing_by_order = {s.stop_order: s for s in route.stops}
        existing_stop_ids = [s.id for s in route.stops]
        referenced_stop_ids = set(
            db.session.execute(
                select(Booking.boarding_stop_id).where(
                    Booking.boarding_stop_id.in_(existing_stop_ids)
                )
            )
            .scalars()
            .all()
        ) | set(
            db.session.execute(
                select(Booking.drop_stop_id).where(Booking.drop_stop_id.in_(existing_stop_ids))
            )
            .scalars()
            .all()
        )

        if len(new_stops) < len(route.stops):
            removed_ids = {s.id for s in route.stops if s.stop_order > len(new_stops)}
            if removed_ids & referenced_stop_ids:
                raise ConflictError(
                    "Cannot remove stops referenced by existing passenger bookings."
                )

        # Avoid unique constraint collisions while renaming/reordering existing stops
        for idx, stop_obj in enumerate(list(route.stops), start=1):
            if idx <= len(new_stops):
                stop_obj.stop_name = f"__tmp_{route.id}_{idx}_{stop_obj.id}"
            else:
                db.session.delete(stop_obj)
        db.session.flush()

        for idx, raw_stop in enumerate(new_stops, start=1):
            clean_stop = raw_stop.strip()
            clean_city = extract_city_name(clean_stop)
            if idx in existing_by_order:
                existing_by_order[idx].stop_name = clean_stop
                existing_by_order[idx].city_name = clean_city
            else:
                db.session.add(
                    RouteStop(
                        route_id=route.id,
                        stop_name=clean_stop,
                        city_name=clean_city,
                        stop_order=idx,
                    )
                )

    db.session.commit()
    db.session.refresh(route)
    return route


def admin_delete_route(route_id: int) -> None:
    route = db.session.get(Route, route_id)
    if route is None:
        raise NotFoundError(f"Route {route_id} was not found.")
    linked_trip = db.session.execute(
        select(Trip.id).where(Trip.route_id == route_id).limit(1)
    ).scalar_one_or_none()
    linked_sched = db.session.execute(
        select(BusSchedule.id).where(BusSchedule.route_id == route_id).limit(1)
    ).scalar_one_or_none()
    if linked_trip is not None or linked_sched is not None:
        raise ConflictError(
            "Cannot delete a route that has schedules or trips. Remove/pause schedules first."
        )
    db.session.delete(route)
    db.session.commit()


# ---------------------------------------------------------------------------
# 3. Bus Fleet Management
# ---------------------------------------------------------------------------


def list_admin_buses(
    query: str | None = None,
    bus_type: str | None = None,
    seat_layout: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(Bus).order_by(Bus.id.desc())
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Bus.operator_name.ilike(q),
                Bus.registration_number.ilike(q),
                Bus.amenities.ilike(q),
            )
        )
    if bus_type and bus_type in Bus.VALID_TYPES:
        stmt = stmt.where(Bus.bus_type == bus_type)
    if seat_layout and seat_layout in Bus.VALID_LAYOUTS:
        stmt = stmt.where(Bus.seat_layout == seat_layout)
    if is_active is not None:
        stmt = stmt.where(Bus.is_active.is_(is_active))

    buses, pagination = _paginate_query(stmt, page=page, per_page=per_page)
    bus_ids = [b.id for b in buses]

    sched_counts = (
        dict(
            db.session.execute(
                select(BusSchedule.bus_id, func.count(BusSchedule.id))
                .where(BusSchedule.bus_id.in_(bus_ids))
                .group_by(BusSchedule.bus_id)
            ).all()
        )
        if bus_ids
        else {}
    )
    items = []
    for b in buses:
        d = b.to_dict()
        d["schedule_count"] = int(sched_counts.get(b.id, 0))
        items.append(d)

    return {
        "buses": items,
        "items": items,
        "count": len(items),
        "pagination": pagination,
    }


def admin_create_bus(payload: dict[str, Any]) -> Bus:
    reg = payload["registration_number"].strip().upper()
    existing = db.session.execute(
        select(Bus).where(func.upper(Bus.registration_number) == reg)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Bus with registration '{reg}' already exists.")

    bus = Bus(
        operator_name=payload["operator_name"].strip(),
        registration_number=reg,
        bus_type=payload.get("bus_type", Bus.TYPE_AC_SEATER),
        seat_layout=payload.get("seat_layout", Bus.LAYOUT_2_2),
        total_seats=int(payload.get("total_seats", 32)),
        amenities=payload.get("amenities"),
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(bus)
    db.session.commit()
    db.session.refresh(bus)
    return bus


def admin_update_bus(bus_id: int, payload: dict[str, Any]) -> Bus:
    bus = db.session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError(f"Bus {bus_id} was not found.")

    old_reg = bus.registration_number.upper()

    if "registration_number" in payload:
        new_reg = payload["registration_number"].strip().upper()
        conflict = db.session.execute(
            select(Bus).where(
                func.upper(Bus.registration_number) == new_reg,
                Bus.id != bus_id,
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise ConflictError(f"Another bus already uses registration '{new_reg}'.")
        bus.registration_number = new_reg

    if "operator_name" in payload:
        bus.operator_name = payload["operator_name"].strip()
    if "bus_type" in payload:
        bus.bus_type = payload["bus_type"]
    if "seat_layout" in payload:
        bus.seat_layout = payload["seat_layout"]
    if "total_seats" in payload:
        bus.total_seats = int(payload["total_seats"])
    if "amenities" in payload:
        bus.amenities = payload["amenities"]
    if "is_active" in payload:
        bus.is_active = bool(payload["is_active"])

    new_specs = build_seat_specs(
        bus.total_seats, seat_layout=bus.seat_layout, bus_type=bus.bus_type
    )
    new_seat_numbers = {sn for sn, _ in new_specs}

    today_ist = get_app_today()
    future_trips = (
        db.session.execute(
            select(Trip).where(
                or_(Trip.bus_id == bus.id, func.upper(Trip.bus_number) == old_reg),
                Trip.travel_date >= today_ist,
            )
        )
        .scalars()
        .all()
    )
    future_trip_ids = [t.id for t in future_trips]
    if future_trip_ids:
        booked_seat_rows = (
            db.session.execute(
                select(TripSeat.seat_number)
                .join(Booking, Booking.seat_id == TripSeat.id)
                .where(
                    Booking.trip_id.in_(future_trip_ids),
                    Booking.status == Booking.STATUS_CONFIRMED,
                )
            )
            .scalars()
            .all()
        )
        if any(sn not in new_seat_numbers for sn in booked_seat_rows):
            raise ConflictError(
                "Cannot change seat capacity or layout because confirmed bookings "
                "occupy seats outside the new configuration."
            )

    # Keep linked schedules and upcoming trips consistent with updated bus specs
    db.session.execute(
        update(BusSchedule)
        .where(
            or_(
                BusSchedule.bus_id == bus.id,
                func.upper(BusSchedule.bus_number) == old_reg,
            )
        )
        .values(
            bus_id=bus.id,
            operator_name=bus.operator_name,
            bus_number=bus.registration_number,
            bus_type=bus.bus_type,
            seat_layout=bus.seat_layout,
            seat_count=bus.total_seats,
        )
    )
    trips_with_any_bookings = set(
        db.session.execute(
            select(Booking.trip_id).where(Booking.trip_id.in_(future_trip_ids)).distinct()
        )
        .scalars()
        .all()
        if future_trip_ids
        else []
    )
    for trip in future_trips:
        trip.bus_id = bus.id
        trip.operator_name = bus.operator_name
        trip.bus_number = bus.registration_number
        trip.bus_type = bus.bus_type
        trip.seat_layout = bus.seat_layout
        if trip.id not in trips_with_any_bookings:
            db.session.execute(delete(TripSeat).where(TripSeat.trip_id == trip.id))
            for sn, st in new_specs:
                db.session.add(TripSeat(trip_id=trip.id, seat_number=sn, seat_type=st))

    db.session.commit()
    db.session.refresh(bus)
    return bus


def admin_delete_bus(bus_id: int) -> None:
    bus = db.session.get(Bus, bus_id)
    if bus is None:
        raise NotFoundError(f"Bus {bus_id} was not found.")

    reg_upper = bus.registration_number.strip().upper()
    linked_sched = db.session.execute(
        select(BusSchedule.id)
        .where(
            or_(
                BusSchedule.bus_id == bus.id,
                func.upper(BusSchedule.bus_number) == reg_upper,
            )
        )
        .limit(1)
    ).scalar_one_or_none()
    if linked_sched is not None:
        raise ConflictError(
            "Cannot delete bus assigned to schedules. Remove or pause schedules first."
        )

    confirmed_booking = db.session.execute(
        select(Booking.id)
        .join(Trip, Trip.id == Booking.trip_id)
        .where(
            or_(Trip.bus_id == bus.id, func.upper(Trip.bus_number) == reg_upper),
            Booking.status == Booking.STATUS_CONFIRMED,
        )
        .limit(1)
    ).scalar_one_or_none()
    if confirmed_booking is not None:
        raise ConflictError("Cannot delete a bus with confirmed booking dependencies.")

    db.session.delete(bus)
    db.session.commit()


# ---------------------------------------------------------------------------
# 4. Schedule Management
# ---------------------------------------------------------------------------


def list_admin_schedules(
    query: str | None = None,
    route_id: int | None = None,
    bus_id: int | None = None,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(BusSchedule).order_by(BusSchedule.id.desc())
    if route_id is not None:
        stmt = stmt.where(BusSchedule.route_id == route_id)
    if bus_id is not None:
        stmt = stmt.where(BusSchedule.bus_id == bus_id)
    if is_active is not None:
        stmt = stmt.where(BusSchedule.is_active.is_(is_active))
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                BusSchedule.operator_name.ilike(q),
                BusSchedule.bus_number.ilike(q),
            )
        )

    schedules, pagination = _paginate_query(stmt, page=page, per_page=per_page)
    min_date, max_date, _ = get_booking_horizon_bounds()

    items = []
    for s in schedules:
        d = s.to_dict()
        upcoming_count = db.session.execute(
            select(func.count(Trip.id)).where(
                Trip.route_id == s.route_id,
                Trip.bus_number == s.bus_number,
                Trip.departure_time == s.departure_time,
                Trip.travel_date >= min_date,
                Trip.travel_date <= max_date,
                Trip.status == Trip.STATUS_SCHEDULED,
            )
        ).scalar_one()
        d["upcoming_trips_count"] = int(upcoming_count)
        items.append(d)

    return {
        "schedules": items,
        "items": items,
        "count": len(items),
        "pagination": pagination,
    }


def admin_create_schedule(payload: dict[str, Any]) -> tuple[BusSchedule, dict[str, int]]:
    route = db.session.get(Route, payload["route_id"])
    if route is None:
        raise NotFoundError(f"Route {payload['route_id']} was not found.")

    bus = None
    if payload.get("bus_id"):
        bus = db.session.get(Bus, payload["bus_id"])
        if bus is None:
            raise NotFoundError(f"Bus {payload['bus_id']} was not found.")
        if not bus.is_active:
            raise ConflictError(f"Bus '{bus.registration_number}' is inactive.")
        operator_name = bus.operator_name
        bus_number = bus.registration_number
        bus_type = bus.bus_type
        seat_layout = bus.seat_layout
        seat_count = int(payload.get("seat_count") or bus.total_seats)
    else:
        operator_name = payload["operator_name"].strip()
        bus_number = payload["bus_number"].strip().upper()
        bus_type = payload.get("bus_type") or Bus.TYPE_AC_SEATER
        seat_layout = payload.get("seat_layout") or Bus.LAYOUT_2_2
        seat_count = int(payload.get("seat_count") or 32)
        bus = _ensure_bus_for_manual_schedule(
            operator_name=operator_name,
            bus_number=bus_number,
            bus_type=bus_type,
            seat_layout=seat_layout,
            seat_count=seat_count,
        )

    existing = db.session.execute(
        select(BusSchedule).where(
            BusSchedule.route_id == route.id,
            BusSchedule.bus_number == bus_number,
            BusSchedule.departure_time == payload["departure_time"],
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("A schedule with this route, bus number, and departure time exists.")

    return create_schedule_with_horizon(
        route_id=route.id,
        bus_id=bus.id,
        operator_name=operator_name,
        bus_number=bus_number,
        bus_type=bus_type,
        seat_layout=seat_layout,
        departure_time=payload["departure_time"],
        arrival_time=payload["arrival_time"],
        base_fare=Decimal(str(payload["base_fare"])),
        seat_count=seat_count,
        horizon_days=payload.get("horizon_days"),
    )


def admin_update_schedule(schedule_id: int, payload: dict[str, Any]) -> BusSchedule:
    schedule = db.session.get(BusSchedule, schedule_id)
    if schedule is None:
        raise NotFoundError(f"Schedule {schedule_id} was not found.")

    old_bus_number = schedule.bus_number
    old_dep = schedule.departure_time

    if "bus_id" in payload and payload["bus_id"] is not None:
        new_bus = db.session.get(Bus, payload["bus_id"])
        if new_bus is None:
            raise NotFoundError(f"Bus {payload['bus_id']} was not found.")
        if not new_bus.is_active:
            raise ConflictError(f"Bus '{new_bus.registration_number}' is inactive.")
        schedule.bus_id = new_bus.id
        schedule.operator_name = new_bus.operator_name
        schedule.bus_number = new_bus.registration_number
        schedule.bus_type = new_bus.bus_type
        schedule.seat_layout = new_bus.seat_layout
        if "seat_count" not in payload:
            schedule.seat_count = new_bus.total_seats

    if "departure_time" in payload:
        schedule.departure_time = payload["departure_time"]
    if "arrival_time" in payload:
        schedule.arrival_time = payload["arrival_time"]
    if "base_fare" in payload:
        schedule.base_fare = Decimal(str(payload["base_fare"]))
    if "seat_count" in payload:
        schedule.seat_count = int(payload["seat_count"])
    if "is_active" in payload:
        schedule.is_active = bool(payload["is_active"])

    # Prevent conflicting schedule tuple
    dup = db.session.execute(
        select(BusSchedule).where(
            BusSchedule.route_id == schedule.route_id,
            BusSchedule.bus_number == schedule.bus_number,
            BusSchedule.departure_time == schedule.departure_time,
            BusSchedule.id != schedule.id,
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise ConflictError("Another schedule already uses this route, bus, and departure time.")

    if payload.get("apply_to_future_trips", True):
        today_ist = get_app_today()
        future_trips = (
            db.session.execute(
                select(Trip).where(
                    Trip.route_id == schedule.route_id,
                    Trip.bus_number == old_bus_number,
                    Trip.departure_time == old_dep,
                    Trip.travel_date >= today_ist,
                    Trip.status == Trip.STATUS_SCHEDULED,
                )
            )
            .scalars()
            .all()
        )
        for trip in future_trips:
            trip.bus_id = schedule.bus_id
            trip.operator_name = schedule.operator_name
            trip.bus_number = schedule.bus_number
            trip.bus_type = schedule.bus_type
            trip.seat_layout = schedule.seat_layout
            trip.departure_time = schedule.departure_time
            trip.arrival_time = schedule.arrival_time
            trip.base_fare = schedule.base_fare

            # Add missing seats if capacity increased on unbooked future trips
            existing_seat_count = db.session.execute(
                select(func.count(TripSeat.id)).where(TripSeat.trip_id == trip.id)
            ).scalar_one()
            if existing_seat_count < schedule.seat_count:
                existing_nums = set(
                    db.session.execute(
                        select(TripSeat.seat_number).where(TripSeat.trip_id == trip.id)
                    )
                    .scalars()
                    .all()
                )
                for sn, st in build_seat_specs(
                    schedule.seat_count,
                    seat_layout=schedule.seat_layout,
                    bus_type=schedule.bus_type,
                ):
                    if sn not in existing_nums:
                        db.session.add(TripSeat(trip_id=trip.id, seat_number=sn, seat_type=st))

    db.session.commit()
    db.session.refresh(schedule)
    return schedule


def admin_toggle_schedule(schedule_id: int, is_active: bool) -> BusSchedule:
    schedule = db.session.get(BusSchedule, schedule_id)
    if schedule is None:
        raise NotFoundError(f"Schedule {schedule_id} was not found.")
    schedule.is_active = bool(is_active)
    db.session.commit()
    db.session.refresh(schedule)
    return schedule


def admin_delete_schedule(schedule_id: int) -> None:
    schedule = db.session.get(BusSchedule, schedule_id)
    if schedule is None:
        raise NotFoundError(f"Schedule {schedule_id} was not found.")

    matching_trip_ids = (
        db.session.execute(
            select(Trip.id).where(
                Trip.route_id == schedule.route_id,
                Trip.bus_number == schedule.bus_number,
                Trip.departure_time == schedule.departure_time,
            )
        )
        .scalars()
        .all()
    )
    if matching_trip_ids:
        any_booking = db.session.execute(
            select(Booking.id).where(Booking.trip_id.in_(matching_trip_ids)).limit(1)
        ).scalar_one_or_none()
        if any_booking is not None:
            raise ConflictError(
                "Cannot delete schedule with existing booking history. Pause the schedule instead."
            )
        db.session.execute(delete(Trip).where(Trip.id.in_(matching_trip_ids)))

    db.session.delete(schedule)
    db.session.commit()


def admin_cancel_trip(trip_id: int) -> Trip:
    trip = db.session.get(Trip, trip_id)
    if trip is None:
        raise NotFoundError(f"Trip {trip_id} was not found.")
    confirmed = db.session.execute(
        select(Booking.id).where(
            Booking.trip_id == trip_id,
            Booking.status == Booking.STATUS_CONFIRMED,
        )
    ).scalar_one_or_none()
    if confirmed is not None:
        raise ConflictError("Cancel confirmed passenger bookings before cancelling this trip.")
    trip.status = Trip.STATUS_CANCELLED
    db.session.commit()
    db.session.refresh(trip)
    return trip


# ---------------------------------------------------------------------------
# 5. Booking & Demo Refund Management
# ---------------------------------------------------------------------------


def list_admin_bookings(
    status: str | None = None,
    refund_status: str | None = None,
    travel_date: date | None = None,
    query: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = (
        select(Booking).join(Trip, Trip.id == Booking.trip_id).order_by(Booking.created_at.desc())
    )
    if status and status in (Booking.STATUS_CONFIRMED, Booking.STATUS_CANCELLED):
        stmt = stmt.where(Booking.status == status)
    if refund_status and refund_status in (
        Booking.REFUND_NONE,
        Booking.REFUND_PENDING,
        Booking.REFUND_PROCESSED,
        Booking.REFUND_NOT_APPLICABLE,
    ):
        stmt = stmt.where(Booking.refund_status == refund_status)
    if travel_date is not None:
        stmt = stmt.where(Trip.travel_date == travel_date)
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Booking.pnr.ilike(q),
                Booking.passenger_name.ilike(q),
                Booking.passenger_email.ilike(q),
                Booking.passenger_phone.ilike(q),
            )
        )

    bookings, pagination = _paginate_query(stmt, page=page, per_page=per_page)
    items = [b.to_dict() for b in bookings]
    return {
        "bookings": items,
        "items": items,
        "count": len(items),
        "pagination": pagination,
    }


def get_admin_booking_detail(pnr: str) -> dict[str, Any]:
    booking = get_booking_by_pnr(pnr)
    data = booking.to_dict()
    data["owner"] = booking.user.to_dict() if booking.user else None
    return data


def admin_cancel_booking(
    pnr: str,
    reason: str | None = None,
    process_refund: bool = True,
) -> Booking:
    return cancel_booking(
        pnr,
        reason=reason or "Cancelled by administrator",
        mark_refund_processed=process_refund,
    )


def admin_process_refund(
    pnr: str,
    amount: Decimal | None = None,
    note: str | None = None,
) -> Booking:
    normalized_pnr = pnr.strip().upper()
    booking = get_booking_by_pnr(normalized_pnr)
    if booking.status != Booking.STATUS_CANCELLED:
        raise ConflictError("Cancel the reservation before processing a demo refund.")
    if booking.refund_status == Booking.REFUND_PROCESSED:
        raise ConflictError(f"Demo refund for {normalized_pnr} has already been processed.")

    refund_amt = amount if amount is not None else booking.total_fare
    if refund_amt < 0 or refund_amt > booking.total_fare:
        raise ValidationAPIError(
            "Refund amount must be between 0 and the reservation total fare.",
            details={"amount": [f"Amount must not exceed {float(booking.total_fare):.2f}."]},
        )

    booking.refund_status = Booking.REFUND_PROCESSED
    booking.refund_amount = refund_amt
    booking.refunded_at = datetime.now(UTC)
    if note:
        booking.cancellation_reason = note.strip()[:255]

    db.session.commit()
    db.session.refresh(booking)
    logger.info(
        "admin_demo_refund_processed",
        extra={"pnr": booking.pnr, "refund_amount": float(refund_amt)},
    )
    return booking


# ---------------------------------------------------------------------------
# 6. User Management & Last-Admin Protection
# ---------------------------------------------------------------------------


def list_admin_users(
    query: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    email_verified: bool | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    stmt = select(User).order_by(User.created_at.desc())
    if role and role in (User.ROLE_USER, User.ROLE_ADMIN):
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if email_verified is not None:
        stmt = stmt.where(User.email_verified.is_(email_verified))
    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(q), User.full_name.ilike(q), User.phone.ilike(q)))

    users, pagination = _paginate_query(stmt, page=page, per_page=per_page)
    user_ids = [u.id for u in users]

    booking_counts = (
        dict(
            db.session.execute(
                select(Booking.user_id, func.count(Booking.id))
                .where(Booking.user_id.in_(user_ids))
                .group_by(Booking.user_id)
            ).all()
        )
        if user_ids
        else {}
    )
    active_sess_counts = (
        dict(
            db.session.execute(
                select(AuthSession.user_id, func.count(AuthSession.id))
                .where(
                    AuthSession.user_id.in_(user_ids),
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > datetime.now(UTC),
                )
                .group_by(AuthSession.user_id)
            ).all()
        )
        if user_ids
        else {}
    )

    items = []
    for u in users:
        entry = u.to_dict()
        entry["booking_count"] = int(booking_counts.get(u.id, 0))
        entry["active_sessions_count"] = int(active_sess_counts.get(u.id, 0))
        items.append(entry)

    return {
        "users": items,
        "items": items,
        "count": len(items),
        "pagination": pagination,
    }


def update_admin_user(
    admin_user: User,
    target_user_id: int,
    payload: dict[str, Any],
) -> User:
    """Update user status/role while preventing self-lockout and removing the last active ADMIN."""
    target = db.session.get(User, target_user_id)
    if target is None:
        raise NotFoundError(f"User {target_user_id} was not found.")

    if target.id == admin_user.id:
        if payload.get("is_active") is False:
            raise ConflictError("Administrators cannot deactivate their own active account.")
        if "role" in payload and payload["role"] != User.ROLE_ADMIN:
            raise ConflictError("Administrators cannot demote their own administrative role.")

    will_lose_admin = (
        target.role == User.ROLE_ADMIN
        and target.is_active
        and (
            payload.get("is_active") is False
            or ("role" in payload and payload["role"] != User.ROLE_ADMIN)
        )
    )
    if will_lose_admin:
        other_active_admins = db.session.execute(
            select(func.count(User.id)).where(
                User.role == User.ROLE_ADMIN,
                User.is_active.is_(True),
                User.id != target.id,
            )
        ).scalar_one()
        if int(other_active_admins) == 0:
            raise ConflictError(
                "Cannot deactivate or demote the last remaining active administrator."
            )

    if "is_active" in payload:
        target.is_active = bool(payload["is_active"])
        if not target.is_active:
            db.session.execute(
                update(AuthSession)
                .where(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )

    if "email_verified" in payload:
        target.email_verified = bool(payload["email_verified"])
    if "role" in payload:
        old_role = target.role
        target.role = payload["role"]
        if old_role != target.role:
            db.session.execute(
                update(AuthSession)
                .where(AuthSession.user_id == target.id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )

    db.session.commit()
    db.session.refresh(target)
    logger.info(
        "admin_user_updated",
        extra={"admin_id": admin_user.id, "target_user_id": target.id},
    )
    return target


def list_user_bookings(user_id: int, status: str | None = None) -> list[dict[str, Any]]:
    """List bookings owned by an authenticated customer."""
    stmt = select(Booking).where(Booking.user_id == user_id).order_by(Booking.created_at.desc())
    if status and status in (Booking.STATUS_CONFIRMED, Booking.STATUS_CANCELLED):
        stmt = stmt.where(Booking.status == status)
    rows = db.session.execute(stmt).scalars().all()
    return [b.to_dict() for b in rows]
