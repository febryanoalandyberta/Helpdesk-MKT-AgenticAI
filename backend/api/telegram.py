from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, cast, String
from typing import Dict, List, Any

from database import get_db
from models.audit_log import AuditLog
from models.ticket import Ticket
from models.site import Site

router = APIRouter()

import os
import aiohttp
import logging
logger = logging.getLogger(__name__)

async def send_telegram_message(message_text: str, target_chat_id: str = None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = target_chat_id or os.getenv("TELEGRAM_DEFAULT_GROUP_ID")
    
    if not bot_token or not chat_id:
        logger.warning("[Telegram] Token or Chat ID not configured. Skipping message.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return True
                else:
                    err = await resp.text()
                    logger.error(f"[Telegram] Failed to send message: {err}")
                    return False
    except Exception as e:
        logger.error(f"[Telegram] Error sending message: {e}")
        return False

async def send_telegram_document(file_path: str, caption: str, target_chat_id: str = None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = target_chat_id or os.getenv("TELEGRAM_DEFAULT_GROUP_ID")
    
    if not bot_token or not chat_id:
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('chat_id', chat_id)
                form.add_field('caption', caption, content_type='text/plain')
                form.add_field('document', f, filename=os.path.basename(file_path))
                
                async with session.post(url, data=form) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        err = await resp.text()
                        logger.error(f"[Telegram] Failed to send document: {err}")
                        return False
    except Exception as e:
        logger.error(f"[Telegram] Error sending document: {e}")
        return False

import asyncio
from database import AsyncSessionLocal
from models.ticket import TicketStatus

_last_update_id = 0

async def handle_telegram_command(text: str, chat_id: int):
    parts = text.split()
    command = parts[0].lower()
    
    if command == "/tutup" and len(parts) > 1:
        ticket_id_str = parts[1].replace("#", "")
        from api.zammad_webhook import zammad_client
        async with AsyncSessionLocal() as db:
            q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == ticket_id_str))
            ticket = q.scalar_one_or_none()
            if ticket:
                ticket.status = TicketStatus.CLOSED
                await db.commit()
                await zammad_client.update_ticket(int(ticket_id_str), "✅ Tiket ditutup dari Telegram oleh Admin.", state="closed")
                await send_telegram_message(f"✅ Tiket #{ticket_id_str} berhasil ditutup.", str(chat_id))
            else:
                await send_telegram_message(f"❌ Tiket #{ticket_id_str} tidak ditemukan.", str(chat_id))

    elif command == "/eskalasi" and len(parts) > 1:
        ticket_id_str = parts[1].replace("#", "")
        from api.zammad_webhook import zammad_client
        async with AsyncSessionLocal() as db:
            q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == ticket_id_str))
            ticket = q.scalar_one_or_none()
            if ticket:
                ticket.status = TicketStatus.ESCALATED
                ticket.escalated = True
                await db.commit()
                await zammad_client.update_ticket(int(ticket_id_str), "⚠️ TIKET DIESKALASI dari Telegram oleh Admin.")
                await send_telegram_message(f"✅ Tiket #{ticket_id_str} berhasil dieskalasi.", str(chat_id))
            else:
                await send_telegram_message(f"❌ Tiket #{ticket_id_str} tidak ditemukan.", str(chat_id))

async def start_telegram_polling():
    global _last_update_id
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning("[TelegramPolling] No bot token found.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    logger.info("[TelegramPolling] Started listening for commands...")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                payload = {"offset": _last_update_id + 1, "timeout": 30}
                async with session.post(url, json=payload, timeout=35) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for result in data.get("result", []):
                            update_id = result["update_id"]
                            _last_update_id = max(_last_update_id, update_id)
                            
                            message = result.get("message", {})
                            text = message.get("text", "")
                            chat_id = message.get("chat", {}).get("id")
                            
                            if text.startswith("/"):
                                await handle_telegram_command(text, chat_id)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"[TelegramPolling] Error: {e}")
                await asyncio.sleep(5)

@router.get("/logs")
async def get_telegram_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    # Join AuditLog -> Ticket -> Site
    # AuditLog.action == 'TELEGRAM_SENT'
    query = (
        select(AuditLog, Ticket, Site)
        .outerjoin(Ticket, AuditLog.ticket_id == cast(Ticket.ticket_id, String))
        .outerjoin(Site, Ticket.site_id == Site.site_id)
        .where(AuditLog.action == "TELEGRAM_SENT")
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    logs = []
    for log, ticket, site in rows:
        site_name = site.site_name if site else "Unknown Site"
        severity = ticket.severity if ticket else "UNKNOWN"
        zammad_id = ticket.zammad_ticket_id if ticket else log.ticket_id
        
        # If severity is Enum, extract value
        if hasattr(severity, 'value'):
            severity = severity.value
            
        logs.append({
            "sent_at": log.created_at.isoformat() if log.created_at else "",
            "ticket_id": zammad_id,
            "site_name": site_name,
            "telegram_group": log.target or "",
            "severity": severity,
            "sent_by": log.actor,
            "message_preview": (log.detail or "")[:200],
            "delivered": log.result == "SUCCESS"
        })
        
    return {"logs": logs}
