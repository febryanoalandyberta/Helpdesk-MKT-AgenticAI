import asyncio
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))
from database import engine

async def alter_table():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE devices ALTER COLUMN site_id DROP NOT NULL;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN cpu_usage DOUBLE PRECISION;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN ram_usage DOUBLE PRECISION;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN disk_usage DOUBLE PRECISION;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN temperature DOUBLE PRECISION;"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN current_active_app VARCHAR(200);"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN current_active_url VARCHAR(500);"))
            await conn.execute(text("ALTER TABLE devices ADD COLUMN last_health_check TIMESTAMP;"))
            print("Successfully added columns to devices table.")
        except Exception as e:
            print(f"Error altering table: {e}")

if __name__ == "__main__":
    asyncio.run(alter_table())
