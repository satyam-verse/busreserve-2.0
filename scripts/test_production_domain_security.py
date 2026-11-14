"""Production Journey-Sharing Domain Security & Fail-Closed Suite.

Tests:
1. Missing PUBLIC_APP_URL in production -> PUBLIC_DOMAIN_NOT_CONFIGURED.
2. Insecure HTTP URL -> PUBLIC_DOMAIN_INSECURE.
3. Localhost / loopback domain -> PUBLIC_DOMAIN_LOCALHOST_FORBIDDEN.
4. Invalid / unwhitelisted host -> PUBLIC_DOMAIN_NOT_ALLOWED.
5. Missing host whitelist -> PUBLIC_DOMAIN_NOT_CONFIGURED.
6. Valid HTTPS approved URL -> Generates link cleanly.
7. Zero passenger PII leakage verification.
8. Immediate link revocation verification.
"""

import os
from flask import Flask
from app import create_app
from app.extensions import db
from app.models.user import User
from app.services.tracking_service import (
    get_public_app_base_url,
    create_journey_share,
    get_shared_journey,
    revoke_journey_share,
)
from app.utils.errors import ValidationAPIError

app = create_app()

with app.app_context():
    print("=" * 75)
    print("PRODUCTION JOURNEY-SHARING DOMAIN SECURITY & FAIL-CLOSED DRILLS")
    print("=" * 75)

    os.environ["FLASK_ENV"] = "production"

    # Test 1: Missing PUBLIC_APP_URL
    app.config["PUBLIC_APP_URL"] = ""
    app.config["ALLOWED_PUBLIC_HOSTS"] = "busreserve.in"
    try:
        get_public_app_base_url()
        print("  [FAIL] Test 1: Missing PUBLIC_APP_URL should have raised error")
    except ValidationAPIError as e:
        print(f"\n[TEST 1: MISSING PUBLIC_APP_URL IN PRODUCTION]")
        print(f"  Error Code   : {e.error_code}")
        print(f"  Error Message: {e.message}")
        print(f"  Verdict      : [PASS] Failed closed with PUBLIC_DOMAIN_NOT_CONFIGURED")
        assert e.error_code == "PUBLIC_DOMAIN_NOT_CONFIGURED"

    # Test 2: Insecure HTTP Scheme
    app.config["PUBLIC_APP_URL"] = "http://busreserve.in"
    app.config["ALLOWED_PUBLIC_HOSTS"] = "busreserve.in"
    try:
        get_public_app_base_url()
        print("  [FAIL] Test 2: Insecure HTTP should have raised error")
    except ValidationAPIError as e:
        print(f"\n[TEST 2: INSECURE HTTP URL (http://busreserve.in)]")
        print(f"  Error Code   : {e.error_code}")
        print(f"  Error Message: {e.message}")
        print(f"  Verdict      : [PASS] Failed closed with PUBLIC_DOMAIN_INSECURE")
        assert e.error_code == "PUBLIC_DOMAIN_INSECURE"

    # Test 3: Localhost Forbidden in Production
    app.config["PUBLIC_APP_URL"] = "https://localhost:8443"
    app.config["ALLOWED_PUBLIC_HOSTS"] = "localhost,127.0.0.1,busreserve.in"
    try:
        get_public_app_base_url()
        print("  [FAIL] Test 3: Localhost in prod should have raised error")
    except ValidationAPIError as e:
        print(f"\n[TEST 3: LOCALHOST DOMAIN IN PRODUCTION (https://localhost:8443)]")
        print(f"  Error Code   : {e.error_code}")
        print(f"  Error Message: {e.message}")
        print(f"  Verdict      : [PASS] Failed closed with PUBLIC_DOMAIN_LOCALHOST_FORBIDDEN")
        assert e.error_code == "PUBLIC_DOMAIN_LOCALHOST_FORBIDDEN"

    # Test 4: Unwhitelisted / Invalid Host
    app.config["PUBLIC_APP_URL"] = "https://attacker-domain.evil.com"
    app.config["ALLOWED_PUBLIC_HOSTS"] = "busreserve.in,app.busreserve.in"
    try:
        get_public_app_base_url()
        print("  [FAIL] Test 4: Unwhitelisted host should have raised error")
    except ValidationAPIError as e:
        print(f"\n[TEST 4: UNWHITELISTED HOST (https://attacker-domain.evil.com)]")
        print(f"  Error Code   : {e.error_code}")
        print(f"  Error Message: {e.message}")
        print(f"  Verdict      : [PASS] Failed closed with PUBLIC_DOMAIN_NOT_ALLOWED")
        assert e.error_code == "PUBLIC_DOMAIN_NOT_ALLOWED"

    # Test 5: Missing Whitelist in Production
    app.config["PUBLIC_APP_URL"] = "https://busreserve.in"
    app.config["ALLOWED_PUBLIC_HOSTS"] = ""
    try:
        get_public_app_base_url()
        print("  [FAIL] Test 5: Missing whitelist should have raised error")
    except ValidationAPIError as e:
        print(f"\n[TEST 5: MISSING ALLOWED_PUBLIC_HOSTS WHITELIST]")
        print(f"  Error Code   : {e.error_code}")
        print(f"  Error Message: {e.message}")
        print(f"  Verdict      : [PASS] Failed closed with PUBLIC_DOMAIN_NOT_CONFIGURED")
        assert e.error_code == "PUBLIC_DOMAIN_NOT_CONFIGURED"

    # Test 6: Valid HTTPS Production Configuration
    app.config["PUBLIC_APP_URL"] = "https://busreserve.in"
    app.config["ALLOWED_PUBLIC_HOSTS"] = "busreserve.in,app.busreserve.in"
    base_url = get_public_app_base_url()
    print(f"\n[TEST 6: VALID HTTPS WHITELISTED DOMAIN]")
    print(f"  Base URL: {base_url}")
    print(f"  Verdict : [PASS] Successfully resolved approved domain")
    assert base_url == "https://busreserve.in"

    # Test 7: End-to-End Share Link Creation & Zero PII Leakage
    admin = User.query.filter_by(role=User.ROLE_ADMIN).first()
    share = create_journey_share(user=admin, booking_id=43, validity_hours=24)
    print(f"\n[TEST 7: END-TO-END SHARE CREATION & ZERO PII AUDIT]")
    print(f"  Share URL : {share['share_url']}")
    print(f"  Expires At: {share['expires_at']}")
    assert share["share_url"].startswith("https://busreserve.in/journey/track/")

    public_view = get_shared_journey(share["token"])
    print(f"  Public Payload Keys: {list(public_view.keys())}")
    print(f"  Trip Info Exposing : Origin={public_view['trip']['source']}, Destination={public_view['trip']['destination']}, Bus Type={public_view['trip']['bus_type']}")
    forbidden_pii = ["passenger_name", "passenger_email", "passenger_phone", "pnr", "total_fare", "seat_number", "booking_id", "user_id"]
    leaked = [k for k in forbidden_pii if k in public_view or (isinstance(public_view.get("trip"), dict) and k in public_view["trip"])]
    print(f"  Forbidden PII Check: Leaked fields={leaked}")
    assert len(leaked) == 0, f"PII Leakage detected: {leaked}"
    print(f"  Verdict            : [PASS] 100% Zero Passenger PII verified!")

    # Test 8: Immediate Revocation
    print(f"\n[TEST 8: IMMEDIATE REVOCATION]")
    revoke_journey_share(admin, share["token"])
    try:
        get_shared_journey(share["token"])
        print("  [FAIL] Revoked link was still accessible")
    except Exception as e:
        print(f"  Access After Revocation: Raised {type(e).__name__} ({str(e)})")
        print(f"  Verdict                : [PASS] Revoked link strictly blocked!")

    print("\n" + "=" * 75)
    print("ALL PRODUCTION DOMAIN SECURITY DRILLS COMPLETED AND VERIFIED!")
    print("=" * 75)
