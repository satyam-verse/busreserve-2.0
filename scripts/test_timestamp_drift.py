import json
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
try:
    from scripts.auth_helpers import get_demo_credentials
except ModuleNotFoundError:
    from auth_helpers import get_demo_credentials

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 1. Login Admin
admin_pw, _ = get_demo_credentials()
req = urllib.request.Request(
    'https://localhost:8443/api/auth/admin/login',
    data=json.dumps({'email': 'admin@busreserve.local', 'password': admin_pw}).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req, context=ctx)
cookies = res.headers.get_all('Set-Cookie') or []
token = None
for c in cookies:
    if 'busreserve_access_token=' in c:
        token = c.split('busreserve_access_token=')[1].split(';')[0].strip()
        break
assert token, "Could not extract access token from cookies"

trip_id = 3
r_trk = urllib.request.urlopen(f'https://localhost:8443/api/tracking/trip/{trip_id}', context=ctx)
cur_seq = json.loads(r_trk.read().decode()).get('driver_sequence_number') or 0

print("=" * 70)
print("DEMONSTRATION 1: VALID DYNAMIC CURRENT TIMESTAMP (Age ~0s)")
print("=" * 70)
seq = cur_seq + 1
now_iso = datetime.now(timezone.utc).isoformat()
payload = {
    'trip_id': trip_id,
    'sequence_number': seq,
    'client_timestamp': now_iso,
    'latitude': 25.5941,
    'longitude': 85.1376,
    'accuracy': 8.5,
    'speed': 15.0,
    'heading': 120.0
}
req = urllib.request.Request(
    'https://localhost:8443/api/tracking/driver/location',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
)
res = urllib.request.urlopen(req, context=ctx)
body = json.loads(res.read().decode())
print(f"HTTP Status      : {res.status} OK")
print(f"Dynamic Timestamp: {now_iso}")
print(f"Sequence Number  : {seq}")
print(f"Active Source    : {body.get('active_source')}")
print(f"Freshness State  : {body.get('freshness')}")
print(f"API Response     : {body}")

print("\n" + "=" * 70)
print("DEMONSTRATION 2: PAST CLOCK-DRIFT VIOLATION (180s in past > 120s limit)")
print("=" * 70)
seq += 1
past_iso = (datetime.now(timezone.utc) - timedelta(seconds=180)).isoformat()
payload['sequence_number'] = seq
payload['client_timestamp'] = past_iso
req = urllib.request.Request(
    'https://localhost:8443/api/tracking/driver/location',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
)
try:
    urllib.request.urlopen(req, context=ctx)
    print("FAILED: Past timestamp was unexpectedly accepted")
except urllib.error.HTTPError as e:
    err_body = json.loads(e.read().decode())
    print(f"HTTP Status      : {e.code} BAD REQUEST")
    print(f"Drift Timestamp  : {past_iso} (-180.0s drift)")
    print(f"Error Code       : {err_body.get('error', {}).get('code')}")
    print(f"Error Message    : {err_body.get('error', {}).get('message')}")

print("\n" + "=" * 70)
print("DEMONSTRATION 3: FUTURE CLOCK-DRIFT VIOLATION (180s in future > 120s limit)")
print("=" * 70)
seq += 1
future_iso = (datetime.now(timezone.utc) + timedelta(seconds=180)).isoformat()
payload['sequence_number'] = seq
payload['client_timestamp'] = future_iso
req = urllib.request.Request(
    'https://localhost:8443/api/tracking/driver/location',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
)
try:
    urllib.request.urlopen(req, context=ctx)
    print("FAILED: Future timestamp was unexpectedly accepted")
except urllib.error.HTTPError as e:
    err_body = json.loads(e.read().decode())
    print(f"HTTP Status      : {e.code} BAD REQUEST")
    print(f"Drift Timestamp  : {future_iso} (+180.0s drift)")
    print(f"Error Code       : {err_body.get('error', {}).get('code')}")
    print(f"Error Message    : {err_body.get('error', {}).get('message')}")
print("=" * 70)
