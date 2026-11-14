"""Transactional booking, seat inventory, dynamic city, and trip search domain services."""

import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, lazyload

from app.extensions import db
from app.models import Booking, City, Route, RouteStop, Trip, TripSeat
from app.services.schedule_service import extract_city_name, get_booking_horizon_bounds
from app.utils.errors import ConflictError, NotFoundError, ValidationAPIError
from app.utils.metrics import metrics_registry

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


def _resolve_city_terms(raw_city: str) -> list[str]:
    """Resolve user-entered city text to canonical city names and aliases from PostgreSQL."""
    term = raw_city.strip()
    if not term:
        return []

    term_lower = term.lower()
    terms: list[str] = [term]
    seen = {term_lower}

    matched_cities = (
        db.session.execute(
            select(City).where(
                City.is_active.is_(True),
                (City.name.ilike(term) | City.aliases.ilike(f"%{term}%")),
            )
        )
        .scalars()
        .all()
    )
    for city in matched_cities:
        aliases_lower = {a.lower() for a in city.alias_list()}
        if city.name.lower() == term_lower or term_lower in aliases_lower:
            for candidate in [city.name, *city.alias_list()]:
                cand_lower = candidate.lower()
                if cand_lower not in seen:
                    seen.add(cand_lower)
                    terms.append(candidate)

    return terms


def _text_matches_terms(text_val: str | None, terms: list[str]) -> bool:
    if not text_val:
        return False
    lowered = text_val.lower()
    return any(t.lower() in lowered for t in terms)


def list_cities(query: str | None = None, limit: int = 15) -> list[dict[str, Any]]:
    """List searchable Indian cities dynamically from cities, routes, and route_stops."""
    catalog: dict[str, dict[str, Any]] = {}

    db_cities = (
        db.session.execute(select(City).where(City.is_active.is_(True)).order_by(City.name))
        .scalars()
        .all()
    )
    for city in db_cities:
        key = city.name.strip().lower()
        catalog[key] = {
            "id": city.id,
            "name": city.name,
            "state": city.state,
            "aliases": city.alias_list(),
            "has_routes": False,
        }

    # Include cities discovered directly from routes and route stops (e.g., admin-created routes)
    routes = db.session.execute(select(Route)).scalars().all()
    active_city_names: set[str] = set()
    for route in routes:
        for endpoint in (route.source, route.destination):
            clean = endpoint.strip()
            if clean:
                active_city_names.add(clean)
        for stop in route.stops:
            stop_city = (stop.city_name or extract_city_name(stop.stop_name)).strip()
            if stop_city:
                active_city_names.add(stop_city)

    for city_name in active_city_names:
        key = city_name.lower()
        if key in catalog:
            catalog[key]["has_routes"] = True
        else:
            catalog[key] = {
                "id": None,
                "name": city_name,
                "state": None,
                "aliases": [],
                "has_routes": True,
            }

    entries = list(catalog.values())

    if query and query.strip():
        q = query.strip().lower()
        scored: list[tuple[int, int, str, dict[str, Any]]] = []
        for item in entries:
            name_low = item["name"].lower()
            state_low = (item["state"] or "").lower()
            aliases = item["aliases"]

            rank: int | None = None
            matched_alias: str | None = None

            if name_low == q:
                rank = 0
            elif name_low.startswith(q):
                rank = 1
            else:
                alias_prefix = next((a for a in aliases if a.lower().startswith(q)), None)
                if alias_prefix:
                    rank = 2
                    matched_alias = alias_prefix
                elif q in name_low:
                    rank = 3
                else:
                    alias_sub = next((a for a in aliases if q in a.lower()), None)
                    if alias_sub:
                        rank = 4
                        matched_alias = alias_sub
                    elif state_low and q in state_low:
                        rank = 5

            if rank is not None:
                enriched = dict(item)
                if matched_alias:
                    enriched["matched_alias"] = matched_alias
                scored.append((rank, 0 if item["has_routes"] else 1, name_low, enriched))

        scored.sort(key=lambda tup: (tup[0], tup[1], tup[2]))
        return [tup[3] for tup in scored[:limit]]

    entries.sort(key=lambda item: (0 if item["has_routes"] else 1, item["name"].lower()))
    return entries[:limit]


