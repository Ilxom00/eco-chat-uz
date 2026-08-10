from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.branch import Branch
from sqlalchemy import update

async def get_all_branches(db: AsyncSession, include_archived: bool = False) -> list[Branch]:
    query = select(Branch).order_by(Branch.sort_order)
    if not include_archived:
        query = query.filter(Branch.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()

async def create_branch(db: AsyncSession, name: str, sort_order: int = None) -> Branch:
    if sort_order is None:
        max_order_result = await db.execute(select(Branch.sort_order).order_by(Branch.sort_order.desc()).limit(1))
        max_order = max_order_result.scalar_one_or_none()
        sort_order = (max_order or 0) + 1

    branch = Branch(name=name, sort_order=sort_order)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch

async def archive_branch(db: AsyncSession, branch_id: str) -> Branch:
    # check no employees
    result = await db.execute(select(Branch).filter(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if branch:
        branch.is_active = False
        await db.commit()
        await db.refresh(branch)
    return branch

async def reorder_branch(db: AsyncSession, branch_id: str, direction: str) -> list[Branch]:
    branches = await get_all_branches(db, include_archived=True)
    # Simple reorder logic to swap
    idx = next((i for i, b in enumerate(branches) if str(b.id) == branch_id), -1)
    if idx != -1:
        if direction == "up" and idx > 0:
            branches[idx].sort_order, branches[idx-1].sort_order = branches[idx-1].sort_order, branches[idx].sort_order
        elif direction == "down" and idx < len(branches) - 1:
            branches[idx].sort_order, branches[idx+1].sort_order = branches[idx+1].sort_order, branches[idx].sort_order
        await db.commit()
    return sorted(branches, key=lambda x: x.sort_order)
