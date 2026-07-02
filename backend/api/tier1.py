from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from database import get_db
from models.ticket import Ticket, TicketStatus
from models.site import Site
from models.device import Device, DeviceStatus

router = APIRouter()

@router.get("/active-diagnostics")
async def get_active_diagnostics(db: AsyncSession = Depends(get_db)):
    """Fetch active tickets currently in TIER1_PROCESSING or TIER0_PROCESSING and their associated devices."""
    
    # Ambil tiket yang sedang diproses
    q = await db.execute(
        select(Ticket)
        .where(Ticket.status.in_([TicketStatus.TIER1_PROCESSING, TicketStatus.TIER0_PROCESSING]))
        .order_by(Ticket.created_at.desc())
        .limit(10)
    )
    tickets = q.scalars().all()
    
    result = []
    for t in tickets:
        site_name = "Unknown Site"
        devices_data = []
        
        if t.site_id:
            site_q = await db.execute(select(Site).where(Site.site_id == t.site_id))
            site = site_q.scalar_one_or_none()
            if site:
                site_name = site.site_name
                
            dev_q = await db.execute(select(Device).where(Device.site_id == t.site_id))
            devices = dev_q.scalars().all()
            
            for d in devices:
                diag_status = "PENDING"
                if t.status == TicketStatus.TIER1_PROCESSING:
                    diag_status = "PING_OK" if d.status == DeviceStatus.ONLINE else "PENDING"
                
                devices_data.append({
                    "device_name": d.device_name,
                    "ip_address": d.ip_address or "Unknown IP",
                    "diagnostic_status": diag_status
                })
                
        result.append({
            "title": t.title,
            "site_name": site_name,
            "zammad_ticket_id": t.zammad_ticket_id or str(t.ticket_id)[:8],
            "severity": t.severity.value if hasattr(t.severity, "value") else str(t.severity),
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "devices": devices_data
        })
        
    return {"active_diagnostics": result}

import asyncio
from fastapi import Query
from fastapi.responses import StreamingResponse

@router.get("/stream_ping")
async def stream_ping(host: str = Query(...)):
    async def ping_generator():
        try:
            # -n untuk Windows, -c untuk Linux. Di dalam kontainer Linux (mkt_backend) kita pakai -c
            # Kita set 10 ping agar terlihat streamingnya
            process = await asyncio.create_subprocess_exec(
                "ping", "-c", "10", host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode('utf-8', errors='ignore').strip()
                if text:
                    yield f"data: {text}\n\n"
                    
            await process.wait()
            yield "data: [PROCESS_COMPLETED]\n\n"
        except Exception as e:
            yield f"data: Error executing ping: {e}\n\n"
            yield "data: [PROCESS_COMPLETED]\n\n"

    return StreamingResponse(ping_generator(), media_type="text/event-stream")
