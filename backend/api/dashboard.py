"""
Dashboard API — Real-time monitoring metrics endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime, timedelta
from database import get_db
from models.ticket import Ticket, TicketStatus, TicketSeverity
from models.site import Site
from models.device import Device, DeviceStatus
from models.incident import IncidentMemory
from models.audit_log import AuditLog

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """Main dashboard overview metrics."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Open tickets
    open_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
        )
    )
    open_tickets = open_q.scalar() or 0

    # Total tickets today
    today_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(Ticket.created_at >= today_start)
    )
    tickets_today = today_q.scalar() or 0

    # Resolved today
    resolved_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.resolved_at >= today_start
        )
    )
    resolved_today = resolved_q.scalar() or 0

    # SLA breached
    sla_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(Ticket.sla_breached == True)
    )
    sla_breached = sla_q.scalar() or 0

    # Auto-resolved (confidence >= 85, tier_level = 0)
    auto_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.tier_level == 0,
            Ticket.confidence_score >= 85,
        )
    )
    auto_resolved = auto_q.scalar() or 0

    # Total resolved all time
    total_resolved_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]))
    )
    total_resolved = total_resolved_q.scalar() or 1  # Avoid division by zero

    # MTTR (average resolution time in minutes)
    mttr_q = await db.execute(
        select(func.avg(
            func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 60
        )).where(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            Ticket.resolved_at.isnot(None)
        )
    )
    mttr_minutes = mttr_q.scalar() or 0

    # Active devices count
    device_q = await db.execute(
        select(func.count(Device.device_id)).where(Device.is_active == True)
    )
    total_devices = device_q.scalar() or 0

    # Online devices
    online_q = await db.execute(
        select(func.count(Device.device_id)).where(Device.status == DeviceStatus.ONLINE)
    )
    online_devices = online_q.scalar() or 0

    return {
        "open_tickets": open_tickets,
        "tickets_today": tickets_today,
        "resolved_today": resolved_today,
        "sla_breached": sla_breached,
        "auto_resolution_rate": round((auto_resolved / total_resolved) * 100, 1),
        "mttr_minutes": round(float(mttr_minutes), 1),
        "total_devices": total_devices,
        "online_devices": online_devices,
        "device_availability_pct": round((online_devices / max(total_devices, 1)) * 100, 1),
        "updated_at": now.isoformat(),
    }


@router.get("/tickets-by-severity")
async def tickets_by_severity(db: AsyncSession = Depends(get_db)):
    """Ticket count grouped by severity."""
    q = await db.execute(
        select(Ticket.severity, func.count(Ticket.ticket_id))
        .where(Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]))
        .group_by(Ticket.severity)
    )
    rows = q.all()
    return {"data": [{"severity": r[0], "count": r[1]} for r in rows]}


@router.get("/tickets-by-category")
async def tickets_by_category(db: AsyncSession = Depends(get_db)):
    """Ticket count grouped by category."""
    q = await db.execute(
        select(Ticket.category, func.count(Ticket.ticket_id))
        .group_by(Ticket.category)
    )
    rows = q.all()
    return {"data": [{"category": r[0], "count": r[1]} for r in rows]}


@router.get("/tickets-by-status")
async def tickets_by_status(db: AsyncSession = Depends(get_db)):
    """Ticket count grouped by status."""
    q = await db.execute(
        select(Ticket.status, func.count(Ticket.ticket_id)).group_by(Ticket.status)
    )
    rows = q.all()
    return {"data": [{"status": r[0], "count": r[1]} for r in rows]}


@router.get("/site-health")
async def site_health(db: AsyncSession = Depends(get_db)):
    """Per-site device health summary."""
    q = await db.execute(
        select(
            Site.site_name,
            Site.city,
            func.count(Device.device_id).label("total"),
            func.sum(case((Device.status == DeviceStatus.ONLINE, 1), else_=0)).label("online"),
            func.sum(case((Device.status == DeviceStatus.OFFLINE, 1), else_=0)).label("offline"),
        )
        .join(Device, Device.site_id == Site.site_id, isouter=True)
        .where(Site.is_active == True)
        .group_by(Site.site_name, Site.city)
        .order_by(Site.site_name)
    )
    rows = q.all()
    return {
        "sites": [
            {
                "site_name": r[0],
                "city": r[1],
                "total_devices": r[2] or 0,
                "online": r[3] or 0,
                "offline": r[4] or 0,
                "health_pct": round(((r[3] or 0) / max((r[2] or 1), 1)) * 100, 1),
            }
            for r in rows
        ]
    }


@router.get("/recent-tickets")
async def recent_tickets(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Most recently created tickets."""
    q = await db.execute(
        select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
    )
    tickets = q.scalars().all()
    return {"tickets": [t.to_dict() for t in tickets]}


@router.get("/confidence-trend")
async def confidence_trend(days: int = 7, db: AsyncSession = Depends(get_db)):
    """Average AI confidence score per day for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    q = await db.execute(
        select(
            func.date(Ticket.created_at).label("date"),
            func.avg(Ticket.confidence_score).label("avg_confidence"),
            func.count(Ticket.ticket_id).label("total"),
        )
        .where(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
    )
    rows = q.all()
    return {
        "data": [
            {
                "date": str(r[0]),
                "avg_confidence": round(float(r[1] or 0), 1),
                "total_tickets": r[2],
            }
            for r in rows
        ]
    }


@router.get("/escalation-stats")
async def escalation_stats(db: AsyncSession = Depends(get_db)):
    """Escalation statistics."""
    total_q = await db.execute(select(func.count(Ticket.ticket_id)))
    total = total_q.scalar() or 1

    escalated_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(Ticket.escalated == True)
    )
    escalated = escalated_q.scalar() or 0

    tier1_q = await db.execute(
        select(func.count(Ticket.ticket_id)).where(Ticket.tier_level == 1)
    )
    tier1 = tier1_q.scalar() or 0

    return {
        "total_tickets": total,
        "escalated": escalated,
        "tier1_processed": tier1,
        "escalation_rate": round((escalated / total) * 100, 1),
        "tier1_rate": round((tier1 / total) * 100, 1),
    }
