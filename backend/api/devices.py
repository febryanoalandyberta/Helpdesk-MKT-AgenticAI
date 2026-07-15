"""
Devices API — Manage 72 POS devices across 18 sites
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from models.device import Device, DeviceStatus

router = APIRouter(prefix="/api/devices", tags=["Devices"])


class AutoRegisterRequest(BaseModel):
    mac_address: str
    hostname: str
    ip_address: str
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    hardware_model: Optional[str] = None


class TelemetryRequest(BaseModel):
    ip_address: str
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    disk_total_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    temperature: float
    current_active_app: Optional[str] = None
    current_active_url: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None


class CreateDeviceRequest(BaseModel):
    site_id: str
    device_name: str
    device_type: str = "POS_TICKETING"
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    hardware_model: Optional[str] = None
    credentials_reference: Optional[str] = None
    ssh_port: str = "22"
    notes: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


@router.get("/")
async def list_devices(
    site_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Device).where(Device.is_active == True)
    if site_id:
        query = query.where(Device.site_id == site_id)
    if device_type:
        query = query.where(Device.device_type == device_type.upper())
    if status:
        query = query.where(Device.status == status.upper())
    q = await db.execute(query.order_by(Device.device_name))
    devices = q.scalars().all()
    return {"devices": [d.to_dict() for d in devices], "total": len(devices)}


@router.get("/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.to_dict()


@router.post("/auto-register")
async def auto_register_device(data: AutoRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if a device with this MAC address already exists
    q = await db.execute(select(Device).where(Device.mac_address == data.mac_address))
    device = q.scalar_one_or_none()

    if device:
        # Update existing device info
        device.ip_address = data.ip_address
        device.hostname = data.hostname
        if data.operating_system:
            device.operating_system = data.operating_system
        if data.os_version:
            device.os_version = data.os_version
        device.last_seen = datetime.utcnow()
        device.status = DeviceStatus.ONLINE
        await db.commit()
        await db.refresh(device)
        return device.to_dict()

    # Create new UNASSIGNED device
    try:
        device_data = data.dict()
        device_data["device_name"] = data.hostname
        device_data["device_type"] = "POS_TICKETING" # Default
        device_data["status"] = DeviceStatus.ONLINE
        device_data["last_seen"] = datetime.utcnow()
        device_data["notes"] = "Auto-registered via Hardware Agent"
        # site_id is left as NULL (nullable=True)
        
        device = Device(**device_data)
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to auto-register: {str(e)}")


@router.post("/{device_id}/telemetry")
async def receive_telemetry(
    device_id: str,
    data: TelemetryRequest,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Update Health Metrics
    device.cpu_usage = data.cpu_usage
    device.ram_usage = data.ram_usage
    device.disk_usage = data.disk_usage
    device.disk_total_gb = data.disk_total_gb
    device.disk_free_gb = data.disk_free_gb
    device.temperature = data.temperature
    device.current_active_app = data.current_active_app
    device.current_active_url = data.current_active_url
    device.last_health_check = datetime.utcnow()
    
    # Update IP if changed (Failover tracking)
    if device.ip_address != data.ip_address:
        device.ip_address = data.ip_address

    if data.operating_system:
        device.operating_system = data.operating_system
    if data.os_version:
        device.os_version = data.os_version

    device.status = DeviceStatus.ONLINE
    device.last_seen = datetime.utcnow()
    
    await db.commit()
    return {"message": "Telemetry updated"}


@router.post("/")
async def create_device(data: CreateDeviceRequest, db: AsyncSession = Depends(get_db)):
    from models.site import Site
    import uuid

    # Coba cek apakah input site_id adalah UUID atau nama site
    actual_site_id = None
    try:
        val = uuid.UUID(data.site_id)
        # Jika valid UUID, pastikan ada di database
        q = await db.execute(select(Site).where(Site.site_id == val))
        site = q.scalar_one_or_none()
        if site:
            actual_site_id = site.site_id
    except ValueError:
        pass
    
    if not actual_site_id:
        # Cari berdasarkan nama (misal "MKT HO")
        q = await db.execute(select(Site).where(Site.site_name.ilike(f"%{data.site_id}%")))
        site = q.scalars().first()
        if site:
            actual_site_id = site.site_id
        else:
            raise HTTPException(status_code=400, detail=f"Site '{data.site_id}' tidak ditemukan. Harap masukkan nama Site atau UUID yang benar.")
    
    try:
        device_data = data.dict()
        device_data["site_id"] = actual_site_id
        device = Device(**device_data)
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device.to_dict()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Gagal menyimpan ke database: {str(e)}")


@router.patch("/{device_id}/status")
async def update_device_status(
    device_id: str,
    data: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.status = data.status.upper()
    device.last_ping = datetime.utcnow()
    if data.status.upper() == "ONLINE":
        device.last_seen = datetime.utcnow()
    device.updated_at = datetime.utcnow()
    await db.commit()
    return {"device_id": device_id, "status": device.status}


@router.post("/{device_id}/ping")
async def ping_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger a ping check for a specific device."""
    import subprocess
    import platform
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.ip_address:
        raise HTTPException(status_code=400, detail="Device has no IP address configured")

    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '3', device.ip_address]
    reachable = False
    ping_output = ""
    try:
        ping_output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        reachable = True
    except subprocess.CalledProcessError as e:
        reachable = False
        ping_output = e.output
    except Exception as e:
        reachable = False
        ping_output = str(e)

    # Update device status
    device.status = DeviceStatus.ONLINE if reachable else DeviceStatus.OFFLINE
    device.last_ping = datetime.utcnow()
    if reachable:
        device.last_seen = datetime.utcnow()
    await db.commit()

    return {
        "device_id": device_id,
        "device_name": device.device_name,
        "ip_address": device.ip_address,
        "reachable": reachable,
        "status": device.status,
        "ping_output": ping_output,
    }

