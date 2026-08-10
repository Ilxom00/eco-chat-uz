"""
eco-chat.uz — Super Admin yaratish skripti
Idempotent: agar mavjud bo'lsa yangilamaydi, yangi yaratadi.

Default: login=user, parol=12345
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# ── Sozlamalar ──────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "user")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345")
ADMIN_FULLNAME = os.getenv("ADMIN_FULLNAME", "Bosh Administrator")
DATABASE_URL   = os.getenv("DATABASE_URL", "postgresql+asyncpg://ecochat:ecochat_pass@postgres:5432/ecochat_db")


async def create_superadmin():
    print(f"  Admin yaratilmoqda: {ADMIN_USERNAME}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import kerakli modullari
    try:
        from app.models.admin import Admin
        from app.utils.security import get_password_hash
    except ImportError:
        # Fallback agar app module yo'q bo'lsa
        import bcrypt
        def get_password_hash(password):
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        from sqlalchemy.orm import DeclarativeBase
        from sqlalchemy import Column, String, Boolean, DateTime
        from sqlalchemy.dialects.postgresql import UUID
        from sqlalchemy.sql import func
        import uuid

        class Base(DeclarativeBase):
            pass

        class Admin(Base):
            __tablename__ = "admins"
            id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            username = Column(String(50), unique=True, nullable=False)
            password_hash = Column(String(255), nullable=False)
            full_name = Column(String(200))
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())

    async with engine.begin() as conn:
        # Jadvalni yaratish (agar mavjud bo'lmasa)
        try:
            from app.models.base import Base as AppBase
            await conn.run_sync(AppBase.metadata.create_all)
        except Exception:
            pass

    async with AsyncSessionLocal() as session:
        # Mavjudligini tekshirish
        result = await session.execute(
            select(Admin).where(Admin.username == ADMIN_USERNAME)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Admin '{ADMIN_USERNAME}' allaqachon mavjud — o'zgartirilmadi.")
        else:
            from app.utils.security import get_password_hash
            new_admin = Admin(
                username=ADMIN_USERNAME,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                full_name=ADMIN_FULLNAME,
                is_active=True,
            )
            session.add(new_admin)
            await session.commit()
            print(f"  Admin '{ADMIN_USERNAME}' muvaffaqiyatli yaratildi!")

    await engine.dispose()


if __name__ == "__main__":
    print("=" * 45)
    print("  eco-chat.uz — Admin yaratish")
    print("=" * 45)
    asyncio.run(create_superadmin())
    print("=" * 45)
    print(f"  Login : {ADMIN_USERNAME}")
    print(f"  Parol : {ADMIN_PASSWORD}")
    print("=" * 45)
