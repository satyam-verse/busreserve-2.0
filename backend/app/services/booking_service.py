"""Transactional booking, seat inventory, and trip search domain services."""

import logging
import secrets
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, lazyload

from app.extensions import db
from app.models import Booking, Route, RouteStop, Trip, TripSeat
from app.utils.errors import ConflictError, NotFoundError, ValidationAPIError

logger = logging.getLogger("busreserve.booking_service")

PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_pnr() -> str:
    """Generate a readable, collision-resistant PNR reference."""
    suffix = "".join(secrets.choice(PNR_ALPHABET) for _ in range(8))
    return f"BR{suffix}"


def _seat_sort_key(seat: TripSeat) -> tuple[int, str]:
    num_part = "".join(ch for ch in seat.seat_number if ch.isdigit())
    alpha_part = "".join(ch for ch in seat.seat_number if not ch.isdigit())
    return (int(num_part) if num_part else 999, alpha_part)


def list_routes() -> list[dict[str, Any]]:
    """Return all configured bus routes with ordered intermediate stops."""
    routes = db.session.execute(select(Route).order_by(Route.id)).scalars().all()
    return [route.to_dict(include_stops=True) for route in routes]


def search_trips(
    source: str | None = None,
    destination: str | None = None,
    travel_date: date | None = None,
    sort_by: str = "departure_asc",
    min_seats: int | None = None,
    featured: bool = False,
) -> list[dict[str, Any]]:
    """Search scheduled bus trips with live available seat counts."""
    total_seats_sq = (
        select(TripSeat.trip_id, func.count(TripSeat.id).label("total_seats"))
        .group_by(TripSeat.trip_id)
        .subquery()
    )
    booked_seats_sq = (
        select(Booking.trip_id, func.count(Booking.id).label("booked_seats"))
        .where(Booking.status == Booking.STATUS_CONFIRMED)
        .group_by(Booking.trip_id)
        .subquery()
    )

    stmt = (
        select(
            Trip,
            func.coalesce(total_seats_sq.c.total_seats, 0).label("total_seats"),
            (
                func.coalesce(total_seats_sq.c.total_seats, 0)
                - func.coalesce(booked_seats_sq.c.booked_seats, 0)
            ).label("available_seats"),
        )
        .join(Route, Trip.route_id == Route.id)
        .outerjoin(total_seats_sq, Trip.id == total_seats_sq.c.trip_id)
        .outerjoin(booked_seats_sq, Trip.id == booked_seats_sq.c.trip_id)
        .options(joinedload(Trip.route))
        .where(Trip.status == Trip.STATUS_SCHEDULED)
    )

    if source:
        stmt = stmt.where(Route.source.ilike(f"%{source.strip()}%"))
    if destination:
        stmt = stmt.where(Route.destination.ilike(f"%{destination.strip()}%"))
    if travel_date is not None:
        stmt = stmt.where(Trip.travel_date == travel_date)
    else:
        stmt = stmt.where(Trip.travel_date >= date.today())

    rows = db.session.execute(stmt).unique().all()

    results = []
    for trip, total_seats, available_seats in rows:
        avail = max(int(available_seats), 0)
        if min_seats is not None and avail < min_seats:
            continue
        item = trip.to_dict(available_seats=avail, total_seats=int(total_seats))
        item["stops"] = [stop.to_dict() for stop in trip.route.stops]
        results.append(item)

    sort_key_map = {
        "departure_asc": lambda r: (r["travel_date"], r["departure_time"], r["base_fare"]),
        "fare_asc": lambda r: (r["base_fare"], r["travel_date"], r["departure_time"]),
        "fare_desc": lambda r: (-r["base_fare"], r["travel_date"], r["departure_time"]),
        "seats_desc": lambda r: (-r["available_seats"], r["travel_date"], r["departure_time"]),
    }
    results.sort(key=sort_key_map.get(sort_by, sort_key_map["departure_asc"]))

    if featured:
        return results[:6]
    return results


