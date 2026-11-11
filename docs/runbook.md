# BusReserve Operations Runbook

## 1. Deploy / Start Stack

```powershell
# Optional: create .env from template and customize secrets
Copy-Item .env.example .env

# Build images and start postgres, backend, frontend, nginx
docker compose up --build -d

# Check container status and health checks
docker compose ps
```

## 2. Stop & Restart Services

```powershell
# Restart backend cleanly
docker compose restart backend

# Stop and remove containers (preserves busreserve_pgdata volume)
docker compose down
```

## 3. View Structured Logs

```powershell
# Stream backend JSON logs
docker compose logs -f --tail=100 backend

# Filter errors or specific request_id
docker compose logs backend | Select-String '"level": "ERROR"'

# Inspect Nginx reverse proxy access/error logs
docker compose logs -f --tail=100 nginx
```

## 4. Health & Readiness Checks

```powershell
# Liveness (process is responsive)
curl.exe -i http://localhost:8080/health/live

# Readiness (PostgreSQL SELECT 1 succeeds)
curl.exe -i http://localhost:8080/health/ready
```

Expected statuses:
- `/health/live` -> `200 OK` (`{"status": "alive", ...}`)
- `/health/ready` -> `200 OK` (`{"status": "ready", "database": "connected"}`) or `503 Service Unavailable` when PostgreSQL is unreachable.

## 5. Database Backup & Verification

**Windows (PowerShell):**
```powershell
.\scripts\backup.ps1
```

**Linux / macOS (Bash):**
```bash
./scripts/backup.sh
```

What it does:
1. Executes `pg_dump -Fc --no-owner --no-acl` inside `busreserve-postgres`.
2. Saves a timestamped archive under `./backups/busreserve_<UTC>.dump`.
3. Validates archive structure via `pg_restore --list`.
4. Writes a `.sha256` checksum file alongside the dump.

## 6. Database Restore & Recovery Verification

**Windows (PowerShell):**
```powershell
.\scripts\restore.ps1 -BackupFile .\backups\busreserve_<timestamp>.dump
```

**Linux / macOS (Bash):**
```bash
./scripts/restore.sh ./backups/busreserve_<timestamp>.dump
```

What it does:
1. Verifies file existence, SHA-256 checksum, and `pg_restore --list` readability.
2. Stops `backend` to prevent concurrent writes during schema replacement.
3. Terminates active PostgreSQL sessions on the target DB and recreates `public` schema.
4. Restores the custom-format dump with `--exit-on-error`.
5. Starts `backend` and polls `/health/ready` inside the container until HTTP `200` succeeds.

## 7. Image Rollback Procedure

Tag stable images before releasing updates:

```powershell
docker tag busreserve-backend:local busreserve-backend:v1.0.0
```

To roll back to a previous local tag or GHCR SHA/digest:

**Windows (PowerShell):**
```powershell
.\scripts\rollback.ps1 -TargetImage busreserve-backend:v1.0.0
```

**Linux / macOS (Bash):**
```bash
./scripts/rollback.sh ghcr.io/<owner>/busreserve-backend@sha256:<digest>
```

The script switches `BACKEND_IMAGE`, recreates only `backend` with `--no-build`, and verifies `/health/ready` returns `200`.

## 8. Incident Response: Backend Failure & Recovery

1. **Detect failure**: Monitor `docker compose ps -a` (`unhealthy` / `Exited`) or probe `http://localhost:8080/health/ready` (returns `504`/`502` from Nginx when backend container is down, `503` when DB is down).
2. **Inspect diagnostics**:
   ```powershell
   docker compose ps
   docker compose logs --tail=100 backend
   docker compose logs --tail=50 postgres
   ```
3. **Recover service**:
   ```powershell
   docker compose up -d backend
   ```
4. **Confirm recovery**:
   - `docker compose ps` reports `busreserve-backend` as `(healthy)`.
   - `curl.exe -i http://localhost:8080/health/ready` returns `200 OK`.
   - Smoke-test read/write endpoint: `curl.exe http://localhost:8080/api/routes`.
