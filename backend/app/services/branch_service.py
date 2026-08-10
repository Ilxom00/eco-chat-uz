import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from app.models.branch import Branch


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


async def resolve_branch_id(
    db: AsyncSession, 
    branch_id: Optional[str | uuid.UUID] = None, 
    branch_name: Optional[str] = None
) -> Optional[uuid.UUID]:
    """Safely resolve valid uuid.UUID for branch from either branch_id or branch_name."""
    if branch_id:
        if isinstance(branch_id, uuid.UUID):
            return branch_id
        try:
            val_uuid = uuid.UUID(str(branch_id))
            res = await db.execute(select(Branch).filter(Branch.id == val_uuid))
            b = res.scalar_one_or_none()
            if b:
                return b.id
        except (ValueError, TypeError):
            pass  # Not a valid UUID (e.g. 'fb_1')

    if branch_name:
        res = await db.execute(select(Branch).filter(Branch.name == branch_name))
        b = res.scalar_one_or_none()
        if b:
            return b.id
        
        # Auto-create branch if not found by name
        new_b = await create_branch(db, name=branch_name)
        return new_b.id

    return None


async def archive_branch(db: AsyncSession, branch_id: str) -> Branch:
    result = await db.execute(select(Branch).filter(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if branch:
        branch.is_active = False
        await db.commit()
        await db.refresh(branch)
    return branch


async def reorder_branch(db: AsyncSession, branch_id: str, direction: str) -> list[Branch]:
    branches = await get_all_branches(db, include_archived=True)
    idx = next((i for i, b in enumerate(branches) if str(b.id) == branch_id), -1)
    if idx != -1:
        if direction == "up" and idx > 0:
            branches[idx].sort_order, branches[idx-1].sort_order = branches[idx-1].sort_order, branches[idx].sort_order
        elif direction == "down" and idx < len(branches) - 1:
            branches[idx].sort_order, branches[idx+1].sort_order = branches[idx+1].sort_order, branches[idx].sort_order
        await db.commit()
    return sorted(branches, key=lambda x: x.sort_order)


async def delete_branch(db: AsyncSession, branch_id: str) -> bool:
    """Filialni o'chiradi. Bog'liq xodimlarning branch_id ni NULL qiladi."""
    try:
        await db.execute(
            text("UPDATE employees SET branch_id = NULL WHERE branch_id = :bid"),
            {"bid": branch_id}
        )
        await db.execute(text("DELETE FROM branches WHERE id = :bid"), {"bid": branch_id})
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e


async def get_employee_count_in_branch(db: AsyncSession, branch_id: str) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM employees WHERE branch_id = :bid"),
        {"bid": branch_id}
    )
    return result.scalar() or 0
