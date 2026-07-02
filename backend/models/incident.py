"""
Incident Memory Model — Long-term AI memory for past incidents
Used by CrewAI Knowledge Agent for pattern matching
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from database import Base


class IncidentMemory(Base):
    __tablename__ = "incident_memories"

    incident_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(100), nullable=True)

    # Core Memory Fields
    summary = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=True)

    # Site/Device Context
    site_name = Column(String(200), nullable=True)
    device_name = Column(String(200), nullable=True)
    device_type = Column(String(100), nullable=True)

    # AI Fields
    tags = Column(JSON, nullable=True)           # ["network", "pos", "printer"]
    embedding_id = Column(String(500), nullable=True)  # ChromaDB document ID

    # Resolution Metrics
    resolution_time_minutes = Column(Integer, nullable=True)
    tier_resolved = Column(Integer, default=0)
    confidence_at_resolution = Column(Float, nullable=True)

    # Knowledge Base Reference
    sop_used = Column(String(500), nullable=True)
    successful = Column(Integer, default=1)  # 1=success, 0=failed

    # Timestamps
    occurred_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<IncidentMemory {self.incident_id} [{self.category}]>"

    def to_dict(self):
        return {
            "incident_id": str(self.incident_id),
            "ticket_id": self.ticket_id,
            "summary": self.summary,
            "root_cause": self.root_cause,
            "resolution": self.resolution,
            "category": self.category,
            "severity": self.severity,
            "site_name": self.site_name,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "tags": self.tags,
            "resolution_time_minutes": self.resolution_time_minutes,
            "tier_resolved": self.tier_resolved,
            "confidence_at_resolution": self.confidence_at_resolution,
            "sop_used": self.sop_used,
            "successful": self.successful,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
