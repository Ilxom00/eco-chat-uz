"""
database.py — Database engine with fallback and persistence
PostgreSQL used if DATABASE_URL points to valid PostgreSQL.
If PostgreSQL is unavailable, falls back to SQLite at /data/eco.db
(persistent Render disk or local ./eco.db).
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.base import Base  # noqa: F401

logger = logging.getLogger(__name__)

_db_url = settings.database_url

# Fix sqlite driver
if _db_url.startswith("sqlite") and "+aiosqlite" not in _db_url:
    _db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

# For PostgreSQL URLs pointing to Docker hostname (postgres:5432),
# check if DATABASE_URL env is explicitly set to a real PostgreSQL server.
# If it's the default localhost/docker postgres and not reachable, use SQLite.
_is_real_postgres = (
    "postgresql" in _db_url and
    not _db_url.startswith("postgresql+asyncpg://ecochat:ecochat_pass@localhost") and
    not _db_url.startswith("postgresql+asyncpg://ecochat:ecochat_pass@postgres:")
)

# Explicitly override if DATABASE_URL env var has a real external Postgres
_env_db_url = os.environ.get("DATABASE_URL", "")
if _env_db_url and "postgresql" in _env_db_url and "@" in _env_db_url:
    # Use the env var directly if it looks like a real external URL
    _host_part = _env_db_url.split("@")[-1].split("/")[0]
    if not _host_part.startswith("localhost") and not _host_part.startswith("postgres:"):
        _db_url = _env_db_url
        if "+asyncpg" not in _db_url:
            _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _is_real_postgres = True
        logger.info("Using external PostgreSQL: %s", _host_part)

if not _is_real_postgres:
    # Use SQLite at persistent path
    # /data is mounted as Render Disk; fallback to ./eco.db locally
    _data_dir = "/data"
    if not os.path.exists(_data_dir):
        _data_dir = os.path.abspath(".")
    _sqlite_path = os.path.join(_data_dir, "eco.db")
    _db_url = f"sqlite+aiosqlite:///{_sqlite_path}"
    logger.info("Using SQLite at: %s", _sqlite_path)

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
