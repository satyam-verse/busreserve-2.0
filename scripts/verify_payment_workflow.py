"""Comprehensive Automated Verification Script for BusReserve 2.0 Payment System.

Tests:
1. Trip seat lookup
2. Payment order creation
3. Session order retrieval
4. Payment bank failure simulation
5. Payment session retry
6. Payment cancellation simulation
7. Payment session re-retry
8. Successful settlement and atomic seat confirmation
9. PNR lookup and ticket verification
10. Conflict and duplicate seat prevention
"""

import json
import ssl
import sys
import urllib.error
import urllib.request

BASE_URL = "https://localhost:8443"

# Disable SSL verification for self-signed development certificates
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def request(method: str, path: str, data: dict = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            code = resp.getcode()
            content = resp.read().decode("utf-8")
            return code, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return e.code, parsed


def run_tests():
    print("=" * 65)
    print("BUSRESERVE 2.0 - PAYMENT WORKFLOW END-TO-END VERIFICATION SUITE")
    print("=" * 65)

    # 1. Search Trips
    print("\n[Step 1] Fetching available trips...")
    code, trips_resp = request("GET", "/api/trips")
    assert code == 200, f"Failed to fetch trips: {code}"
    trips = trips_resp.get("trips", [])
    assert len(trips) > 0, "No trips returned"
    trip = trips[0]
    trip_id = trip["id"]
    print(f"  Selected Trip #{trip_id}: {trip['source']} -> {trip['destination']} ({trip['operator_name']})")

    # 2. Get Seat Map
    print("\n[Step 2] Fetching seat map for trip...")
    code, seat_resp = request("GET", f"/api/trips/{trip_id}/seats")
    assert code == 200, f"Failed to fetch seats: {code}"
    available_seats = [s for s in seat_resp["seats"] if s["is_available"]]
    assert len(available_seats) > 0, "No available seats on trip"
    chosen_seat = available_seats[-1]  # Pick last available seat to preserve lower seat numbers
    seat_number = chosen_seat["seat_number"]
    fare = chosen_seat["fare"]
    stops = seat_resp.get("stops", [])
    boarding_stop_id = stops[0]["id"]
    drop_stop_id = stops[-1]["id"]
    print(f"  Selected Available Seat: {seat_number} (Fare: Rs.{fare})")

    passenger_payload = {
        "trip_id": trip_id,
        "seat_number": seat_number,
        "boarding_stop_id": boarding_stop_id,
        "drop_stop_id": drop_stop_id,
        "passenger_name": "Dr. Ananya Sharma",
        "passenger_email": "ananya.sharma@example.com",
        "passenger_phone": "9876543210",
    }

    # 3. Create Payment Order
    print("\n[Step 3] Initializing payment order (POST /api/payments/order)...")
    code, order_res = request("POST", "/api/payments/order", {
        **passenger_payload,
        "gateway": "MOCK_SANDBOX",
        "payment_method": "UPI",
        "idempotency_key": f"test_idemp_{seat_number}_{trip_id}",
    })
    assert code == 201, f"Failed to create order: {code} {order_res}"
    tx = order_res["transaction"]
    checkout = order_res["checkout"]
    txn_ref = tx["transaction_ref"]
    assert txn_ref, "Missing transaction_ref"
    assert tx["status"] == "INITIATED", f"Expected INITIATED, got {tx['status']}"
    print(f"  Payment Order Created Successfully! TXN: {txn_ref}, Order: {tx['gateway_order_id']}, Status: {tx['status']}")

    # 4. Retrieve Payment Order Session
    print(f"\n[Step 4] Retrieving order session by reference (GET /api/payments/order/{txn_ref})...")
    code, get_res = request("GET", f"/api/payments/order/{txn_ref}")
    assert code == 200, f"Failed to get order: {code} {get_res}"
    assert get_res["transaction"]["transaction_ref"] == txn_ref
    assert get_res["already_settled"] is False
    print("  Order Session retrieved successfully with active status and checkout params.")

    # 5. Simulate Bank Failure
    print("\n[Step 5] Simulating Bank / Gateway Failure (POST /api/payments/fail)...")
    code, fail_res = request("POST", "/api/payments/fail", {
        "transaction_ref": txn_ref,
        "error_code": "BANK_DECLINED",
        "error_message": "Card issuer declined the transaction (Simulated Sandbox).",
    })
    assert code == 200, f"Failed to record failure: {code} {fail_res}"
    assert fail_res["transaction"]["status"] == "FAILED"
    assert fail_res["transaction"]["error_code"] == "BANK_DECLINED"
    print(f"  Bank failure recorded: Status={fail_res['transaction']['status']}, Code={fail_res['transaction']['error_code']}")

    # 6. Retry Failed Payment
    print("\n[Step 6] Re-opening failed order for retry (POST /api/payments/retry)...")
    code, retry_res = request("POST", "/api/payments/retry", {
        "transaction_ref": txn_ref,
    })
    assert code == 200, f"Failed to retry: {code} {retry_res}"
    assert retry_res["transaction"]["status"] == "INITIATED"
    print(f"  Session re-opened! Status reset to: {retry_res['transaction']['status']}")

    # 7. Simulate User Cancellation
    print("\n[Step 7] Simulating User Cancellation (POST /api/payments/cancel)...")
    code, cancel_res = request("POST", "/api/payments/cancel", {
        "transaction_ref": txn_ref,
        "reason": "Passenger cancelled checkout window",
    })
    assert code == 200, f"Failed to cancel: {code} {cancel_res}"
    assert cancel_res["transaction"]["status"] == "CANCELLED"
    print(f"  Cancellation recorded: Status={cancel_res['transaction']['status']}")

    # 8. Retry Cancelled Payment
    print("\n[Step 8] Re-opening cancelled order for retry (POST /api/payments/retry)...")
    code, retry_res2 = request("POST", "/api/payments/retry", {
        "transaction_ref": txn_ref,
    })
    assert code == 200, f"Failed to retry: {code} {retry_res2}"
    assert retry_res2["transaction"]["status"] == "INITIATED"
    print(f"  Session re-opened! Status reset to: {retry_res2['transaction']['status']}")

    # 9. Verify and Atomically Confirm Settlement
    print("\n[Step 9] Cryptographic Verification & Settlement (POST /api/payments/verify)...")
    code, verify_res = request("POST", "/api/payments/verify", {
        "transaction_ref": txn_ref,
        "gateway_payment_id": f"PAY_MOCK_{txn_ref}",
        "gateway_signature": checkout.get("mock_signature") or f"mock_sig_{txn_ref}",
        "booking": passenger_payload,
    })
    assert code == 200, f"Failed to verify and settle: {code} {verify_res}"
    booking = verify_res["booking"]
    payment = verify_res.get("payment") or verify_res.get("transaction")
    pnr = booking["pnr"]
    assert pnr, "PNR was not generated"
    assert booking["status"] == "CONFIRMED", f"Expected CONFIRMED, got {booking['status']}"
    assert payment["status"] == "SUCCESS", f"Expected SUCCESS, got {payment['status']}"
    print(f"  Booking Confirmed! PNR: {pnr}")
    print(f"  Passenger: {booking['passenger_name']}, Seat: {booking['seat_number']}")
    print(f"  Fare: Rs.{booking['total_fare']}, Payment Status: {payment['status']}")

    # 10. Track Booking via PNR Lookup
    print(f"\n[Step 10] Tracking confirmed booking via PNR (GET /api/bookings/{pnr})...")
    code, pnr_res = request("GET", f"/api/bookings/{pnr}")
    assert code == 200, f"Failed to fetch booking by PNR: {code} {pnr_res}"
    assert pnr_res["booking"]["pnr"] == pnr
    assert pnr_res["booking"]["status"] == "CONFIRMED"
    print("  Booking successfully verified in database via PNR tracking API.")

    # 11. Conflict Prevention (Double Booking Prevention)
    print(f"\n[Step 11] Verifying conflict prevention on seat {seat_number}...")
    code, conflict_order = request("POST", "/api/payments/order", {
        **passenger_payload,
        "passenger_name": "Duplicate Tester",
        "gateway": "MOCK_SANDBOX",
        "payment_method": "UPI",
    })
    assert code == 409, f"Expected 409 Conflict, got {code} {conflict_order}"
    print(f"  Conflict safely prevented: HTTP {code} - {conflict_order.get('error', {}).get('message')}")

    # 12. Idempotent Settle Check
    print(f"\n[Step 12] Verifying idempotent settle check on transaction {txn_ref}...")
    code, idempotent_res = request("POST", "/api/payments/verify", {
        "transaction_ref": txn_ref,
        "gateway_payment_id": f"PAY_MOCK_{txn_ref}",
        "gateway_signature": checkout.get("mock_signature") or f"mock_sig_{txn_ref}",
        "booking": passenger_payload,
    })
    assert code == 200, f"Expected 200 for idempotent verify, got {code}"
    assert idempotent_res.get("idempotent") is True or idempotent_res.get("already_settled") is True
    assert idempotent_res["booking"]["pnr"] == pnr
    print("  Idempotency verified: Returned already settled booking without duplicate charges.")

    print("\n" + "=" * 65)
    print("ALL 12 VERIFICATION TEST CASES PASSED FLAWLESSLY!")
    print("=" * 65)


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}", file=sys.stderr)
        sys.exit(1)
