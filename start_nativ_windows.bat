@echo off
echo ========================================================
echo   🚀 MKT HELPDESK AGENTIC AI - NATIVE MODE STARTUP 🚀
echo ========================================================
echo Peringatan: Mode ini berjalan 100%% tanpa Docker karena WSL Anda rusak!
echo.

echo [1/3] Menyiapkan Environment...
set DATABASE_URL=sqlite+aiosqlite:///./helpdesk_demo.db

echo [2/3] Menjalankan MKT Backend (Port 8000)...
:: Matikan proses python lama di port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

cd backend
start "MKT Backend API" cmd /c "title MKT Backend API && ..\crewai_agents\.venv\Scripts\python.exe -m uvicorn main:app --port 8000"
cd ..

echo.
echo [3/3] Menjalankan Mesin CrewAI Engine (Port 8002)...
:: Matikan proses python lama di port 8002
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8002 ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

cd crewai_agents
start "Mesin MKT CrewAI" cmd /c "title Mesin MKT CrewAI && .venv\Scripts\python.exe api.py"
cd ..

echo.
echo ========================================================
echo ✅ SEMUA SERVICE NATIVE BERHASIL DIJALANKAN!
echo ========================================================
echo - Dashboard UI : Buka file index.html di folder frontend
echo - Buat Tiket   : Buka terminal dan ketik `python scratch\test_zammad.py`
echo.
pause
