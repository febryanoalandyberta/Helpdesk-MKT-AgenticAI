"""
Audit Log Model — All agent and user actions recorded
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(100), nullable=True)
    actor = Column(String(200), nullable=False)       # "Tier0Agent", "Tier1Agent", "user:admin"
    action = Column(String(500), nullable=False)       # "TICKET_ANALYZED", "SSH_CONNECT", etc.
    target = Column(String(500), nullable=True)        # IP address, device_id, etc.
    result = Column(String(50), nullable=True)         # "SUCCESS", "FAILED", "ESCALATED"
    detail = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    ip_source = Column(String(50), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AuditLog {self.actor}::{self.action} [{self.result}]>"

    def to_dict(self):
        return {
            "log_id": str(self.log_id),
            "ticket_id": self.ticket_id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "result": self.result,
            "detail": self.detail,
            "metadata": self.meta_data,
            "ip_source": self.ip_source,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
