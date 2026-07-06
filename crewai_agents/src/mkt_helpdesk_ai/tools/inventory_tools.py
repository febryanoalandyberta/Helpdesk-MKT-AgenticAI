"""
Site Lookup & Device Lookup Tools — Tier 0 Agent Tools
Sesuai instruksi.md Section 6: Tier 0 Tools:
  - site_lookup
  - device_lookup
"""
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from loguru import logger


class SiteLookupInput(BaseModel):
    query: str = Field(..., description="Site name, city, or site_id to search for")


class SiteLookup(BaseTool):
    name: str = "site_lookup"
    description: str = (
        "Look up site information by name, city, or site ID. "
        "Returns site details including PIC contacts and Telegram group ID. "
        "Use this to identify which site is affected by the ticket."
    )
    args_schema: type = SiteLookupInput

    def _run(self, query: str) -> Dict[str, Any]:
        try:
            import asyncio
            from database import AsyncSessionLocal
            from models.site import Site
            from sqlalchemy import select, or_

            async def _fetch():
                async with AsyncSessionLocal() as db:
                    q = await db.execute(
                        select(Site).where(
                            or_(
                                Site.site_name.ilike(f"%{query}%"),
                                Site.city.ilike(f"%{query}%"),
                                Site.site_id.cast(str) == query,
                            )
                        ).limit(5)
                    )
                    sites = q.scalars().all()
                    return [s.to_dict() for s in sites]

            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(_fetch())
            loop.close()

            logger.info(f"[SiteLookup] Found {len(results)} sites for query: '{query}'")
            return {"success": True, "sites": results, "total": len(results)}
        except Exception as e:
            logger.error(f"[SiteLookup] Error: {e}")
            return {"success": False, "sites": [], "error": str(e)}


class DeviceLookupInput(BaseModel):
    query: str = Field(..., description="Device name, IP address, hostname, or device_id to search for")
    site_id: Optional[str] = Field(None, description="Optional site_id to filter devices by site")
    device_type: Optional[str] = Field(None, description="Filter by device type: POS_TICKETING or POS_FNB")


class DeviceLookup(BaseTool):
    name: str = "device_lookup"
    description: str = (
        "Look up POS device information by name, IP address, hostname, or device ID. "
        "Returns device details including IP address, OS, credentials reference, and status. "
        "Use this to identify the specific device affected by the ticket."
    )
    args_schema: type = DeviceLookupInput

    def _run(self, query: str, site_id: Optional[str] = None,
             device_type: Optional[str] = None) -> Dict[str, Any]:
        try:
            import asyncio
            from database import AsyncSessionLocal
            from models.device import Device
            from sqlalchemy import select, or_

            async def _fetch():
                async with AsyncSessionLocal() as db:
                    conditions = [
                        Device.device_name.ilike(f"%{query}%"),
                        Device.ip_address.ilike(f"%{query}%"),
                        Device.hostname.ilike(f"%{query}%"),
                    ]
                    q = select(Device).where(or_(*conditions))
                    if site_id:
                        q = q.where(Device.site_id == site_id)
                    if device_type:
                        q = q.where(Device.device_type == device_type.upper())
                    q = q.limit(10)
                    result = await db.execute(q)
                    devices = result.scalars().all()
                    
                    # Fuzzy Matching Fallback
                    if not devices:
                        import difflib
                        fq = select(Device)
                        if site_id:
                            fq = fq.where(Device.site_id == site_id)
                        if device_type:
                            fq = fq.where(Device.device_type == device_type.upper())
                            
                        all_res = await db.execute(fq)
                        all_devices = all_res.scalars().all()
                        
                        device_names = [d.device_name for d in all_devices]
                        # Find closest matches with a low cutoff to allow significant typos
                        closest = difflib.get_close_matches(query, device_names, n=3, cutoff=0.3)
                        
                        if closest:
                            logger.info(f"[DeviceLookup] Exact match failed. Fuzzy matched '{query}' to {closest}")
                            devices = [d for d in all_devices if d.device_name in closest]

                    return [d.to_dict() for d in devices]

            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(_fetch())
            loop.close()

            logger.info(f"[DeviceLookup] Found {len(results)} devices for query: '{query}'")
            return {"success": True, "devices": results, "total": len(results)}
        except Exception as e:
            logger.error(f"[DeviceLookup] Error: {e}")
            return {"success": False, "devices": [], "error": str(e)}


class InventoryTools:
    @staticmethod
    def get_all() -> list:
        return [SiteLookup(), DeviceLookup()]
