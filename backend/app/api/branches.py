from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import branch_service

router = APIRouter(prefix="/branches", tags=["branches"], dependencies=[Depends(get_current_admin)])

@router.get("/")
async def list_branches(include_archived: bool = False, db: AsyncSession = Depends(get_db)):
    branches = await branch_service.get_all_branches(db, include_archived)
    return branches

@router.post("/")
async def create_branch(data: dict, db: AsyncSession = Depends(get_db)):
    branch = await branch_service.create_branch(db, name=data.get("name"), sort_order=data.get("sort_order"))
    return branch

@router.patch("/{id}/archive")
async def archive_branch(id: str, db: AsyncSession = Depends(get_db)):
    branch = await branch_service.archive_branch(db, id)
    return branch

@router.patch("/{id}/reorder")
async def reorder_branch(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    branches = await branch_service.reorder_branch(db, id, data.get("direction"))
    return branches
