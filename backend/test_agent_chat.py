import asyncio
from database import AsyncSessionLocal
from models.ticket import Ticket
from api.tickets import process_ticket_ai

async def main():
    async with AsyncSessionLocal() as db:
        # Create ticket
        ticket = Ticket(
            title="Test Simulation",
            description="Second display suka berkedip",
            status="NEW"
        )
        db.add(ticket)
        await db.commit()
        
        ticket_id = str(ticket.ticket_id)
        
        # Trigger AI
        try:
            await process_ticket_ai(ticket_id)
            await db.refresh(ticket)
            
            raw = ticket.ai_recommendation or ""
            print("RAW AFTER PROCESS:", repr(raw))
            
            internal_keywords = [
                "Remember to follow ALL the rules",
                "Your job is on the line",
                "Thought:", "Action:", "Action Input:", "Observation:",
                "Final Answer:", "I need to", "I should", "I will",
                "Human:", "Assistant:", "System:", "> Entering", "> Finished",
            ]
            has_leak = any(kw.lower() in raw.lower() for kw in internal_keywords)
            import re
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', raw))

            if has_leak or has_chinese or not raw.strip():
                print("FALLBACK TRIGGERED!")
            else:
                print("SUCCESS: ", raw)
                
        except Exception as e:
            print("EXCEPTION:", e)
            
asyncio.run(main())
