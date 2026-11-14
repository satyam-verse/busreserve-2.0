#!/usr/bin/env bash
# BusReserve 2.0 — Clean Environment Setup & Deployment Automation Script (Linux/macOS)
set -euo pipefail

echo "======================================================================"
echo "BUSRESERVE 2.0 — REPRODUCIBLE DEPLOYMENT SETUP"
echo "Algions AI Labs Assessment — Cloud Deployment & CI/CD"
echo "======================================================================"

# Step 1: Verify Docker & Compose
echo -e "\n[Step 1/5] Checking Docker & Docker Compose availability..."
docker --version
docker compose version

# Step 2: Ensure Environment File & Local TLS Certificates Exist
echo -e "\n[Step 2/5] Preparing environment configuration & TLS certificates..."
if [ ! -f ".env" ]; then
    echo "  .env not found. Creating from .env.example with random cryptographic secrets..."
    cp .env.example .env
    RAND_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    RAND_JWT=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i.bak "s/replace-with-strong-random-secret-32b/${RAND_SECRET}/" .env && rm -f .env.bak
    sed -i.bak "s/replace-with-strong-jwt-secret-32b/${RAND_JWT}/" .env && rm -f .env.bak
    echo "  Generated cryptographic secrets for SECRET_KEY and JWT_SECRET_KEY in .env."
else
    echo "  Found existing .env file. Keeping existing configurations."
fi

# Ensure TLS certs exist for Nginx HTTPS reverse proxy
if [ ! -f "nginx/certs/selfsigned.crt" ] || [ ! -f "nginx/certs/selfsigned.key" ]; then
    echo "  Generating local SSL/TLS certificates for HTTPS reverse proxy..."
    bash scripts/generate_local_ssl_certs.sh
else
    echo "  Found existing TLS certificates in nginx/certs/."
fi

# Step 3: Build & Start Stack
echo -e "\n[Step 3/5] Building and launching multi-container stack via Docker Compose..."
docker compose up --build -d

# Step 4: Health & Readiness Polling
echo -e "\n[Step 4/5] Waiting for all container healthchecks to report healthy..."
MAX_ATTEMPTS=30
HEALTHY=false
for i in $(seq 1 ${MAX_ATTEMPTS}); do
    echo "  Attempt ${i}/${MAX_ATTEMPTS}: Checking readiness probe http://localhost:8080/health/ready..."
    if curl -s -f -m 3 http://localhost:8080/health/ready >/dev/null 2>&1; then
        HEALTHY=true
        echo "  Readiness check passed: Database connected, API responsive."
        break
    fi
    sleep 3
done

if [ "${HEALTHY}" != "true" ]; then
    echo "ERROR: Deployment failed readiness check after ${MAX_ATTEMPTS} attempts." >&2
    exit 1
fi

# Step 5: Smoke Testing Endpoints
echo -e "\n[Step 5/5] Smoke testing public ingress endpoints..."
curl -s http://localhost:8080/health/live
echo ""
curl -s http://localhost:8080/api/routes | grep -q "routes" && echo "  HTTP /api/routes: Verified"
curl -s http://localhost:8080/metrics | grep -q "busreserve_app_uptime_seconds" && echo "  HTTP /metrics: Verified"
curl -k -s -f https://localhost:8443/health/ready >/dev/null 2>&1 && echo "  HTTPS /health/ready: Verified (TLS 1.2/1.3 reverse proxy on port 8443)"

echo -e "\n======================================================================"
echo "DEPLOYMENT SUCCESSFUL!"
echo "Frontend SPA (HTTP):  http://localhost:8080"
echo "Frontend SPA (HTTPS): https://localhost:8443"
echo "Health (HTTP):        http://localhost:8080/health/ready"
echo "Health (HTTPS):       https://localhost:8443/health/ready"
echo "Prometheus Metrics:   http://localhost:8080/metrics (or https://localhost:8443/metrics)"
echo "API Base URL:         http://localhost:8080/api (or https://localhost:8443/api)"
echo "======================================================================"
