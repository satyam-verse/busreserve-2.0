"""Prompt sanitization, injection guardrails, and deterministic travel NLP extraction."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

# Patterns targeting prompt-injection, secret disclosure, SQL tampering, or auth bypass.
_SECURITY_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.I),
    re.compile(
        r"(?:reveal|print|show|dump|leak|expose)\s+(?:the\s+)?(?:system\s+prompt|hidden\s+prompt|secrets?|env|environment\s+variables?)",
        re.I,
    ),
    re.compile(
        r"(?:gemini_api_key|jwt_secret_key|secret_key|password_hash|admin\s+password)", re.I
    ),
    re.compile(
        r"\b(?:drop\s+table|delete\s+from|truncate\s+table|union\s+select|select\s+\*\s+from)\b",
        re.I,
    ),
    re.compile(r"(?:bypass\s+(?:auth|rbac|permission|admin)|other\s+users?\s+bookings?)", re.I),
]

_PNR_PATTERN = re.compile(r"\b(BR[A-Z0-9]{6,12})\b", re.I)
_ISO_DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_DMY_DATE_PATTERN = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b")
_BUDGET_PATTERN = re.compile(
    r"(?:under|below|less\s+than|within|max(?:imum)?|up\s*to|budget(?:\s+of)?)\s*(?:rs\.?|inr|₹)?\s*(\d{2,5})\b"
    r"|(?:rs\.?|inr|₹)\s*(\d{2,5})\s*(?:or\s+less|max|budget)?\b",
    re.I,
)
_SEATS_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:seats?|tickets?|passengers?|people|persons?)\b", re.I
)
_DAY_MONTH_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b"
    r"|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2})\b",
    re.I,
)

_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def sanitize_user_input(raw_message: str, max_length: int = 1000) -> tuple[str, bool, str | None]:
    """Strip unsafe control characters, enforce length limit, and detect injection probes."""
    if not isinstance(raw_message, str):
        return "", False, None

    # Remove control bytes other than standard whitespace/newlines
    cleaned = "".join(ch if (ch >= " " or ch in "\n\t") else " " for ch in raw_message)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].strip()

    for pattern in _SECURITY_PATTERNS:
        if pattern.search(cleaned):
            return cleaned, True, "security_guardrail"

    return cleaned, False, None


def _build_city_terms(cities: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Return list of (lowercase_term, canonical_city_name) sorted longest-first."""
    pairs: dict[str, str] = {}
    for city in cities:
        name = str(city.get("name") or "").strip()
        if not name:
            continue
        pairs[name.lower()] = name
        for alias in city.get("aliases") or []:
            clean_alias = str(alias).strip()
            if clean_alias and clean_alias.lower() not in pairs:
                pairs[clean_alias.lower()] = name
    return sorted(pairs.items(), key=lambda item: -len(item[0]))


_STOP_CITY_WORDS = {
    "me",
    "you",
    "us",
    "my",
    "our",
    "your",
    "a",
    "an",
    "the",
    "all",
    "any",
    "some",
    "bus",
    "buses",
    "trip",
    "trips",
    "route",
    "routes",
    "schedule",
    "schedules",
    "seat",
    "seats",
    "travel",
    "go",
    "book",
    "ride",
    "visit",
    "see",
    "get",
    "choose",
    "pick",
    "select",
    "today",
    "tomorrow",
    "tmrw",
    "tonight",
    "now",
    "morning",
    "afternoon",
    "evening",
    "night",
    "overnight",
    "cheapest",
    "cheap",
    "lowest",
    "budget",
    "fastest",
    "shortest",
    "earliest",
    "under",
    "below",
    "within",
    "around",
    "near",
    "here",
    "there",
}

_EXPLICIT_FROM_TO_PATTERN = re.compile(
    r"\bfrom\s+([a-z][a-z\s]{1,28}?)\s+to\s+([a-z][a-z\s]{1,28}?)"
    r"(?=\s+(?:today|tomorrow|tmrw|tonight|on|in|for|with|under|below|within|by|before|after|"
    r"departure|bus|buses|trip|trips|\d)|[?.!,]|$)",
    re.I,
)


