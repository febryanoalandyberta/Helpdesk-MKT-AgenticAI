from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import httpx
import os
import shutil
import uuid
import tempfile
from pathlib import Path
from fpdf import FPDF

from database import get_db
from models.device import Device
from models.ticket import Ticket, TicketStatus, ChatMessage, ChatSender

UPLOAD_DIR = Path("uploads")
if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


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

    # 3. Find existing ACTIVE ticket for this device (NEW, TIER0, TIER1, ESCALATED)
    active_statuses = [
        TicketStatus.NEW, TicketStatus.TIER0_PROCESSING,
        TicketStatus.TIER1_PROCESSING, TicketStatus.ESCALATED
    ]
    existing_q = await db.execute(
        select(Ticket)
        .where(Ticket.device_id == device.device_id)
        .where(Ticket.status.in_(active_statuses))
        .order_by(Ticket.created_at.desc())
        .limit(1)
    )
    ticket = existing_q.scalar_one_or_none()

    # If ticket exists but hasn't been updated for 2 hours, consider it expired and create a new one
    if ticket:
        from datetime import datetime, timedelta
        if (datetime.utcnow() - ticket.updated_at) > timedelta(hours=2):
            ticket = None

    if ticket:
        # Append the follow-up message to existing ticket description
        ticket.description = (ticket.description or "") + f"\n\n[Follow-up dari Kasir]: {data.message}"
        ticket.status = TicketStatus.TIER1_PROCESSING
        await db.commit()
        await db.refresh(ticket)
    else:
        # Create new ticket only if no active ticket exists
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

        # Create ticket in Zammad only for new tickets
        from api.zammad_webhook import zammad_client
        customer_email = "febryanoit@megakreasitech.com"
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
    ai_response = "Mohon ditunggu, laporan Anda sedang kami analisis..."
    try:
        from api.tickets import process_ticket_ai
        await process_ticket_ai(str(ticket.ticket_id))

        await db.refresh(ticket)
        raw = ticket.ai_recommendation or ""

        # Sanitize: filter internal CrewAI prompt leaks before sending to customer
        internal_keywords = [
            "Remember to follow ALL the rules",
            "Your job is on the line",
            "Thought:", "Action:", "Action Input:", "Observation:",
            "Final Answer:", "I need to", "I should", "I will",
            "Human:", "Assistant:", "System:", "> Entering", "> Finished",
        ]
        has_leak = any(kw.lower() in raw.lower() for kw in internal_keywords)
        
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', raw))

        if has_leak or has_chinese or not raw.strip():
            ai_response = (
                "Terima kasih sudah menginformasikan kendala ini. "
                "Tim IT Helpdesk sedang menganalisis lebih lanjut dan akan segera memberikan solusi. "
                "Mohon kesabarannya ya! 🙏"
            )
        else:
            ai_response = raw
    except Exception as e:
        print(f"[Agent Chat] Failed to contact CrewAI: {e}")
        ai_response = "Mohon ditunggu. Laporan Anda telah dicatat dan akan segera ditangani oleh tim IT Helpdesk."

    return {
        "status": "success",
        "ticket_id": str(ticket.ticket_id),
        "reply": ai_response
    }



