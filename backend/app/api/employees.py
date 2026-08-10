from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import employee_service

router = APIRouter(tags=["employees"], dependencies=[Depends(get_current_admin)])

@router.get("/")
async def list_employees(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
    employees, total = await employee_service.list_employees(db, {}, page, page_size)
    return {"items": employees, "total": total}

@router.get("/{id}")
async def get_employee(id: str, db: AsyncSession = Depends(get_db)):
    return await employee_service.get_employee_full_detail(db, id)

@router.delete("/{id}")
async def delete_employee(id: str, db: AsyncSession = Depends(get_db)):
    await employee_service.delete_employee_cascade(db, id)
    return {"message": "Xodim va barcha bog'liq ma'lumotlar o'chirildi"}
