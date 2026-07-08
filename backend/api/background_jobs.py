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
            await check_zammad_health()
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

async def check_zammad_health():
    """State machine memonitor kesehatan Zammad persisten via DB dengan Debounce 3x."""
    from api.zammad_webhook import zammad_client
    import httpx
    from database import AsyncSessionLocal
    from sqlalchemy import select, desc
    
    current_status = "OFFLINE"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{zammad_client.base_url}/api/v1/users/me",
                headers=zammad_client.headers,
            )
            if resp.status_code == 200:
                current_status = "ONLINE"
    except Exception:
        current_status = "OFFLINE"

    from api.telegram import send_telegram_message

    async with AsyncSessionLocal() as db:
        # Get past status
        q = await db.execute(
            select(AuditLog)
            .where(AuditLog.action == "ZAMMAD_HEALTH_TRANSITION")
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        last_transition = q.scalar_one_or_none()
        past_status = last_transition.detail if last_transition else "ONLINE"
        
        # Get consecutive fails
        q_fails = await db.execute(
            select(AuditLog)
            .where(AuditLog.action == "ZAMMAD_PING_FAIL")
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        last_fail = q_fails.scalar_one_or_none()
        fail_count = 0
        if last_fail and "Count: " in last_fail.detail:
            try:
                fail_count = int(last_fail.detail.split("Count: ")[-1])
            except:
                fail_count = 0

        if current_status == "OFFLINE":
            fail_count += 1
            db.add(AuditLog(
                ticket_id="SYSTEM", actor="HealthCheck", action="ZAMMAD_PING_FAIL",
                result="FAILED", detail=f"Ping failed. Count: {fail_count}"
            ))
            
            if past_status == "ONLINE" and fail_count >= 3:
                logger.warning("[HealthCheck] Zammad went OFFLINE! (Debounce threshold met)")
                await send_telegram_message("🚨 <b>DARURAT: KONEKSI ZAMMAD TERPUTUS!</b> 🚨\nSistem gagal terhubung ke Zammad sebanyak 3 kali berturut-turut (15 menit). Penarikan otomatis ditangguhkan sementara.")
                db.add(AuditLog(
                    ticket_id="SYSTEM", actor="HealthCheck", action="ZAMMAD_HEALTH_TRANSITION",
                    result="SUCCESS", detail="OFFLINE"
                ))
            await db.commit()

        elif current_status == "ONLINE":
            if fail_count > 0:
                db.add(AuditLog(
                    ticket_id="SYSTEM", actor="HealthCheck", action="ZAMMAD_PING_FAIL",
                    result="SUCCESS", detail="Ping success. Count: 0"
                ))
                
            if past_status == "OFFLINE":
                logger.info("[HealthCheck] Zammad is back ONLINE!")
                await send_telegram_message("✅ <b>INFO: ZAMMAD KEMBALI ONLINE!</b> ✅\nSistem berhasil terhubung kembali. Memulai Auto-Sync untuk tiket yang tertahan...")
                db.add(AuditLog(
                    ticket_id="SYSTEM", actor="HealthCheck", action="ZAMMAD_HEALTH_TRANSITION",
                    result="SUCCESS", detail="ONLINE"
                ))
                asyncio.create_task(auto_sync_pending_tickets())
                
            await db.commit()

async def auto_sync_pending_tickets():
    """Menarik semua tiket yang ID Zammad-nya NULL lalu mencoba disinkronkan. Maks 3 percobaan."""
    from api.zammad_webhook import zammad_client
    from database import AsyncSessionLocal
    from sqlalchemy import select, func
    from api.telegram import send_telegram_message
    
    logger.info("[AutoSync] Starting auto-sync for pending tickets...")
    success_count = 0
    fail_count = 0
    
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == None))
        pending_tickets = q.scalars().all()
        
        for t in pending_tickets:
            fail_q = await db.execute(
                select(func.count(AuditLog.id)).where(
                    AuditLog.ticket_id == str(t.ticket_id),
                    AuditLog.action == "ZAMMAD_SYNC_FAILED"
                )
            )
            failed_attempts = fail_q.scalar() or 0
            
            if failed_attempts >= 3:
                logger.warning(f"[AutoSync] Skipping ticket {t.ticket_id} (Failed {failed_attempts} times)")
                continue
                
            logger.info(f"[AutoSync] Attempting to sync ticket {t.ticket_id}")
            customer_email = t.reporter_email or "febryanoit@megakreasitech.com"
            zammad_id = await zammad_client.create_ticket(
                title=t.title,
                body=t.description or "No description",
                customer=customer_email
            )
            
            if zammad_id:
                t.zammad_ticket_id = str(zammad_id)
                db.add(AuditLog(
                    ticket_id=str(t.ticket_id),
                    actor="AutoSync",
                    action="ZAMMAD_SYNC_SUCCESS",
                    result="SUCCESS",
                    detail=f"Synced as #{zammad_id}"
                ))
                await db.commit()
                success_count += 1
            else:
                db.add(AuditLog(
                    ticket_id=str(t.ticket_id),
                    actor="AutoSync",
                    action="ZAMMAD_SYNC_FAILED",
                    result="FAILED",
                    detail=f"Attempt {failed_attempts + 1}"
                ))
                await db.commit()
                fail_count += 1
                
    if success_count > 0 or fail_count > 0:
        msg = f"🔄 <b>Laporan Auto-Sync Zammad</b> 🔄\n\n✅ Berhasil: {success_count} Tiket\n❌ Gagal: {fail_count} Tiket\n\n<i>Tiket yang tertahan telah diproses.</i>"
        await send_telegram_message(msg)
