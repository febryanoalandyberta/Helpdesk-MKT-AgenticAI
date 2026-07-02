"""
Ticket Model — Helpdesk ticket from Zammad
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Float, Text, Enum, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class TicketSeverity(str, PyEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketStatus(str, PyEnum):
    NEW = "NEW"
    ANALYZING = "ANALYZING"
    TIER0_PROCESSING = "TIER0_PROCESSING"
    TIER1_PROCESSING = "TIER1_PROCESSING"
    WAITING_INFO = "WAITING_INFO"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCategory(str, PyEnum):
    HARDWARE = "HARDWARE"
    SOFTWARE = "SOFTWARE"
    NETWORK = "NETWORK"
    PRINTING = "PRINTING"
    PAYMENT = "PAYMENT"
    APPLICATION = "APPLICATION"
    OTHER = "OTHER"


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zammad_ticket_id = Column(String(100), unique=True, nullable=True)

    # Relations
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.site_id"), nullable=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.device_id"), nullable=True)

    # Ticket Info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    reporter_name = Column(String(200), nullable=True)
    reporter_email = Column(String(200), nullable=True)

    # Classification
    category = Column(Enum(TicketCategory), default=TicketCategory.OTHER)
    severity = Column(Enum(TicketSeverity), default=TicketSeverity.MEDIUM)
    status = Column(Enum(TicketStatus), default=TicketStatus.NEW)

    # AI Analysis
    confidence_score = Column(Float, default=0.0)
    ai_analysis = Column(Text, nullable=True)
    ai_recommendation = Column(Text, nullable=True)
    sop_reference = Column(String(500), nullable=True)
    root_cause = Column(Text, nullable=True)

    # Processing Details
    tier_level = Column(Integer, default=0)  # 0 = Tier0, 1 = Tier1
    escalated = Column(Boolean, default=False)
    escalated_to = Column(String(200), nullable=True)
    escalated_at = Column(DateTime, nullable=True)

    # Resolution
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(200), nullable=True)

    # SLA
    sla_deadline = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    telegram_message_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("Site", back_populates="tickets")
    device = relationship("Device", back_populates="tickets")

    def __repr__(self):
        return f"<Ticket {self.zammad_ticket_id} [{self.severity}] {self.status}>"

    def to_dict(self):
        return {
            "ticket_id": str(self.ticket_id),
            "zammad_ticket_id": self.zammad_ticket_id,
            "site_id": str(self.site_id) if self.site_id else None,
            "device_id": str(self.device_id) if self.device_id else None,
            "title": self.title,
            "description": self.description,
            "reporter_name": self.reporter_name,
            "reporter_email": self.reporter_email,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "ai_analysis": self.ai_analysis,
            "ai_recommendation": self.ai_recommendation,
            "sop_reference": self.sop_reference,
            "root_cause": self.root_cause,
            "tier_level": self.tier_level,
            "escalated": self.escalated,
            "escalated_to": self.escalated_to,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_breached": self.sla_breached,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
