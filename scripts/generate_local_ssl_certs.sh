#!/usr/bin/env bash
# Shell script to generate self-signed TLS certificates for local HTTPS reverse proxy.
set -euo pipefail

OUTPUT_DIR="${1:-nginx/certs}"
mkdir -p "${OUTPUT_DIR}"

CERT_PATH="${OUTPUT_DIR}/selfsigned.crt"
KEY_PATH="${OUTPUT_DIR}/selfsigned.key"

echo "==> Generating Local SSL/TLS Certificates for Nginx..."

# Check if certificates already exist
if [[ -f "${CERT_PATH}" && -f "${KEY_PATH}" ]]; then
    echo "--> Existing certificates found at ${OUTPUT_DIR}. Preserving them."
    exit 0
fi

# Try using running backend container
if docker ps --format '{{.Names}}' | grep -q "busreserve-backend"; then
    echo "--> Generating via busreserve-backend Python runtime..."
    cat scripts/generate_local_ssl_certs.py | docker exec -i busreserve-backend python - /tmp/nginx_certs
    docker cp busreserve-backend:/tmp/nginx_certs/selfsigned.crt "${CERT_PATH}"
    docker cp busreserve-backend:/tmp/nginx_certs/selfsigned.key "${KEY_PATH}"
    echo "--> Certificates extracted to ${OUTPUT_DIR}"
    exit 0
fi

# Fallback 1: Local Python
if python3 -c "import cryptography" &>/dev/null; then
    echo "--> Generating via local python3..."
    python3 scripts/generate_local_ssl_certs.py "${OUTPUT_DIR}"
    exit 0
fi

# Fallback 2: OpenSSL
if command -v openssl &>/dev/null; then
    echo "--> Generating via openssl CLI..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${KEY_PATH}" -out "${CERT_PATH}" \
        -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Algions AI Labs/OU=DevOps/CN=localhost"
    exit 0
fi

echo "ERROR: Unable to generate TLS certificates. Ensure Docker, Python cryptography, or OpenSSL is installed." >&2
exit 1