def _clean_candidate_city(raw_candidate: str, city_lookup: dict[str, str]) -> str | None:
    cleaned = re.sub(r"\s+", " ", raw_candidate.strip(" .,!?;:\"'"))
    if len(cleaned) < 2:
        return None
    if cleaned.lower() in city_lookup:
        return city_lookup[cleaned.lower()]
    tokens = cleaned.lower().split()
    if not tokens or any(tok in _STOP_CITY_WORDS for tok in tokens):
        return None
    return " ".join(part.capitalize() for part in cleaned.split())


def _extract_cities(
    lowered: str, city_terms: list[tuple[str, str]]
) -> tuple[str | None, str | None]:
    city_lookup = {term: canonical for term, canonical in city_terms}
    matches_with_pos: list[tuple[int, int, str]] = []
    occupied_spans: list[tuple[int, int]] = []

    for term, canonical in city_terms:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", re.I)
        for m in pattern.finditer(lowered):
            start, end = m.span()
            if any(not (end <= s or start >= e) for s, e in occupied_spans):
                continue
            occupied_spans.append((start, end))
            matches_with_pos.append((start, end, canonical))

    if not matches_with_pos:
        if pair_match := _EXPLICIT_FROM_TO_PATTERN.search(lowered):
            cand_src = _clean_candidate_city(pair_match.group(1), city_lookup)
            cand_dst = _clean_candidate_city(pair_match.group(2), city_lookup)
            if cand_src and cand_dst and cand_src.lower() != cand_dst.lower():
                return cand_src, cand_dst
        return None, None

    matches_with_pos.sort(key=lambda tup: tup[0])
    ordered_unique: list[tuple[int, int, str]] = []
    seen_cities: set[str] = set()
    for start, end, cname in matches_with_pos:
        if cname.lower() not in seen_cities:
            seen_cities.add(cname.lower())
            ordered_unique.append((start, end, cname))

    if len(ordered_unique) >= 2:
        # Check if user explicitly reversed wording: "to X from Y"
        pos0, _end0, c0 = ordered_unique[0]
        pos1, _end1, c1 = ordered_unique[1]
        prefix0 = lowered[max(0, pos0 - 10) : pos0]
        prefix1 = lowered[max(0, pos1 - 10) : pos1]
        if re.search(r"\bto\s*$", prefix0) and re.search(r"\bfrom\s*$", prefix1):
            return c1, c0
        return c0, c1

    pos_only, end_only, only_city = ordered_unique[0]
    before_text = lowered[:pos_only]
    if from_before := re.search(r"\bfrom\s+([a-z][a-z\s]{1,28}?)\s+to\s*$", before_text):
        cand_src = _clean_candidate_city(from_before.group(1), city_lookup)
        if cand_src and cand_src.lower() != only_city.lower():
            return cand_src, only_city

    after_text = lowered[end_only:]
    if to_after := re.match(
        r"^\s+to\s+([a-z][a-z\s]{1,28}?)"
        r"(?=\s+(?:today|tomorrow|tmrw|tonight|on|in|for|with|under|below|within|by|before|after|"
        r"departure|bus|buses|trip|trips|\d)|[?.!,]|$)",
        after_text,
    ):
        cand_dst = _clean_candidate_city(to_after.group(1), city_lookup)
        if cand_dst and cand_dst.lower() != only_city.lower():
            return only_city, cand_dst

    prefix = lowered[max(0, pos_only - 10) : pos_only]
    if re.search(r"\b(?:to|towards|for)\s*$", prefix):
        return None, only_city
    if re.search(r"\b(?:from|leaving|departing)\s*$", prefix):
        return only_city, None
    return only_city, None


