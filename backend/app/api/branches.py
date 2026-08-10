from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import branch_service

router = APIRouter(tags=["branches"], dependencies=[Depends(get_current_admin)])

@router.get("/")
async def list_branches(include_archived: bool = False, db: AsyncSession = Depends(get_db)):
    branches = await branch_service.get_all_branches(db, include_archived)
    result = []
    for b in branches:
        emp_count = await branch_service.get_employee_count_in_branch(db, str(b.id))
        result.append({
            "id": str(b.id),
            "name": b.name,
            "sort_order": b.sort_order,
            "is_active": b.is_active,
            "employee_count": emp_count,
        })
    return result

@router.post("/")
async def create_branch(data: dict, db: AsyncSession = Depends(get_db)):
    branch = await branch_service.create_branch(db, name=data.get("name"), sort_order=data.get("sort_order"))
    return {"id": str(branch.id), "name": branch.name, "sort_order": branch.sort_order, "employee_count": 0}

@router.delete("/{id}")
async def delete_branch(id: str, db: AsyncSession = Depends(get_db)):
    await branch_service.delete_branch(db, id)
    return {"message": "Filial o'chirildi. Xodimlar filialdan chiqarildi."}

@router.patch("/{id}/archive")
async def archive_branch(id: str, db: AsyncSession = Depends(get_db)):
    branch = await branch_service.archive_branch(db, id)
    return branch

@router.patch("/{id}/reorder")
async def reorder_branch(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    branches = await branch_service.reorder_branch(db, id, data.get("direction"))
    return branches
