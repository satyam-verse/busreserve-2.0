"""Live GPS Tracking domain service: source management, atomic upserts, and journey sharing."""

import hashlib
import logging
import math
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from flask import current_app
from sqlalchemy import select, text

from app.extensions import db
from app.models.booking import Booking
from app.models.tracking import (
    JourneyShare,
    TripDriverAssignment,
    TripLiveLocation,
    TripLocationHistory,
)
from app.models.trip import Trip
from app.models.user import User
from app.services.notification_service import notify_journey_shared
from app.utils.errors import (
    APIError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAPIError,
)
from app.utils.metrics import metrics_registry

logger = logging.getLogger("busreserve.tracking")

# GPS Freshness thresholds (seconds)
FRESHNESS_LIVE_MAX_SEC = 30
FRESHNESS_WEAK_MAX_SEC = 60
FRESHNESS_STALE_MAX_SEC = 120

# Sanity filters
MAX_CLOCK_DRIFT_SEC = 120.0
MAX_PHYSICAL_SPEED_MPS = 45.0  # 162 km/h
MAX_GPS_ACCURACY_METERS = 100.0


def _utcnow() -> datetime:
    return datetime.now(UTC)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two GPS coordinates in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_freshness_status(last_seen_dt: datetime | None, now: datetime | None = None) -> str:
    """Determine freshness state: LIVE (0-30s), WEAK_SIGNAL (31-60s), STALE (61-120s), OFFLINE (>120s)."""
    if last_seen_dt is None:
        return "OFFLINE"
    current_time = now or _utcnow()
    if last_seen_dt.tzinfo is None:
        last_seen_dt = last_seen_dt.replace(tzinfo=UTC)
    age_seconds = (current_time - last_seen_dt).total_seconds()
    if age_seconds < 0:
        age_seconds = 0.0

    if age_seconds <= FRESHNESS_LIVE_MAX_SEC:
        return "LIVE"
    elif age_seconds <= FRESHNESS_WEAK_MAX_SEC:
        return "WEAK_SIGNAL"
    elif age_seconds <= FRESHNESS_STALE_MAX_SEC:
        return "STALE"
    else:
        return "OFFLINE"


def validate_gps_payload_sanity(
    payload: dict[str, Any],
    last_lat: float | None,
    last_lon: float | None,
    last_time: datetime | None,
    now: datetime | None = None,
) -> None:
    """Validate client timestamp drift, GPS accuracy, and physical jump plausibility."""
    current_time = now or _utcnow()
    client_ts = payload["client_timestamp"]
    if client_ts.tzinfo is None:
        client_ts = client_ts.replace(tzinfo=UTC)

    # 1. Clock drift check
    drift = abs((current_time - client_ts).total_seconds())
    if drift > MAX_CLOCK_DRIFT_SEC:
        raise ValidationAPIError(
            f"Client timestamp rejected due to excessive clock drift ({drift:.1f}s > {MAX_CLOCK_DRIFT_SEC}s).",
            details={"client_timestamp": ["Device clock is out of sync."]},
        )

    # 2. Accuracy check
    acc = payload.get("accuracy")
    if acc is not None and acc > MAX_GPS_ACCURACY_METERS:
        raise ValidationAPIError(
            f"GPS signal accuracy too degraded ({acc:.1f}m > {MAX_GPS_ACCURACY_METERS}m).",
            details={"accuracy": ["Inaccurate GPS coordinates rejected."]},
        )

    # 3. Speed / jump sanity check
    reported_speed = payload.get("speed")
    if reported_speed is not None and reported_speed > MAX_PHYSICAL_SPEED_MPS:
        raise ValidationAPIError(
            f"Reported vehicle speed exceeds physical limit ({reported_speed:.1f} m/s).",
            details={"speed": ["Unrealistic vehicle speed."]},
        )

    if last_lat is not None and last_lon is not None and last_time is not None:
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=UTC)
        time_delta = (client_ts - last_time).total_seconds()
        if time_delta > 0:
            jump_meters = haversine_distance_meters(
                last_lat, last_lon, payload["latitude"], payload["longitude"]
            )
            calculated_speed = jump_meters / time_delta
            if calculated_speed > MAX_PHYSICAL_SPEED_MPS and jump_meters > 500.0:
                raise ValidationAPIError(
                    f"Teleportation detected: distance jump of {jump_meters:.1f}m in {time_delta:.1f}s.",
                    details={"latitude": ["Impossible coordinate jump detected."]},
                )


