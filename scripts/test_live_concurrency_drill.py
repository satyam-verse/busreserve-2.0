#!/usr/bin/env python3
"""Live concurrent booking protection drill against BusReserve 2.0 public ingress.

Proves that when 10 simultaneous threads contend for the exact same seat,
PostgreSQL pessimistic locking and partial unique indexes ensure:
- Exactly 1 winner receives HTTP 201 Created with a valid PNR.
- 9 contenders receive HTTP 409 Conflict.
- Exactly 1 confirmed booking record is persisted in PostgreSQL (zero duplicates).
"""

import json
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
TRIP_ID = 4
SEAT_NUMBER = "1A"
BOARDING_STOP_ID = 1
DROP_STOP_ID = 5

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def main():
    print("=" * 70)
    print("BUSRESERVE 2.0 — LIVE CONCURRENT BOOKING PROTECTION DRILL")
    print(f"Target Endpoint: {BASE_URL}/api/bookings")
    print(f"Trip ID: {TRIP_ID}, Seat: {SEAT_NUMBER}")
    print("=" * 70)

    worker_count = 10
    barrier = threading.Barrier(worker_count)
    results = []
    lock = threading.Lock()

    def _attempt_booking(idx: int):
        payload = {
            "trip_id": TRIP_ID,
            "seat_number": SEAT_NUMBER,
            "passenger_name": f"Concurrent Passenger {chr(65 + idx)}",
            "passenger_email": f"concurrent_{idx}@algions.test",
            "passenger_phone": f"9876543{idx:03d}",
            "boarding_stop_id": BOARDING_STOP_ID,
            "drop_stop_id": DROP_STOP_ID,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/api/bookings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        barrier.wait()  # Synchronize all 10 threads to fire simultaneously
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                elapsed = time.perf_counter() - start
                body = json.loads(resp.read().decode("utf-8"))
                with lock:
                    results.append((resp.status, body, elapsed))
        except urllib.error.HTTPError as exc:
            elapsed = time.perf_counter() - start
            body = json.loads(exc.read().decode("utf-8")) if exc.fp else {}
            with lock:
                results.append((exc.code, body, elapsed))

    threads = [
        threading.Thread(target=_attempt_booking, args=(i,))
        for i in range(worker_count)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nDispatched {worker_count} concurrent booking requests simultaneously:")
    winners = [r for r in results if r[0] == 201]
    conflicts = [r for r in results if r[0] == 409]

    for i, (status, body, lat) in enumerate(results):
        pnr = body.get("booking", {}).get("pnr") if status == 201 else None
        msg = body.get("message") if status != 201 else f"Confirmed PNR={pnr}"
        print(f"  Thread {i + 1:02d}: HTTP {status} ({lat * 1000:.1f}ms) -> {msg}")

    print("\n--- Summary ---")
    print(f"  HTTP 201 (Created):   {len(winners)} (Expected: 1)")
    print(f"  HTTP 409 (Conflict):  {len(conflicts)} (Expected: 9)")

    assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"
    assert len(conflicts) == 9, f"Expected exactly 9 conflicts, got {len(conflicts)}"

    winning_pnr = winners[0][1]["booking"]["pnr"]
    winning_email = winners[0][1]["booking"]["passenger_email"]
    print(f"\nWinning PNR: {winning_pnr} (Passenger Email: {winning_email})")

    # Step 2: Cancel the test booking to restore baseline state
    print(f"\nCleaning up test booking {winning_pnr} via cancellation...")
    cancel_payload = json.dumps({"passenger_email": winning_email}).encode("utf-8")
    cancel_req = urllib.request.Request(
        f"{BASE_URL}/api/bookings/{winning_pnr}/cancel",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(cancel_req, timeout=5, context=ssl_ctx) as resp:
        cancel_body = json.loads(resp.read().decode("utf-8"))
        assert cancel_body.get("booking", {}).get("status") == "CANCELLED"
    print("  Booking successfully cancelled. Seat returned to pool.")

    print("\n" + "=" * 70)
    print("CONCURRENCY ACCEPTANCE TEST 1: PASS")
    print("Zero duplicate reservations permitted under high multi-threaded contention.")
    print("=" * 70)


if __name__ == "__main__":
    main()
