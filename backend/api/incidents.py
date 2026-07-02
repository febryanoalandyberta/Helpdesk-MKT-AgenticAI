"""
Incidents API — Incident memory management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models.incident import IncidentMemory

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


class CreateIncidentRequest(BaseModel):
    ticket_id: Optional[str] = None
    summary: str
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    site_name: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    tags: Optional[List[str]] = None
    sop_used: Optional[str] = None


@router.get("/")
async def list_incidents(
    category: Optional[str] = None,
    site_name: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(IncidentMemory).order_by(desc(IncidentMemory.created_at)).limit(limit)
    if category:
        query = query.where(IncidentMemory.category == category.upper())
    if site_name:
        query = query.where(IncidentMemory.site_name.ilike(f"%{site_name}%"))
    q = await db.execute(query)
    incidents = q.scalars().all()
    return {"incidents": [i.to_dict() for i in incidents], "total": len(incidents)}


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(IncidentMemory).where(IncidentMemory.incident_id == incident_id))
    incident = q.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.to_dict()


@router.post("/")
async def create_incident(data: CreateIncidentRequest, db: AsyncSession = Depends(get_db)):
    incident = IncidentMemory(**data.dict())
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident.to_dict()


@router.get("/audit-logs/")
async def list_audit_logs(
    ticket_id: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    from models.audit_log import AuditLog
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if ticket_id:
        query = query.where(AuditLog.ticket_id == ticket_id)
    if actor:
        query = query.where(AuditLog.actor.ilike(f"%{actor}%"))
    q = await db.execute(query)
    logs = q.scalars().all()
    return {"logs": [l.to_dict() for l in logs], "total": len(logs)}
