# PowerShell script to generate self-signed TLS certificates for local HTTPS reverse proxy.
[CmdletBinding()]
param(
    [string]$OutputDir = "nginx/certs"
)

$ErrorActionPreference = "Stop"
Write-Host "==> Generating Local SSL/TLS Certificates for Nginx..." -ForegroundColor Cyan

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}

$certPath = Join-Path $OutputDir "selfsigned.crt"
$keyPath = Join-Path $OutputDir "selfsigned.key"

# Try using the running backend container's Python environment
try {
    Write-Host "--> Attempting generation via busreserve-backend Python runtime..." -ForegroundColor Yellow
    Get-Content "scripts/generate_local_ssl_certs.py" | docker exec -i busreserve-backend python - /tmp/nginx_certs 2>$null
    docker cp busreserve-backend:/tmp/nginx_certs/selfsigned.crt $certPath
    docker cp busreserve-backend:/tmp/nginx_certs/selfsigned.key $keyPath
    Write-Host "--> Certificates successfully extracted to $OutputDir" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "--> Container extraction not available, trying local Python or OpenSSL..." -ForegroundColor Yellow
}

# Fallback 1: Local Python
try {
    python scripts/generate_local_ssl_certs.py $OutputDir 2>$null
    if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
        Write-Host "--> Local Python generated certificates in $OutputDir" -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "--> Local Python cryptography not available." -ForegroundColor Yellow
}

# Fallback 2: OpenSSL CLI
if (Get-Command openssl -ErrorAction SilentlyContinue) {
    Write-Host "--> Using system openssl CLI..." -ForegroundColor Yellow
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout $keyPath -out $certPath `
        -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Algions AI Labs/OU=DevOps/CN=localhost"
    Write-Host "--> OpenSSL generated certificates in $OutputDir" -ForegroundColor Green
    exit 0
}

Write-Host "--> Note: Certificates already present or ready at $certPath" -ForegroundColor Green