def list_routes() -> list[dict[str, Any]]:
    """Return all configured bus routes with ordered intermediate stops."""
    routes = db.session.execute(select(Route).order_by(Route.id)).scalars().all()
    return [route.to_dict(include_stops=True) for route in routes]


def _match_route_stops(
    route: Route,
    source_terms: list[str],
    dest_terms: list[str],
) -> tuple[bool, int | None, int | None]:
    """Check whether a route serves a requested source->destination pair via endpoints or stops."""
    stops = sorted(route.stops, key=lambda s: s.stop_order)

    if not source_terms and not dest_terms:
        b_id = stops[0].id if len(stops) >= 2 else None
        d_id = stops[-1].id if len(stops) >= 2 else None
        return True, b_id, d_id

    if source_terms and dest_terms:
        # 1. Direct route endpoint match
        if _text_matches_terms(route.source, source_terms) and _text_matches_terms(
            route.destination, dest_terms
        ):
            b_id = stops[0].id if len(stops) >= 2 else None
            d_id = stops[-1].id if len(stops) >= 2 else None
            return True, b_id, d_id

        # 2. Intermediate stop-to-stop match (boarding stop precedes drop stop)
        for idx, s_from in enumerate(stops):
            from_city = s_from.city_name or extract_city_name(s_from.stop_name)
            if _text_matches_terms(from_city, source_terms) or _text_matches_terms(
                s_from.stop_name, source_terms
            ):
                for s_to in stops[idx + 1 :]:
                    to_city = s_to.city_name or extract_city_name(s_to.stop_name)
                    if _text_matches_terms(to_city, dest_terms) or _text_matches_terms(
                        s_to.stop_name, dest_terms
                    ):
                        return True, s_from.id, s_to.id
        return False, None, None

    if source_terms:
        if _text_matches_terms(route.source, source_terms):
            b_id = stops[0].id if len(stops) >= 2 else None
            d_id = stops[-1].id if len(stops) >= 2 else None
            return True, b_id, d_id
        for s_from in stops[:-1]:
            from_city = s_from.city_name or extract_city_name(s_from.stop_name)
            if _text_matches_terms(from_city, source_terms) or _text_matches_terms(
                s_from.stop_name, source_terms
            ):
                return True, s_from.id, stops[-1].id
        return False, None, None

    # Only dest_terms provided
    if _text_matches_terms(route.destination, dest_terms):
        b_id = stops[0].id if len(stops) >= 2 else None
        d_id = stops[-1].id if len(stops) >= 2 else None
        return True, b_id, d_id
    for s_to in stops[1:]:
        to_city = s_to.city_name or extract_city_name(s_to.stop_name)
        if _text_matches_terms(to_city, dest_terms) or _text_matches_terms(
            s_to.stop_name, dest_terms
        ):
            return True, stops[0].id, s_to.id
    return False, None, None


