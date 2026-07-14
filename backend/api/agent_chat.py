from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import httpx
from database import get_db
from models.device import Device
from models.ticket import Ticket, TicketStatus

router = APIRouter(prefix="/api/chat", tags=["Agent Chat"])

class ChatMessageRequest(BaseModel):
    device_id: str
    message: str
    sender: str = "User"

@router.post("/incoming")
async def handle_incoming_chat(data: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validate device
    q = await db.execute(select(Device).where(Device.device_id == data.device_id))
    device = q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # 2. Get Site Name
    from models.site import Site
    sq = await db.execute(select(Site).where(Site.site_id == device.site_id))
    site_obj = sq.scalar_one_or_none()
    site_name = site_obj.site_name if site_obj else "Unknown Site"
    
    # 3. Create or find active ticket for this device
    # If the device already has an active ticket, we append to it (for simplicity, we create a new one here or just send to AI)
    # To keep it simple, we create a new Ticket for every new issue, or append to latest.
    
    # Let's create a Ticket
    description = f"[Dari PC Kasir: {device.device_name} / {site_name}] {data.message}"
    ticket = Ticket(
        title=f"Chat Report from {device.device_name}",
        description=description,
        reporter_name=data.sender,
        status=TicketStatus.NEW,
        device_id=device.device_id,
        site_id=device.site_id
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    # Create ticket in Zammad
    from api.zammad_webhook import zammad_client
    customer_email = "febryanoit@megakreasitech.com" # Default fallback
    zammad_id = await zammad_client.create_ticket(
        title=ticket.title,
        body=ticket.description,
        customer=customer_email
    )
    if zammad_id:
        ticket.zammad_ticket_id = str(zammad_id)
        db.add(ticket)
        await db.commit()

    # 4. Trigger AI (CrewAI)
    ai_response = "Sistem AI sedang memproses laporan Anda..."
    try:
        from api.tickets import process_ticket_ai
        # Panggil process_ticket_ai secara synchronous (await) agar DB, Zammad, dan Telegram terupdate
        await process_ticket_ai(str(ticket.ticket_id))
        
        # Refresh tiket dari DB untuk mendapatkan hasil yang sudah disimpan
        await db.refresh(ticket)
        if ticket.ai_analysis and ticket.ai_recommendation:
            ai_response = f"{ticket.ai_analysis}\n\n{ticket.ai_recommendation}"
        elif ticket.ai_recommendation:
            ai_response = ticket.ai_recommendation
        else:
            ai_response = "Laporan berhasil diteruskan ke AI dan Zammad. Menunggu pengecekan tim teknis."
    except Exception as e:
        print(f"[Agent Chat] Failed to contact CrewAI: {e}")
        ai_response = "Mohon ditunggu . Laporan Anda telah dicatat dan akan segera ditangani oleh tim IT Helpdesk"

    return {
        "status": "success",
        "ticket_id": str(ticket.ticket_id),
        "reply": ai_response
    }
