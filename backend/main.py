"""
Helpdesk MKT Agentic AI Automation
FastAPI Main Application Entry Point
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import os

from config import settings
from database import init_db
from api.tickets import router as tickets_router
from api.sites import router as sites_router
from api.devices import router as devices_router
from api.dashboard import router as dashboard_router
from api.auth import router as auth_router
from api.incidents import router as incidents_router
from api.users import router as users_router
from api.telegram import router as telegram_router
from api.tier1 import router as tier1_router
from api.zammad_webhook import router as zammad_router, start_zammad_polling
from api.agent_chat import router as agent_chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("  MKT Helpdesk Agentic AI — Starting Up")
    logger.info("=" * 60)

    # Initialize database
    try:
        await init_db()
        logger.info("[DB] Database tables initialized successfully")
    except Exception as e:
        logger.error(f"[DB] Failed to initialize database: {e}")

    # Seed initial data if empty
    try:
        await seed_initial_data()
    except Exception as e:
        logger.warning(f"[Seed] Seed skipped or failed: {e}")

    # Start Zammad polling background task (Step 2: Sistem mengambil tiket baru dari Zammad)
    asyncio.create_task(start_zammad_polling())
    logger.info("[Zammad] Background polling started")

    # Start Background Jobs (SLA Monitoring & Log Cleanup)
    from api.background_jobs import background_scheduler_loop
    asyncio.create_task(background_scheduler_loop())
    logger.info("[BackgroundJobs] Task scheduler started")

    # Start Telegram Polling (Two-Way Interactive)
    from api.telegram import start_telegram_polling
    asyncio.create_task(start_telegram_polling())
    logger.info("[Telegram] Long polling started")

    logger.info("[APP] Application ready — MKT Helpdesk AI is online")
    yield

    logger.info("[APP] Shutting down MKT Helpdesk AI")


app = FastAPI(
    title="Helpdesk MKT Agentic AI Automation",
    description=(
        "Enterprise AI-powered IT Helpdesk system for PT Megakreasi Tech (MKT). "
        "Manages 18 Sam's Studio's cinema sites with 72 POS devices using CrewAI multi-agent system."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tickets_router)
app.include_router(sites_router)
app.include_router(devices_router)
app.include_router(dashboard_router)
app.include_router(incidents_router)
app.include_router(telegram_router, prefix="/api/telegram", tags=["telegram"])
app.include_router(tier1_router, prefix="/api/tier1", tags=["tier1"])
app.include_router(zammad_router)
app.include_router(agent_chat_router)

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }


async def seed_initial_data():
    """Seed 18 Sam's Studio's sites and 72 POS devices on first run."""
    from database import AsyncSessionLocal
    from models.site import Site
    from models.device import Device
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        count_q = await db.execute(select(func.count(Site.site_id)))
        count = count_q.scalar()
        if count and count > 0:
            logger.info(f"[Seed] Database already has {count} sites, skipping seed.")
            return

        sites_data = [
            {"site_name": "Sam's Studio's Jakarta Pusat", "city": "Jakarta Pusat"},
            {"site_name": "Sam's Studio's Jakarta Selatan", "city": "Jakarta Selatan"},
            {"site_name": "Sam's Studio's Jakarta Barat", "city": "Jakarta Barat"},
            {"site_name": "Sam's Studio's Jakarta Utara", "city": "Jakarta Utara"},
            {"site_name": "Sam's Studio's Jakarta Timur", "city": "Jakarta Timur"},
            {"site_name": "Sam's Studio's Bandung", "city": "Bandung"},
            {"site_name": "Sam's Studio's Surabaya", "city": "Surabaya"},
            {"site_name": "Sam's Studio's Medan", "city": "Medan"},
            {"site_name": "Sam's Studio's Makassar", "city": "Makassar"},
            {"site_name": "Sam's Studio's Semarang", "city": "Semarang"},
            {"site_name": "Sam's Studio's Yogyakarta", "city": "Yogyakarta"},
            {"site_name": "Sam's Studio's Palembang", "city": "Palembang"},
            {"site_name": "Sam's Studio's Balikpapan", "city": "Balikpapan"},
            {"site_name": "Sam's Studio's Pekanbaru", "city": "Pekanbaru"},
            {"site_name": "Sam's Studio's Malang", "city": "Malang"},
            {"site_name": "Sam's Studio's Denpasar", "city": "Denpasar"},
            {"site_name": "Sam's Studio's Tangerang", "city": "Tangerang"},
            {"site_name": "Sam's Studio's Bekasi", "city": "Bekasi"},
        ]

        device_types = [
            ("POS Ticketing 01", "POS_TICKETING"),
            ("POS Ticketing 02", "POS_TICKETING"),
            ("POS FNB 01", "POS_FNB"),
            ("POS FNB 02", "POS_FNB"),
        ]

        for i, site_d in enumerate(sites_data, 1):
            site = Site(
                site_name=site_d["site_name"],
                city=site_d["city"],
                timezone="Asia/Jakarta",
                pic_primary=f"PIC Primary Site {i}",
                pic_primary_phone=f"+62812{1000000 + i}",
                pic_secondary=f"PIC Secondary Site {i}",
            )
            db.add(site)
            await db.flush()

            for j, (dev_name, dev_type) in enumerate(device_types, 1):
                device = Device(
                    site_id=site.site_id,
                    device_name=f"{dev_name} - {site_d['city']}",
                    device_type=dev_type,
                    ip_address=f"192.168.{i}.{j * 10}",
                    operating_system="Windows 10",
                    os_version="22H2",
                    hardware_model="POS Terminal X200",
                    ssh_port="22",
                )
                db.add(device)

        await db.commit()
        logger.info("[Seed] ✅ Seeded 18 sites and 72 POS devices successfully!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
