# =====================================================================
# MKT Helpdesk AI - Local Hardware Monitor Agent
# =====================================================================
# Script ini di-install di setiap PC POS Windows.
# Fungsinya: Memantau jika ada kabel USB/Printer/HDMI yang dicabut,
# lalu mengirimkan alert/webhook ke Backend Helpdesk MKT secara diam-diam.
# =====================================================================

param (
    [string]$DeviceId = "ac24b84c-828a-47b0-888e-6addeb698418",  # Ganti dengan Device ID komputer ini
    [string]$BackendUrl = "http://10.20.0.182:8000" # IP Server Backend MKT Helpdesk
)

# Gunakan scope global agar terbaca di dalam event action
$global:WebhookEndpoint = "$BackendUrl/api/devices/$DeviceId/hardware-alert"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " MKT Helpdesk AI - Local Hardware & Network Monitor " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Device ID : $DeviceId"
Write-Host "Server    : $BackendUrl"
Write-Host "Status    : Menunggu aktivitas cabut USB/HDMI/LAN..." -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Cyan

# ---------------------------------------------------------
# 1. MONITOR USB / DISPLAY / PRINTER (PnP Entity)
# ---------------------------------------------------------
$queryPnP = "SELECT * FROM __InstanceDeletionEvent WITHIN 3 WHERE TargetInstance ISA 'Win32_PnPEntity'"

Register-WmiEvent -Query $queryPnP -SourceIdentifier "MKT_Hardware_Disconnect" -Action {
    $device = $Event.SourceEventArgs.NewEvent.TargetInstance
    $deviceName = $device.Name
    $deviceDesc = $device.Description

    # Filter hanya untuk USB, Printer, Mouse, Keyboard, Display/HDMI
    if ($deviceName -match "USB|Printer|Mouse|Keyboard|Display|Monitor|HDMI" -or $deviceDesc -match "USB|Printer|Mouse|Keyboard|Display|Monitor|HDMI") {
        
        $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        $hardwareType = "USB/Peripheral"
        if ($deviceName -match "Printer") { $hardwareType = "Printer" }
        if ($deviceName -match "Display|Monitor|HDMI") { $hardwareType = "Display" }

        Write-Host "[$timestamp] ALARM: Perangkat Fisik '$deviceName' ($hardwareType) TERCABUT!" -ForegroundColor Red

        $payload = @{
            hardware_name = "$deviceName"
            hardware_type = "$hardwareType"
            event_type = "DISCONNECTED"
            timestamp = "$timestamp"
        } | ConvertTo-Json

        try {
            Invoke-RestMethod -Uri $global:WebhookEndpoint -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 5
            Write-Host " -> Laporan terkirim ke Server MKT." -ForegroundColor Green
        } catch {
            Write-Host " -> Gagal mengirim laporan: $_" -ForegroundColor DarkRed
        }
    }
}

# ---------------------------------------------------------
# 2. MONITOR KABEL LAN / ETHERNET
# ---------------------------------------------------------
# NetConnectionStatus: 2 = Connected, 7 = Media Disconnected (Kabel Cabut)
$queryNet = "SELECT * FROM __InstanceModificationEvent WITHIN 3 WHERE TargetInstance ISA 'Win32_NetworkAdapter' AND TargetInstance.NetConnectionStatus = 7 AND PreviousInstance.NetConnectionStatus = 2"

Register-WmiEvent -Query $queryNet -SourceIdentifier "MKT_Network_Disconnect" -Action {
    $adapter = $Event.SourceEventArgs.NewEvent.TargetInstance
    $adapterName = $adapter.Name

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    
    Write-Host "[$timestamp] ALARM: Kabel LAN pada '$adapterName' TERCABUT!" -ForegroundColor Red

    $payload = @{
        hardware_name = "Kabel LAN - $adapterName"
        hardware_type = "Network/LAN"
        event_type = "DISCONNECTED"
        timestamp = "$timestamp"
    } | ConvertTo-Json

    try {
        Invoke-RestMethod -Uri $global:WebhookEndpoint -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 5
        Write-Host " -> Laporan Jaringan terkirim ke Server MKT." -ForegroundColor Green
    } catch {
        Write-Host " -> Gagal mengirim laporan Jaringan: $_" -ForegroundColor DarkRed
    }
}

# ---------------------------------------------------------
# LOOP UTAMA (Menjaga Script Tetap Hidup)
# ---------------------------------------------------------
try {
    while ($true) {
        Start-Sleep -Seconds 60
    }
} finally {
    Unregister-Event -SourceIdentifier "MKT_Hardware_Disconnect" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "MKT_Network_Disconnect" -ErrorAction SilentlyContinue
}
