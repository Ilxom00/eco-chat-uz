from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import BaseModel

class Employee(BaseModel):
    __tablename__ = 'employees'
    
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(300), nullable=False)
    phone = Column(String(20), nullable=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.id'), nullable=True)
    registration_state = Column(String(30), default='PENDING')
    registered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_emp_telegram', 'telegram_user_id'),
        Index('ix_emp_branch', 'branch_id'),
    )
