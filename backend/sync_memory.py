import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket, TicketStatus
from models.incident import IncidentMemory
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Ticket).where(Ticket.status.in_([TicketStatus.CLOSED, TicketStatus.RESOLVED])))
        tickets = q.scalars().all()
        
        for t in tickets:
            # Check if it already exists
            iq = await db.execute(select(IncidentMemory).where(IncidentMemory.ticket_id == str(t.ticket_id)))
            existing = iq.scalar_one_or_none()
            if not existing:
                memory = IncidentMemory(
                    ticket_id=str(t.ticket_id),
                    summary=t.title,
                    root_cause=t.root_cause or "Tidak diketahui",
                    resolution=t.resolution or t.ai_recommendation or "Diselesaikan secara manual",
                    category=t.category or "OTHER",
                    severity=t.severity.value if hasattr(t.severity, 'value') else str(t.severity),
                    site_name="Sams Studio",
                    device_name="POS Terminal",
                )
                db.add(memory)
                print(f"Added {t.title} to Incident Memory")
                
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
