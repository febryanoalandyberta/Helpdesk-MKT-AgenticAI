"""
Site Model — Represents each cinema site managed by MKT
Sam's Studio's has 18 sites across 18 cities.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class Site(Base):
    __tablename__ = "sites"

    site_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    timezone = Column(String(50), default="Asia/Jakarta")
    address = Column(Text, nullable=True)

    # Telegram Group for this site
    telegram_group_id = Column(String(100), nullable=True)

    # PIC (Person in Charge)
    pic_primary = Column(String(200), nullable=True)
    pic_primary_phone = Column(String(50), nullable=True)
    pic_secondary = Column(String(200), nullable=True)
    pic_secondary_phone = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    devices = relationship("Device", back_populates="site", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="site")

    def __repr__(self):
        return f"<Site {self.site_name} - {self.city}>"

    def to_dict(self):
        return {
            "site_id": str(self.site_id),
            "site_name": self.site_name,
            "city": self.city,
            "timezone": self.timezone,
            "address": self.address,
            "telegram_group_id": self.telegram_group_id,
            "pic_primary": self.pic_primary,
            "pic_primary_phone": self.pic_primary_phone,
            "pic_secondary": self.pic_secondary,
            "pic_secondary_phone": self.pic_secondary_phone,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
