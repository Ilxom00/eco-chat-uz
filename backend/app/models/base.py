"""
eco-chat.uz — SQLAlchemy Base Model
ALWAYS uses String(36) for UUID primary keys.
This works for BOTH SQLite and PostgreSQL:
  - SQLite: stores as text
  - PostgreSQL: auto-casts varchar to uuid column
"""
import uuid

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String

Base = declarative_base()


class BaseModel(Base):
    """Abstract base with String(36) UUID primary key — works for SQLite AND PostgreSQL."""
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
