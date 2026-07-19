import asyncio
from database import AsyncSessionLocal
from models.device import Device
from models.port_checker import PortCheckerLog
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Device).where(Device.device_name.ilike('%DCP-ENCODER%')))
        device = q.scalar_one_or_none()
        if not device:
            q = await db.execute(select(Device).limit(1))
            device = q.scalar_one_or_none()
        
        if not device:
            print("No devices found in DB.")
            return

        log = PortCheckerLog(
            device_id=str(device.device_id),
            device_name=device.device_name,
            device_type="HDMI/Display",
            category="HARDWARE_FAILURE",
            summary="Display monitor disconnected: TEST-MONITOR-001"
        )
        db.add(log)
        await db.commit()
        print(f"Injected into {device.device_name} (ID: {device.device_id})")

asyncio.run(main())
