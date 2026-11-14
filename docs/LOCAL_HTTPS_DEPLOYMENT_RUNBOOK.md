# BusReserve 2.0 — Local & VM HTTPS Deployment Runbook (Strict ₹0 / Month)

**Organization:** Algions AI Labs Private Limited  
**Role:** DevOps & Cloud Engineering  
**Project Title:** Cloud Deployment & CI/CD – Bus Booking Platform  
**Target Infrastructure Budget:** **Strict ₹0 / month** (Evaluator-Ready Local Container / VM Deployment)

---

## 1. Executive Summary & Assessment Alignment

Per the Algions AI Labs assessment specification, paid cloud hosting or dedicated AWS accounts are **NOT mandatory**. The assessment explicitly accepts local VM or containerized deployments with an Nginx reverse proxy and HTTPS termination.

This runbook documents the **primary, guaranteed zero-cost deployment mode** for BusReserve 2.0. Any evaluator can run, inspect, stress test, and audit the complete platform on their local machine or any Linux VM without incurring any cloud expenses or configuring cloud credentials.

---

## 2. Zero-Cost Architectural Topology

```mermaid
flowchart TD
    ClientHTTP["Client Browser (HTTP :8080)"] --> Nginx
    ClientHTTPS["Client Browser (HTTPS :8443 TLS 1.2/1.3)"] --> Nginx

    subgraph Host["Local Machine / Linux VM (Docker Host)"]
        subgraph DockerNet["Isolated Bridge Network (busreserve_net)"]
            Nginx["Nginx 1.27 Reverse Proxy\n(:80 & :443 internal | :8080 & :8443 host)\nTLS Termination & Security Headers"]

            Nginx -->|"/" (React SPA)| Frontend["Frontend Container (Nginx)\n(:80 internal)"]
            Nginx -->|"/api/*"\n"/health/*"\n"/metrics"| Backend["Backend API Container\n(Flask 3.1 + Gunicorn 23.0)\n(:5000 internal | non-root uid=10001)"]
            Backend -->|"SQLAlchemy / psycopg2"| Postgres[("PostgreSQL 16 Engine\n(:5432 internal | unexposed)")]
            Postgres --- Volume[("Persistent Volume\nbusreserve_pgdata")]
        end
    end
```

### Network Isolation & Port Mapping
| Service | Internal Port | Host Port | Ingress Rule | Security Profile |
| :--- | :--- | :--- | :--- | :--- |
| `nginx` | `80`, `443` | `8080`, `8443` | Exposed to host | Reverse proxy, TLS termination, HSTS/CSP |
| `backend` | `5000` | None | Internal network only | Non-root `uid=10001`, Gunicorn 4 workers |
| `frontend` | `80` | None | Internal network only | Unprivileged static web server |
| `postgres` | `5432` | None | Internal network only | Unexposed, named persistent volume |

---

## 3. Quick Start Deployment (Single Command)

### On Windows (PowerShell):
```powershell
.\scripts\setup_clean_environment.ps1
```

### On Linux / macOS (Bash):
```bash
chmod +x scripts/*.sh
./scripts/setup_clean_environment.sh
```

### Automated Steps Performed:
1. **Pre-flight Check**: Validates Docker daemon and Docker Compose availability.
2. **Secret Generation**: Creates `.env` from `.env.example` with cryptographically random 32-byte hex secrets (`SECRET_KEY`, `JWT_SECRET_KEY`).
3. **TLS Provisioning**: Automatically generates 2048-bit RSA keys and self-signed X.509 certificates with SANs for `localhost`, `127.0.0.1`, `::1` into `nginx/certs/`.
4. **Orchestrated Build**: Launches all 4 containers (`postgres`, `backend`, `frontend`, `nginx`) in detached mode with resource constraints.
5. **Readiness Polling**: Polls `/health/ready` until database and gunicorn report ready.
6. **Ingress Smoke Verification**: Confirms HTTP (`:8080`) and HTTPS (`:8443`) endpoints.

---

## 4. HTTPS & TLS Reverse Proxy Configuration