def _extract_date(
    lowered: str,
    today_ist: date,
    max_date: date,
) -> tuple[date | None, bool]:
    parsed_date: date | None = None

    if "day after tomorrow" in lowered:
        parsed_date = today_ist + timedelta(days=2)
    elif "tomorrow" in lowered or "tmrw" in lowered:
        parsed_date = today_ist + timedelta(days=1)
    elif "today" in lowered or "tonight" in lowered:
        parsed_date = today_ist
    elif iso_match := _ISO_DATE_PATTERN.search(lowered):
        try:
            parsed_date = date.fromisoformat(iso_match.group(1))
        except ValueError:
            parsed_date = None
    elif dmy_match := _DMY_DATE_PATTERN.search(lowered):
        day_val, month_val, year_val = (int(dmy_match.group(i)) for i in (1, 2, 3))
        try:
            parsed_date = date(year_val, month_val, day_val)
        except ValueError:
            parsed_date = None
    elif dm_match := _DAY_MONTH_PATTERN.search(lowered):
        if dm_match.group(1) and dm_match.group(2):
            day_val = int(dm_match.group(1))
            month_val = _MONTH_MAP.get(dm_match.group(2).lower(), 0)
        else:
            month_val = _MONTH_MAP.get((dm_match.group(3) or "").lower(), 0)
            day_val = int(dm_match.group(4))
        if month_val:
            try:
                candidate = date(today_ist.year, month_val, day_val)
                if candidate < today_ist - timedelta(days=30):
                    candidate = date(today_ist.year + 1, month_val, day_val)
                parsed_date = candidate
            except ValueError:
                parsed_date = None

    if parsed_date is None:
        return None, False

    out_of_horizon = parsed_date < today_ist or parsed_date > max_date
    return parsed_date, out_of_horizon


def _classify_intent(lowered: str, pnr: str | None, src: str | None, dst: str | None) -> str:
    if pnr or any(
        k in lowered for k in ("pnr", "ticket status", "booking status", "check booking")
    ):
        return "pnr_lookup"
    if any(k in lowered for k in ("my booking", "my ticket", "my reservation", "trip history")):
        return "my_bookings"
    if any(k in lowered for k in ("cancel", "refund", "money back")):
        return "cancellation_refund_guidance"
    if any(
        k in lowered
        for k in ("how to book", "book a seat", "booking steps", "seat lock", "how does booking")
    ):
        return "booking_guidance"
    if any(
        k in lowered
        for k in (
            "90 day",
            "90-day",
            "horizon",
            "how far in advance",
            "advance booking",
            "timezone",
            "ist",
        )
    ):
        return "horizon_info"
    if any(
        k in lowered
        for k in (
            "recommend",
            "suggest",
            "find",
            "search",
            "show",
            "bus",
            "buses",
            "trip",
            "trips",
            "cheapest",
            "cheap",
            "lowest",
            "earliest",
            "overnight",
            "sleeper",
            "morning",
            "evening",
            "afternoon",
            "seat",
            "fare",
            "schedule",
        )
    ) or (src is not None or dst is not None):
        if "route" in lowered and not src and not dst and "recommend" not in lowered:
            return "route_info"
        return "trip_recommendation"
    if any(k in lowered for k in ("route", "cities", "city", "corridor", "operate")):
        return "route_info"
    return "general_help"


