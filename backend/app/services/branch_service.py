import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, func
from app.models.branch import Branch
from app.models.employee import Employee

logger = logging.getLogger(__name__)


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

    branch = Branch(id=uuid.uuid4(), name=name, sort_order=sort_order)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


async def resolve_branch_id(
    db: AsyncSession,
    branch_id: Optional[str | uuid.UUID] = None,
    branch_name: Optional[str] = None
) -> Optional[uuid.UUID]:
    """
    Safely resolve branch UUID using ORM queries only.
    NEVER uses raw text() queries with string UUID params to avoid asyncpg type errors.
    """
    bid_str = str(branch_id).strip() if branch_id else None

    # 1. If already a uuid.UUID, return directly
    if isinstance(branch_id, uuid.UUID):
        return branch_id

    # 2. Try parsing string as UUID and look up via ORM
    if bid_str:
        try:
            bid_uuid = uuid.UUID(bid_str)
            result = await db.execute(select(Branch).filter(Branch.id == bid_uuid))
            branch = result.scalar_one_or_none()
            if branch:
                return branch.id
        except (ValueError, TypeError):
            pass  # Not a valid UUID string, try other methods

    # 3. Try fb_X fallback index pattern (fb_1 = sort_order 1)
    if bid_str and "fb_" in bid_str:
        try:
            sort_num = int(bid_str.split("fb_")[1])
            result = await db.execute(
                select(Branch).filter(Branch.sort_order == sort_num, Branch.is_active == True)
            )
            branch = result.scalar_one_or_none()
            if branch:
                return branch.id
        except (ValueError, IndexError):
            pass

    # 4. Try exact name match via ORM
    query_name = branch_name or bid_str
    if query_name:
        # Exact match first
        result = await db.execute(select(Branch).filter(Branch.name == query_name))
        branch = result.scalar_one_or_none()
        if branch:
            return branch.id

        # Fuzzy/case-insensitive match
        result = await db.execute(select(Branch).filter(Branch.name.ilike(f"%{query_name}%")))
        branch = result.scalars().first()
        if branch:
            return branch.id

    # 5. Fallback: first active branch via ORM
    result = await db.execute(
        select(Branch).filter(Branch.is_active == True).order_by(Branch.sort_order).limit(1)
    )
    branch = result.scalar_one_or_none()
    if branch:
        return branch.id

    return None


async def get_branch_by_id(db: AsyncSession, branch_id: str) -> Optional[Branch]:
    """Get branch by ID string. Safely converts to UUID for asyncpg compatibility."""
    try:
        bid_uuid = uuid.UUID(str(branch_id).strip())
        result = await db.execute(select(Branch).filter(Branch.id == bid_uuid))
        return result.scalar_one_or_none()
    except (ValueError, TypeError):
        return None


async def archive_branch(db: AsyncSession, branch_id: str) -> Branch:
    branch = await get_branch_by_id(db, branch_id)
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
    """Delete branch and unlink employees."""
    try:
        bid_uuid = uuid.UUID(str(branch_id).strip())
        # Unlink employees using ORM
        emps = await db.execute(select(Employee).filter(Employee.branch_id == bid_uuid))
        for emp in emps.scalars().all():
            emp.branch_id = None
        # Delete branch using ORM
        branch = await db.execute(select(Branch).filter(Branch.id == bid_uuid))
        b = branch.scalar_one_or_none()
        if b:
            await db.delete(b)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e


async def get_employee_count_in_branch(db: AsyncSession, branch_id: str) -> int:
    try:
        bid_uuid = uuid.UUID(str(branch_id).strip())
        result = await db.execute(
            select(func.count()).select_from(Employee).filter(Employee.branch_id == bid_uuid)
        )
        return result.scalar() or 0
    except (ValueError, TypeError):
        return 0