### Certificate Generation
Local TLS certificates are generated using pure Python `cryptography` or OpenSSL via [`scripts/generate_local_ssl_certs.py`](../scripts/generate_local_ssl_certs.py):
- **Key**: 2048-bit RSA (`nginx/certs/selfsigned.key`)
- **Certificate**: X.509 SHA-256 (`nginx/certs/selfsigned.crt`)
- **Subject**: `CN=localhost, O=Algions AI Labs, OU=DevOps Engineering, C=IN`
- **Validity**: 365 days
- **SANs**: `localhost`, `*.localhost`, `127.0.0.1`, `::1`

### Nginx SSL Directives ([`nginx/nginx.conf`](../nginx/nginx.conf))
```nginx
server {
    listen 80;
    listen [::]:80;
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name localhost _;

    ssl_certificate     /etc/nginx/certs/selfsigned.crt;
    ssl_certificate_key /etc/nginx/certs/selfsigned.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self';" always;
    ...
}
```

---

## 5. Live Endpoint Verification

| Target | HTTP Endpoint | HTTPS Endpoint | Expected Response |
| :--- | :--- | :--- | :--- |
| **Health Liveness** | `http://localhost:8080/health/live` | `https://localhost:8443/health/live` | `{"status":"live","service":"busreserve-backend"}` |
| **Health Readiness** | `http://localhost:8080/health/ready` | `https://localhost:8443/health/ready` | `{"database":"connected","status":"ready"}` |
| **Prometheus Metrics**| `http://localhost:8080/metrics` | `https://localhost:8443/metrics` | Prometheus metrics text format |
| **Routes API** | `http://localhost:8080/api/routes` | `https://localhost:8443/api/routes` | Active route catalog JSON |
| **Frontend UI** | `http://localhost:8080/` | `https://localhost:8443/` | React 18 SPA HTML |

### Verification Command (PowerShell / Bash):
```powershell
# Probe HTTPS readiness endpoint
curl.exe -k -i https://localhost:8443/health/ready

# Probe HTTPS Prometheus metrics
curl.exe -k -i https://localhost:8443/metrics
```

---

## 6. The Five Mandatory Company Acceptance Tests

### Test 1: Concurrency Protection (Pessimistic Locking Drill)
```powershell
python scripts/test_live_concurrency_drill.py https://localhost:8443
```
- Dispatches 10 simultaneous threads for the exact same seat over HTTPS.
- **Evidence**: Exactly 1 winner receives `HTTP 201 Created` with PNR; 9 contenders receive `HTTP 409 Conflict`. Zero duplicate bookings created in PostgreSQL.

### Test 2: Clean Environment Setup
```powershell
.\scripts\setup_clean_environment.ps1
```
- Completely automated setup from clean state in under 20 seconds.

### Test 3: CI/CD Pipeline Verification
```powershell
# Inspect the GitHub Actions workflow
cat .github/workflows/ci.yml
```
- Verifies linting, 55 tests, Trivy vulnerability scan, and image publishing to `ghcr.io`.

### Test 4: Fault Recovery Under Ingress
```powershell
# Induce failure
docker compose stop backend
# Verify Nginx gateway error
curl.exe -k -i https://localhost:8443/health/ready  # Returns 504 / 502
# Recover service
docker compose start backend
# Verify healthy within seconds
curl.exe -k -i https://localhost:8443/health/ready  # Returns 200 OK
```

### Test 5: Disaster Recovery & Rollback
```powershell
# Run automated non-destructive backup & restore drill
python scripts/verify_backup_restore.py

# Rollback container image
.\scripts\rollback.ps1 -TargetImage busreserve-backend:v1.0.0
```

---

## 7. Cost Breakdown (Actual ₹0 Verification)

| Component | Architecture Choice | Cost |
| :--- | :--- | :--- |
| Container Runtime | Local Docker Engine / Docker Compose | **₹0.00** |
| Reverse Proxy | Containerized Nginx with self-signed SAN TLS | **₹0.00** |
| Database Engine | Containerized PostgreSQL 16 on persistent volume | **₹0.00** |
| CI/CD Pipeline | GitHub Actions free tier public/private quota | **₹0.00** |
| Image Registry | GitHub Container Registry (`ghcr.io`) | **₹0.00** |
| SSL/TLS Certificates | Locally generated 2048-bit RSA X.509 certs | **₹0.00** |
| **Total Monthly Spend** | **Fully functional production-grade stack** | **₹0.00 / month** |
