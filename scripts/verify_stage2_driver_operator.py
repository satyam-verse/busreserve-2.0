import sys
import ssl
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, UTC

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

def test_stage2():
    print("=== Testing Stage 2: Driver GPS Console & Operator Fleet Dashboard ===")

    # 1. Login as Admin (who can act as supervisor/driver/operator)
    admin_pw, _ = get_demo_credentials()
    login_payload = json.dumps({"email": "admin@busreserve.local", "password": admin_pw}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/auth/admin/login", data=login_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, context=ctx) as res:
        login_data = json.loads(res.read())
        admin_token = login_data.get("token") or login_data.get("access_token")
        if not admin_token:
            for c in res.headers.get_all("Set-Cookie") or []:
                if "busreserve_access_token=" in c:
                    admin_token = c.split("busreserve_access_token=")[1].split(";")[0].strip()
        print("✓ Logged in as Admin, token obtained:", bool(admin_token))

    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    # 2. Driver assigned trips endpoint: GET /api/driver/trips
    req = urllib.request.Request(f"{BASE_URL}/api/driver/trips", headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        driver_trips_data = json.loads(res.read())
        trips = driver_trips_data.get("trips", [])
        assert len(trips) > 0, "No trips returned for driver"
        target_trip = trips[0]
        trip_id = target_trip["id"]
        print(f"✓ GET /api/driver/trips returned {len(trips)} trips. Target trip #{trip_id}")

    # 3. Driver GPS ingestion: POST /api/tracking/driver/location
    driver_ping_payload = json.dumps({
        "trip_id": trip_id,
        "sequence_number": int(time.time() * 10),
        "client_timestamp": datetime.now(UTC).isoformat(),
        "latitude": 25.612040,
        "longitude": 85.144120,
        "accuracy": 8.5,
        "speed": 12.5,
        "heading": 85.0
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/driver/location", data=driver_ping_payload, headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        ping_res = json.loads(res.read())
        assert ping_res.get("status") == "ACCEPTED"
        assert ping_res.get("active_source") == "DRIVER"
        assert ping_res.get("freshness") == "LIVE"
        print(f"✓ Driver GPS ping accepted: status={ping_res['status']}, freshness={ping_res['freshness']}")

    # 4. Check trip live status reflects LIVE driver
    req = urllib.request.Request(f"{BASE_URL}/api/tracking/trip/{trip_id}", headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        live_res = json.loads(res.read())
        assert live_res.get("status") == "LIVE"
        assert live_res.get("active_source") == "DRIVER"
        assert live_res.get("is_live") is True
        print(f"✓ Trip #{trip_id} tracking confirmed LIVE with active_source=DRIVER")

    # 5. Driver Dispatch Departure: POST /api/driver/trip/<trip_id>/depart
    req = urllib.request.Request(f"{BASE_URL}/api/driver/trip/{trip_id}/depart", data=b"{}", headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        depart_res = json.loads(res.read())
        assert "delivery_status" in depart_res
        ds = depart_res["delivery_status"]
        print(f"✓ Driver marked trip departed. Alerts status: Sent={ds['sent']}, Mock={ds['mock']}, Pending={ds['not_configured']}")

    # 6. Operator Fleet Endpoint: GET /api/operator/fleet
    req = urllib.request.Request(f"{BASE_URL}/api/operator/fleet", headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        fleet_res = json.loads(res.read())
        fleet = fleet_res.get("fleet", [])
        assert len(fleet) > 0, "Fleet list empty"
        print(f"✓ GET /api/operator/fleet returned {len(fleet)} fleet buses with live GPS tracking health")

    # 7. Operator Trips Endpoint: GET /api/operator/trips
    req = urllib.request.Request(f"{BASE_URL}/api/operator/trips", headers=admin_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        op_trips_res = json.loads(res.read())
        op_trips = op_trips_res.get("trips", [])
        assert len(op_trips) > 0, "Operator trips empty"
        print(f"✓ GET /api/operator/trips returned {len(op_trips)} trips")

    # 8. Verify Frontend Routes exist and serve HTTP 200
    for route in ["/driver", "/operator"]:
        req = urllib.request.Request(f"{BASE_URL}{route}")
        with urllib.request.urlopen(req, context=ctx) as res:
            assert res.status == 200
            html = res.read().decode("utf-8")
            assert "BusReserve" in html or "root" in html
            print(f"✓ Frontend route {route} successfully resolved (HTTP 200)")

    print("\nSTAGE 2 VERIFICATION 100% COMPLETE & PASSED!\n")

if __name__ == "__main__":
    test_stage2()
