@echo off
color 0E
echo =====================================================================
echo    MKT Helpdesk AI - Uninstaller Hardware Monitor
echo =====================================================================
echo.
echo Mencabut pemantauan kabel (MKT Hardware Monitor) dari sistem Anda...
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_VBS=%STARTUP_DIR%\MKT_Hardware_Monitor.vbs"

:: 1. Hapus file dari Startup
if not exist "%TARGET_VBS%" goto skip_del
echo Menghapus pendaftaran dari Windows Startup...
del /F /Q "%TARGET_VBS%"
echo [OK] Pendaftaran startup dihapus.

:skip_del
echo.
echo Mematikan proses background yang sedang berjalan...
:: Mematikan secara spesifik powershell yang menjalankan hardware_monitor.ps1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name = 'powershell.exe' AND CommandLine LIKE '%%hardware_monitor.ps1%%'\" | Invoke-CimMethod -MethodName Terminate | Out-Null" >nul 2>&1

echo [OK] Proses berhasil dihentikan.
echo.
echo =====================================================================
echo [SUKSES] Uninstall Selesai!
echo =====================================================================
echo Aplikasi tidak lagi berjalan dan tidak akan menyala saat PC dihidupkan.
echo Anda kini dapat menghapus folder "scripts" ini dengan aman.
echo.
pause
