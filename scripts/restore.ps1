param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$ContainerName = "busreserve-postgres",
    [string]$DbUser = $(if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "busreserve" }),
    [string]$DbName = $(if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "busreserve" }),
    [string]$TargetDb = "",
    [switch]$ConfirmOverwriteProduction
)

$ErrorActionPreference = "Stop"

$destinationDb = if ($TargetDb) { $TargetDb } else { $DbName }

if ($destinationDb -eq $DbName -and !$ConfirmOverwriteProduction) {
    Write-Host "[restore] SAFETY GUARD: Attempting to restore directly to production database '$DbName'." -ForegroundColor Yellow
    Write-Host "[restore] To overwrite the production database, you MUST specify -ConfirmOverwriteProduction." -ForegroundColor Yellow
    Write-Host "[restore] For non-destructive verification, specify -TargetDb <test_database_name>." -ForegroundColor Cyan
    throw "Aborted: -ConfirmOverwriteProduction required to restore over primary database '$DbName'."
}

if (!(Test-Path $BackupFile) -or (Get-Item $BackupFile).Length -eq 0) {
    throw "Backup file '$BackupFile' was not found or is empty."
}

$shaFile = "${BackupFile}.sha256"
if (Test-Path $shaFile) {
    Write-Host "[restore] Verifying SHA-256 checksum..."
    $expected = ((Get-Content $shaFile -TotalCount 1).Split(" ")[0]).Trim().ToLower()
    $actual = (Get-FileHash -Path $BackupFile -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) {
        throw "Checksum mismatch: expected $expected, got $actual"
    }
}

Write-Host "[restore] Verifying backup readability..."
cmd /c "docker exec -i $ContainerName pg_restore --list < `"$BackupFile`"" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Backup archive failed pg_restore --list verification."
}

if ($destinationDb -eq $DbName) {
    Write-Host "[restore] Stopping backend container during database restore..."
    docker compose stop backend | Out-Null

    Write-Host "[restore] Terminating active connections and resetting public schema on $DbName..."
    docker exec $ContainerName psql -U $DbUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DbName' AND pid <> pg_backend_pid();" | Out-Null
    docker exec $ContainerName psql -U $DbUser -d $DbName -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" | Out-Null

    Write-Host "[restore] Restoring data into $DbName..."
    cmd /c "docker exec -i $ContainerName pg_restore -U $DbUser -d $DbName --no-owner --no-acl --exit-on-error < `"$BackupFile`""
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore failed."
    }

    Write-Host "[restore] Restarting backend container and verifying readiness..."
    docker compose start backend | Out-Null

    for ($i = 0; $i -lt 20; $i++) {
        $prevPref = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        docker exec busreserve-backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health/ready', timeout=3)" *> $null
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prevPref
        if ($code -eq 0) {
            Write-Host "[restore] Verification passed: backend /health/ready returned 200."
            exit 0
        }
        Start-Sleep -Seconds 2
    }
    throw "Backend failed readiness check after database restore."
} else {
    Write-Host "[restore] Performing isolated restore into verification database '$destinationDb' (zero downtime)..."
    docker exec $ContainerName psql -U $DbUser -d postgres -c "DROP DATABASE IF EXISTS $destinationDb;" | Out-Null
    docker exec $ContainerName psql -U $DbUser -d postgres -c "CREATE DATABASE $destinationDb;" | Out-Null

    Write-Host "[restore] Restoring archive into '$destinationDb'..."
    cmd /c "docker exec -i $ContainerName pg_restore -U $DbUser -d $destinationDb --no-owner --no-acl --exit-on-error < `"$BackupFile`""
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore failed into isolated database '$destinationDb'."
    }

    Write-Host "[restore] Verifying table counts in '$destinationDb'..."
    docker exec $ContainerName psql -U $DbUser -d $destinationDb -c "SELECT count(*) AS total_bookings FROM bookings;"
    docker exec $ContainerName psql -U $DbUser -d $destinationDb -c "SELECT count(*) AS total_trips FROM trips;"
    Write-Host "[restore] Isolated restore verification completed successfully for '$destinationDb'." -ForegroundColor Green
}
