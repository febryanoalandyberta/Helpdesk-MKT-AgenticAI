import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket
from api.tickets import process_ticket_ai
import uuid

async def main():
    async with AsyncSessionLocal() as db:
        ticket = Ticket(title="Test Ticket", description="Test", status="NEW")
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        
        ticket_id = str(ticket.ticket_id)
        print("Before processing, AI Rec:", repr(ticket.ai_recommendation))
        
        # Simulate what process_ticket_ai does in another session
        async with AsyncSessionLocal() as db2:
            from sqlalchemy import select
            q = await db2.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
            t2 = q.scalar_one()
            t2.ai_recommendation = "HELLO WORLD"
            await db2.commit()
            
        # Back to session 1
        await db.refresh(ticket)
        print("After refresh, AI Rec:", repr(ticket.ai_recommendation))
        
        # Cleanup
        await db.delete(ticket)
        await db.commit()

asyncio.run(main())
