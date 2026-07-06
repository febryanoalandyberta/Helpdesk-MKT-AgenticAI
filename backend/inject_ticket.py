import sys, asyncio
sys.path.insert(0, '/app')
from database import AsyncSessionLocal
from models.ticket import Ticket, TicketSeverity
from models.site import Site
from sqlalchemy import select
from api.zammad_webhook import trigger_ai_for_new_ticket

async def create_ticket():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Site).where(Site.site_name.ilike('%cianjur%')))
        site = q.scalar_one_or_none()
        
        desc = 'No Laporan : NW/CNJ/2 Juli 2026\nProblem : POS Tiketing tidak bisa akses internet\nSite : Cianjur\nEquipment : POS Tiketing\nPIC : Anna\nDetail Problem : POS tiketing tidak bisa akses internet , solusi yang sudah dilakukan restart PC dan cabut colok kabel LAN'
        
        t = Ticket(
            zammad_ticket_id='9999',
            title='Manual Report: POS Tiketing Internet Issue',
            description=desc,
            status='Open',
            severity=TicketSeverity.HIGH,
            site_id=site.site_id if site else None
        )
        db.add(t)
        await db.commit()
        await db.refresh(t)
        print(f'Ticket created: {t.ticket_id}')
        
        # Trigger API
        await trigger_ai_for_new_ticket(str(t.ticket_id))
        print('AI processing triggered.')

asyncio.run(create_ticket())
