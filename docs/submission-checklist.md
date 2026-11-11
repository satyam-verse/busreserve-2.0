# BusReserve Submission Checklist

**Organization:** ALGIONS AI LABS PRIVATE LIMITED  
**Role:** DevOps & Cloud Engineering  
**Project Title:** Cloud Deployment & CI/CD – Bus Booking Platform  
**Assessment Deadline:** November 15, 2026

---

## 1. Repository & CI/CD Metadata

- **Repository URL:** `<PENDING_GITHUB_REMOTE_URL — configure remote and push with approval>`
- **Primary Branch:** `master` (or `main` once pushed to GitHub; `.github/workflows/ci.yml` supports both `main` and `master`)
- **Final Commit ID:** `<PENDING_INITIAL_COMMIT — workspace currently uncommitted locally>`
- **CI Pipeline Run URL:** `<PENDING_GITHUB_PUSH — runs automatically on push/PR to main or master>`
- **Local Container Image Tags & IDs (Verified Locally):**
  - `busreserve-backend:local` — `sha256:dc17b0d624d7b0d4585da717ce594e5db0bcaadefb1c04d9632facdfe95abd9c` (non-root `uid=10001(appuser)`)
  - `busreserve-frontend:local` — `sha256:2e41a80d9e494d4e66bb7b6073865dae7c9df7a958527b09afdcba649bebb75f`
  - **GHCR Published Image Tag / Digest:** `<PENDING_GITHUB_PUSH_TO_PRIMARY_BRANCH>`

---

## 2. Deployment Evidence

Executed `docker compose up --build -d` and verified with `docker compose ps`:

```text
NAME                  IMAGE                       COMMAND                  SERVICE    STATUS
busreserve-backend    busreserve-backend:local    "/app/entrypoint.sh"     backend    Up (healthy)
busreserve-frontend   busreserve-frontend:local   "/docker-entrypoint.…"   frontend   Up (healthy)
busreserve-nginx      nginx:1.27-alpine           "/docker-entrypoint.…"   nginx      Up (healthy)  0.0.0.0:8080->80/tcp
busreserve-postgres   postgres:16-alpine          "docker-entrypoint.s…"   postgres   Up (healthy)
```

End-to-end Nginx ingress smoke verification (`http://localhost:8080`):
- `GET /` -> `200 OK` (React SPA served)
- `GET /api/routes` -> `200 OK` (`count=5`)
- `GET /api/trips?source=Patna&destination=Ranchi` -> `200 OK` (`found=8`)
- `POST /api/bookings` -> `201 Created` (`PNR=BR52SADG4L`), duplicate `POST /api/bookings` -> `409 Conflict`
- `GET /api/bookings/BR52SADG4L` -> `200 OK` (`CONFIRMED`), `POST /api/bookings/BR52SADG4L/cancel` -> `200 OK` (`CANCELLED`)
- `GET /api/admin/overview` -> `200 OK` (`demo_only=true`, `trips=42`, masked passenger PII)

---

## 3. Health Check & Observability Recovery Evidence

- **Liveness probe (`GET http://localhost:8080/health/live`):** `200 OK` (`{"status":"alive","service":"busreserve-api","request_id":"..."}`)
- **Readiness probe (`GET http://localhost:8080/health/ready`):** `200 OK` (`{"status":"ready","database":"connected","request_id":"..."}`)
- **Non-root container verification (`docker exec busreserve-backend id`):** `uid=10001(appuser) gid=10001(appgroup) groups=10001(appgroup)`
- **Failure & recovery drill (`docker compose stop backend` -> probe -> `docker compose start backend`):**
  - Baseline `/health/ready`: `HTTP 200`
  - After `docker compose stop backend`: Nginx returned `504 Gateway Time-out`
  - After `docker compose start backend`: `busreserve-backend` returned to `(healthy)` and `/health/ready` returned `HTTP 200`

---

## 4. Backup, Restore & Rollback Evidence

1. Created booking `PNR=BRJVA4M6MW` (`Meera Joshi`, seat `1A`) via `POST http://localhost:8080/api/bookings`.
2. Executed `.\scripts\backup.ps1`:
   - Archive: `.\backups\busreserve_20261111T073427Z.dump`
   - Verified `pg_restore --list`
   - SHA-256: `e9231481a0e35466aa702150578b4394b0810d8ba301e05d68fabf7b63a487a2`
3. Simulated data loss via `DELETE FROM bookings WHERE pnr = 'BRJVA4M6MW';` and confirmed `GET /api/bookings/BRJVA4M6MW` returned `404`.
4. Executed `.\scripts\restore.ps1 -BackupFile .\backups\busreserve_20261111T073427Z.dump`:
   - Checksum verified, backend stopped, schema recreated, dump restored, backend restarted, `/health/ready` returned `200`.
   - `GET http://localhost:8080/api/bookings/BRJVA4M6MW` returned `200 OK` (`Meera Joshi`, `CONFIRMED`).
5. Executed rollback drill (`.\scripts\rollback.ps1 -TargetImage busreserve-backend:v1.0.0` and restored back to `busreserve-backend:local`):
   - Verified container image switch via `docker inspect` and `/health/ready` returning `200`.

---

## 5. Automated Testing & Concurrency Test Output

Executed against live PostgreSQL 16 (`pytest 9.0.3`, `Flask 3.1.3`, `ruff 0.8.4`, `pip-audit 2.7.3`):

```text
16 passed in 6.16s
- tests/test_bookings.py (5 passed)
- tests/test_concurrency.py::test_concurrent_api_bookings_allow_only_single_winner PASSED
- tests/test_concurrency.py::test_postgres_partial_unique_index_enforced_across_independent_sessions PASSED
- tests/test_health.py (3 passed)
- tests/test_routes_and_trips.py (6 passed)
```

Live Nginx -> Gunicorn -> PostgreSQL concurrent race verification (`http://localhost:8080/api/bookings`):
- 8 synchronized concurrent threads targeting the same seat: **1 HTTP `201 Created` (`BRBFDRM83M`)**, **7 HTTP `409 Conflict`**.

Static & vulnerability checks:
- `ruff check .` -> `All checks passed!`
- `ruff format --check .` -> `29 files already formatted`
- `pip-audit` -> `No known vulnerabilities found`
- `npm run build` (`frontend`) -> `vite v6.4.6` built production bundle cleanly

---

## 6. Demo Video Link

- **Demo Video Link:** `<PENDING_RECORDING>`

---

## 7. AI Usage Declaration

- Built using **Google Antigravity** AI coding assistant for scaffolding, backend/frontend implementation, Docker/Nginx/CI configuration, automated test authoring, and documentation, with all runtime tests, container builds, observability drills, and backup/restore/rollback workflows executed and verified locally.

---

## 8. Known Limitations

1. **Local HTTP only by default:** Docker Compose runs HTTP on port `8080`; production TLS requires a valid domain and certificates using [nginx.https.conf.example](../nginx/nginx.https.conf.example).
2. **Unauthenticated Demo Admin View:** `/admin` (`GET /api/admin/overview`) has no login system per MVP scope and intentionally masks passenger PII; production deployment should place `/admin` behind authentication/RBAC.
3. **No Payment Gateway / Live GPS:** Booking confirmation simulates instant confirmation without payment processing or live bus telemetry.
4. **Remote CI/CD Execution:** `.github/workflows/ci.yml` has been authored and aligned with local test/build steps, and awaits repository push to GitHub to generate live GitHub Actions run URLs and GHCR image digests.