def search_trips(
    source: str | None = None,
    destination: str | None = None,
    travel_date=None,
    sort_by: str = "departure_asc",
    min_seats: int | None = None,
    featured: bool = False,
) -> list[dict[str, Any]]:
    """Search scheduled bus trips across DB routes/stops within the configurable horizon."""
    min_date, max_date, horizon_days = get_booking_horizon_bounds()

    if travel_date is not None:
        if travel_date < min_date:
            raise ValidationAPIError(
                "Travel date cannot be in the past.",
                details={
                    "travel_date": [
                        f"Select a travel date between {min_date.isoformat()} "
                        f"and {max_date.isoformat()}."
                    ]
                },
            )
        if travel_date > max_date:
            raise ValidationAPIError(
                f"Travel date exceeds the {horizon_days}-day booking window.",
                details={
                    "travel_date": [
                        f"Bookings are available up to {max_date.isoformat()} "
                        f"({horizon_days}-day horizon)."
                    ]
                },
            )

    source_terms = _resolve_city_terms(source) if source else []
    dest_terms = _resolve_city_terms(destination) if destination else []

    route_matches: dict[int, tuple[int | None, int | None]] = {}
    if source_terms or dest_terms:
        all_routes = db.session.execute(select(Route)).scalars().all()
        for route in all_routes:
            matched, b_id, d_id = _match_route_stops(route, source_terms, dest_terms)
            if matched:
                route_matches[route.id] = (b_id, d_id)
        if not route_matches:
            return []

    stmt = (
        select(Trip)
        .options(joinedload(Trip.route))
        .where(Trip.status == Trip.STATUS_SCHEDULED)
        .order_by(Trip.travel_date.asc(), Trip.departure_time.asc())
    )

    if route_matches:
        stmt = stmt.where(Trip.route_id.in_(list(route_matches.keys())))

    if travel_date is not None:
        stmt = stmt.where(Trip.travel_date == travel_date)
    else:
        stmt = stmt.where(Trip.travel_date >= min_date, Trip.travel_date <= max_date)

    # Bound unfiltered catalog browsing to avoid loading thousands of 90-day rows at once
    if not route_matches and travel_date is None:
        stmt = stmt.limit(24 if featured else 60)

    trips = db.session.execute(stmt).unique().scalars().all()
    if not trips:
        return []

    trip_ids = [t.id for t in trips]

    seat_totals = dict(
        db.session.execute(
            select(TripSeat.trip_id, func.count(TripSeat.id))
            .where(TripSeat.trip_id.in_(trip_ids))
            .group_by(TripSeat.trip_id)
        ).all()
    )
    booked_totals = dict(
        db.session.execute(
            select(Booking.trip_id, func.count(Booking.id))
            .where(
                Booking.trip_id.in_(trip_ids),
                Booking.status == Booking.STATUS_CONFIRMED,
            )
            .group_by(Booking.trip_id)
        ).all()
    )

    results = []
    for trip in trips:
        total_seats = int(seat_totals.get(trip.id, 0))
        booked_seats = int(booked_totals.get(trip.id, 0))
        avail = max(total_seats - booked_seats, 0)
        if min_seats is not None and avail < min_seats:
            continue
        item = trip.to_dict(available_seats=avail, total_seats=total_seats)
        item["stops"] = [stop.to_dict() for stop in trip.route.stops]
        if trip.route_id in route_matches:
            b_id, d_id = route_matches[trip.route_id]
            if b_id is not None:
                item["matched_boarding_stop_id"] = b_id
            if d_id is not None:
                item["matched_drop_stop_id"] = d_id
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


def get_trip_seats(
    trip_id: int,
    tier: str | None = None,
    position: str | None = None,
    max_fare: float | None = None,
    available_only: bool = False,
) -> dict[str, Any]:
    """Return a trip's details, ordered stops, and per-seat availability with optional filtering."""
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

    base_fare = float(trip.base_fare)
    all_seat_payloads = [
        seat.to_dict(is_available=(seat.id not in occupied_seat_ids), fare=base_fare) for seat in seats
    ]
    available_count = sum(1 for s in all_seat_payloads if s["is_available"])

    filtered_seats = all_seat_payloads
    if tier:
        clean_tier = tier.strip().upper()
        filtered_seats = [s for s in filtered_seats if s.get("seat_tier") == clean_tier]
    if position:
        clean_pos = position.strip().upper()
        filtered_seats = [s for s in filtered_seats if s.get("position_type") == clean_pos]
    if max_fare is not None:
        filtered_seats = [s for s in filtered_seats if (s.get("fare") or base_fare) <= max_fare]
    if available_only:
        filtered_seats = [s for s in filtered_seats if s.get("is_available")]

    return {
        "trip": trip.to_dict(available_seats=available_count, total_seats=len(all_seat_payloads)),
        "stops": [stop.to_dict() for stop in trip.route.stops],
        "seats": filtered_seats,
        "total_seats_count": len(all_seat_payloads),
        "available_seats_count": available_count,
        "filtered_seats_count": len(filtered_seats),
    }