def get_trip_seats(trip_id: int) -> dict[str, Any]:
    """Return a trip's details, ordered stops, and per-seat availability."""
    trip = db.session.execute(
        select(Trip).options(joinedload(Trip.route)).where(Trip.id == trip_id)
    ).scalar_one_or_none()
    if trip is None:
        raise NotFoundError(f"Trip with id {trip_id} was not found.")

    seats = db.session.execute(select(TripSeat).where(TripSeat.trip_id == trip_id)).scalars().all()
    seats.sort(key=_seat_sort_key)

    occupied_seat_ids = set(
        db.session.execute(
            select(Booking.seat_id).where(
                Booking.trip_id == trip_id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        )
        .scalars()
        .all()
    )

    fare = float(trip.base_fare)
    seat_payloads = [
        seat.to_dict(is_available=(seat.id not in occupied_seat_ids), fare=fare) for seat in seats
    ]
    available_count = sum(1 for s in seat_payloads if s["is_available"])

    return {
        "trip": trip.to_dict(available_seats=available_count, total_seats=len(seat_payloads)),
        "stops": [stop.to_dict() for stop in trip.route.stops],
        "seats": seat_payloads,
    }


def _extract_pg_constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def create_booking(payload: dict[str, Any]) -> Booking:
    """Atomically reserve a seat for a trip using PostgreSQL row locking and partial unique index.

    Guarantees that two concurrent transactions can never both confirm the same
    (trip_id, seat_id). Any validation failure or database conflict rolls back cleanly.
    """
    trip_id = payload["trip_id"]
    boarding_stop_id = payload["boarding_stop_id"]
    drop_stop_id = payload["drop_stop_id"]
    requested_date = payload.get("travel_date")
    seat_number = payload.get("seat_number")
    seat_id = payload.get("seat_id")

    try:
        trip = db.session.execute(select(Trip).where(Trip.id == trip_id)).scalar_one_or_none()
        if trip is None:
            raise NotFoundError(f"Trip with id {trip_id} was not found.")

        if trip.status != Trip.STATUS_SCHEDULED:
            raise ConflictError(f"Trip {trip_id} is {trip.status} and cannot accept bookings.")

        if trip.travel_date < date.today():
            raise ValidationAPIError(
                "Cannot create a booking for a past travel date.",
                details={"travel_date": [f"Trip travel date {trip.travel_date} is in the past."]},
            )

        if requested_date is not None and requested_date != trip.travel_date:
            raise ValidationAPIError(
                "Provided travel_date does not match the scheduled trip date.",
                details={
                    "travel_date": [
                        f"Expected {trip.travel_date.isoformat()}, received "
                        f"{requested_date.isoformat()}."
                    ]
                },
            )

        boarding_stop = db.session.get(RouteStop, boarding_stop_id)
        drop_stop = db.session.get(RouteStop, drop_stop_id)
        if boarding_stop is None or boarding_stop.route_id != trip.route_id:
            raise ValidationAPIError(
                "Invalid boarding stop for this trip's route.",
                details={"boarding_stop_id": ["Boarding stop does not belong to this route."]},
            )
        if drop_stop is None or drop_stop.route_id != trip.route_id:
            raise ValidationAPIError(
                "Invalid drop stop for this trip's route.",
                details={"drop_stop_id": ["Drop stop does not belong to this route."]},
            )
        if boarding_stop.stop_order >= drop_stop.stop_order:
            raise ValidationAPIError(
                "Boarding stop must precede drop stop along the route.",
                details={
                    "drop_stop_id": [
                        f"Drop stop '{drop_stop.stop_name}' (order {drop_stop.stop_order}) must "
                        f"come after boarding stop '{boarding_stop.stop_name}' "
                        f"(order {boarding_stop.stop_order})."
                    ]
                },
            )

        # Lock the specific TripSeat row (FOR UPDATE) so concurrent bookings for the same
        # seat serialize cleanly while bookings for different seats proceed in parallel.
        seat_stmt = select(TripSeat).where(TripSeat.trip_id == trip.id)
        if seat_id is not None:
            seat_stmt = seat_stmt.where(TripSeat.id == seat_id)
        if seat_number is not None:
            seat_stmt = seat_stmt.where(TripSeat.seat_number == seat_number)

        seat = db.session.execute(seat_stmt.with_for_update(of=TripSeat)).scalar_one_or_none()
        if seat is None:
            raise NotFoundError(
                f"Requested seat was not found on trip {trip_id}.",
                details={"seat": ["Invalid seat_number or seat_id for this trip."]},
            )

        existing_confirmed = db.session.execute(
            select(Booking.id).where(
                Booking.trip_id == trip.id,
                Booking.seat_id == seat.id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        ).scalar_one_or_none()
        if existing_confirmed is not None:
            raise ConflictError(
                f"Seat {seat.seat_number} on trip {trip.id} is already reserved.",
                details={"seat_number": [f"Seat {seat.seat_number} is no longer available."]},
            )

        booking = None
        for _ in range(5):
            candidate_pnr = generate_pnr()
            booking = Booking(
                pnr=candidate_pnr,
                trip_id=trip.id,
                seat_id=seat.id,
                passenger_name=payload["passenger_name"],
                passenger_email=payload["passenger_email"],
                passenger_phone=payload["passenger_phone"],
                boarding_stop_id=boarding_stop.id,
                drop_stop_id=drop_stop.id,
                total_fare=trip.base_fare,
                status=Booking.STATUS_CONFIRMED,
            )
            try:
                with db.session.begin_nested():
                    db.session.add(booking)
                    db.session.flush()
                break
            except IntegrityError as exc:
                constraint = _extract_pg_constraint_name(exc)
                if constraint == "bookings_pnr_key":
                    logger.warning("pnr_collision_retrying", extra={"pnr": candidate_pnr})
                    continue
                raise

        db.session.commit()
        db.session.refresh(booking)
        logger.info(
            "booking_confirmed",
            extra={
                "pnr": booking.pnr,
                "trip_id": trip.id,
                "seat_number": seat.seat_number,
            },
        )
        return booking

    except IntegrityError as exc:
        db.session.rollback()
        constraint = _extract_pg_constraint_name(exc)
        logger.warning(
            "booking_integrity_conflict",
            extra={"trip_id": trip_id, "constraint": constraint},
        )
        raise ConflictError(
            "Seat could not be reserved because it was just booked by another passenger."
        ) from exc
    except Exception:
        db.session.rollback()
        raise


def get_booking_by_pnr(pnr: str) -> Booking:
    """Retrieve a booking ticket by its PNR code."""
    normalized_pnr = pnr.strip().upper()
    booking = db.session.execute(
        select(Booking).where(Booking.pnr == normalized_pnr)
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundError(f"Booking with PNR '{normalized_pnr}' was not found.")
    return booking


def cancel_booking(pnr: str) -> Booking:
    """Cancel an existing confirmed booking and immediately free the seat."""
    normalized_pnr = pnr.strip().upper()
    try:
        booking = db.session.execute(
            select(Booking)
            .options(lazyload("*"))
            .where(Booking.pnr == normalized_pnr)
            .with_for_update(of=Booking)
        ).scalar_one_or_none()
        if booking is None:
            raise NotFoundError(f"Booking with PNR '{normalized_pnr}' was not found.")

        if booking.status == Booking.STATUS_CANCELLED:
            raise ConflictError(f"Booking '{normalized_pnr}' is already cancelled.")

        booking.status = Booking.STATUS_CANCELLED
        db.session.commit()
        booking = get_booking_by_pnr(normalized_pnr)
        logger.info(
            "booking_cancelled",
            extra={
                "pnr": booking.pnr,
                "trip_id": booking.trip_id,
                "seat_id": booking.seat_id,
            },
        )
        return booking
    except Exception:
        db.session.rollback()
        raise


def _mask_name(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "Guest"
    first = parts[0]
    masked_first = f"{first[0]}{'*' * max(len(first) - 1, 2)}"
    if len(parts) == 1:
        return masked_first
    return f"{masked_first} {parts[-1][0]}."


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    prefix = local[0] if local else "*"
    return f"{prefix}***@{domain}"


def get_admin_overview() -> dict[str, Any]:
    """Return aggregated, PII-masked operational stats for the local demo admin view."""
    total_trips = db.session.execute(select(func.count(Trip.id))).scalar_one()
    total_bookings = db.session.execute(select(func.count(Booking.id))).scalar_one()
    confirmed_bookings = db.session.execute(
        select(func.count(Booking.id)).where(Booking.status == Booking.STATUS_CONFIRMED)
    ).scalar_one()
    cancelled_bookings = db.session.execute(
        select(func.count(Booking.id)).where(Booking.status == Booking.STATUS_CANCELLED)
    ).scalar_one()
    total_seats = db.session.execute(select(func.count(TripSeat.id))).scalar_one()

    occupancy_rate = round((confirmed_bookings / total_seats) * 100, 1) if total_seats else 0.0

    # Per-trip occupancy breakdown
    trip_rows = search_trips()
    trip_occupancy = [
        {
            "trip_id": t["id"],
            "route_name": t["route_name"],
            "operator_name": t["operator_name"],
            "travel_date": t["travel_date"],
            "departure_time": t["departure_time"],
            "total_seats": t["total_seats"],
            "occupied_seats": t["total_seats"] - t["available_seats"],
            "available_seats": t["available_seats"],
            "occupancy_rate": round(
                ((t["total_seats"] - t["available_seats"]) / t["total_seats"]) * 100, 1
            )
            if t["total_seats"]
            else 0.0,
        }
        for t in trip_rows
    ]

    recent = (
        db.session.execute(select(Booking).order_by(Booking.created_at.desc()).limit(12))
        .scalars()
        .all()
    )
    recent_records = [
        {
            "pnr": b.pnr,
            "trip_id": b.trip_id,
            "route_name": b.trip.route.name if b.trip and b.trip.route else None,
            "travel_date": b.trip.travel_date.isoformat() if b.trip else None,
            "seat_number": b.seat.seat_number if b.seat else None,
            "passenger_display": _mask_name(b.passenger_name),
            "passenger_email_masked": _mask_email(b.passenger_email),
            "total_fare": float(b.total_fare),
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in recent
    ]

    return {
        "demo_only": True,
        "notice": "Demo-only local operational view; passenger PII is masked.",
        "summary": {
            "total_trips": int(total_trips),
            "total_bookings": int(total_bookings),
            "confirmed_bookings": int(confirmed_bookings),
            "cancelled_bookings": int(cancelled_bookings),
            "total_seats": int(total_seats),
            "occupied_seats": int(confirmed_bookings),
            "available_seats": max(int(total_seats) - int(confirmed_bookings), 0),
            "occupancy_rate": occupancy_rate,
        },
        "trip_occupancy": trip_occupancy,
        "recent_bookings": recent_records,
    }
