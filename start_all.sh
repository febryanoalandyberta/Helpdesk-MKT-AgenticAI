#!/bin/bash

# ========================================================
#   🚀 MKT HELPDESK AGENTIC AI - STARTUP SCRIPT 🚀
# ========================================================

echo "========================================================"
echo "  🚀 MKT HELPDESK AGENTIC AI - STARTUP SCRIPT 🚀"
echo "========================================================"
echo ""

# Pastikan script dijalankan dari direktori tempat script ini berada
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "[1/4] Memeriksa Docker..."
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker belum terinstall atau tidak berjalan!"
    exit 1
fi
if ! docker info &> /dev/null; then
    echo "[ERROR] Docker daemon tidak berjalan atau butuh akses sudo."
    exit 1
fi

echo ""
echo "[2/4] Menjalankan Zammad Ticketing System..."
cd zammad
docker compose up -d
cd ..

echo ""
echo "[3/4] Menjalankan MKT Backend, Database, dan AI Memory..."
docker compose up -d

echo ""
echo "[4/4] Menjalankan Mesin CrewAI Engine (Port 8002)..."
cd crewai_agents

# Matikan proses lama di port 8002 jika ada (mencegah tabrakan port)
if command -v fuser &> /dev/null; then
    fuser -k 8002/tcp >/dev/null 2>&1
else
    PIDS=$(lsof -t -i:8002 2>/dev/null)
    if [ ! -z "$PIDS" ]; then
        kill -9 $PIDS >/dev/null 2>&1
    fi
fi

# Menjalankan AI Engine di background menggunakan nohup (agar log tersimpan)
if [ ! -d ".venv" ]; then
    echo "[WARNING] Virtual environment (.venv) tidak ditemukan di folder crewai_agents!"
    echo "Harap setup python venv terlebih dahulu jika belum."
else
    # Menggunakan python dari virtual environment linux
    nohup .venv/bin/python api.py > crewai_engine.log 2>&1 &
fi
cd ..

echo ""
echo "========================================================"
echo "✅ SEMUA SERVICE BERHASIL DIJALANKAN!"
echo "========================================================"
echo "- Dashboard UI : Buka file frontend/index.html di browser"
echo "- Backend API  : http://localhost:8000"
echo "- Zammad       : http://localhost:8080"
echo "- Mesin AI     : Berjalan di background (Port 8002, log di crewai_agents/crewai_engine.log)"
echo ""
