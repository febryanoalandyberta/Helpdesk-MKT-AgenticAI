"""
Database Module — SQLAlchemy Async Engine + Session
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine_kwargs = {"echo": settings.DEBUG}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    from sqlalchemy import text
    import logging
    async with engine.begin() as conn:
        from models import site, device, ticket, incident, user, audit_log, telemetry_history  # noqa
        await conn.run_sync(Base.metadata.create_all)
        
        # Initialize TimescaleDB Hypertable
        if not settings.DATABASE_URL.startswith("sqlite"):
            try:
                # Create hypertable
                await conn.execute(text("SELECT create_hypertable('telemetry_logs', by_range('time'), if_not_exists => TRUE);"))
                # Enable compression
                await conn.execute(text("ALTER TABLE telemetry_logs SET (timescaledb.compress);"))
                # Add retention policy (drop after 3 months)
                await conn.execute(text("SELECT add_retention_policy('telemetry_logs', INTERVAL '3 months', if_not_exists => TRUE);"))
                # Add compression policy (compress after 7 days)
                await conn.execute(text("SELECT add_compression_policy('telemetry_logs', INTERVAL '7 days', if_not_exists => TRUE);"))
            except Exception as e:
                logging.warning(f"TimescaleDB initialization error (usually safe to ignore if already configured): {e}")
