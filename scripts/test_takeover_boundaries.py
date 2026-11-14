"""Boundary verification for 60-second Operator Takeover Threshold.

Tests exact boundaries:
- 30 seconds (LIVE upper bound): Driver supremacy maintained, operator takeover blocked.
- 31 seconds (WEAK_SIGNAL lower bound): Driver supremacy maintained, operator takeover blocked.
- 60 seconds (WEAK_SIGNAL upper bound): Driver supremacy maintained, operator takeover blocked.
- 61 seconds (STALE lower bound): Driver stale, operator takeover ACTIVATED.
- Instant driver recovery: Fresh driver update (0s) immediately regains priority.
"""

from datetime import UTC, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.tracking import TripLiveLocation
from app.models.user import User
from app.models.trip import Trip
from app.services.tracking_service import (
    get_freshness_status,
    record_operator_gps,
    record_driver_gps,
    get_active_trip_location,
)

app = create_app()

with app.app_context():
    print("=" * 75)
    print("BOUNDARY TEST 1: Python Freshness State Machine Boundaries")
    print("=" * 75)
    now = datetime.now(UTC)

    test_intervals = [
        (0, "LIVE"),
        (15, "LIVE"),
        (30, "LIVE"),
        (31, "WEAK_SIGNAL"),
        (45, "WEAK_SIGNAL"),
        (60, "WEAK_SIGNAL"),
        (61, "STALE"),
        (90, "STALE"),
        (120, "STALE"),
        (121, "OFFLINE"),
        (300, "OFFLINE"),
    ]

    for sec, expected in test_intervals:
        dt = now - timedelta(seconds=sec)
        actual = get_freshness_status(dt, now=now)
        match = "[PASS]" if actual == expected else "[FAIL]"
        print(f"  {match} Age: {sec:>3}s | Timestamp: {dt.strftime('%H:%M:%S')} | Expected: {expected:<11} | Actual: {actual}")
        assert actual == expected, f"Boundary mismatch at {sec}s: expected {expected}, got {actual}"

    print("\n" + "=" * 75)
    print("BOUNDARY TEST 2: PostgreSQL Atomic Takeover Upsert at 30s, 31s, 60s, 61s")
    print("=" * 75)

    admin = User.query.filter_by(role=User.ROLE_ADMIN).first()
    trip_id = 1
    trip = db.session.get(Trip, trip_id)

    # Helper to set simulated driver state
    def set_driver_simulated_age(age_sec: int, seq: int):
        sim_time = datetime.now(UTC) - timedelta(seconds=age_sec)
        loc = TripLiveLocation.query.filter_by(trip_id=trip_id).first()
        if not loc:
            loc = TripLiveLocation(
                trip_id=trip_id,
                bus_id=trip.bus_id,
                driver_user_id=admin.id,
                is_active=True,
            )
            db.session.add(loc)
        loc.driver_server_received_at = sim_time
        loc.driver_client_timestamp = sim_time
        loc.driver_latitude = 25.6000
        loc.driver_longitude = 85.1400
        loc.driver_sequence_number = seq
        loc.latitude = 25.6000
        loc.longitude = 85.1400
        loc.active_source = "DRIVER"
        loc.server_received_at = sim_time
        # Reset operator coordinates and sequence to close proximity to prevent teleportation flag
        loc.operator_latitude = 25.6000
        loc.operator_longitude = 85.1400
        loc.operator_sequence_number = None
        loc.operator_client_timestamp = sim_time
        loc.operator_server_received_at = sim_time
        db.session.commit()
        return sim_time

    # Helper to execute operator ping
    op_seq = 200
    # Boundaries tested:
    # 30s (LIVE): age <= 30s -> Takeover blocked, active_source = DRIVER
    # 31s (WEAK_SIGNAL): 30s < age <= 60s -> Takeover blocked, active_source = DRIVER
    # 60s boundary (WEAK_SIGNAL): age <= 60s -> Takeover blocked, active_source = DRIVER
    # 61s boundary (STALE): age > 60s -> Takeover activated, active_source = OPERATOR
    boundaries = [
        (30, 29.5, "LIVE", "DRIVER", False, "TAKEOVER BLOCKED (Driver LIVE <= 30s)"),
        (31, 31.0, "WEAK_SIGNAL", "DRIVER", False, "TAKEOVER BLOCKED (Driver WEAK_SIGNAL 31-60s)"),
        (60, 59.5, "WEAK_SIGNAL", "DRIVER", False, "TAKEOVER BLOCKED (Driver WEAK_SIGNAL <= 60s boundary)"),
        (61, 61.5, "STALE", "OPERATOR", True, "TAKEOVER ACTIVATED (Driver STALE > 60s boundary)"),
    ]

    for nominal_sec, actual_offset, expected_state, expected_src, expected_broadcast, verdict in boundaries:
        op_seq += 1
        d_time = set_driver_simulated_age(actual_offset, seq=10)
        curr_state = get_freshness_status(d_time)

        # Coordinate moving slightly (few meters from 25.6000, 85.1400)
        op_lat = 25.6005 + (op_seq * 0.00001)
        op_lon = 85.1405 + (op_seq * 0.00001)
        op_payload = {
            "trip_id": trip_id,
            "sequence_number": op_seq,
            "client_timestamp": datetime.now(UTC),
            "latitude": op_lat,
            "longitude": op_lon,
            "accuracy": 10.0,
            "speed": 15.0,
            "heading": 90.0,
        }

        res = record_operator_gps(admin, op_payload)
        active_src = res.get("active_source")
        broadcast = res.get("is_active_broadcast")
        active_loc = get_active_trip_location(trip_id)

        print(f"\n[BOUNDARY {nominal_sec} SECONDS] (Driver State: {curr_state})")
        print(f"  Target Boundary     : {nominal_sec}s (offset {actual_offset}s)")
        print(f"  Operator Ping Seq   : {op_seq}")
        print(f"  Result Active Source: {active_src}")
        print(f"  Is Broadcast Active : {broadcast}")
        print(f"  Live Coordinates    : {active_loc['coordinates']['latitude']}, {active_loc['coordinates']['longitude']}")
        print(f"  Verdict             : {verdict}")

        assert active_src == expected_src, f"Expected active source {expected_src} at {nominal_sec}s, got {active_src}"
        assert broadcast == expected_broadcast
        print(f"  [PASS] Boundary {nominal_sec}s verified successfully.")

    print("\n" + "=" * 75)
    print("BOUNDARY TEST 3: Instant Automatic Return to Driver GPS")
    print("=" * 75)
    # Now driver sends a fresh ping (age 0s)
    driver_payload = {
        "trip_id": trip_id,
        "sequence_number": 20,
        "client_timestamp": datetime.now(UTC),
        "latitude": 25.6010,
        "longitude": 85.1410,
        "accuracy": 5.0,
        "speed": 20.0,
        "heading": 180.0,
    }
    d_res = record_driver_gps(admin, driver_payload)
    active_loc = get_active_trip_location(trip_id)
    print(f"  Driver Fresh Ping (Age 0s) Submitted: Seq=20")
    print(f"  Active Source Immediately Restored  : {d_res['active_source']}")
    print(f"  Freshness State                     : {d_res['freshness']}")
    print(f"  Live Coordinates Switched to Driver : {active_loc['coordinates']['latitude']}, {active_loc['coordinates']['longitude']}")
    assert d_res["active_source"] == "DRIVER"
    assert d_res["freshness"] == "LIVE"
    assert abs(active_loc["coordinates"]["latitude"] - 25.6010) < 0.0001
    print("  [PASS] Automatic Driver Priority Restoration Verified!")
    print("=" * 75)
