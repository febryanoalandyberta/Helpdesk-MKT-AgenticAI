"""
Zammad Integration Module — Webhook Receiver + Active Polling
===============================================================
Sesuai instruksi.md Step 2: "Sistem mengambil tiket baru dari Zammad"
Sesuai diagram: Site/Customer ↔ Zammad ↔ Agent AI Tier 0

Dua mode:
1. WEBHOOK: Zammad mengirim POST ke /api/zammad/webhook saat tiket baru/update
2. POLLING: Background task polling Zammad setiap N detik (fallback jika webhook tidak bisa)
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from loguru import logger

from config import settings
from database import get_db
from models.ticket import Ticket, TicketStatus, TicketSeverity
from models.audit_log import AuditLog

def parse_zammad_priority(data: dict) -> TicketSeverity:
    pid = str(data.get("priority_id", "")).strip()
    pname = str(data.get("priority", "")).lower().strip()
    if pid == "4" or "critical" in pname or "urgent" in pname:
        return TicketSeverity.CRITICAL
    elif pid == "3" or "high" in pname:
        return TicketSeverity.HIGH
    elif pid == "1" or "low" in pname:
        return TicketSeverity.LOW
    else:
        return TicketSeverity.MEDIUM

router = APIRouter(prefix="/api/zammad", tags=["Zammad Integration"])

# ─── ZAMMAD CLIENT ───────────────────────────────────────────
class ZammadClient:
    """HTTP client untuk Zammad REST API."""

    def __init__(self):
        self.base_url = settings.ZAMMAD_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Token token={settings.ZAMMAD_TOKEN}",
            "Content-Type": "application/json",
        }

    async def get_new_tickets(self, since_id: int = 0) -> List[Dict]:
        """Ambil tiket baru dari Zammad yang belum diproses."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/tickets",
                    headers=self.headers,
                    params={"limit": 20, "sort_by": "created_at", "order_by": "desc"},
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    return data
                tickets = data.get("tickets", []) or data.get("assets", {}).get("Ticket", {}).values()
                return list(tickets)
        except Exception as e:
            logger.warning(f"[Zammad] Failed to fetch tickets: {e}")
            return []

    async def get_ticket_detail(self, ticket_id: int) -> Optional[Dict]:
        """Ambil detail lengkap tiket dari Zammad."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/tickets/{ticket_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"[Zammad] Failed to get ticket {ticket_id}: {e}")
            return None

    async def get_ticket_articles(self, ticket_id: int) -> List[Dict]:
        """Ambil artikel (body/komentar) dari sebuah tiket."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/api/v1/ticket_articles/by_ticket/{ticket_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"[Zammad] Failed to get articles for ticket {ticket_id}: {e}")
            return []

    async def update_ticket(self, ticket_id: int, note: str, state: Optional[str] = None) -> bool:
        """Tambahkan catatan ke tiket Zammad (Step 9: Update tiket)."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Tambah artikel (public note agar customer bisa baca)
                await client.post(
                    f"{self.base_url}/api/v1/ticket_articles",
                    headers=self.headers,
                    json={
                        "ticket_id": ticket_id,
                        "body": note,
                        "type": "note",
                        "internal": False,
                    },
                )
                # Update state jika perlu
                if state:
                    await client.put(
                        f"{self.base_url}/api/v1/tickets/{ticket_id}",
                        headers=self.headers,
                        json={"state": state},
                    )
                logger.info(f"[Zammad] Updated ticket #{ticket_id}")
                return True
        except Exception as e:
            logger.error(f"[Zammad] Failed to update ticket {ticket_id}: {e}")
            return False

    async def close_ticket(self, ticket_id: int, resolution: str) -> bool:
        """Tutup tiket Zammad setelah resolved."""
        return await self.update_ticket(ticket_id, resolution, state="closed")


zammad_client = ZammadClient()


# ─── WEBHOOK ENDPOINT ────────────────────────────────────────
@router.post("/webhook")
async def zammad_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Sesuai diagram: Zammad → Agent AI Tier 0
    Zammad mengirim POST ke sini saat ada tiket baru/update.
    Setup di Zammad: Admin → Integrations → Webhooks → tambah URL ini.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event_type", "ticket.create")
    ticket_data = payload.get("ticket", {})
    article_data = payload.get("article", {})
    zammad_id = str(ticket_data.get("id", ""))

    logger.info(f"[Zammad Webhook] Received event={event_type}, ticket_id={zammad_id}")

    if not zammad_id:
        return {"status": "ignored", "reason": "No ticket ID in payload"}

    # Cek apakah sudah ada di sistem
    q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == zammad_id))
    existing = q.scalar_one_or_none()

    if existing and event_type == "ticket.create":
        return {"status": "skipped", "reason": "Ticket already exists"}

    # Simpan/update tiket
    if not existing:
        description = article_data.get("body", "")
        if not description:
            description = ticket_data.get("body", "")

        ticket = Ticket(
            zammad_ticket_id=zammad_id,
            title=ticket_data.get("title", "Untitled Ticket"),
            description=description,
            reporter_name=str(ticket_data.get("customer", ticket_data.get("customer_id", ""))),
            severity=parse_zammad_priority(ticket_data),
            status=TicketStatus.NEW,
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

        db.add(AuditLog(
            ticket_id=str(ticket.ticket_id),
            actor="ZammadWebhook",
            action="TICKET_RECEIVED_FROM_ZAMMAD",
            target=f"zammad_ticket_id={zammad_id}",
            result="SUCCESS",
            detail=f"Event: {event_type}",
        ))
        await db.commit()

        # Trigger AI processing di background (Step 3: CrewAI jalankan Tier 0)
        background_tasks.add_task(trigger_ai_for_new_ticket, str(ticket.ticket_id))
        logger.info(f"[Zammad Webhook] New ticket {ticket.ticket_id} queued for AI processing")
        
    elif existing and event_type == "ticket.update":
        # Sinkronisasi status jika tiket di-update di Zammad
        zammad_state = str(ticket_data.get("state", "")).lower()
        if zammad_state in ["closed", "resolved"]:
            existing.status = TicketStatus.CLOSED
            existing.resolved_at = datetime.utcnow()
            await db.commit()
            logger.info(f"[Zammad Webhook] Ticket {existing.ticket_id} closed from Zammad sync")

    return {"status": "accepted", "ticket_id": str(existing.ticket_id if existing else ticket.ticket_id)}


# ─── ACTIVE POLLING ──────────────────────────────────────────
_last_polled_id: int = 0


async def poll_zammad_for_new_tickets():
    """
    Step 2: Sistem mengambil tiket baru dari Zammad.
    Berjalan sebagai background task setiap ZAMMAD_POLL_INTERVAL detik.
    """
    global _last_polled_id
    logger.info(f"[Zammad Polling] Checking for new tickets (last_id={_last_polled_id})")

    try:
        new_tickets = await zammad_client.get_new_tickets(since_id=_last_polled_id)

        if not new_tickets:
            logger.debug("[Zammad Polling] No new tickets found.")
            return

        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            for zt in new_tickets:
                zammad_id = str(zt.get("id", ""))
                if not zammad_id:
                    continue

                q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == zammad_id))
                existing = q.scalar_one_or_none()
                if existing:
                    zammad_state = str(zt.get("state", "")).lower()
                    state_id = zt.get("state_id")
                    if (zammad_state in ["closed", "resolved"] or state_id == 4) and existing.status != TicketStatus.CLOSED:
                        existing.status = TicketStatus.CLOSED
                        from datetime import datetime
                        existing.resolved_at = datetime.utcnow()
                        await db.commit()
                        logger.info(f"[Zammad Polling] Sync: Ticket {existing.ticket_id} closed")
                    continue

                description = zt.get("body", "")
                if not description:
                    # Ambil dari articles jika kosong
                    articles = await zammad_client.get_ticket_articles(int(zammad_id))
                    if articles and len(articles) > 0:
                        description = articles[0].get("body", "")

                ticket = Ticket(
                    zammad_ticket_id=zammad_id,
                    title=zt.get("title", "Untitled"),
                    description=description,
                    reporter_name=str(zt.get("customer_id", zt.get("customer", ""))),
                    severity=parse_zammad_priority(zt),
                    status=TicketStatus.NEW,
                )
                db.add(ticket)
                db.add(AuditLog(
                    actor="ZammadPoller",
                    action="TICKET_POLLED_FROM_ZAMMAD",
                    target=f"zammad_ticket_id={zammad_id}",
                    result="SUCCESS",
                ))
                await db.commit()
                await db.refresh(ticket)

                # Step 3: Trigger CrewAI
                await trigger_ai_for_new_ticket(str(ticket.ticket_id))
                _last_polled_id = max(_last_polled_id, int(zammad_id))

        logger.info(f"[Zammad Polling] Processed {len(new_tickets)} tickets. Last ID: {_last_polled_id}")

    except Exception as e:
        logger.error(f"[Zammad Polling] Error: {e}")


async def trigger_ai_for_new_ticket(ticket_id: str):
    """Setelah tiket diterima dari Zammad, jalankan CrewAI Tier 0."""
    from api.tickets import process_ticket_ai
    import asyncio
    asyncio.create_task(process_ticket_ai(ticket_id))


async def start_zammad_polling():
    """Start background polling loop."""
    logger.info(f"[Zammad Polling] Starting polling every {settings.ZAMMAD_POLL_INTERVAL}s")
    while True:
        await asyncio.sleep(settings.ZAMMAD_POLL_INTERVAL)
        await poll_zammad_for_new_tickets()


# ─── STATUS ENDPOINT ─────────────────────────────────────────
@router.get("/status")
async def zammad_status():
    """Cek koneksi ke Zammad."""
    if not settings.ZAMMAD_URL or not settings.ZAMMAD_TOKEN:
        return {
            "connected": False,
            "reason": "ZAMMAD_URL atau ZAMMAD_TOKEN belum dikonfigurasi di .env",
            "webhook_url": "http://your-server:8000/api/zammad/webhook",
        }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.ZAMMAD_URL.rstrip('/')}/api/v1/users/me",
                headers={"Authorization": f"Token token={settings.ZAMMAD_TOKEN}"},
            )
            if resp.status_code == 200:
                user = resp.json()
                return {
                    "connected": True,
                    "zammad_url": settings.ZAMMAD_URL,
                    "logged_in_as": user.get("login"),
                    "polling_interval": settings.ZAMMAD_POLL_INTERVAL,
                    "webhook_url": "http://your-server:8000/api/zammad/webhook",
                }
            return {"connected": False, "reason": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


@router.post("/test-trigger")
async def test_trigger(background_tasks: BackgroundTasks):
    """Test endpoint: simulate menerima tiket dari Zammad."""
    background_tasks.add_task(poll_zammad_for_new_tickets)
    return {"status": "polling triggered manually"}
