#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup-file.dump>" >&2
  exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="${POSTGRES_CONTAINER:-busreserve-postgres}"
DB_USER="${POSTGRES_USER:-busreserve}"
DB_NAME="${POSTGRES_DB:-busreserve}"
TARGET_DB="${TARGET_DB:-}"
CONFIRM_OVERWRITE="${CONFIRM_OVERWRITE_PRODUCTION:-false}"

DEST_DB="${TARGET_DB:-${DB_NAME}}"

if [ "${DEST_DB}" = "${DB_NAME}" ] && [ "${CONFIRM_OVERWRITE}" != "true" ]; then
  echo "[restore] SAFETY GUARD: Attempting to restore directly to primary database '${DB_NAME}'." >&2
  echo "[restore] Set CONFIRM_OVERWRITE_PRODUCTION=true to confirm overwriting the primary database." >&2
  echo "[restore] Or set TARGET_DB=<isolated_db_name> for safe, isolated restoration verification." >&2
  exit 1
fi

if [ ! -s "${BACKUP_FILE}" ]; then
  echo "[restore] ERROR: Backup file '${BACKUP_FILE}' not found or empty." >&2
  exit 1
fi

if [ -f "${BACKUP_FILE}.sha256" ]; then
  echo "[restore] Verifying SHA-256 checksum..."
  (cd "$(dirname "${BACKUP_FILE}")" && sha256sum -c "$(basename "${BACKUP_FILE}.sha256")")
fi

echo "[restore] Verifying backup readability..."
docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${BACKUP_FILE}" > /dev/null

if [ "${DEST_DB}" = "${DB_NAME}" ]; then
  echo "[restore] Stopping backend container to avoid active DB writes..."
  docker compose stop backend

  echo "[restore] Terminating active DB connections and recreating schema on ${DB_NAME}..."
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null

  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c \
    "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

  echo "[restore] Restoring data into ${DB_NAME}..."
  docker exec -i "${CONTAINER_NAME}" pg_restore -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl --exit-on-error < "${BACKUP_FILE}"

  echo "[restore] Starting backend container and verifying health..."
  docker compose start backend

  for _ in $(seq 1 20); do
    if docker exec busreserve-backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/ready', timeout=3)" >/dev/null 2>&1; then
      echo "[restore] Verification passed: backend /health/ready returned 200."
      exit 0
    fi
    sleep 2
  done

  echo "[restore] ERROR: Backend failed readiness check after restore." >&2
  exit 1
else
  echo "[restore] Performing isolated restore into verification database '${DEST_DB}' (zero downtime)..."
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DEST_DB};" >/dev/null
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DEST_DB};" >/dev/null

  echo "[restore] Restoring archive into '${DEST_DB}'..."
  docker exec -i "${CONTAINER_NAME}" pg_restore -U "${DB_USER}" -d "${DEST_DB}" --no-owner --no-acl --exit-on-error < "${BACKUP_FILE}"

  echo "[restore] Verifying table counts in '${DEST_DB}'..."
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DEST_DB}" -c "SELECT count(*) AS total_bookings FROM bookings;"
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DEST_DB}" -c "SELECT count(*) AS total_trips FROM trips;"
  echo "[restore] Isolated restore verification completed successfully for '${DEST_DB}'."
fi
