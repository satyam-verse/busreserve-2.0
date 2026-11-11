#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backend-image:tag-or-digest>" >&2
  exit 1
fi

TARGET_IMAGE="$1"
echo "[rollback] Rolling back backend service to image: ${TARGET_IMAGE}"
BACKEND_IMAGE="${TARGET_IMAGE}" docker compose up -d --no-build backend

for _ in $(seq 1 20); do
  if docker exec busreserve-backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/ready', timeout=3)" >/dev/null 2>&1; then
    echo "[rollback] Success: backend running on ${TARGET_IMAGE} and /health/ready is 200."
    exit 0
  fi
  sleep 2
done

echo "[rollback] ERROR: Backend failed readiness check after rollback." >&2
exit 1
