"""
Device Model — POS devices managed per site
Each site has 4 devices: 2 POS Ticketing + 2 POS FNB
Total: 18 sites × 4 devices = 72 POS minimum
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Boolean, Text, Enum, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class DeviceType(str, PyEnum):
    POS_TICKETING = "POS_TICKETING"
    POS_FNB = "POS_FNB"
    SERVER = "SERVER"
    NETWORK = "NETWORK"
    OTHER = "OTHER"


class DeviceStatus(str, PyEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.site_id"), nullable=True)

    device_name = Column(String(200), nullable=False)
    device_type = Column(Enum(DeviceType), nullable=False, default=DeviceType.POS_TICKETING)

    # Network Info
    ip_address = Column(String(50), nullable=True)
    hostname = Column(String(200), nullable=True)
    mac_address = Column(String(50), nullable=True)

    # OS & Specs
    operating_system = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    hardware_model = Column(String(200), nullable=True)

    # Health & Telemetry
    cpu_usage = Column(Float, nullable=True)
    ram_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    disk_total_gb = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    
    # User Activity
    current_active_app = Column(String(200), nullable=True)
    current_active_url = Column(String(500), nullable=True)
    last_health_check = Column(DateTime, nullable=True)

    # Remote Access (encrypted reference)
    credentials_reference = Column(String(500), nullable=True)
    ssh_port = Column(String(10), default="22")

    # Status
    status = Column(Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    is_active = Column(Boolean, default=True)
    last_ping = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("Site", back_populates="devices")
    tickets = relationship("Ticket", back_populates="device")

    def __repr__(self):
        return f"<Device {self.device_name} ({self.device_type}) @ {self.ip_address}>"

    def to_dict(self):
        return {
            "device_id": str(self.device_id),
            "site_id": str(self.site_id) if self.site_id else None,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "ip_address": self.ip_address,
            "hostname": self.hostname,
            "mac_address": self.mac_address,
            "operating_system": self.operating_system,
            "os_version": self.os_version,
            "hardware_model": self.hardware_model,
            "cpu_usage": self.cpu_usage,
            "ram_usage": self.ram_usage,
            "disk_usage": self.disk_usage,
            "disk_total_gb": self.disk_total_gb,
            "disk_free_gb": self.disk_free_gb,
            "temperature": self.temperature,
            "current_active_app": self.current_active_app,
            "current_active_url": self.current_active_url,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "ssh_port": self.ssh_port,
            "status": self.status,
            "is_active": self.is_active,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
