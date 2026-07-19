import asyncio
from database import engine, Base
from models import incident
from sqlalchemy import text
from datetime import datetime

async def run():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT created_at, category, device_name, summary FROM incident_memories ORDER BY created_at DESC"))
        rows = result.fetchall()
        print(f"Total records in incident_memories: {len(rows)}")
        print("-" * 50)
        for row in rows:
            print(f"[{row[0]}] {row[1]} - {row[2]}: {row[3]}")

asyncio.run(run())
