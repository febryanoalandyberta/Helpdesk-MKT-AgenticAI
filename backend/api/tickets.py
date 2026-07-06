"""
Tickets API — CRUD + AI Processing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import get_db
from models.ticket import Ticket, TicketStatus, TicketSeverity, TicketCategory
from models.site import Site
from models.device import Device
from models.audit_log import AuditLog
from loguru import logger

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    zammad_ticket_id: Optional[str] = None
    site_id: Optional[str] = None
    device_id: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    severity: Optional[str] = "MEDIUM"


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    resolution: Optional[str] = None
    note: Optional[str] = None


@router.get("/")
async def list_tickets(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    site_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Ticket).order_by(desc(Ticket.created_at)).limit(limit).offset(offset)
    if status:
        stat_upper = status.upper()
        if stat_upper in ["CLOSED", "RESOLVED"]:
            query = query.where(Ticket.status.in_(["CLOSED", "RESOLVED"]))
        else:
            query = query.where(Ticket.status == stat_upper)
    if severity:
        query = query.where(Ticket.severity == severity.upper())
    if site_id:
        query = query.where(Ticket.site_id == site_id)

    result = await db.execute(query)
    tickets = result.scalars().all()
    return {"tickets": [t.to_dict() for t in tickets], "total": len(tickets)}


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = q.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket.to_dict()


@router.post("/")
async def create_ticket(
    data: CreateTicketRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ticket = Ticket(
        title=data.title,
        description=data.description,
        zammad_ticket_id=data.zammad_ticket_id,
        site_id=data.site_id,
        device_id=data.device_id,
        reporter_name=data.reporter_name,
        reporter_email=data.reporter_email,
        severity=data.severity or TicketSeverity.MEDIUM,
        status=TicketStatus.NEW,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    # Sync to Zammad if ticket was created from Dashboard (no zammad_ticket_id provided)
    if not data.zammad_ticket_id:
        from api.zammad_webhook import zammad_client
        
        customer_email = data.reporter_email
        if not customer_email or "@" not in customer_email:
            customer_email = "febryanoit@megakreasitech.com"
            
        zammad_id = await zammad_client.create_ticket(
            title=data.title,
            body=data.description,
            customer=customer_email
        )
        if zammad_id:
            ticket.zammad_ticket_id = str(zammad_id)
            await db.commit()

    # Audit log
    db.add(AuditLog(
        ticket_id=str(ticket.ticket_id),
        actor="system",
        action="TICKET_CREATED",
        result="SUCCESS",
        detail=f"Ticket '{data.title}' created",
    ))
    await db.commit()

    # Trigger AI processing in background
    background_tasks.add_task(process_ticket_ai, str(ticket.ticket_id))
    logger.info(f"[TicketsAPI] Created ticket {ticket.ticket_id}, queued for AI processing")

    return {"ticket": ticket.to_dict(), "message": "Ticket created and queued for AI analysis"}


@router.put("/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    data: UpdateTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = q.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if data.status:
        ticket.status = data.status.upper()
        if data.status.upper() == "RESOLVED":
            ticket.resolved_at = datetime.utcnow()
    if data.severity:
        ticket.severity = data.severity.upper()
    if data.resolution:
        ticket.resolution = data.resolution

    ticket.updated_at = datetime.utcnow()
    db.add(AuditLog(
        ticket_id=ticket_id,
        actor="helpdesk_user",
        action="TICKET_UPDATED",
        result="SUCCESS",
        detail=f"Status={data.status}, Resolution={data.resolution}",
    ))
    await db.commit()
    await db.refresh(ticket)
    return ticket.to_dict()


@router.post("/{ticket_id}/process")
async def trigger_ai_processing(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger AI processing for a ticket."""
    q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = q.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    background_tasks.add_task(process_ticket_ai, ticket_id)
    return {"message": f"AI processing triggered for ticket {ticket_id}"}


import asyncio

