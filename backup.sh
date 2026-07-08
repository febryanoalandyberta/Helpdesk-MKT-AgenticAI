#!/bin/bash
set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups/$TIMESTAMP"
ZIP_FILE="backups/${TIMESTAMP}_MKT_Helpdesk_Backup.zip"

echo -e "\e[36mMKT Helpdesk AI - Disaster Recovery Backup System\e[0m"
echo -e "\e[36m=================================================\e[0m"
echo "Starting backup process for timestamp: $TIMESTAMP"

# Pastikan script berjalan dari direktori yang benar
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

mkdir -p "backups"
mkdir -p "$BACKUP_DIR"

# 1. Backup Backend Database
echo "[1/4] Dumping Backend Database (helpdesk_mkt)..."
docker exec mkt_postgres pg_dump -U mkt_user -d helpdesk_mkt -F c > "$BACKUP_DIR/backend_db.dump"

# 2. Backup Zammad Database
echo "[2/4] Dumping Zammad Database (zammad_production)..."
docker exec zammad-zammad-postgresql-1 pg_dump -U zammad -d zammad_production -F c > "$BACKUP_DIR/zammad_db.dump"

# 3. Backup Zammad Storage (Attachments)
echo "[3/4] Copying Zammad File Storage (Attachments)..."
docker cp zammad-zammad-railsserver-1:/opt/zammad/storage "$BACKUP_DIR/zammad_storage"

# 4. Backup Config files & Knowledge Base
echo "[4/4] Copying Configuration Files (.env) & Knowledge Base..."
mkdir -p "$BACKUP_DIR/config"
[ -f "backend/.env" ] && cp "backend/.env" "$BACKUP_DIR/config/backend.env"
[ -f "crewai_agents/.env" ] && cp "crewai_agents/.env" "$BACKUP_DIR/config/crewai_agents.env"
[ -f "zammad/.env" ] && cp "zammad/.env" "$BACKUP_DIR/config/zammad.env"
[ -f "docker-compose.yml" ] && cp "docker-compose.yml" "$BACKUP_DIR/config/"
[ -f "zammad/docker-compose.yml" ] && cp "zammad/docker-compose.yml" "$BACKUP_DIR/config/zammad_docker-compose.yml"
[ -f "IT_Helpdesk_Knowledge_Base.md" ] && cp "IT_Helpdesk_Knowledge_Base.md" "$BACKUP_DIR/config/"

# Zip everything
echo "Compressing backup to $ZIP_FILE..."
cd backups
zip -r "$(basename "$ZIP_FILE")" "$TIMESTAMP" > /dev/null
cd ..

# Cleanup temp folder
rm -rf "$BACKUP_DIR"

echo -e "\e[32m✅ Backup Completed Successfully!\e[0m"
echo -e "\e[33mFile saved at: $ZIP_FILE\e[0m"
