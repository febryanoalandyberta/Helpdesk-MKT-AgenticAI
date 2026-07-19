from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    # In TimescaleDB hypertables, the time column must be part of the primary key
    # if we want to use a composite primary key, or we just rely on time + device_id.
    # For a hypertable, it's common to not have a surrogate serial primary key, 
    # but SQLAlchemy requires at least one primary key.
    
    from sqlalchemy.dialects.postgresql import UUID
    time = Column(DateTime, primary_key=True, default=datetime.utcnow)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    
    cpu_usage = Column(Float, nullable=True)
    ram_usage = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    
    active_app = Column(String(255), nullable=True)
    active_url = Column(String(1000), nullable=True)

    # Relationship
    device = relationship("Device", backref="telemetry_history")

    def to_dict(self):
        return {
            "time": self.time.isoformat() + "Z" if self.time else None,
            "device_id": str(self.device_id),
            "cpu_usage": self.cpu_usage,
            "ram_usage": self.ram_usage,
            "temperature": self.temperature,
            "active_app": self.active_app,
            "active_url": self.active_url
        }
