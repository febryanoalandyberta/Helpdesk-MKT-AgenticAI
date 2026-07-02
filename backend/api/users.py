"""
Users API — CRUD manajemen user (khusus SUPER_ADMIN & USER_ADMIN)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.user import User, UserRole
from api.auth import get_current_user, require_admin, require_super_admin, hash_password

router = APIRouter(prefix="/api/users", tags=["Users"])


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    telegram_id: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    new_password: str


# ── List semua user ──────────────────────────────────────────────────────────

@router.get("/")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(User).order_by(User.created_at.desc()))
    users = q.scalars().all()
    return {"users": [u.to_dict() for u in users], "total": len(users)}


# ── Detail satu user ─────────────────────────────────────────────────────────

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(User).where(User.user_id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return user.to_dict()


# ── Update user ──────────────────────────────────────────────────────────────

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(User).where(User.user_id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    if current_user.role != UserRole.SUPER_ADMIN:
        if str(current_user.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Hanya Super Admin yang bisa mengedit akun orang lain.")
        if data.role is not None and data.role != user.role:
            raise HTTPException(status_code=403, detail="Anda tidak diizinkan mengubah role Anda sendiri.")
        if data.is_active is not None and data.is_active != user.is_active:
            raise HTTPException(status_code=403, detail="Anda tidak diizinkan menonaktifkan akun sendiri.")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.telegram_id is not None:
        user.telegram_id = data.telegram_id

    await db.commit()
    await db.refresh(user)
    return {"message": "User berhasil diperbarui.", "user": user.to_dict()}


# ── Reset password (hanya SUPER_ADMIN) ──────────────────────────────────────

@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(User).where(User.user_id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    if current_user.role != UserRole.SUPER_ADMIN and str(current_user.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang bisa mengganti password orang lain.")

    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"message": f"Password user '{user.username}' berhasil direset."}


# ── Hapus user (hanya SUPER_ADMIN) ──────────────────────────────────────────

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(User).where(User.user_id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")

    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Hanya Super Admin yang dapat menghapus user.")
    if str(user.user_id) == str(current_user.user_id):
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun sendiri.")

    await db.delete(user)
    await db.commit()
    return {"message": f"User '{user.username}' berhasil dihapus."}
