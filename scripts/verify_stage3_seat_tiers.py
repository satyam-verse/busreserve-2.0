import sys
import ssl
import json
import urllib.request
import urllib.error

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://localhost:8443"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_stage3():
    print("=== Testing Stage 3: Premium Seats, Amenities & Cheapest Seat Finder ===")

    # 1. Fetch seat map for Trip 1 (Seater Coach with Standard & Premium)
    req = urllib.request.Request(f"{BASE_URL}/api/trips/1/seats")
    with urllib.request.urlopen(req, context=ctx) as res:
        seat_data = json.loads(res.read())
        seats = seat_data.get("seats", [])
        assert len(seats) > 0, "No seats returned for Trip 1"
        tiers_found = set(s.get("seat_tier") for s in seats)
        print(f"✓ GET /api/trips/1/seats returned {len(seats)} seats. Tiers found: {tiers_found}")
        assert "STANDARD" in tiers_found
        assert "PREMIUM" in tiers_found

        # Check amenities on premium seats
        premium_seats = [s for s in seats if s.get("seat_tier") == "PREMIUM"]
        assert len(premium_seats) > 0
        sample_prem = premium_seats[0]
        assert "amenities" in sample_prem
        print(f"✓ Premium seat {sample_prem['seat_number']}: fare=₹{sample_prem['fare']}, amenities={sample_prem['amenities']}")

    # 1b. Fetch seat map for Sleeper Trip (Trip 31728)
    req = urllib.request.Request(f"{BASE_URL}/api/trips/31728/seats")
    with urllib.request.urlopen(req, context=ctx) as res:
        sleeper_data = json.loads(res.read())
        sleeper_seats = sleeper_data.get("seats", [])
        sleeper_tiers = set(s.get("seat_tier") for s in sleeper_seats)
        print(f"✓ GET /api/trips/31728/seats returned {len(sleeper_seats)} seats. Tiers found: {sleeper_tiers}")
        assert "SLEEPER" in sleeper_tiers
        sample_sleeper = [s for s in sleeper_seats if s.get("seat_tier") == "SLEEPER"][0]
        print(f"✓ Sleeper seat {sample_sleeper['seat_number']}: fare=₹{sample_sleeper['fare']}, amenities={sample_sleeper['amenities']}")

    # 2. Query Cheapest Seats endpoint: GET /api/trips/1/cheapest-seats
    req = urllib.request.Request(f"{BASE_URL}/api/trips/1/cheapest-seats")
    with urllib.request.urlopen(req, context=ctx) as res:
        cheap_data = json.loads(res.read())
        assert "overall_cheapest_seat" in cheap_data
        overall = cheap_data["overall_cheapest_seat"]
        print(f"✓ GET /api/trips/1/cheapest-seats: Overall lowest fare is ₹{overall['fare']} for Seat {overall['seat_number']} ({overall.get('seat_tier')})")

        tiers_info = cheap_data.get("tiers", {})
        assert "STANDARD" in tiers_info
        assert "PREMIUM" in tiers_info
        assert "SLEEPER" in tiers_info
        print(f"✓ Tier breakdown: Standard=₹{tiers_info['STANDARD']['lowest_fare']}, Premium=₹{tiers_info['PREMIUM']['lowest_fare']}, Sleeper=₹{tiers_info['SLEEPER']['lowest_fare']}")

    # 3. Test filtering seats by tier: GET /api/trips/1/seats?tier=PREMIUM
    req = urllib.request.Request(f"{BASE_URL}/api/trips/1/seats?tier=PREMIUM")
    with urllib.request.urlopen(req, context=ctx) as res:
        filtered_data = json.loads(res.read())
        filtered_seats = filtered_data.get("seats", [])
        assert all(s.get("seat_tier") == "PREMIUM" for s in filtered_seats), "Filtered seats contain non-premium seats"
        print(f"✓ Filtering by tier=PREMIUM returned {len(filtered_seats)} seats, all verified PREMIUM")

    # 4. Verify Frontend Seat Selection Route /trips/1/seats serves HTTP 200
    req = urllib.request.Request(f"{BASE_URL}/trips/1/seats")
    with urllib.request.urlopen(req, context=ctx) as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "BusReserve" in html or "root" in html
        print("✓ Frontend route /trips/1/seats successfully resolved (HTTP 200)")

    print("\nSTAGE 3 VERIFICATION 100% COMPLETE & PASSED!\n")

if __name__ == "__main__":
    test_stage3()
