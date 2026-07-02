#!/bin/bash
set -e

ZIP_FILE="$1"

if [ -z "$ZIP_FILE" ]; then
    echo -e "\e[31mUsage: ./restore.sh ./backups/20260612_150000_MKT_Helpdesk_Backup.zip\e[0m"
    exit 1
fi

if [ ! -f "$ZIP_FILE" ]; then
    echo -e "\e[31mError: Backup file $ZIP_FILE not found!\e[0m"
    exit 1
fi

# Pastikan script berjalan dari direktori yang benar
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

TEMP_DIR="backups/restore_temp"
[ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo -e "\e[36mMKT Helpdesk AI - Disaster Recovery Restore System\e[0m"
echo -e "\e[36m==================================================\e[0m"
echo "Extracting $ZIP_FILE..."
unzip -q "$ZIP_FILE" -d "$TEMP_DIR"

# Temukan folder hasil ekstrak (nama timestamp)
EXTRACTED_FOLDER=$(ls -1 "$TEMP_DIR" | head -n 1)
FULL_TEMP_DIR="$TEMP_DIR/$EXTRACTED_FOLDER"

echo "Checking containers..."
if ! docker ps --format "{{.Names}}" | grep -q "mkt_postgres" || ! docker ps --format "{{.Names}}" | grep -q "zammad-zammad-postgresql-1"; then
    echo -e "\e[31mError: Docker containers are not running! Please run './start_all.sh' first.\e[0m"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 1. Restore Backend Database
echo "[1/4] Restoring Backend Database..."
docker cp "$FULL_TEMP_DIR/backend_db.dump" mkt_postgres:/tmp/backend_db.dump
docker exec mkt_postgres pg_restore -U mkt_user -d helpdesk_mkt -1 -c -F c /tmp/backend_db.dump || true
docker exec mkt_postgres rm /tmp/backend_db.dump

# 2. Restore Zammad Database
echo "[2/4] Restoring Zammad Database..."
docker cp "$FULL_TEMP_DIR/zammad_db.dump" zammad-zammad-postgresql-1:/tmp/zammad_db.dump
docker exec zammad-zammad-postgresql-1 pg_restore -U zammad -d zammad_production -1 -c -F c /tmp/zammad_db.dump || true
docker exec zammad-zammad-postgresql-1 rm /tmp/zammad_db.dump

# 3. Restore Zammad Storage
echo "[3/4] Restoring Zammad File Storage..."
docker cp "$FULL_TEMP_DIR/zammad_storage/storage/." zammad-zammad-railsserver-1:/opt/zammad/storage/

# 4. Restore Configs
echo "[4/4] Restoring Configuration Files..."
[ -f "$FULL_TEMP_DIR/config/backend.env" ] && cp "$FULL_TEMP_DIR/config/backend.env" "backend/.env"
[ -f "$FULL_TEMP_DIR/config/crewai_agents.env" ] && cp "$FULL_TEMP_DIR/config/crewai_agents.env" "crewai_agents/.env"
[ -f "$FULL_TEMP_DIR/config/zammad.env" ] && cp "$FULL_TEMP_DIR/config/zammad.env" "zammad/.env"

rm -rf "$TEMP_DIR"

echo -e "\e[32m✅ Restore Completed Successfully!\e[0m"
echo -e "\e[33mIt is highly recommended to restart all containers now:\e[0m"
echo "./start_all.sh (or restart the services via docker compose)"
