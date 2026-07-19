"""
Port Checker API — Manages hardware physical connection incidents
"""
import io
import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models.port_checker import PortCheckerLog

router = APIRouter(prefix="/api/port-checker", tags=["Port Checker"])

class CreatePortLogRequest(BaseModel):
    summary: str
    category: Optional[str] = None
    hardware_type: Optional[str] = None
    hardware_name: Optional[str] = None
    device_name: Optional[str] = None
    device_id: Optional[str] = None
    site_name: Optional[str] = None # Not in PortCheckerLog model currently, but kept for compatibility with incoming payloads

@router.post("/")
async def create_port_log(data: CreatePortLogRequest, db: AsyncSession = Depends(get_db)):
    # Fallback to map the device_id if not present in request.
    mapped_device_id = data.device_id

    if not mapped_device_id and data.device_name:
        # Search for device by device_name (hostname)
        from models.device import Device
        q = await db.execute(select(Device.device_id).where(Device.device_name == data.device_name))
        found_id = q.scalar_one_or_none()
        if found_id:
            mapped_device_id = str(found_id)

    log_data = {
        "summary": data.summary,
        "category": data.category,
        "device_name": data.device_name,
        "hardware_type": data.hardware_type,
        "hardware_name": data.hardware_name,
        "device_id": mapped_device_id,
        "is_read": False
    }
    
    port_log = PortCheckerLog(**log_data)
    db.add(port_log)
    await db.commit()
    await db.refresh(port_log)
    return port_log.to_dict()

@router.get("/{device_id}")
async def get_device_port_logs(
    device_id: str, 
    limit: int = 50, 
    db: AsyncSession = Depends(get_db)
):
    # For a specific device, fetch logs. If device_id is unknown, we can also query by device_name
    query = select(PortCheckerLog).where(PortCheckerLog.device_id == device_id).order_by(desc(PortCheckerLog.created_at)).limit(limit)
    q = await db.execute(query)
    logs = q.scalars().all()
    
    # If no logs by device_id, try by device_name (for backward compatibility if the agent only sent device_name)
    if not logs:
        # We need the device_name from devices table if we had it, but since we just have device_id here, 
        # let's assume the frontend will only query by device_id.
        pass

    return {"logs": [l.to_dict() for l in logs]}

@router.post("/mark-read/{device_id}")
async def mark_device_logs_read(device_id: str, db: AsyncSession = Depends(get_db)):
    # Update all unread logs for this device to read
    stmt = update(PortCheckerLog).where(
        (PortCheckerLog.device_id == device_id) & (PortCheckerLog.is_read == False)
    ).values(is_read=True)
    await db.execute(stmt)
    await db.commit()
    return {"success": True}

@router.get("/export/{device_id}")
async def export_port_logs(device_id: str, db: AsyncSession = Depends(get_db)):
    query = select(PortCheckerLog).where(PortCheckerLog.device_id == device_id).order_by(desc(PortCheckerLog.created_at))
    q = await db.execute(query)
    logs = q.scalars().all()

    if not logs:
        raise HTTPException(status_code=404, detail="No port checker history found for this device")

    # Create Excel Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Port Checker History"

    headers = ["Waktu (WIB)", "Kategori", "Perangkat Terkait", "Ringkasan", "Status"]
    for col_num, header_title in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=header_title)

    from zoneinfo import ZoneInfo
    jkt_tz = ZoneInfo("Asia/Jakarta")

    for row_num, l in enumerate(logs, 2):
        local_time_str = ""
        if l.created_at:
            utc_time = l.created_at.replace(tzinfo=ZoneInfo("UTC"))
            local_time = utc_time.astimezone(jkt_tz)
            local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        ws.cell(row=row_num, column=1, value=local_time_str)
        ws.cell(row=row_num, column=2, value=l.category or "-")
        # Kombinasikan Hardware Type & Name untuk kejelasan
        hardware_desc = f"{l.hardware_type or ''} - {l.hardware_name or ''}".strip(' -')
        ws.cell(row=row_num, column=3, value=hardware_desc if hardware_desc else "-")
        ws.cell(row=row_num, column=4, value=l.summary or "-")
        ws.cell(row=row_num, column=5, value="Sudah Dibaca" if l.is_read else "Belum Dibaca")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    headers_dict = {
        'Content-Disposition': f'attachment; filename="port_checker_{device_id}.xlsx"'
    }
    return Response(content=output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers_dict)
