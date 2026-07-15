import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket
from sqlalchemy import select, desc

async def main():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Ticket).order_by(desc(Ticket.created_at)).limit(5))
        tickets = q.scalars().all()
        for t in tickets:
            print(f"ID: {t.zammad_ticket_id}, Title: {t.title}, Status: {t.status}")

asyncio.run(main())
