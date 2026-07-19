import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket
from sqlalchemy import select, desc
async def main():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Ticket).order_by(desc(Ticket.created_at)).limit(1))
        t = q.scalar_one_or_none()
        print("TICKET ID:", t.ticket_id)
        print("AI RECOM:", repr(t.ai_recommendation))
asyncio.run(main())
