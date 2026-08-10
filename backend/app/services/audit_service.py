from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.audit import AuditLog

async def log(db: AsyncSession, admin_id: str, action: str, entity_type: str = None, entity_id: str = None, old_value: dict = None, new_value: dict = None, ip: str = None):
    audit_log = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip
    )
    db.add(audit_log)
    await db.commit()

async def get_logs(db: AsyncSession, filters: dict, page: int, page_size: int) -> tuple[list, int]:
    query = select(AuditLog)
    total_query = select(func.count()).select_from(AuditLog)
    
    total = (await db.execute(total_query)).scalar()
    logs = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    
    return logs, total
