import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from database import AsyncSessionLocal
from models.ticket import Ticket, TicketStatus
from models.audit_log import AuditLog

logger = logging.getLogger(__name__)

async def background_scheduler_loop():
    """Run scheduled background tasks periodically."""
    logger.info("[BackgroundJobs] Scheduler started")
    while True:
        try:
            await check_sla_breaches()
            await cleanup_old_logs()
            await generate_weekly_report_job()
        except Exception as e:
            logger.error(f"[BackgroundJobs] Error in loop: {e}")
        
        # Run every 5 minutes
        await asyncio.sleep(300)

async def generate_weekly_report_job():
    """Membuat dan mengirim laporan mingguan PDF ke Telegram setiap Senin jam 08:00."""
    now = datetime.utcnow()
    # Senin = 0, jam 08:xx UTC (atau sesuaikan dengan UTC vs WIB)
    # Jika kita berasumsi server adalah UTC dan ingin WIB jam 08:00, maka UTC = 01:00.
    # Mari kita gunakan hari Senin (0) dan jam 1 UTC.
    if now.weekday() == 0 and now.hour == 1:
        # Untuk mencegah report dibuat berulang-ulang dalam 1 jam, kita cek audit log
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            today_str = now.strftime('%Y-%m-%d')
            q = await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "WEEKLY_REPORT_SENT",
                    AuditLog.detail.like(f"%{today_str}%")
                )
            )
            already_sent = q.scalar_one_or_none()
            
            if not already_sent:
                from api.report_generator import generate_weekly_pdf_report
                from api.telegram import send_telegram_document
                import os
                
                filepath = f"temp/Weekly_Report_{today_str}.pdf"
                await generate_weekly_pdf_report(db, filepath)
                
                caption = "📊 *Laporan Mingguan Helpdesk MKT AI*\n\nBerikut adalah rangkuman performa penanganan tiket selama 7 hari terakhir."
                success = await send_telegram_document(filepath, caption)
                
                if success:
                    db.add(AuditLog(
                        ticket_id="SYSTEM",
                        actor="system",
                        action="WEEKLY_REPORT_SENT",
                        result="SUCCESS",
                        detail=f"Report sent for {today_str}"
                    ))
                    await db.commit()
                    logger.info("[BackgroundJobs] Weekly PDF report generated and sent successfully.")
                    
                if os.path.exists(filepath):
                    os.remove(filepath)

async def check_sla_breaches():
    """SLA Early Warning System: Notify if ticket is open for > 2 hours."""
    from api.telegram import send_telegram_message
    
    async with AsyncSessionLocal() as db:
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        
        # Cari tiket open yang umurnya sudah melebihi 2 jam tapi belum tertandai sla_breached
        q = await db.execute(
            select(Ticket).where(
                Ticket.status.in_([TicketStatus.NEW, TicketStatus.TIER1_PROCESSING]),
                Ticket.created_at <= two_hours_ago,
                Ticket.sla_breached == False
            )
        )
        tickets = q.scalars().all()
        
        for t in tickets:
            t.sla_breached = True
            await db.commit()
            
            # Kirim peringatan ke Telegram
            message = (
                f"🚨 <b>URGENT SLA WARNING</b> 🚨\n\n"
                f"<b>Ticket ID:</b> #{t.zammad_ticket_id or str(t.ticket_id)[:8]}\n"
                f"<b>Judul:</b> {t.title}\n"
                f"<b>Durasi:</b> Lebih dari 2 Jam!\n\n"
                f"Mohon tim teknis segera mengambil alih penanganan tiket ini."
            )
            await send_telegram_message(message)
            logger.warning(f"[SLA] Ticket {t.ticket_id} breached SLA (2 hours)")

async def cleanup_old_logs():
    """Pembersihan Otomatis: Hapus audit log yang lebih dari 30 hari pada jam 3 pagi."""
    now = datetime.utcnow()
    # Hanya jalankan jika jam menunjukkan pukul 03:xx (UTC)
    if now.hour == 3:
        async with AsyncSessionLocal() as db:
            thirty_days_ago = now - timedelta(days=30)
            
            try:
                # Delete logs older than 30 days
                stmt = delete(AuditLog).where(AuditLog.created_at < thirty_days_ago)
                result = await db.execute(stmt)
                await db.commit()
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(f"[Cleanup] Berhasil menghapus {deleted_count} baris log lama (>30 hari).")
            except Exception as e:
                logger.error(f"[Cleanup] Gagal menghapus log lama: {e}")