class UpdateDeviceRequest(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    operating_system: Optional[str] = None

@router.put("/{device_id}")
async def update_device(
    device_id: str,
    data: UpdateDeviceRequest,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if data.device_name is not None:
        device.device_name = data.device_name
    if data.device_type is not None:
        device.device_type = data.device_type
    if data.ip_address is not None:
        device.ip_address = data.ip_address
    if data.operating_system is not None:
        device.operating_system = data.operating_system

    device.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(device)
    return device.to_dict()

@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()
    return {"message": "Device deleted successfully"}

class HardwareAlertRequest(BaseModel):
    hardware_name: str
    hardware_type: str
    event_type: str
    timestamp: str

@router.post("/{device_id}/hardware-alert")
async def hardware_alert(
    device_id: str,
    data: HardwareAlertRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook for Local Agent (Hardware Monitor) installed on POS device.
    It receives disconnect/connect events of USB/HDMI devices.
    """
    import httpx
    q = await db.execute(select(Device).where(Device.device_id == device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if data.event_type.upper() == "DISCONNECTED":
        # Get actual site name
        from models.site import Site
        sq = await db.execute(select(Site).where(Site.site_id == device.site_id))
        site_obj = sq.scalar_one_or_none()
        actual_site_name = site_obj.site_name if site_obj else str(device.site_id)

        # Log to Incident Memory
        from models.incident import IncidentMemory
        incident = IncidentMemory(
            summary=f"Kerusakan Fisik/Kabel Tercabut: {data.hardware_name} pada perangkat {device.device_name}",
            root_cause=f"{data.hardware_type} {data.hardware_name} terdeteksi terputus dari sistem.",
            category="HARDWARE",
            severity="HIGH",
            site_name=actual_site_name,
            device_name=device.device_name,
            device_type=device.device_type,
            tags=["hardware", "disconnect", data.hardware_type.lower()]
        )
        db.add(incident)
        await db.commit()

        # Try to trigger CrewAI to analyze & notify Telegram
        try:
            payload = {
                "ticket_id": f"ALERT-{device.device_name}",
                "title": f"Hardware Alert: {data.hardware_name} Disconnected",
                "customer": "System Monitor",
                "description": f"URGENT: Perangkat {data.hardware_name} ({data.hardware_type}) baru saja terputus atau dicabut dari komputer kasir {device.device_name} (Site: {actual_site_name}) pada pukul {data.timestamp}. Mohon segera periksa fisik kabel atau perangkat tersebut di lokasi.",
                "created_at": data.timestamp,
                "zammad_status": "new"
            }
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://host.docker.internal:8001/api/analyze",
                    json=payload,
                    timeout=5.0
                )
        except Exception:
            pass # Ignore if AI is down

    return {"message": "Alert received and processed"}
