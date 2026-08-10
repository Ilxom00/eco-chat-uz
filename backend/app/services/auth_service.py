from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import pytz

from app.models.admin import Admin
from app.models.audit import AuditLog
from app.utils.security import verify_password, create_access_token, decode_token
from app.config import settings

async def authenticate_admin(db: AsyncSession, username: str, password: str) -> Admin | None:
    result = await db.execute(select(Admin).filter(Admin.username == username, Admin.is_active == True))
    admin = result.scalar_one_or_none()
    if not admin:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin

async def get_current_admin(db: AsyncSession, token: str) -> Admin | None:
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        return None
    result = await db.execute(select(Admin).filter(Admin.username == username, Admin.is_active == True))
    return result.scalar_one_or_none()

async def create_access_token_for_admin(admin_id: str, username: str) -> str:
    return create_access_token(data={"sub": username, "id": str(admin_id)})

async def log_admin_action(db: AsyncSession, admin_id, action, entity_type=None, entity_id=None, old_value=None, new_value=None, ip=None):
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip
    )
    db.add(log)
    await db.commit()