def record_driver_gps(
    driver_user: User,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Ingest driver GPS ping with atomic PostgreSQL upsert and driver supremacy."""
    trip_id = payload["trip_id"]
    seq_num = payload["sequence_number"]
    client_ts = payload["client_timestamp"]
    if client_ts.tzinfo is None:
        client_ts = client_ts.replace(tzinfo=UTC)
    now = _utcnow()

    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip with id {trip_id} was not found.")

    # Check driver assignment
    assignment = db.session.execute(
        select(TripDriverAssignment).where(
            TripDriverAssignment.trip_id == trip_id,
            TripDriverAssignment.driver_id == driver_user.id,
            TripDriverAssignment.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if not assignment and driver_user.role != User.ROLE_ADMIN:
        active_other_driver = db.session.execute(
            select(TripDriverAssignment).where(
                TripDriverAssignment.trip_id == trip_id,
                TripDriverAssignment.driver_id != driver_user.id,
                TripDriverAssignment.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if active_other_driver:
            raise ForbiddenError(f"Driver {driver_user.id} is not assigned to trip {trip_id}.")

    # Fetch current live row if present for sequence & jump checks
    existing_row = db.session.execute(
        select(TripLiveLocation).where(TripLiveLocation.trip_id == trip_id)
    ).scalar_one_or_none()

    if existing_row:
        if (
            existing_row.driver_sequence_number is not None
            and seq_num <= existing_row.driver_sequence_number
        ):
            raise ConflictError(
                f"Non-monotonic driver sequence {seq_num} <= {existing_row.driver_sequence_number}."
            )
        validate_gps_payload_sanity(
            payload,
            last_lat=existing_row.driver_latitude,
            last_lon=existing_row.driver_longitude,
            last_time=existing_row.driver_client_timestamp or existing_row.driver_server_received_at,
            now=now,
        )
    else:
        validate_gps_payload_sanity(payload, None, None, None, now=now)

    # Atomic PostgreSQL Upsert guaranteeing driver supremacy
    upsert_sql = text("""
        INSERT INTO trip_live_locations (
            trip_id, bus_id, driver_sequence_number, operator_sequence_number,
            driver_server_received_at, driver_client_timestamp,
            driver_latitude, driver_longitude, driver_speed, driver_heading, driver_accuracy,
            latitude, longitude, speed, heading, accuracy, active_source,
            server_received_at, is_active, created_at
        ) VALUES (
            :trip_id, :bus_id, :seq, 0,
            :now, :client_ts,
            :lat, :lon, :spd, :hdg, :acc,
            :lat, :lon, :spd, :hdg, :acc, 'DRIVER',
            :now, true, :now
        )
        ON CONFLICT (trip_id) DO UPDATE SET
            driver_sequence_number = EXCLUDED.driver_sequence_number,
            driver_server_received_at = EXCLUDED.driver_server_received_at,
            driver_client_timestamp = EXCLUDED.driver_client_timestamp,
            driver_latitude = EXCLUDED.driver_latitude,
            driver_longitude = EXCLUDED.driver_longitude,
            driver_speed = EXCLUDED.driver_speed,
            driver_heading = EXCLUDED.driver_heading,
            driver_accuracy = EXCLUDED.driver_accuracy,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            speed = EXCLUDED.speed,
            heading = EXCLUDED.heading,
            accuracy = EXCLUDED.accuracy,
            active_source = 'DRIVER',
            server_received_at = EXCLUDED.server_received_at,
            is_active = true
        WHERE trip_live_locations.driver_sequence_number IS NULL
           OR trip_live_locations.driver_sequence_number < EXCLUDED.driver_sequence_number
        RETURNING id, active_source, driver_sequence_number;
    """)

    result = db.session.execute(
        upsert_sql,
        {
            "trip_id": trip_id,
            "bus_id": trip.bus_id,
            "seq": seq_num,
            "lat": payload["latitude"],
            "lon": payload["longitude"],
            "acc": payload.get("accuracy"),
            "spd": payload.get("speed"),
            "hdg": payload.get("heading"),
            "client_ts": client_ts,
            "now": now,
        },
    ).fetchone()

    if not result:
        db.session.rollback()
        raise ConflictError("Concurrent driver update conflict or stale sequence number.")

    # Record immutable audit history
    history = TripLocationHistory(
        trip_id=trip_id,
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        speed=payload.get("speed"),
        heading=payload.get("heading"),
        source=TripLiveLocation.SOURCE_DRIVER,
        recorded_at=now,
    )
    db.session.add(history)
    db.session.commit()

    metrics_registry.inc_counter(
        "busreserve_gps_updates_total", 1.0, {"source": "DRIVER", "status": "ACCEPTED"}
    )

    return {
        "status": "ACCEPTED",
        "trip_id": trip_id,
        "source": "DRIVER",
        "active_source": "DRIVER",
        "sequence_number": seq_num,
        "timestamp": client_ts.isoformat(),
        "freshness": "LIVE",
    }


def record_operator_gps(
    operator_user: User,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Ingest operator GPS ping with atomic upsert, sequence check, and driver priority protection."""
    trip_id = payload["trip_id"]
    seq_num = payload["sequence_number"]
    client_ts = payload["client_timestamp"]
    if client_ts.tzinfo is None:
        client_ts = client_ts.replace(tzinfo=UTC)
    now = _utcnow()

    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip with id {trip_id} was not found.")

    # Authorization: Operator must own the trip, or be ADMIN
    if operator_user.role != User.ROLE_ADMIN:
        if not operator_user.operator_id or operator_user.operator_id != trip.operator_id:
            raise ForbiddenError("You are not authorized to update GPS for this trip.")

    # Fetch current row for sequence checks and sanity
    existing_row = db.session.execute(
        select(TripLiveLocation).where(TripLiveLocation.trip_id == trip_id)
    ).scalar_one_or_none()

    if existing_row:
        if (
            existing_row.operator_sequence_number is not None
            and seq_num <= existing_row.operator_sequence_number
        ):
            raise ConflictError(
                f"Non-monotonic operator sequence {seq_num} <= {existing_row.operator_sequence_number}."
            )
        validate_gps_payload_sanity(
            payload,
            last_lat=existing_row.operator_latitude,
            last_lon=existing_row.operator_longitude,
            last_time=existing_row.operator_client_timestamp or existing_row.operator_server_received_at,
            now=now,
        )
    else:
        validate_gps_payload_sanity(payload, None, None, None, now=now)

    # Atomic PostgreSQL Upsert with conditional takeover:
    # If driver timestamp is fresh (within 60s), operator coordinates are recorded to operator_*
    # but active_source remains DRIVER and broadcast coordinates are NOT overwritten.
    upsert_sql = text("""
        INSERT INTO trip_live_locations (
            trip_id, bus_id, operator_user_id, driver_sequence_number, operator_sequence_number,
            operator_server_received_at, operator_client_timestamp,
            operator_latitude, operator_longitude, operator_speed, operator_heading, operator_accuracy,
            latitude, longitude, speed, heading, accuracy, active_source,
            server_received_at, is_active, created_at
        ) VALUES (
            :trip_id, :bus_id, :operator_user_id, 0, :seq,
            :now, :client_ts,
            :lat, :lon, :spd, :hdg, :acc,
            :lat, :lon, :spd, :hdg, :acc, 'OPERATOR',
            :now, true, :now
        )
        ON CONFLICT (trip_id) DO UPDATE SET
            operator_user_id = EXCLUDED.operator_user_id,
            operator_sequence_number = EXCLUDED.operator_sequence_number,
            operator_server_received_at = EXCLUDED.operator_server_received_at,
            operator_client_timestamp = EXCLUDED.operator_client_timestamp,
            operator_latitude = EXCLUDED.operator_latitude,
            operator_longitude = EXCLUDED.operator_longitude,
            operator_speed = EXCLUDED.operator_speed,
            operator_heading = EXCLUDED.operator_heading,
            operator_accuracy = EXCLUDED.operator_accuracy,
            is_active = true,
            active_source = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.active_source
                ELSE 'OPERATOR'
            END,
            latitude = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.latitude
                ELSE EXCLUDED.latitude
            END,
            longitude = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.longitude
                ELSE EXCLUDED.longitude
            END,
            speed = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.speed
                ELSE EXCLUDED.speed
            END,
            heading = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.heading
                ELSE EXCLUDED.heading
            END,
            accuracy = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.accuracy
                ELSE EXCLUDED.accuracy
            END,
            server_received_at = CASE
                WHEN trip_live_locations.driver_server_received_at IS NOT NULL
                     AND (EXCLUDED.server_received_at - trip_live_locations.driver_server_received_at) <= INTERVAL '60 seconds'
                THEN trip_live_locations.server_received_at
                ELSE EXCLUDED.server_received_at
            END
        WHERE trip_live_locations.operator_sequence_number IS NULL
           OR trip_live_locations.operator_sequence_number < EXCLUDED.operator_sequence_number
        RETURNING id, active_source, operator_sequence_number;
    """)

    result = db.session.execute(
        upsert_sql,
        {
            "trip_id": trip_id,
            "bus_id": trip.bus_id,
            "operator_user_id": operator_user.id,
            "seq": seq_num,
            "lat": payload["latitude"],
            "lon": payload["longitude"],
            "acc": payload.get("accuracy"),
            "spd": payload.get("speed"),
            "hdg": payload.get("heading"),
            "client_ts": client_ts,
            "now": now,
        },
    ).fetchone()

    if not result:
        db.session.rollback()
        raise ConflictError("Concurrent operator update conflict or stale sequence number.")

    active_source = result.active_source

    # Record history
    history = TripLocationHistory(
        trip_id=trip_id,
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        speed=payload.get("speed"),
        heading=payload.get("heading"),
        source=TripLiveLocation.SOURCE_OPERATOR,
        recorded_at=now,
    )
    db.session.add(history)
    db.session.commit()

    metrics_registry.inc_counter(
        "busreserve_gps_updates_total", 1.0, {"source": "OPERATOR", "status": "ACCEPTED"}
    )

    return {
        "status": "ACCEPTED",
        "trip_id": trip_id,
        "source": "OPERATOR",
        "active_source": active_source,
        "sequence_number": seq_num,
        "timestamp": client_ts.isoformat(),
        "is_active_broadcast": (active_source == "OPERATOR"),
    }


def get_active_trip_location(trip_id: int) -> dict[str, Any]:
    """Retrieve the authoritative live location and freshness state for a trip."""
    trip = db.session.get(Trip, trip_id)
    if not trip:
        raise NotFoundError(f"Trip with id {trip_id} was not found.")

    loc = db.session.execute(
        select(TripLiveLocation).where(TripLiveLocation.trip_id == trip_id)
    ).scalar_one_or_none()

    if not loc or not loc.is_active:
        return {
            "trip_id": trip_id,
            "status": "OFFLINE",
            "is_live": False,
            "coordinates": None,
            "active_source": None,
            "speed": None,
            "heading": None,
            "last_updated": None,
        }

    now = _utcnow()
    freshness = get_freshness_status(loc.server_received_at, now=now)

    effective_source = loc.active_source
    lat = loc.latitude
    lon = loc.longitude

    if loc.driver_server_received_at:
        driver_freshness = get_freshness_status(loc.driver_server_received_at, now=now)
        if driver_freshness in ("LIVE", "WEAK_SIGNAL") and effective_source != "DRIVER":
            effective_source = "DRIVER"
            if loc.driver_latitude is not None and loc.driver_longitude is not None:
                lat = loc.driver_latitude
                lon = loc.driver_longitude

    return {
        "trip_id": trip_id,
        "status": freshness,
        "is_live": freshness in ("LIVE", "WEAK_SIGNAL"),
        "coordinates": {
            "latitude": lat,
            "longitude": lon,
            "accuracy": loc.accuracy,
        },
        "active_source": effective_source,
        "speed": loc.speed,
        "heading": loc.heading,
        "last_updated": loc.server_received_at.isoformat() if loc.server_received_at else None,
        "driver_freshness": get_freshness_status(loc.driver_server_received_at, now=now),
        "operator_freshness": get_freshness_status(loc.operator_server_received_at, now=now),
        "driver_sequence_number": loc.driver_sequence_number,
        "operator_sequence_number": loc.operator_sequence_number,
    }


def get_public_app_base_url() -> str:
    """Validate and return the trusted public base URL for journey sharing links.

    Production requirements (Fail-closed):
    - PUBLIC_APP_URL is strictly required.
    - Must use HTTPS scheme.
    - Localhost / loopback domains are strictly forbidden.
    - ALLOWED_PUBLIC_HOSTS whitelist is strictly required.
    - Target hostname must match an entry in ALLOWED_PUBLIC_HOSTS.
    """
    env = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    is_prod = env in ("production", "prod") or (
        current_app and current_app.config.get("ENV") == "production"
    )

    app_url = current_app.config.get("PUBLIC_APP_URL") or os.getenv("PUBLIC_APP_URL")
    if not app_url:
        if is_prod:
            logger.error("public_app_url_missing_in_production")
            raise ValidationAPIError(
                "Public sharing is temporarily unavailable: trusted domain is not configured.",
                error_code="PUBLIC_DOMAIN_NOT_CONFIGURED",
            )
        return "https://localhost:8443"

    parsed = urlparse(app_url.strip())
    host = (parsed.hostname or "").lower()

    raw_hosts = current_app.config.get("ALLOWED_PUBLIC_HOSTS") or os.getenv("ALLOWED_PUBLIC_HOSTS", "")
    if isinstance(raw_hosts, str):
        allowed_hosts = [h.strip().lower() for h in raw_hosts.split(",") if h.strip()]
    elif isinstance(raw_hosts, (list, tuple, set)):
        allowed_hosts = [str(h).strip().lower() for h in raw_hosts if str(h).strip()]
    else:
        allowed_hosts = []

    if is_prod:
        if parsed.scheme != "https":
            logger.error("insecure_public_url_in_production", extra={"url": app_url})
            raise ValidationAPIError(
                "Public sharing configuration requires HTTPS in production.",
                error_code="PUBLIC_DOMAIN_INSECURE",
            )
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            logger.error("localhost_forbidden_in_production", extra={"host": host})
            raise ValidationAPIError(
                "Localhost URLs cannot be used for public journey sharing in production.",
                error_code="PUBLIC_DOMAIN_LOCALHOST_FORBIDDEN",
            )
        if not allowed_hosts:
            logger.error("allowed_public_hosts_missing_in_production")
            raise ValidationAPIError(
                "Public sharing is temporarily unavailable: allowed hosts whitelist is not configured.",
                error_code="PUBLIC_DOMAIN_NOT_CONFIGURED",
            )
        if host not in allowed_hosts:
            logger.error("untrusted_public_host_in_production", extra={"host": host})
            raise ValidationAPIError(
                f"Public sharing host '{host}' is not in approved hosts list.",
                error_code="PUBLIC_DOMAIN_NOT_ALLOWED",
            )
    else:
        # Development / Testing
        if allowed_hosts and host not in allowed_hosts and host not in ("localhost", "127.0.0.1"):
            logger.error("untrusted_public_host", extra={"host": host})
            raise ValidationAPIError(
                f"Public sharing host '{host}' is not in approved hosts list.",
                error_code="PUBLIC_DOMAIN_NOT_ALLOWED",
            )

    return app_url.rstrip("/")


def create_journey_share(
    user: User,
    booking_id: int,
    validity_hours: int = 24,
) -> dict[str, Any]:
    """Generate a secure, random 32-byte sharing token and store only its SHA-256 hash."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise NotFoundError(f"Booking with id {booking_id} was not found.")

    if user.role != User.ROLE_ADMIN and booking.user_id != user.id:
        if booking.passenger_email.lower() != user.email.lower():
            raise ForbiddenError("You can only share journeys for your own bookings.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    base_url = get_public_app_base_url()
    share_url = f"{base_url}/journey/track/{raw_token}"

    now = _utcnow()
    expires_at = now + timedelta(hours=max(1, min(168, validity_hours)))

    share_record = JourneyShare(
        booking_id=booking.id,
        user_id=user.id,
        token_hash=token_hash,
        is_active=True,
        expires_at=expires_at,
        created_at=now,
    )
    db.session.add(share_record)
    db.session.commit()
    db.session.refresh(share_record)

    notify_journey_shared(booking.id, share_url)

    metrics_registry.inc_counter("busreserve_journey_shares_created_total", 1.0)

    return {
        "share_id": share_record.id,
        "booking_id": booking.id,
        "token": raw_token,
        "share_url": share_url,
        "expires_at": expires_at.isoformat(),
        "validity_hours": validity_hours,
    }


def revoke_journey_share(user: User, raw_token_or_hash: str) -> bool:
    """Revoke an active journey share token immediately."""
    if len(raw_token_or_hash) == 64:
        token_hash = raw_token_or_hash
    else:
        token_hash = hashlib.sha256(raw_token_or_hash.encode("utf-8")).hexdigest()

    share = db.session.execute(
        select(JourneyShare).where(JourneyShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if not share:
        raise NotFoundError("Journey share token was not found.")

    if user.role != User.ROLE_ADMIN and share.user_id != user.id:
        raise ForbiddenError("You can only revoke your own journey sharing links.")

    share.is_active = False
    share.revoked_at = _utcnow()
    db.session.commit()
    return True


def get_shared_journey(raw_token: str) -> dict[str, Any]:
    """Retrieve live transit information for a shared journey with ZERO passenger PII."""
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    share = db.session.execute(
        select(JourneyShare).where(JourneyShare.token_hash == token_hash)
    ).scalar_one_or_none()

    if not share:
        raise NotFoundError("Tracking link was not found.")

    if not share.is_valid():
        raise APIError(
            "Tracking link has expired or has been revoked.",
            status_code=410,
            error_code="gone",
        )

    booking = db.session.get(Booking, share.booking_id)
    if not booking or not booking.trip:
        raise NotFoundError("Associated trip details are unavailable.")

    trip = booking.trip
    tracking_data = get_active_trip_location(trip.id)

    # Return transit data strictly without any passenger PII:
    # NO passenger_name, NO passenger_email, NO passenger_phone, NO PNR, NO seat_number, NO fare
    return {
        "is_active": True,
        "expires_at": share.expires_at.isoformat(),
        "trip": {
            "id": trip.id,
            "route_name": trip.route.name if trip.route else None,
            "source": trip.source,
            "destination": trip.destination,
            "bus_type": trip.bus_type,
            "departure_time": trip.departure_time.strftime("%H:%M") if trip.departure_time else None,
            "arrival_time": trip.arrival_time.strftime("%H:%M") if trip.arrival_time else None,
            "travel_date": trip.travel_date.isoformat(),
            "status": trip.status,
            "boarding_stop": booking.boarding_stop.stop_name if booking.boarding_stop else None,
            "drop_stop": booking.drop_stop.stop_name if booking.drop_stop else None,
        },
        "tracking": tracking_data,
    }
