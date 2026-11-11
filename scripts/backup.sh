#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${POSTGRES_CONTAINER:-busreserve-postgres}"
DB_USER="${POSTGRES_USER:-busreserve}"
DB_NAME="${POSTGRES_DB:-busreserve}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DIR}/busreserve_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "[backup] Creating PostgreSQL custom-format dump at ${BACKUP_FILE}..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc --no-owner --no-acl > "${BACKUP_FILE}"

if [ ! -s "${BACKUP_FILE}" ]; then
  echo "[backup] ERROR: Backup file ${BACKUP_FILE} is empty." >&2
  exit 1
fi

echo "[backup] Verifying dump archive integrity with pg_restore --list..."
docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${BACKUP_FILE}" > /dev/null

CHECKSUM=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
echo "${CHECKSUM}  $(basename "${BACKUP_FILE}")" > "${BACKUP_FILE}.sha256"

echo "[backup] Success: ${BACKUP_FILE} (sha256: ${CHECKSUM})"
