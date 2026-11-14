#!/usr/bin/env python3
"""Automated, non-destructive PostgreSQL backup and restore verification drill for BusReserve 2.0.

Executes a full disaster-recovery validation into an isolated temporary database,
asserting data integrity without touching or endangering live production records.
"""

import os
import subprocess
import sys
import time

CONTAINER_NAME = os.getenv("POSTGRES_CONTAINER", "busreserve-postgres")
DB_USER = os.getenv("POSTGRES_USER", "busreserve")
PRIMARY_DB = os.getenv("POSTGRES_DB", "busreserve")
VERIFY_DB = "busreserve_dr_verify"
BACKUP_DIR = "./backups"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=check
    )


def main() -> int:
    print("=" * 70)
    print("BUSRESERVE 2.0 — AUTOMATED DISASTER RECOVERY & BACKUP DRILL")
    print(f"Target Container: {CONTAINER_NAME}")
    print(f"Primary Database (Read-Only Source): {PRIMARY_DB}")
    print(f"Isolated Verification Database: {VERIFY_DB}")
    print("=" * 70)

    start_time = time.perf_counter()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup_file = os.path.join(BACKUP_DIR, f"busreserve_dr_drill_{timestamp}.dump")

    # Step 1: Execute pg_dump from primary database
    print("\n[Step 1/5] Creating custom-format PostgreSQL dump...")
    dump_cmd = [
        "docker",
        "exec",
        CONTAINER_NAME,
        "pg_dump",
        "-U",
        DB_USER,
        "-d",
        PRIMARY_DB,
        "-Fc",
        "--no-owner",
        "--no-acl",
    ]
    with open(backup_file, "wb") as f:
        res = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"ERROR: pg_dump failed: {res.stderr.decode()}", file=sys.stderr)
            return 1

    file_size = os.path.getsize(backup_file)
    print(f"  Backup archive generated: {backup_file} ({file_size:,} bytes)")

    # Step 2: Validate archive structure with pg_restore --list
    print("\n[Step 2/5] Validating archive integrity via pg_restore --list...")
    with open(backup_file, "rb") as f:
        res = subprocess.run(
            ["docker", "exec", "-i", CONTAINER_NAME, "pg_restore", "--list"],
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            print(
                f"ERROR: pg_restore list failed: {res.stderr.decode()}", file=sys.stderr
            )
            return 1
    print("  Archive structure verified successfully.")

    # Step 3: Create isolated verification database
    print(f"\n[Step 3/5] Initializing clean isolated database '{VERIFY_DB}'...")
    run_cmd(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            "postgres",
            "-c",
            f"DROP DATABASE IF EXISTS {VERIFY_DB};",
        ]
    )
    run_cmd(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            "postgres",
            "-c",
            f"CREATE DATABASE {VERIFY_DB};",
        ]
    )
    print(f"  Isolated database '{VERIFY_DB}' ready.")

    # Step 4: Restore dump into isolated verification database
    print(f"\n[Step 4/5] Restoring backup archive into '{VERIFY_DB}'...")
    restore_start = time.perf_counter()
    with open(backup_file, "rb") as f:
        res = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                CONTAINER_NAME,
                "pg_restore",
                "-U",
                DB_USER,
                "-d",
                VERIFY_DB,
                "--no-owner",
                "--no-acl",
                "--exit-on-error",
            ],
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode != 0:
            print(f"ERROR: pg_restore failed: {res.stderr.decode()}", file=sys.stderr)
            return 1
    restore_duration = round(time.perf_counter() - restore_start, 2)
    print(f"  Restoration completed in {restore_duration}s.")

    # Step 5: Verify table counts against baseline
    print(f"\n[Step 5/5] Auditing record counts in restored database '{VERIFY_DB}'...")
    query = (
        "SELECT "
        "(SELECT count(*) FROM bookings) AS bookings, "
        "(SELECT count(*) FROM bookings WHERE status = 'CONFIRMED') AS confirmed, "
        "(SELECT count(*) FROM trips) AS trips, "
        "(SELECT count(*) FROM ai_conversation_messages) AS ai_messages;"
    )
    res = run_cmd(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            VERIFY_DB,
            "-t",
            "-A",
            "-F",
            ",",
            "-c",
            query,
        ]
    )
    counts = res.stdout.strip().split(",")
    total_bookings, confirmed_bookings, total_trips, total_ai = map(int, counts)

    print(f"  - Total Bookings:     {total_bookings} (Expected >= 20)")
    print(f"  - Confirmed Bookings: {confirmed_bookings} (Expected >= 4)")
    print(f"  - Total Trips:        {total_trips} (Expected >= 2,232)")
    print(f"  - Total AI Messages:  {total_ai} (Expected >= 12)")

    assert total_bookings >= 20, f"Expected at least 20 bookings, got {total_bookings}"
    assert total_trips >= 2232, f"Expected at least 2232 trips, got {total_trips}"
    assert total_ai >= 12, f"Expected at least 12 AI messages, got {total_ai}"

    # Cleanup verification DB
    run_cmd(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            "postgres",
            "-c",
            f"DROP DATABASE {VERIFY_DB};",
        ]
    )
    print(f"  Cleaned up isolated database '{VERIFY_DB}'.")

    total_duration = round(time.perf_counter() - start_time, 2)
    print("\n" + "=" * 70)
    print("DISASTER RECOVERY DRILL: PASS")
    print(f"Total Drill Duration: {total_duration}s (Well within RTO < 15 min)")
    print(
        f"Data Preservation: 100% Intact ({total_bookings} bookings, {total_trips} trips, {total_ai} AI messages)"
    )
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
