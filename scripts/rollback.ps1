param(
    [Parameter(Mandatory = $true)]
    [string]$TargetImage
)

$ErrorActionPreference = "Stop"

Write-Host "[rollback] Rolling back backend service to image: $TargetImage"
$env:BACKEND_IMAGE = $TargetImage
docker compose up -d --no-build backend
if ($LASTEXITCODE -ne 0) {
    throw "Failed to recreate backend container with image $TargetImage"
}

for ($i = 0; $i -lt 20; $i++) {
    $prevPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker exec busreserve-backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/ready', timeout=3)" *> $null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevPref
    if ($code -eq 0) {
        Write-Host "[rollback] Success: backend running on $TargetImage and /health/ready is 200."
        exit 0
    }
    Start-Sleep -Seconds 2
}

throw "Backend failed readiness check after rollback to $TargetImage"
