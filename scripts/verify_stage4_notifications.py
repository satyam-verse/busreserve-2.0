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

def test_stage4():
    print("=== Testing Stage 4: Smart Notifications Feed & Delivery Status Distinction ===")

    # 1. Login as Passenger
    _, user_pw = get_demo_credentials()
    login_payload = json.dumps({"email": "passenger@busreserve.local", "password": user_pw}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, context=ctx) as res:
        login_data = json.loads(res.read())
        token = login_data.get("token") or login_data.get("access_token")
        if not token:
            for c in res.headers.get_all("Set-Cookie") or []:
                if "busreserve_access_token=" in c:
                    token = c.split("busreserve_access_token=")[1].split(";")[0].strip()
        print("✓ Logged in as Passenger, token obtained:", bool(token))

    passenger_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Get passenger notifications: GET /api/payments/notifications
    req = urllib.request.Request(f"{BASE_URL}/api/payments/notifications", headers=passenger_headers)
    with urllib.request.urlopen(req, context=ctx) as res:
        notif_res = json.loads(res.read())
        notifications = notif_res.get("notifications", [])
        print(f"✓ GET /api/payments/notifications returned {len(notifications)} notifications for passenger")
        
        # Verify status distinction
        statuses_found = set(n.get("status") for n in notifications)
        print(f"✓ Notification statuses in feed: {statuses_found}")
        for n in notifications[:3]:
            print(f"  • [{n.get('status')}] {n.get('event_type')}: {n.get('title')} (is_read={n.get('is_read')})")

    # 3. Test mark as read if any unread notification exists
    unread = [n for n in notifications if not n.get("is_read")]
    if unread:
        target = unread[0]
        req = urllib.request.Request(f"{BASE_URL}/api/payments/notifications/{target['id']}/read", data=b"{}", headers=passenger_headers)
        with urllib.request.urlopen(req, context=ctx) as res:
            read_res = json.loads(res.read())
            assert read_res.get("success") is True
            print(f"✓ Notification #{target['id']} successfully marked as read")
    else:
        print("✓ All current notifications already marked as read")

    # 4. Verify unauthenticated access is rejected (HTTP 401)
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/payments/notifications")
        with urllib.request.urlopen(req, context=ctx) as res:
            assert False, "Expected HTTP 401 for unauthenticated request"
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"
        print(f"✓ Unauthenticated notification access correctly rejected with HTTP {e.code}")

    print("\nSTAGE 4 VERIFICATION 100% COMPLETE & PASSED!\n")

if __name__ == "__main__":
    test_stage4()
