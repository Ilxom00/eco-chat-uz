from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import BaseModel

class Admin(BaseModel):
    __tablename__ = 'admins'
    
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
