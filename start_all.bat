@echo off
echo ========================================================
echo   🚀 MKT HELPDESK AGENTIC AI - STARTUP SCRIPT 🚀
echo ========================================================
echo.

echo [1/4] Memeriksa Docker Desktop...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker belum berjalan! 
    echo Silakan buka aplikasi "Docker Desktop" di Windows Anda terlebih dahulu.
    echo Tekan tombol apa saja jika Docker sudah hijau / running...
    pause
)

echo.
echo [2/4] Menjalankan Zammad Ticketing System...
cd zammad
docker-compose up -d
cd ..

echo.
echo [3/4] Menjalankan MKT Backend, Database, dan AI Memory...
docker-compose up -d

echo.
echo [4/4] Menjalankan Mesin CrewAI Engine (Port 8002)...
cd crewai_agents

:: Matikan proses python lama di port 8002 jika ada (mencegah tabrakan port)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8002 ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

:: Menjalankan AI Engine di jendela baru agar log bisa dipantau
start "Mesin MKT CrewAI" cmd /c "title Mesin MKT CrewAI && .venv\Scripts\python.exe api.py"
cd ..

echo.
echo ========================================================
echo ✅ SEMUA SERVICE BERHASIL DIJALANKAN!
echo ========================================================
echo - Dashboard UI : Langsung buka file index.html di browser (atau klik kanan Open with Live Server)
echo - Backend API  : http://localhost:8000
echo - Zammad       : http://localhost:8080
echo - Mesin AI     : Berjalan di jendela CMD terpisah (Port 8002)
echo.
pause
