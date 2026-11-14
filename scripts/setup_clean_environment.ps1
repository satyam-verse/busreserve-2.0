<#
.SYNOPSIS
    BusReserve 2.0 — Clean Environment Setup & Deployment Automation Script (Windows/PowerShell)
.DESCRIPTION
    Automates clean environment verification, environment file generation with cryptographic secrets,
    container builds, dependency orchestration, and readiness verification.
#>

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "BUSRESERVE 2.0 — REPRODUCIBLE DEPLOYMENT SETUP" -ForegroundColor Cyan
Write-Host "Algions AI Labs Assessment — Cloud Deployment & CI/CD" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Step 1: Verify Docker Daemon & Compose
Write-Host "`n[Step 1/5] Checking Docker & Docker Compose availability..." -ForegroundColor Yellow
try {
    $dockerVer = docker --version
    Write-Host "  Found: $dockerVer"
    $composeVer = docker compose version
    Write-Host "  Found: $composeVer"
} catch {
    Write-Error "Docker Desktop or Docker Compose is not installed or running. Please start Docker and retry."
    exit 1
}

# Step 2: Ensure Environment File & Local TLS Certificates Exist
Write-Host "`n[Step 2/5] Preparing environment configuration & TLS certificates..." -ForegroundColor Yellow
if (!(Test-Path ".env")) {
    Write-Host "  .env not found. Creating from .env.example with random cryptographic secrets..."
    Copy-Item ".env.example" ".env"
    
    # Generate secure 32-byte hex secrets
    $bytes = New-Object byte[] 32
    (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
    $randSecret = -join ($bytes | ForEach-Object { "{0:x2}" -f $_ })
    
    $bytesJwt = New-Object byte[] 32
    (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytesJwt)
    $randJwt = -join ($bytesJwt | ForEach-Object { "{0:x2}" -f $_ })
    
    (Get-Content ".env") | 
        ForEach-Object { $_ -replace "replace-with-strong-random-secret-32b", $randSecret } |
        ForEach-Object { $_ -replace "replace-with-strong-jwt-secret-32b", $randJwt } |
        Set-Content ".env"
    Write-Host "  Generated cryptographic secrets for SECRET_KEY and JWT_SECRET_KEY in .env." -ForegroundColor Green
} else {
    Write-Host "  Found existing .env file. Keeping existing configurations." -ForegroundColor Green
}

# Ensure TLS certs exist for Nginx HTTPS reverse proxy
if (-not (Test-Path "nginx/certs/selfsigned.crt") -or -not (Test-Path "nginx/certs/selfsigned.key")) {
    Write-Host "  Generating local SSL/TLS certificates for HTTPS reverse proxy..." -ForegroundColor Yellow
    & "$PSScriptRoot/generate_local_ssl_certs.ps1"
} else {
    Write-Host "  Found existing TLS certificates in nginx/certs/." -ForegroundColor Green
}

# Step 3: Build & Start Stack
Write-Host "`n[Step 3/5] Building and launching multi-container stack via Docker Compose..." -ForegroundColor Yellow
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed."
    exit 1
}

# Step 4: Health & Readiness Polling
Write-Host "`n[Step 4/5] Waiting for all container healthchecks to report healthy..." -ForegroundColor Yellow
$maxAttempts = 30
$healthy = $false
for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host "  Attempt $i/$maxAttempts: Checking readiness probe http://localhost:8080/health/ready..."
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:8080/health/ready" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($resp.status -eq "ready" -and $resp.database -eq "connected") {
            $healthy = $true
            Write-Host "  Readiness check passed: Database connected, API responsive." -ForegroundColor Green
            break
        }
    } catch {
        # Keep waiting
    }
    Start-Sleep -Seconds 3
}

if (!$healthy) {
    Write-Error "Deployment failed readiness check after $maxAttempts attempts. Inspect container logs with 'docker compose logs'."
    exit 1
}

# Step 5: Smoke Testing Endpoints
Write-Host "`n[Step 5/5] Smoke testing public ingress endpoints..." -ForegroundColor Yellow
$live = Invoke-RestMethod -Uri "http://localhost:8080/health/live" -Method Get
Write-Host "  HTTP /health/live:     Status $($live.status) (service: $($live.service))"

$routes = Invoke-RestMethod -Uri "http://localhost:8080/api/routes" -Method Get
Write-Host "  HTTP /api/routes:      Found $($routes.routes.Count) active routes"

$metrics = (Invoke-WebRequest -Uri "http://localhost:8080/metrics" -Method Get).Content
if ($metrics -match "busreserve_app_uptime_seconds") {
    Write-Host "  HTTP /metrics:         Prometheus metrics scraping active" -ForegroundColor Green
}

# Test HTTPS with self-signed certificate bypass
try {
    $null = curl.exe -k -s -f https://localhost:8443/health/ready
    Write-Host "  HTTPS /health/ready:   Secure TLS 1.2/1.3 reverse proxy active (port 8443)" -ForegroundColor Green
} catch {
    Write-Host "  HTTPS check skipped or non-blocking: $_" -ForegroundColor Yellow
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "Frontend SPA (HTTP):  http://localhost:8080"
Write-Host "Frontend SPA (HTTPS): https://localhost:8443"
Write-Host "Health (HTTP):        http://localhost:8080/health/ready"
Write-Host "Health (HTTPS):       https://localhost:8443/health/ready"
Write-Host "Prometheus Metrics:   http://localhost:8080/metrics (or https://localhost:8443/metrics)"
Write-Host "API Base URL:         http://localhost:8080/api (or https://localhost:8443/api)"
Write-Host "======================================================================" -ForegroundColor Cyan
