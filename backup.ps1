$ErrorActionPreference = "Stop"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "backups\$Timestamp"
$ZipFile = "backups\${Timestamp}_MKT_Helpdesk_Backup.zip"

Write-Host "MKT Helpdesk AI - Disaster Recovery Backup System" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Starting backup process for timestamp: $Timestamp"

if (!(Test-Path "backups")) {
    New-Item -ItemType Directory -Path "backups" | Out-Null
}
New-Item -ItemType Directory -Path $BackupDir | Out-Null

# 1. Backup Backend Database
Write-Host "[1/4] Dumping Backend Database (helpdesk_mkt)..."
docker exec mkt_postgres pg_dump -U mkt_user -d helpdesk_mkt -F c -f /tmp/backend_db.dump
docker cp mkt_postgres:/tmp/backend_db.dump $BackupDir\backend_db.dump
docker exec mkt_postgres rm /tmp/backend_db.dump

# 2. Backup Zammad Database
Write-Host "[2/4] Dumping Zammad Database (zammad_production)..."
docker exec zammad-zammad-postgresql-1 pg_dump -U zammad -d zammad_production -F c -f /tmp/zammad_db.dump
docker cp zammad-zammad-postgresql-1:/tmp/zammad_db.dump $BackupDir\zammad_db.dump
docker exec zammad-zammad-postgresql-1 rm /tmp/zammad_db.dump

# 3. Backup Zammad Storage (Attachments)
Write-Host "[3/4] Copying Zammad File Storage (Attachments)..."
docker cp zammad-zammad-railsserver-1:/opt/zammad/storage $BackupDir\zammad_storage

# 4. Backup Config files & Knowledge Base
Write-Host "[4/4] Copying Configuration Files (.env) & Knowledge Base..."
New-Item -ItemType Directory -Path "$BackupDir\config" | Out-Null
if (Test-Path "backend\.env") { Copy-Item "backend\.env" "$BackupDir\config\backend.env" }
if (Test-Path "crewai_agents\.env") { Copy-Item "crewai_agents\.env" "$BackupDir\config\crewai_agents.env" }
if (Test-Path "zammad\.env") { Copy-Item "zammad\.env" "$BackupDir\config\zammad.env" }
Copy-Item "docker-compose.yml" "$BackupDir\config\"
Copy-Item "zammad\docker-compose.yml" "$BackupDir\config\zammad_docker-compose.yml"
if (Test-Path "IT_Helpdesk_Knowledge_Base.md") { Copy-Item "IT_Helpdesk_Knowledge_Base.md" "$BackupDir\config\" }

# Zip everything
Write-Host "Compressing backup to $ZipFile..."
Compress-Archive -Path "$BackupDir\*" -DestinationPath $ZipFile -Force

# Cleanup temp folder
Remove-Item -Recurse -Force $BackupDir

Write-Host "✅ Backup Completed Successfully!" -ForegroundColor Green
Write-Host "File saved at: $ZipFile" -ForegroundColor Yellow
