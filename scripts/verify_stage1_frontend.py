import sys
import ssl
import json
import urllib.request
import urllib.error

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from scripts.auth_helpers import get_demo_credentials
except ModuleNotFoundError:
    from auth_helpers import get_demo_credentials

BASE_URL = "https://localhost:8443"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_stage1():
    print("=== Testing Stage 1: Passenger GPS & Journey Sharing Backend/Frontend ===")

    # 1. Login as demo user
    _, user_pw = get_demo_credentials()
    login_payload = json.dumps({"email": "passenger@busreserve.local", "password": user_pw}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, context=ctx) as res:
        login_data = json.loads(res.read())
        token = login_data.get("token") or login_data.get("access_token") or (login_data.get("data") and login_data["data"].get("token"))
        if not token:
            cookie_headers = res.headers.get_all("Set-Cookie") or []
            for c in cookie_headers:
                if "busreserve_access_token=" in c:
                    token = c.split("busreserve_access_token=")[1].split(";")[0].strip()
        print("✓ Logged in as demo user, token obtained:", bool(token))

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Get user bookings to find an active trip
    req = urllib.request.Request(f"{BASE_URL}/api/user/bookings", headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        bookings_data = json.loads(res.read())
        bookings = bookings_data.get("bookings", [])
        assert len(bookings) > 0, "No bookings found for user"
        target_booking = bookings[0]
        trip_id = target_booking["trip_id"]
        pnr = target_booking["pnr"]
        print(f"✓ Found booking {pnr} for trip {trip_id}")

    # 3. Test GET /api/tracking/trip/<trip_id>
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/trip/{trip_id}", headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        live_data = json.loads(res.read())
        assert "trip_id" in live_data
        assert "status" in live_data
        print(f"✓ GET /api/tracking/trip/{trip_id} returned status={live_data['status']}, source={live_data.get('active_source')}")

    # 4. Create journey share link
    booking_id = target_booking["id"]
    share_payload = json.dumps({"booking_id": booking_id, "validity_hours": 24}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/share", data=share_payload, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        share_res = json.loads(res.read())
        share_token = share_res["token"]
        share_url = share_res["share_url"]
        print(f"✓ Created journey share: token={share_token}, url={share_url}")
        assert "journey/track" in share_url

    # 5. Access public tracking endpoint (Unauthenticated)
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/shared/{share_token}")
    with urllib.request.urlopen(req, context=ctx) as res:
        shared_data = json.loads(res.read())
        assert shared_data["is_active"] is True
        assert "trip" in shared_data
        assert "tracking" in shared_data
        # Assert ZERO passenger PII
        pii_fields = ["passenger_name", "email", "phone", "pnr", "fare", "seat", "user_id"]
        for pii in pii_fields:
            assert pii not in shared_data, f"PII leak detected: {pii} is present in public tracking data!"
            assert pii not in shared_data.get("trip", {}), f"PII leak in trip: {pii}"
        print("✓ Public tracking endpoint verified: 100% ZERO PII leaked")

    # 6. Verify frontend route serves 200 OK for /journey/track/<share_token>
    req = urllib.request.Request(f"{BASE_URL}/journey/track/{share_token}")
    with urllib.request.urlopen(req, context=ctx) as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "BusReserve" in html or "root" in html
        print(f"✓ Frontend route /journey/track/{share_token} successfully resolved (HTTP 200)")

    # 7. Revoke journey share link
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/share/{share_token}", headers=headers, method="DELETE")
    with urllib.request.urlopen(req, context=ctx) as res:
        revoke_res = json.loads(res.read())
        print(f"✓ Revoked journey share {share_token}: {revoke_res.get('message')}")

    # 8. Access revoked link: MUST return HTTP 410 Gone
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/tracking/shared/{share_token}")
        with urllib.request.urlopen(req, context=ctx) as res:
            assert False, "Expected HTTP 410 Gone, but got HTTP 200"
    except urllib.error.HTTPError as e:
        assert e.code == 410, f"Expected HTTP 410 Gone, got HTTP {e.code}"
        print(f"✓ Revoked link correctly returned HTTP 410 Gone")

    print("\nSTAGE 1 VERIFICATION 100% COMPLETE & PASSED!\n")

if __name__ == "__main__":
    test_stage1()
