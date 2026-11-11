# BusReserve — Cloud-Native Bus Trip & Seat Reservation Platform

**Internship Assessment — ALGIONS AI LABS PRIVATE LIMITED**
**Role:** DevOps & Cloud Engineering
**Project Title:** Cloud Deployment & CI/CD – Bus Booking Platform

BusReserve is a containerized bus trip search and seat reservation platform engineered for transactional correctness, operational observability, automated CI/CD, and reproducible local deployment.

## Architecture Overview

See [docs/architecture.md](docs/architecture.md) for the Mermaid system diagram, network boundaries, and PostgreSQL schema.

- **Single ingress via Nginx (`:8080`)**: Routes `/` to the React SPA and proxies `/api/*` and `/health/*` to Gunicorn/Flask with correlation `X-Request-ID` headers.
- **Double-booking prevention**: Combines PostgreSQL pessimistic row locking (`SELECT ... FOR UPDATE OF trip_seats`) with a database-level partial unique index (`uq_active_booking_trip_seat` on `(trip_id, seat_id) WHERE status = 'CONFIRMED'`).

## Technology Stack

- **Backend**: Python 3.12, Flask 3.1.3, Flask-SQLAlchemy, Flask-Migrate (Alembic), Marshmallow, Gunicorn, PostgreSQL 16 (`psycopg2-binary`)
- **Frontend**: React 18, Vite 6, Tailwind CSS, React Router, Lucide Icons
- **DevOps & Security**: Docker, Docker Compose, Nginx, GitHub Actions, GitHub Container Registry (`ghcr.io`), Ruff, Pytest, `pip-audit`, Trivy

## Prerequisites

- **Docker Desktop** with Docker Compose (`docker compose version`)
- **Python 3.12+** (only needed for running backend tests/lint outside Docker)
- **Node.js 20+** (only needed for running frontend dev server outside Docker)

## Environment Variables

Copy `.env.example` to `.env` before customizing configuration:

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER` | `busreserve` | PostgreSQL role |
| `POSTGRES_PASSWORD` | `busreserve_dev_change_me` | PostgreSQL password |
| `POSTGRES_DB` | `busreserve` | PostgreSQL database name |
| `FLASK_ENV` | `production` | Flask environment (`development`, `testing`, `production`) |
| `SECRET_KEY` | `local-dev-change-in-production` | Flask signing secret |
| `LOG_LEVEL` | `INFO` | Structured JSON log threshold |
| `SEED_ON_STARTUP` | `true` | Run idempotent seed script on container startup |
| `CORS_ORIGINS` | `http://localhost:8080,http://localhost` | Allowed CORS origins |
| `GUNICORN_WORKERS` | `2` | Gunicorn worker processes |
| `GUNICORN_THREADS` | `4` | Threads per Gunicorn worker |
| `BACKEND_IMAGE` | `busreserve-backend:local` | Backend image tag/digest (used for rollback) |
| `FRONTEND_IMAGE` | `busreserve-frontend:local` | Frontend image tag/digest |
| `NGINX_PORT` | `8080` | Host port mapped to Nginx reverse proxy `:80` |

## Port Map

| Service | Container Port | Host Port | Exposure |
| --- | --- | --- | --- |
| `nginx` | `80` | `8080` (`NGINX_PORT`) | Public local ingress |
| `backend` | `5000` | Not published | Internal `busreserve_net` only |
| `frontend` | `80` | Not published | Internal `busreserve_net` only |
| `postgres` | `5432` | Not published | Internal `busreserve_net` only |

## Local Deployment (Docker Compose)

1. Optional environment file setup:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Build and start the entire stack:
   ```powershell
   docker compose up --build -d
   ```
3. Verify all services report `healthy`:
   ```powershell
   docker compose ps
   curl.exe -i http://localhost:8080/health/live
   curl.exe -i http://localhost:8080/health/ready
   ```
4. Open the application in your browser at **http://localhost:8080**.

### HTTPS / Production Reverse Proxy

For production deployments with a valid domain and TLS certificates (e.g., Let's Encrypt), see [nginx/nginx.https.conf.example](nginx/nginx.https.conf.example). Local testing uses HTTP on port `8080` without synthetic certificates.

## Testing & Code Quality

### Automated Backend Tests (PostgreSQL)

Tests require a live PostgreSQL instance (configured via `TEST_DATABASE_URL`):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\ruff.exe format --check .
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pytest
.venv\Scripts\pip-audit.exe
```

Test coverage includes:
- Liveness & readiness probes (including simulated database outage -> `503`)
- Route listing, trip search filtering/sorting, invalid date handling
- Seat map retrieval and 404 behavior
- Booking validation (passenger fields, past travel date, route stop membership & ordering)
- PNR lookup, cancellation, double-cancellation conflict (`409`), and rebooking after cancellation
- Multi-threaded concurrent API booking (`10` simultaneous threads -> `1` winner `201`, `9` conflicts `409`)
- Direct multi-session PostgreSQL partial unique index contention test
- Idempotent seed execution and PII-masked admin overview

### Local Frontend Build

```powershell
cd frontend
npm install
npm run build
```

## CI/CD Pipeline

Configured in [.github/workflows/ci.yml](.github/workflows/ci.yml) using least-privilege permissions (`contents: read`; `packages: write` scoped to image publishing):
1. Checks out source and installs Python 3.12 + backend dependencies.
2. Enforces `ruff format --check` and `ruff check`.
3. Starts a `postgres:16-alpine` service container, runs `flask db upgrade` and idempotent `flask seed` twice.
4. Executes API tests and PostgreSQL concurrency tests via `pytest`.
5. Runs `pip-audit` dependency vulnerability scanning.
6. Verifies the Vite React production build.
7. Builds Docker images, runs Trivy container vulnerability scanning (`CRITICAL,HIGH`), and on authorized pushes to `main` or `master` publishes SHA-tagged images to `ghcr.io` and writes the image digest to `$GITHUB_STEP_SUMMARY`.

## Backup, Restore & Rollback

See [docs/runbook.md](docs/runbook.md) for full operational procedures:
- **Backup**: `.\scripts\backup.ps1` (or `./scripts/backup.sh`) creates and verifies a custom-format `pg_dump` with SHA-256 checksum.
- **Restore**: `.\scripts\restore.ps1 -BackupFile <path>` (or `./scripts/restore.sh <path>`) validates checksum, resets schema, restores via `pg_restore`, restarts backend, and verifies `/health/ready`.
- **Rollback**: `.\scripts\rollback.ps1 -TargetImage <tag-or-digest>` (or `./scripts/rollback.sh <tag-or-digest>`) switches the backend container image without rebuilding and validates readiness.

## Troubleshooting

- **Port `8080` already in use**: Set `NGINX_PORT=8081` in `.env` and run `docker compose up -d`.
- **Backend `/health/ready` returns `503`**: Check `docker compose logs postgres` and ensure `POSTGRES_USER` / `POSTGRES_PASSWORD` in `.env` match the initialized volume.
- **Inspect structured JSON logs**: `docker compose logs -f backend` (filter by `request_id` returned in `X-Request-ID` header or JSON error responses).