def extract_travel_preferences(
    message: str,
    cities: list[dict[str, Any]],
    today_ist: date,
    max_date: date,
    *,
    prior_context: dict[str, Any] | None = None,
    explicit_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract grounded structured search slots and intent from passenger text."""
    lowered = message.lower()
    city_terms = _build_city_terms(cities)

    src, dst = _extract_cities(lowered, city_terms)
    travel_date, out_of_horizon = _extract_date(lowered, today_ist, max_date)

    pnr_match = _PNR_PATTERN.search(message)
    pnr = pnr_match.group(1).upper() if pnr_match else None

    max_budget: float | None = None
    if budget_match := _BUDGET_PATTERN.search(lowered):
        raw_num = budget_match.group(1) or budget_match.group(2)
        if raw_num:
            max_budget = float(raw_num)

    min_seats: int | None = None
    if seats_match := _SEATS_PATTERN.search(lowered):
        count = int(seats_match.group(1))
        if 1 <= count <= 40:
            min_seats = count

    time_window: str | None = None
    if "early morning" in lowered:
        time_window = "early_morning"
    elif "morning" in lowered:
        time_window = "morning"
    elif "afternoon" in lowered:
        time_window = "afternoon"
    elif "evening" in lowered:
        time_window = "evening"
    elif any(k in lowered for k in ("overnight", "night", "late")):
        time_window = "overnight"

    bus_type_filter: str | None = None
    if "volvo" in lowered or "multi" in lowered:
        bus_type_filter = "VOLVO_MULTI_AXLE"
    elif "sleeper" in lowered:
        bus_type_filter = "SLEEPER"
    elif "non-ac" in lowered or "non ac" in lowered:
        bus_type_filter = "NON_AC_SEATER"
    elif re.search(r"\bac\b", lowered):
        bus_type_filter = "AC"

    seat_preference: str | None = None
    if "window" in lowered:
        seat_preference = "WINDOW"
    elif "aisle" in lowered:
        seat_preference = "AISLE"

    preference = "balanced"
    if any(k in lowered for k in ("cheap", "cheapest", "lowest", "budget", "affordable")):
        preference = "cheapest"
    elif any(k in lowered for k in ("earliest", "first bus", "early")):
        preference = "earliest"
    elif any(k in lowered for k in ("overnight", "night bus")):
        preference = "overnight"
    elif any(k in lowered for k in ("fastest", "shortest", "quickest", "less time")):
        preference = "shortest"
    elif any(k in lowered for k in ("most seats", "less crowded", "empty", "plenty of seats")):
        preference = "most_seats"

    intent = _classify_intent(lowered, pnr, src, dst)

    # Inherit isolated prior conversation origin/destination ONLY on follow-up trip refinement turns
    if (
        prior_context
        and intent == "trip_recommendation"
        and src is None
        and dst is None
        and any(
            k in lowered
            for k in (
                "cheaper",
                "cheap",
                "overnight",
                "morning",
                "evening",
                "earlier",
                "later",
                "tomorrow",
                "sleeper",
                "under",
                "window",
                "same route",
            )
        )
    ):
        src = prior_context.get("source")
        dst = prior_context.get("destination")
        if travel_date is None and prior_context.get("travel_date"):
            try:
                candidate = datetime.strptime(prior_context["travel_date"], "%Y-%m-%d").date()
                if today_ist <= candidate <= max_date:
                    travel_date = candidate
            except ValueError:
                pass

    overrides = explicit_overrides or {}
    if overrides.get("source"):
        src = str(overrides["source"]).strip()
    if overrides.get("destination"):
        dst = str(overrides["destination"]).strip()
    if overrides.get("travel_date"):
        val = overrides["travel_date"]
        travel_date = val if isinstance(val, date) else date.fromisoformat(str(val))
        out_of_horizon = travel_date < today_ist or travel_date > max_date
    if overrides.get("max_budget") is not None:
        max_budget = float(overrides["max_budget"])
    if overrides.get("min_seats") is not None:
        min_seats = int(overrides["min_seats"])
    if overrides.get("preference"):
        preference = str(overrides["preference"]).strip().lower()
    if overrides.get("time_window"):
        time_window = str(overrides["time_window"]).strip().lower()
    if overrides.get("bus_type"):
        bus_type_filter = str(overrides["bus_type"]).strip().upper()
    if overrides.get("seat_preference"):
        seat_preference = str(overrides["seat_preference"]).strip().upper()

    return {
        "intent": intent,
        "source": src,
        "destination": dst,
        "travel_date": travel_date.isoformat() if travel_date else None,
        "travel_date_obj": travel_date,
        "out_of_horizon": out_of_horizon,
        "time_window": time_window,
        "max_budget": max_budget,
        "min_seats": min_seats,
        "bus_type": bus_type_filter,
        "seat_preference": seat_preference,
        "preference": preference,
        "pnr": pnr,
    }
