import asyncio
from database import engine, Base
from models import incident
from sqlalchemy import text

async def run():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT created_at, summary FROM incident_memories ORDER BY created_at DESC LIMIT 5"))
        for row in result.fetchall():
            print(row)

asyncio.run(run())
