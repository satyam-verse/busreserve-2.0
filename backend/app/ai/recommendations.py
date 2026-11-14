"""Smart PostgreSQL-grounded route and trip recommendation engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select

from app.extensions import db
from app.models import TripSeat
from app.services.booking_service import search_trips


def _parse_hour(hhmm: str) -> int:
    try:
        return int(hhmm.split(":")[0])
    except (ValueError, IndexError, AttributeError):
        return 12


def _matches_time_window(departure_hhmm: str, window: str | None) -> bool:
    if not window:
        return True
    hour = _parse_hour(departure_hhmm)
    if window == "early_morning":
        return 4 <= hour <= 8
    if window == "morning":
        return 5 <= hour <= 11
    if window == "afternoon":
        return 12 <= hour <= 16
    if window == "evening":
        return 17 <= hour <= 20
    if window == "overnight":
        return hour >= 20 or hour < 5
    return True


def _matches_bus_type(trip_bus_type: str, requested: str | None) -> bool:
    if not requested:
        return True
    req = requested.upper()
    if req == "SLEEPER":
        return trip_bus_type in {"AC_SLEEPER", "SEATER_SLEEPER"}
    if req == "AC":
        return trip_bus_type in {"AC_SEATER", "AC_SLEEPER", "SEATER_SLEEPER", "VOLVO_MULTI_AXLE"}
    return trip_bus_type == req


def _available_seat_types_by_trip(trip_ids: list[int]) -> dict[int, dict[str, int]]:
    if not trip_ids:
        return {}
    rows = db.session.execute(
        select(TripSeat.trip_id, TripSeat.seat_type, func.count(TripSeat.id))
        .where(TripSeat.trip_id.in_(trip_ids))
        .group_by(TripSeat.trip_id, TripSeat.seat_type)
    ).all()
    counts: dict[int, dict[str, int]] = {}
    for tid, stype, cnt in rows:
        counts.setdefault(int(tid), {})[str(stype)] = int(cnt)
    return counts


class RecommendationEngine:
    """Queries live PostgreSQL trips and ranks real schedules by user criteria."""

    @staticmethod
    def recommend(
        parsed_query: dict[str, Any],
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        if parsed_query.get("out_of_horizon"):
            return {"trips": [], "total_candidates": 0, "filters_relaxed": False}

        source = parsed_query.get("source")
        destination = parsed_query.get("destination")
        travel_date: date | None = parsed_query.get("travel_date_obj")
        min_seats = parsed_query.get("min_seats")
        max_budget = parsed_query.get("max_budget")
        time_window = parsed_query.get("time_window")
        bus_type = parsed_query.get("bus_type")
        seat_preference = parsed_query.get("seat_preference")
        preference = parsed_query.get("preference", "balanced")

        # Always fetch live scheduled trips from booking_service (never raw fake data)
        raw_trips = search_trips(
            source=source,
            destination=destination,
            travel_date=travel_date,
            sort_by="departure_asc",
            min_seats=min_seats,
            featured=(source is None and destination is None and travel_date is None),
        )
        # Never recommend sold-out buses
        available_trips = [t for t in raw_trips if int(t.get("available_seats", 0)) > 0]
        if not available_trips:
            return {"trips": [], "total_candidates": 0, "filters_relaxed": False}

        filtered = [
            t
            for t in available_trips
            if (max_budget is None or float(t["base_fare"]) <= float(max_budget))
            and _matches_time_window(t["departure_time"], time_window)
            and _matches_bus_type(t.get("bus_type", ""), bus_type)
        ]

        filters_relaxed = False
        if not filtered:
            # If user had a strict time/bus preference but route exists, keep max_budget strict
            budget_only = [
                t
                for t in available_trips
                if max_budget is None or float(t["base_fare"]) <= float(max_budget)
            ]
            if budget_only and (time_window or bus_type):
                filtered = budget_only
                filters_relaxed = True
            else:
                return {
                    "trips": [],
                    "total_candidates": len(available_trips),
                    "filters_relaxed": False,
                }

        seat_type_counts = _available_seat_types_by_trip([t["id"] for t in filtered])

        min_fare = min(float(t["base_fare"]) for t in filtered)
        max_fare = max(float(t["base_fare"]) for t in filtered)
        min_dur = min(int(t["duration_minutes"]) for t in filtered)
        max_dur = max(int(t["duration_minutes"]) for t in filtered)

        ranked: list[dict[str, Any]] = []
        for trip in filtered:
            enriched = dict(trip)
            fare = float(trip["base_fare"])
            dur = int(trip["duration_minutes"])
            avail = int(trip["available_seats"])
            hour = _parse_hour(trip["departure_time"])
            reasons: list[str] = []

            if fare <= min_fare + 1e-6:
                reasons.append("Lowest fare" if len(filtered) > 1 else f"Fare ₹{fare:.0f}")
            if dur <= min_dur and len(filtered) > 1:
                reasons.append(f"Fastest ({trip['duration_display']})")
            if hour >= 20 or hour < 5:
                reasons.append("Overnight schedule")
            elif 5 <= hour <= 11:
                reasons.append("Morning departure")
            if avail >= 10:
                reasons.append(f"{avail} seats open")
            else:
                reasons.append(f"Only {avail} seats left")

            trip_seat_types = seat_type_counts.get(trip["id"], {})
            if seat_preference and trip_seat_types.get(seat_preference, 0) > 0:
                reasons.append(f"Has {seat_preference.lower()} seats")

            # Compute normalized preference score (higher is better, 0..100)
            fare_norm = 1.0 if max_fare == min_fare else (max_fare - fare) / (max_fare - min_fare)
            dur_norm = 1.0 if max_dur == min_dur else (max_dur - dur) / (max_dur - min_dur)
            avail_norm = min(avail / 25.0, 1.0)
            score = (fare_norm * 45.0) + (dur_norm * 30.0) + (avail_norm * 25.0)
            if seat_preference and trip_seat_types.get(seat_preference, 0) > 0:
                score += 8.0

            enriched["reasons"] = reasons[:3]
            enriched["ai_score"] = round(min(100.0, score), 1)
            ranked.append(enriched)

        def _sort_key(item: dict[str, Any]):
            hour = _parse_hour(item["departure_time"])
            if preference == "cheapest":
                return (0, float(item["base_fare"]), item["travel_date"], item["departure_time"])
            if preference == "earliest":
                return (0, item["travel_date"], item["departure_time"], float(item["base_fare"]))
            if preference == "overnight":
                is_night = 0 if (hour >= 20 or hour < 5) else 1
                return (
                    is_night,
                    item["travel_date"],
                    item["departure_time"],
                    float(item["base_fare"]),
                )
            if preference == "shortest":
                return (
                    0,
                    int(item["duration_minutes"]),
                    float(item["base_fare"]),
                    item["travel_date"],
                )
            if preference == "most_seats":
                return (
                    0,
                    -int(item["available_seats"]),
                    float(item["base_fare"]),
                    item["travel_date"],
                )
            return (0, -float(item["ai_score"]), item["travel_date"], item["departure_time"])

        ranked.sort(key=_sort_key)
        return {
            "trips": ranked[:limit],
            "total_candidates": len(filtered),
            "filters_relaxed": filters_relaxed,
        }
