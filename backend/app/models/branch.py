from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from .base import BaseModel

class Branch(BaseModel):
    __tablename__ = 'branches'
    
    name = Column(String(200), unique=True, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
