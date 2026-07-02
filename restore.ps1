$ErrorActionPreference = "Stop"

$ZipFile = $args[0]

if (-not $ZipFile) {
    Write-Host "Usage: .\restore.ps1 .\backups\20260612_150000_MKT_Helpdesk_Backup.zip" -ForegroundColor Red
    exit 1
}

if (!(Test-Path $ZipFile)) {
    Write-Host "Error: Backup file $ZipFile not found!" -ForegroundColor Red
    exit 1
}

$TempDir = "backups\restore_temp"
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }

Write-Host "MKT Helpdesk AI - Disaster Recovery Restore System" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Extracting $ZipFile..."
Expand-Archive -Path $ZipFile -DestinationPath $TempDir -Force

Write-Host "Checking containers..."
$containers = docker ps --format "{{.Names}}"
if ($containers -notmatch "mkt_postgres" -or $containers -notmatch "zammad-zammad-postgresql-1") {
    Write-Host "Error: Docker containers are not running! Please run 'docker-compose up -d' first." -ForegroundColor Red
    Remove-Item -Recurse -Force $TempDir
    exit 1
}

# 1. Restore Backend Database
Write-Host "[1/4] Restoring Backend Database..."
docker cp $TempDir\backend_db.dump mkt_postgres:/tmp/backend_db.dump
# Drop and Recreate DB requires a trick or we just use -c (clean) to drop objects before creating.
docker exec mkt_postgres pg_restore -U mkt_user -d helpdesk_mkt -1 -c -F c /tmp/backend_db.dump
docker exec mkt_postgres rm /tmp/backend_db.dump

# 2. Restore Zammad Database
Write-Host "[2/4] Restoring Zammad Database..."
docker cp $TempDir\zammad_db.dump zammad-zammad-postgresql-1:/tmp/zammad_db.dump
docker exec zammad-zammad-postgresql-1 pg_restore -U zammad -d zammad_production -1 -c -F c /tmp/zammad_db.dump
docker exec zammad-zammad-postgresql-1 rm /tmp/zammad_db.dump

# 3. Restore Zammad Storage
Write-Host "[3/4] Restoring Zammad File Storage..."
docker cp $TempDir\zammad_storage\storage zammad-zammad-railsserver-1:/opt/zammad/

# 4. Restore Configs
Write-Host "[4/4] Restoring Configuration Files..."
if (Test-Path "$TempDir\config\backend.env") { Copy-Item "$TempDir\config\backend.env" "backend\.env" -Force }
if (Test-Path "$TempDir\config\crewai_agents.env") { Copy-Item "$TempDir\config\crewai_agents.env" "crewai_agents\.env" -Force }
if (Test-Path "$TempDir\config\zammad.env") { Copy-Item "$TempDir\config\zammad.env" "zammad\.env" -Force }

Remove-Item -Recurse -Force $TempDir

Write-Host "✅ Restore Completed Successfully!" -ForegroundColor Green
Write-Host "It is highly recommended to restart all containers now:" -ForegroundColor Yellow
Write-Host "docker-compose restart"
