"""
seed_admin.py — Setup akun Super Admin pertama kali
Jalankan SEKALI saat pertama kali setup sistem:
  python seed_admin.py

Atau dengan custom credentials:
  python seed_admin.py --username myadmin --password mypassword --email admin@company.com
"""
import asyncio
import argparse
import sys
import os

# Pastikan kita bisa import dari folder backend
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select
from database import AsyncSessionLocal, init_db
from models.user import User, UserRole
from api.auth import hash_password


async def seed_super_admin(username: str, password: str, email: str, full_name: str):
    await init_db()

    async with AsyncSessionLocal() as db:
        # Cek apakah sudah ada Super Admin
        q = await db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN))
        existing = q.scalar_one_or_none()

        if existing:
            print(f"\n[INFO] Super Admin sudah ada: '{existing.username}' ({existing.email})")
            print("       Tidak ada perubahan yang dilakukan.")
            return

        # Cek apakah username sudah dipakai
        q2 = await db.execute(select(User).where(User.username == username))
        if q2.scalar_one_or_none():
            print(f"\n[ERROR] Username '{username}' sudah digunakan oleh akun lain!")
            return

        # Buat Super Admin
        admin = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print("\n" + "=" * 55)
        print("  ✅ Super Admin berhasil dibuat!")
        print("=" * 55)
        print(f"  Username  : {admin.username}")
        print(f"  Email     : {admin.email}")
        print(f"  Full Name : {admin.full_name}")
        print(f"  Role      : {admin.role}")
        print(f"  User ID   : {admin.user_id}")
        print("=" * 55)
        print("\n  ⚠️  SIMPAN PASSWORD INI DENGAN AMAN!")
        print(f"  Password  : {password}")
        print("\n  Sekarang Anda bisa login di dashboard menggunakan")
        print(f"  username dan password di atas.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Super Admin pertama untuk MKT Helpdesk AI")
    parser.add_argument("--username",  default="superadmin",          help="Username (default: superadmin)")
    parser.add_argument("--password",  default="Admin@MKT2024!",      help="Password (default: Admin@MKT2024!)")
    parser.add_argument("--email",     default="admin@mkt.co.id",     help="Email (default: admin@mkt.co.id)")
    parser.add_argument("--fullname",  default="Super Administrator",  help="Nama lengkap")
    args = parser.parse_args()

    asyncio.run(seed_super_admin(
        username=args.username,
        password=args.password,
        email=args.email,
        full_name=args.fullname,
    ))
