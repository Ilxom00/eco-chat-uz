from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import audit_service

router = APIRouter(tags=["audit"], dependencies=[Depends(get_current_admin)])

@router.get("/")
async def get_audit_logs(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
    items, total = await audit_service.get_logs(db, {}, page, page_size)
    return {"items": items, "total": total}
