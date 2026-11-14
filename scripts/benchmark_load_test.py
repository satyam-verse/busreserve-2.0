#!/usr/bin/env python3
"""Synthetic concurrent load testing and latency benchmarking harness for BusReserve 2.0.

Evaluates API throughput, response latencies (P50/P95/P99), and error rates across
search, seat catalog, route lookups, metrics, and checkout endpoints without external dependencies.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("BENCHMARK_BASE_URL", "http://localhost:8080")


def make_request(
    url: str, method: str = "GET", payload: dict | None = None
) -> tuple[int, float]:
    """Execute a single HTTP request and return (status_code, latency_seconds)."""
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = time.perf_counter() - start
            return resp.status, elapsed
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - start
        return exc.code, elapsed
    except Exception:
        elapsed = time.perf_counter() - start
        return 0, elapsed


def run_benchmark_scenario(
    name: str,
    url_or_fn,
    total_requests: int = 100,
    concurrency: int = 10,
) -> dict[str, float | int]:
    print(
        f"\n--- Scenario: {name} ({total_requests} requests, concurrency={concurrency}) ---"
    )
    latencies: list[float] = []
    status_counts: dict[int, int] = {}

    start_wall = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        if callable(url_or_fn):
            futures = [executor.submit(url_or_fn, i) for i in range(total_requests)]
        else:
            futures = [
                executor.submit(make_request, url_or_fn) for _ in range(total_requests)
            ]

        for future in as_completed(futures):
            code, lat = future.result()
            latencies.append(lat)
            status_counts[code] = status_counts.get(code, 0) + 1

    total_time = time.perf_counter() - start_wall
    latencies.sort()
    count = len(latencies)

    rps = round(count / total_time, 2)
    p50 = round(latencies[int(math.floor(count * 0.50))] * 1000, 2)
    p95 = round(latencies[int(math.floor(count * 0.95))] * 1000, 2)
    p99 = round(latencies[int(math.floor(count * 0.99))] * 1000, 2)
    avg_lat = round((sum(latencies) / count) * 1000, 2)
    successes = sum(c for code, c in status_counts.items() if 200 <= code < 400)
    success_rate = round((successes / count) * 100, 1)

    print(f"  Throughput:    {rps} RPS (executed in {total_time:.2f}s)")
    print(f"  Success Rate:  {success_rate}% ({status_counts})")
    print(f"  Avg Latency:   {avg_lat} ms")
    print(f"  P50 Latency:   {p50} ms")
    print(f"  P95 Latency:   {p95} ms")
    print(f"  P99 Latency:   {p99} ms")

    return {
        "name": name,
        "total": count,
        "concurrency": concurrency,
        "rps": rps,
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "avg_ms": avg_lat,
        "success_rate": success_rate,
    }


def main() -> int:
    print("=" * 70)
    print("BUSRESERVE 2.0 — SYNTHETIC CONCURRENCY LOAD BENCHMARK")
    print(f"Target Base URL: {BASE_URL}")
    print("=" * 70)

    # Health check probe
    code, _ = make_request(f"{BASE_URL}/health/live")
    if code != 200:
        print(
            f"ERROR: Server at {BASE_URL} is not responding (status {code}).",
            file=sys.stderr,
        )
        return 1

    results = []

    # Scenario 1: Health Readiness Probe
    r1 = run_benchmark_scenario(
        "Readiness Probe (/health/ready)", f"{BASE_URL}/health/ready", 100, 15
    )
    results.append(r1)

    # Scenario 2: Dynamic City Autocomplete
    r2 = run_benchmark_scenario(
        "City Autocomplete (/api/cities?q=Bangalore)",
        f"{BASE_URL}/api/cities?q=Bangalore",
        100,
        20,
    )
    results.append(r2)

    # Scenario 3: Route Catalog
    r3 = run_benchmark_scenario(
        "Catalog Routes (/api/routes)", f"{BASE_URL}/api/routes", 100, 20
    )
    results.append(r3)

    # Scenario 4: Prometheus Metrics Scrape Endpoint
    r4 = run_benchmark_scenario(
        "Prometheus Metrics (/metrics)", f"{BASE_URL}/metrics", 50, 10
    )
    results.append(r4)

    # Scenario 5: Trip Search Query
    r5 = run_benchmark_scenario(
        "Trip Catalog (/api/trips)",
        f"{BASE_URL}/api/trips?source=Bengaluru&destination=Hyderabad",
        60,
        15,
    )
    results.append(r5)

    # Scenario 6: Seat Map Inspection
    r6 = run_benchmark_scenario(
        "Trip Seat Map (/api/trips/1/seats)", f"{BASE_URL}/api/trips/1/seats", 50, 10
    )
    results.append(r6)

    print("\n" + "=" * 70)
    print("LOAD BENCHMARK SUMMARY")
    print(
        f"{'Scenario':<35} | {'RPS':<8} | {'P50 (ms)':<9} | {'P95 (ms)':<9} | {'Success':<8}"
    )
    print("-" * 75)
    for r in results:
        print(
            f"{r['name']:<35} | {r['rps']:<8} | {r['p50_ms']:<9} | {r['p95_ms']:<9} | {r['success_rate']}%"
        )
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
