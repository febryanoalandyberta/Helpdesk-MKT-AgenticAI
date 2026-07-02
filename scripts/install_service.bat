@echo off
color 0A
echo =====================================================================
echo    MKT Helpdesk AI - Installer Hardware Monitor (Background)
echo =====================================================================
echo.
echo Script ini akan memasang hardware_monitor.ps1 agar berjalan
echo secara otomatis dan tersembunyi (tanpa layar hitam) setiap kali 
echo PC kasir ini dihidupkan.
echo.

:: Mendapatkan direktori tempat script ini berada
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%hardware_monitor.ps1"
set "VBS_SCRIPT=%SCRIPT_DIR%hardware_monitor_hidden.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Memeriksa apakah file PS1 ada
if not exist "%PS_SCRIPT%" (
    color 0C
    echo [ERROR] File hardware_monitor.ps1 tidak ditemukan di folder ini!
    echo Pastikan file install_service.bat ini berada di folder yang sama.
    echo.
    pause
)

:: 0. Mematikan service lama jika masih berjalan (Mencegah bentrok / double process)
echo Membersihkan sisa proses lama...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name = 'powershell.exe' AND CommandLine LIKE '%%hardware_monitor.ps1%%'\" | Invoke-CimMethod -MethodName Terminate | Out-Null" >nul 2>&1

:: 1. Membuat file VBScript pembungkus untuk menyembunyikan console
echo Membuat komponen background service...
echo Set objShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo command = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ ^& "%PS_SCRIPT%" ^& """" >> "%VBS_SCRIPT%"
echo objShell.Run command, 0, False >> "%VBS_SCRIPT%"

:: 2. Menyalin file VBScript ke folder Startup Windows
echo Mendaftarkan service ke Windows Startup...
copy "%VBS_SCRIPT%" "%STARTUP_DIR%\MKT_Hardware_Monitor.vbs" /Y > nul

echo.
echo =====================================================================
echo [SUKSES] Instalasi Selesai!
echo =====================================================================
echo.
echo 1. Hardware Monitor telah didaftarkan.
echo 2. Pemantauan kabel akan otomatis berjalan setiap PC menyala.
echo 3. Menjalankan service untuk pertama kalinya sekarang...
echo.

:: Menjalankan script secara gaib sekarang juga
wscript "%STARTUP_DIR%\MKT_Hardware_Monitor.vbs"

echo Service telah aktif di latar belakang.
echo Anda dapat menutup jendela ini dengan aman.
pause
