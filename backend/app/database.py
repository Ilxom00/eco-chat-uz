from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.base import Base  # noqa: F401 — re-exported for main.py

import os
# Auto-fix: postgresql needs async driver (asyncpg), sqlite needs (aiosqlite)
_db_url = settings.database_url
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("sqlite") and "+aiosqlite" not in _db_url:
    _db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# Environment Guards
is_prod = (
    os.getenv("APP_ENV") == "production" or 
    os.getenv("ENVIRONMENT") == "production" or 
    settings.environment == "production"
)

if is_prod:
    if not _db_url or _db_url.startswith("sqlite"):
        import sys
        print("CRITICAL: Production PostgreSQL connection unavailable (SQLite URL blocked). Startup aborted to protect persistent data.", file=sys.stderr)
        raise RuntimeError("Production PostgreSQL unavailable. Startup aborted to protect persistent data.")

# Persistent volume redirect for SQLite (only in non-prod)
if not is_prod and _db_url.startswith("sqlite") and os.path.exists("/backups"):
    if "ecochat.db" in _db_url and "/backups/" not in _db_url:
        _db_url = "sqlite+aiosqlite:////backups/ecochat.db"




# SQLite needs check_same_thread=False; PostgreSQL ignores it
_connect_args = {}
if _db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    _db_url,
    echo=(settings.environment == "development"),
    connect_args=_connect_args,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async_session_maker = AsyncSessionLocal


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
