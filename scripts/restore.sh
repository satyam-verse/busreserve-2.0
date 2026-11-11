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

echo "[restore] Stopping backend container to avoid active DB writes..."
docker compose stop backend

echo "[restore] Terminating active DB connections and recreating schema..."
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