def find_cheapest_seats(trip_id: int) -> dict[str, Any]:
    """Find and group the cheapest available seats by tier for instant passenger discovery."""
    seat_data = get_trip_seats(trip_id, available_only=True)
    available_seats = seat_data.get("seats", [])

    grouped_by_tier: dict[str, list[dict[str, Any]]] = {
        "STANDARD": [],
        "PREMIUM": [],
        "SLEEPER": [],
    }
    for seat in available_seats:
        tier = seat.get("seat_tier", "STANDARD")
        if tier in grouped_by_tier:
            grouped_by_tier[tier].append(seat)
        else:
            grouped_by_tier[tier] = [seat]

    cheapest_per_tier: dict[str, Any] = {}
    for tier, seat_list in grouped_by_tier.items():
        if seat_list:
            seat_list.sort(key=lambda s: (s.get("fare", 999999), s.get("seat_number", "")))
            cheapest_per_tier[tier] = {
                "lowest_fare": seat_list[0].get("fare"),
                "available_count": len(seat_list),
                "best_seat": seat_list[0],
                "seats": seat_list[:5],
            }
        else:
            cheapest_per_tier[tier] = {
                "lowest_fare": None,
                "available_count": 0,
                "best_seat": None,
                "seats": [],
            }

    overall_cheapest = None
    if available_seats:
        sorted_all = sorted(available_seats, key=lambda s: (s.get("fare", 999999), s.get("seat_number", "")))
        overall_cheapest = sorted_all[0]

    return {
        "trip": seat_data.get("trip"),
        "overall_cheapest_seat": overall_cheapest,
        "tiers": cheapest_per_tier,
    }



def _extract_pg_constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def create_booking(payload: dict[str, Any], user_id: int | None = None) -> Booking:
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

    min_date, max_date, horizon_days = get_booking_horizon_bounds()

    try:
        trip = db.session.execute(select(Trip).where(Trip.id == trip_id)).scalar_one_or_none()
        if trip is None:
            raise NotFoundError(f"Trip with id {trip_id} was not found.")

        if trip.status != Trip.STATUS_SCHEDULED:
            raise ConflictError(f"Trip {trip_id} is {trip.status} and cannot accept bookings.")

        if trip.travel_date < min_date:
            raise ValidationAPIError(
                "Cannot create a booking for a past travel date.",
                details={"travel_date": [f"Trip travel date {trip.travel_date} is in the past."]},
            )

        if trip.travel_date > max_date:
            raise ValidationAPIError(
                f"Bookings are only permitted within the {horizon_days}-day booking window.",
                details={
                    "travel_date": [
                        f"Trip travel date {trip.travel_date.isoformat()} exceeds "
                        f"{max_date.isoformat()}."
                    ]
                },
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

        effective_fare = seat.seat_fare if seat.seat_fare is not None else trip.base_fare
        booking = None
        for _ in range(5):
            candidate_pnr = generate_pnr()
            booking = Booking(
                pnr=candidate_pnr,
                trip_id=trip.id,
                user_id=user_id,
                seat_id=seat.id,
                passenger_name=payload["passenger_name"],
                passenger_email=payload["passenger_email"],
                passenger_phone=payload["passenger_phone"],
                boarding_stop_id=boarding_stop.id,
                drop_stop_id=drop_stop.id,
                total_fare=effective_fare,
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
        metrics_registry.inc_counter(
            "busreserve_bookings_created_total", 1.0, {"status": "CONFIRMED"}
        )
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


def cancel_booking(
    pnr: str,
    reason: str | None = None,
    mark_refund_processed: bool = False,
) -> Booking:
    """Cancel an existing confirmed booking, record demo refund state, and free the seat."""
    normalized_pnr = pnr.strip().upper()
    now = datetime.now(UTC)
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
        booking.cancelled_at = now
        booking.refund_amount = booking.total_fare
        if reason:
            booking.cancellation_reason = reason.strip()[:255]
        if mark_refund_processed:
            booking.refund_status = Booking.REFUND_PROCESSED
            booking.refunded_at = now
        else:
            booking.refund_status = Booking.REFUND_PENDING
        db.session.commit()
        booking = get_booking_by_pnr(normalized_pnr)
        metrics_registry.inc_counter(
            "busreserve_bookings_created_total", 1.0, {"status": "CANCELLED"}
        )
        logger.info(
            "booking_cancelled",
            extra={
                "pnr": booking.pnr,
                "trip_id": booking.trip_id,
                "seat_id": booking.seat_id,
                "refund_status": booking.refund_status,
            },
        )
        return booking
    except Exception:
        db.session.rollback()
        raise
