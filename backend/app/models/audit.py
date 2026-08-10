from sqlalchemy import Column, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.sql import func
from .base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    admin_id = Column(String(36), ForeignKey('admins.id'), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_audit_admin_action_date', 'admin_id', 'action', 'created_at'),
    )
