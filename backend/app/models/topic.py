from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.sql import func
from .base import BaseModel

class Topic(BaseModel):
    __tablename__ = 'topics'
    
    short_name = Column(String(100), nullable=False)
    full_name = Column(String(500), nullable=False)
    sequence_order = Column(Integer, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_topic_order_active', 'sequence_order', 'is_active'),
    )