class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, ticket_id: str):
        await websocket.accept()
        if ticket_id not in self.active_connections:
            self.active_connections[ticket_id] = []
        self.active_connections[ticket_id].append(websocket)

    def disconnect(self, websocket: WebSocket, ticket_id: str):
        if ticket_id in self.active_connections:
            self.active_connections[ticket_id].remove(websocket)
            if not self.active_connections[ticket_id]:
                del self.active_connections[ticket_id]

    async def broadcast(self, ticket_id: str, message: dict):
        if ticket_id in self.active_connections:
            for connection in self.active_connections[ticket_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{ticket_id}")
async def websocket_endpoint(websocket: WebSocket, ticket_id: str, db: AsyncSession = Depends(get_db)):
    await manager.connect(websocket, ticket_id)
    try:
        while True:
            data = await websocket.receive_json()
            # data format: {"sender": "USER|AGENT", "message_type": "TEXT|FILE", "content": "hello"}
            
            sender_enum = ChatSender.USER
            if data.get("sender") == "AGENT":
                sender_enum = ChatSender.AGENT
                
            msg = ChatMessage(
                ticket_id=ticket_id,
                sender=sender_enum,
                message_type=data.get("message_type", "TEXT"),
                content=data.get("content", "")
            )
            db.add(msg)
            await db.commit()
            
            # Add timestamp to broadcast
            broadcast_data = {
                "sender": data.get("sender", "USER"),
                "message_type": data.get("message_type", "TEXT"),
                "content": data.get("content", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.broadcast(ticket_id, broadcast_data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, ticket_id)

@router.post("/upload")
async def upload_chat_file(ticket_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Uploads a file, compresses images if possible, and saves locally."""
    # Check if ticket exists
    q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = q.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    file_extension = os.path.splitext(file.filename)[1].lower()
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / new_filename

    if file_extension in ['.jpg', '.jpeg', '.png'] and HAS_PILLOW:
        try:
            image = Image.open(file.file)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            max_width = 1200
            if image.width > max_width:
                w_percent = max_width / float(image.width)
                h_size = int((float(image.height) * float(w_percent)))
                image = image.resize((max_width, h_size), Image.Resampling.LANCZOS)
                
            image.save(file_path, optimize=True, quality=60)
        except Exception:
            with open(file_path, "wb") as buffer:
                file.file.seek(0)
                shutil.copyfileobj(file.file, buffer)
    else:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    return {"filename": new_filename, "url": f"/uploads/{new_filename}"}

@router.get("/export-pdf/{ticket_id}")
async def export_chat_pdf(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and return a read-only PDF of the chat history."""
    q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = q.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    q_msg = await db.execute(select(ChatMessage).where(ChatMessage.ticket_id == ticket_id).order_by(ChatMessage.timestamp))
    messages = q_msg.scalars().all()

    pdf = FPDF()
    pdf.add_page()
    
    # Check if a custom font exists (useful for emojis/unicode), else fallback to helvetica
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "MKT IT Helpdesk - Bukti Percakapan Live Chat", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Ticket ID: {ticket.ticket_id}", new_x="LMARGIN", new_y="NEXT")
    # Clean up non-latin1 characters for basic helvetica font
    clean_title = ticket.title.encode('latin-1', 'replace').decode('latin-1') if ticket.title else ""
    pdf.cell(0, 8, f"Judul Tiket: {clean_title}", new_x="LMARGIN", new_y="NEXT")
    
    # Konversi ke WIB (GMT+7)
    from datetime import timedelta
    export_time_wib = datetime.utcnow() + timedelta(hours=7)
    pdf.cell(0, 8, f"Tanggal Export: {export_time_wib.strftime('%Y-%m-%d %H:%M:%S')} WIB", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    for msg in messages:
        sender_label = "IT Helpdesk" if msg.sender.name == "AGENT" else "Kasir (POS User)"
        
        # Asumsikan msg.timestamp tersimpan dalam UTC, konversi ke WIB
        msg_time_wib = msg.timestamp + timedelta(hours=7)
        time_str = msg_time_wib.strftime('%Y-%m-%d %H:%M:%S')
        
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"[{time_str}] {sender_label}:", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("helvetica", "", 10)
        content = msg.content
        if msg.message_type == 'FILE':
            content = f"[FILE ATTACHMENT: {msg.content}]"
            
        clean_content = content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, clean_content)
        pdf.ln(3)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    
    return FileResponse(
        path=temp_file.name, 
        filename=f"Chat_Evidence_{ticket.ticket_id}.pdf", 
        media_type="application/pdf"
    )

class LiveChatMessage(BaseModel):
    sender: str
    message_type: str = "TEXT"
    content: str

@router.get("/messages/{ticket_id}")
async def get_chat_messages(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all chat messages for a ticket. Used for HTTP polling instead of WebSocket."""
    q_msg = await db.execute(select(ChatMessage).where(ChatMessage.ticket_id == ticket_id).order_by(ChatMessage.timestamp.asc()))
    messages = q_msg.scalars().all()
    return [msg.to_dict() for msg in messages]

@router.post("/messages/{ticket_id}")
async def post_live_chat_message(ticket_id: str, data: LiveChatMessage, db: AsyncSession = Depends(get_db)):
    """Post a live chat message via HTTP (avoids WebSocket Mixed Content block)."""
    sender_enum = ChatSender.USER
    if data.sender == "AGENT":
        sender_enum = ChatSender.AGENT
        
    msg = ChatMessage(
        ticket_id=ticket_id,
        sender=sender_enum,
        message_type=data.message_type,
        content=data.content
    )
    db.add(msg)
    await db.commit()
    
    # Broadcast to any active websockets (like the Dashboard)
    broadcast_data = {
        "sender": data.sender,
        "message_type": data.message_type,
        "content": data.content,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(ticket_id, broadcast_data)
    
    return {"status": "success"}
