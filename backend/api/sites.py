"""
Sites API — Manage 18 Sam's Studio's cinema sites
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.site import Site
from models.device import Device

router = APIRouter(prefix="/api/sites", tags=["Sites"])


class CreateSiteRequest(BaseModel):
    site_name: str
    city: str
    timezone: str = "Asia/Jakarta"
    address: Optional[str] = None
    telegram_group_id: Optional[str] = None
    pic_primary: Optional[str] = None
    pic_primary_phone: Optional[str] = None
    pic_secondary: Optional[str] = None
    pic_secondary_phone: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def list_sites(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Site).where(Site.is_active == True).order_by(Site.site_name))
    sites = q.scalars().all()
    
    # Hitung manual karena return list of dicts
    result = []
    for s in sites:
        s_dict = s.to_dict()
        dev_q = await db.execute(select(Device).where(Device.site_id == s.site_id, Device.is_active == True))
        devices = dev_q.scalars().all()
        s_dict["device_count"] = len(devices)
        result.append(s_dict)
        
    return {"sites": result, "total": len(sites)}


@router.get("/{site_id}")
async def get_site(site_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Site).where(Site.site_id == site_id))
    site = q.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site.to_dict()


@router.get("/{site_id}/devices")
async def get_site_devices(site_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(Device).where(Device.site_id == site_id, Device.is_active == True)
    )
    devices = q.scalars().all()
    return {"devices": [d.to_dict() for d in devices]}


@router.post("/")
async def create_site(data: CreateSiteRequest, db: AsyncSession = Depends(get_db)):
    site = Site(**data.dict())
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site.to_dict()


@router.put("/{site_id}")
async def update_site(site_id: str, data: CreateSiteRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Site).where(Site.site_id == site_id))
    site = q.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    for k, v in data.dict(exclude_none=True).items():
        setattr(site, k, v)
    await db.commit()
    await db.refresh(site)
    return site.to_dict()


@router.delete("/{site_id}")
async def delete_site(site_id: str, db: AsyncSession = Depends(get_db)):
    # Cek apakah masih ada device di site ini
    q_devices = await db.execute(select(Device).where(Device.site_id == site_id))
    devices = q_devices.scalars().all()
    if len(devices) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete site. There are devices attached to this site. Delete or reassign them first.")
    
    q = await db.execute(select(Site).where(Site.site_id == site_id))
    site = q.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
        
    await db.delete(site)
    await db.commit()
    return {"message": "Site deleted successfully"}
