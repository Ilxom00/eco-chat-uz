"""
eco-chat.uz — Local Admin yaratish (SQLite rejimi)
Login: user | Parol: 12345
bcrypt to'g'ridan-to'g'ri ishlatiladi (passlib'siz)
"""
import asyncio
import os
import sys
import bcrypt
import uuid

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./ecochat_local.db"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "user")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "12345")
ADMIN_FULLNAME = os.getenv("ADMIN_FULLNAME", "Bosh Administrator")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def create_local_admin():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(
        "sqlite+aiosqlite:///./ecochat_local.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(
            text("SELECT id FROM admins WHERE username = :u"),
            {"u": ADMIN_USERNAME},
        )
        existing = result.fetchone()

        if not existing:
            admin_id = str(uuid.uuid4())
            pw_hash = hash_password(ADMIN_PASSWORD)
            await session.execute(
                text("""
                    INSERT INTO admins (id, username, password_hash, full_name, is_active)
                    VALUES (:id, :username, :pw, :fn, 1)
                """),
                {"id": admin_id, "username": ADMIN_USERNAME, "pw": pw_hash, "fn": ADMIN_FULLNAME},
            )
            await session.commit()
            print(f"Admin yaratildi: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        else:
            print(f"Admin allaqachon mavjud: {ADMIN_USERNAME}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_local_admin())
    print(f"Login: {ADMIN_USERNAME}  |  Parol: {ADMIN_PASSWORD}")
