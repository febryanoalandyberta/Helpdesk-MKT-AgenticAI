"""
Port Checker Log Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class PortCheckerLog(Base):
    __tablename__ = "port_checker_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(100), nullable=True) # Optional since older hardware agents might not send it, but they should.
    device_name = Column(String(200), nullable=True)
    device_type = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    summary = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PortCheckerLog {self.log_id} [{self.category}]>"

    def to_dict(self):
        return {
            "log_id": str(self.log_id),
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "category": self.category,
            "summary": self.summary,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