async def process_ticket_ai(ticket_id: str):
    """Background task: run CrewAI orchestrator on the ticket."""
    from database import AsyncSessionLocal
    import os
    
    async with AsyncSessionLocal() as db:
        try:
            q = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
            ticket = q.scalar_one_or_none()
            if not ticket:
                return

            ticket.status = TicketStatus.TIER0_PROCESSING
            await db.commit()

            logger.info(f"[TicketsAPI] Triggering real CrewAI analysis for {ticket_id}...")
            
            import httpx
            
            site_name = "Unknown Site"
            from models.site import Site
            if ticket.site_id:
                site_q = await db.execute(select(Site).where(Site.site_id == ticket.site_id))
                site_obj = site_q.scalar_one_or_none()
                if site_obj:
                    site_name = site_obj.site_name
            else:
                import re
                desc = ticket.description or ""
                match = re.search(r'(?i)Site\s*:\s*([A-Za-z0-9\s]+)', desc)
                if match:
                    extracted_site = match.group(1).strip()
                    site_q = await db.execute(select(Site).where(Site.site_name.ilike(f"%{extracted_site}%")))
                    site_obj = site_q.scalar_one_or_none()
                    if site_obj:
                        ticket.site_id = site_obj.site_id
                        site_name = site_obj.site_name

            payload = {
                "ticket_id": str(ticket.ticket_id),
                "title": ticket.title or "",
                "description": ticket.description or "",
                "reporter_name": ticket.reporter_name or "Unknown",
                "site_name": site_name,
                "severity": ticket.severity or "LOW"
            }
            
            ai_success = False
            async with httpx.AsyncClient(timeout=120) as client:
                try:
                    resp = await client.post("http://crewai:8002/api/analyze", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("status") == "success":
                        result_text = data.get("result", "")
                        ai_success = True
                        
                        # Set default values
                        ticket.ai_analysis = "Analisis selesai. Silakan periksa log CrewAI untuk detail."
                        ticket.ai_recommendation = result_text[:500] + "..." if len(result_text) > 500 else result_text
                        ticket.sop_reference = "SOP-AI-001"
                        ticket.confidence_score = 85.0
                        ticket.root_cause = "Dianalisis oleh AI"
                        
                        try:
                            import json
                            import re
                            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                            if json_match:
                                parsed = json.loads(json_match.group(0))
                                if "analysis" in parsed:
                                    ticket.ai_analysis = parsed.get("analysis", ticket.ai_analysis)
                                    ticket.ai_recommendation = parsed.get("recommendation", ticket.ai_recommendation)
                                    ticket.sop_reference = parsed.get("sop_reference", ticket.sop_reference)
                                    ticket.confidence_score = float(parsed.get("confidence_score", ticket.confidence_score))
                                    ticket.root_cause = parsed.get("root_cause", ticket.root_cause)
                                else:
                                    ai_success = False
                                    ticket.ai_analysis = "Pengecekan manual diperlukan (Output AI Non-Standar)."
                                    ticket.ai_recommendation = result_text[:800]
                            else:
                                ai_success = False
                                ticket.ai_analysis = "Analisis selesai (Format Non-Standar)."
                                ticket.ai_recommendation = result_text[:800]
                        except Exception as parse_err:
                            ai_success = False
                            ticket.ai_analysis = "Analisis selesai namun gagal diekstrak secara struktural."
                            ticket.ai_recommendation = result_text[:800]
                            logger.warning(f"Failed to parse JSON output from CrewAI: {parse_err}")
                            
                    else:
                        ticket.ai_analysis = f"Error dari AI Engine: {data.get('message')}"
                        ticket.ai_recommendation = ""
                        ticket.confidence_score = 0.0
                except Exception as req_err:
                    ticket.ai_analysis = f"Gagal terhubung ke CrewAI Engine (pastikan berjalan di port 8002): {req_err}"
                    ticket.ai_recommendation = ""
                    ticket.confidence_score = 0.0
            
            ticket.status = TicketStatus.TIER1_PROCESSING
            
            # Auto-Resolution Check (Step 3: Auto-Resolution if Confidence >= 95%)
            if ticket.confidence_score >= 95.0:
                ticket.status = TicketStatus.RESOLVED
                ticket.resolution = ticket.ai_recommendation
                ticket.resolved_at = datetime.utcnow()
                ticket.resolved_by = "MKT Agentic AI"
                logger.info(f"[TicketsAPI] Ticket {ticket_id} AUTO-RESOLVED due to high confidence ({ticket.confidence_score}%)")
            elif ticket.confidence_score < 40.0 and ticket.confidence_score > 0:
                ticket.status = TicketStatus.ESCALATED
                ticket.escalated = True
                ticket.escalated_at = datetime.utcnow()
                logger.warning(f"[TicketsAPI] Ticket {ticket_id} AUTO-ESCALATED due to low confidence ({ticket.confidence_score}%)")
            
            ticket.tier_level = 1
            await db.commit()
            
            if ticket.zammad_ticket_id:
                from api.zammad_webhook import zammad_client
                state_update = "closed" if ticket.status == TicketStatus.RESOLVED else "open"
                note = (
                    f"🤖 MKT AI Agent (Tier 0)\n\n"
                    f"Analisis:\n{ticket.ai_analysis}\n\n"
                    f"Rekomendasi:\n{ticket.ai_recommendation}\n"
                )
                if ticket.status == TicketStatus.RESOLVED:
                    note += "\n\n✅ Tiket ditutup otomatis oleh AI karena tingkat akurasi solusi dipastikan sangat tinggi."
                elif ticket.status == TicketStatus.ESCALATED:
                    note += "\n\n⚠️ TIKET DIESKALASI OTOMATIS: AI mendeteksi masalah kompleks. Mohon bantuan tim teknis/manusia segera."
                
                await zammad_client.update_ticket(int(ticket.zammad_ticket_id), note, state=state_update)

            # FALLBACK TELEGRAM NOTIFICATION
            if ticket.status == TicketStatus.TIER1_PROCESSING or ticket.severity == "CRITICAL" or getattr(ticket, 'status', None) == TicketStatus.ESCALATED:
                from api.telegram import send_telegram_message
                message = (
                    f"🚨 <b>ESKALASI TIKET MKT HELPDESK</b> 🚨\n\n"
                    f"<b>Ticket ID:</b> #{ticket.zammad_ticket_id or str(ticket.ticket_id)[:8]}\n"
                    f"<b>Site:</b> {site_name}\n"
                    f"<b>Severity:</b> {ticket.severity.value if hasattr(ticket.severity, 'value') else ticket.severity}\n"
                    f"<b>Problem:</b> {ticket.title}\n"
                    f"<b>Detail:</b>\n<i>{re.sub(r'<[^>]+>', ' ', ticket.description or '')[:300].strip()}{'...' if len(ticket.description or '') > 300 else ''}</i>\n\n"
                    f"<b>AI Status:</b> {'Auto-Escalated (Butuh Perhatian Tim IT)' if getattr(ticket, 'escalated', False) else 'Menunggu pengecekan manual'}\n"
                    f"Mohon PIC segera menindaklanjuti tiket ini!"
                )
                success = await send_telegram_message(message)
                if success:
                    logger.info(f"[TicketsAPI] Sent Telegram notification for {ticket_id}")
                    db.add(AuditLog(
                        ticket_id=str(ticket_id), actor="Tier1Agent", action="TELEGRAM_SENT",
                        result="SUCCESS", detail=message[:100]
                    ))
                else:
                    db.add(AuditLog(
                        ticket_id=str(ticket_id), actor="Tier1Agent", action="TELEGRAM_SENT",
                        result="FAILED", detail="Gagal mengirim ke Telegram API."
                    ))
                    await db.commit()

            logger.info(f"[TicketsAPI] AI processing complete for {ticket_id}")

        except Exception as e:
            logger.error(f"[TicketsAPI] AI processing error for {ticket_id}: {e}")
