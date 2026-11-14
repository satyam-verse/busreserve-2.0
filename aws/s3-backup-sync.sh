#!/usr/bin/env bash
# BusReserve 2.0 — Automated S3 Database Backup & Off-Site Synchronization
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-busreserve-postgres}"
DB_USER="${POSTGRES_USER:-busreserve}"
DB_NAME="${POSTGRES_DB:-busreserve}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DIR}/busreserve_${TIMESTAMP}.dump"
mkdir -p "${BACKUP_DIR}"

echo "[s3-backup] Creating custom-format PostgreSQL dump..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc --no-owner --no-acl > "${BACKUP_FILE}"

if [ ! -s "${BACKUP_FILE}" ]; then
    echo "[s3-backup] ERROR: Backup file ${BACKUP_FILE} is empty." >&2
    exit 1
fi

echo "[s3-backup] Verifying archive integrity with pg_restore --list..."
docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${BACKUP_FILE}" > /dev/null

CHECKSUM=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
echo "${CHECKSUM}  $(basename "${BACKUP_FILE}")" > "${BACKUP_FILE}.sha256"
echo "[s3-backup] Local backup verified: ${BACKUP_FILE} (SHA-256: ${CHECKSUM})"

# Off-site S3 sync if S3_BACKUP_BUCKET is configured and aws CLI is available
if [ -n "${S3_BUCKET}" ] && command -v aws >/dev/null 2>&1; then
    echo "[s3-backup] Uploading backup to Amazon S3 (s3://${S3_BUCKET}/)..."
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/$(basename "${BACKUP_FILE}")" --sse AES256
    aws s3 cp "${BACKUP_FILE}.sha256" "s3://${S3_BUCKET}/$(basename "${BACKUP_FILE}.sha256")"
    echo "[s3-backup] S3 sync completed successfully."
else
    echo "[s3-backup] S3 sync skipped (S3_BACKUP_BUCKET not set or aws CLI not installed). Local archive preserved."
fi
