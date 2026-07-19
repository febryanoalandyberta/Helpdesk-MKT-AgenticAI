import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Ticket).where(Ticket.zammad_ticket_id == 'HW/MKT-HO/19-07-2026'))
        t = q.scalar_one_or_none()
        if t:
            print("TICKET FOUND!")
            print("ID:", t.ticket_id)
            print("Zammad:", t.zammad_ticket_id)
            print("AI Recommendation:", repr(t.ai_recommendation))
            print("Created At:", t.created_at)
            print("Updated At:", t.updated_at)
        else:
            print("TICKET NOT FOUND BY ZAMMAD ID")
asyncio.run(main())
