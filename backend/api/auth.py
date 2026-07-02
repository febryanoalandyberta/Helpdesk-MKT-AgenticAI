"""
Authentication API — JWT + RBAC untuk Helpdesk MKT staff
Roles: SUPER_ADMIN > USER_ADMIN > OPERATOR > GUEST
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import get_db
from models.user import User, UserRole
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class RegisterRequest(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str
    role: str = "OPERATOR"


# ── Utility ─────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ── Dependency: get current user ─────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesi tidak valid. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    q = await db.execute(select(User).where(User.username == username))
    user = q.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


# ── RBAC Role Guards ──────────────────────────────────────────────────────────

def require_role(*allowed_roles: UserRole):
    """Dependency factory — pastikan user memiliki salah satu role yang diizinkan."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Role '{current_user.role}' tidak memiliki izin untuk aksi ini.",
            )
        return current_user
    return checker


# Shortcut guards yang bisa dipakai di router lain
require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_admin       = require_role(UserRole.SUPER_ADMIN, UserRole.USER_ADMIN)
require_operator    = require_role(UserRole.SUPER_ADMIN, UserRole.USER_ADMIN, UserRole.OPERATOR)
require_any         = require_role(UserRole.SUPER_ADMIN, UserRole.USER_ADMIN, UserRole.OPERATOR, UserRole.GUEST)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(User).where(User.username == form_data.username))
    user = q.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda tidak aktif. Hubungi Super Admin.",
        )
    user.last_login = datetime.utcnow()
    await db.commit()
    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.post("/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),   # Hanya admin yang bisa daftarkan user baru
):
    # USER_ADMIN hanya boleh buat OPERATOR dan GUEST
    if current_user.role == UserRole.USER_ADMIN and data.role not in ["OPERATOR", "GUEST"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User Admin hanya dapat membuat akun dengan role OPERATOR atau GUEST.",
        )

    q = await db.execute(select(User).where(User.username == data.username))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username sudah digunakan.")

    q2 = await db.execute(select(User).where(User.email == data.email))
    if q2.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email sudah digunakan.")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": "Akun berhasil dibuat.", "user": user.to_dict()}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()
