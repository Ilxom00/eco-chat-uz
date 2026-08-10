"""
eco-chat.uz — SQLAlchemy Base Model
SQLite va PostgreSQL uchun mos UUID strategiyasi.
"""
import uuid
import os

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

Base = declarative_base()


def _is_sqlite() -> bool:
    db_url = os.getenv("DATABASE_URL", "")
    return db_url.startswith("sqlite")


class BaseModel(Base):
    """Abstract base with UUID primary key (SQLite va PostgreSQL compatible)."""
    __abstract__ = True

    if _is_sqlite():
        # SQLite: UUID as String(36)
        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        # PostgreSQL: native UUID
        id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
