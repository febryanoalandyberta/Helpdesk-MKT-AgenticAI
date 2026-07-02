"""
User Model — RBAC for Helpdesk MKT staff
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class UserRole(str, PyEnum):
    SUPER_ADMIN = "SUPER_ADMIN"   # Full access — kelola semua termasuk user
    USER_ADMIN  = "USER_ADMIN"    # Kelola user Operator & Guest
    OPERATOR    = "OPERATOR"      # Buat tiket, trigger AI, lihat dashboard
    GUEST       = "GUEST"         # Read-only — hanya lihat dashboard


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    full_name = Column(String(300), nullable=True)
    hashed_password = Column(String(500), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True)
    telegram_id = Column(String(100), nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "telegram_id": self.telegram_id,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
