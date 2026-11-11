param(
    [string]$ContainerName = "busreserve-postgres",
    [string]$DbUser = $(if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "busreserve" }),
    [string]$DbName = $(if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "busreserve" }),
    [string]$BackupDir = ".\backups"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$backupFile = Join-Path $BackupDir "busreserve_${timestamp}.dump"

Write-Host "[backup] Creating PostgreSQL custom-format dump at $backupFile..."
$cmd = "docker exec $ContainerName pg_dump -U $DbUser -d $DbName -Fc --no-owner --no-acl > `"$backupFile`""
cmd /c $cmd
if ($LASTEXITCODE -ne 0 -or !(Test-Path $backupFile) -or (Get-Item $backupFile).Length -eq 0) {
    throw "Backup failed or produced empty file: $backupFile"
}

Write-Host "[backup] Verifying dump archive integrity with pg_restore --list..."
cmd /c "docker exec -i $ContainerName pg_restore --list < `"$backupFile`"" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Backup verification failed for $backupFile"
}

$hash = (Get-FileHash -Path $backupFile -Algorithm SHA256).Hash.ToLower()
"$hash  $(Split-Path $backupFile -Leaf)" | Set-Content -Path "${backupFile}.sha256"

Write-Host "[backup] Success: $backupFile (sha256: $hash)"
Write-Output $backupFile
