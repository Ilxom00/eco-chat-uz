import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, func
from app.models.branch import Branch

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
) -> Optional[str]:
    """
    Safely resolve branch ID as STRING.
    Returns str(uuid) — works for BOTH SQLite (String(36)) and PostgreSQL (UUID auto-cast).
    """
    bid_str = str(branch_id).strip() if branch_id else None

    # 1. If already a uuid.UUID, return as string
    if isinstance(branch_id, uuid.UUID):
        return str(branch_id)

    # 2. Try parsing string as UUID and look up via ORM
    if bid_str:
        try:
            bid_uuid = uuid.UUID(bid_str)
            result = await db.execute(select(Branch).filter(Branch.id == str(bid_uuid)))
            branch = result.scalar_one_or_none()
            if branch:
                return str(branch.id)
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
                return str(branch.id)
        except (ValueError, IndexError):
            pass

    # 4. Try exact name match via ORM
    query_name = branch_name or bid_str
    if query_name:
        result = await db.execute(select(Branch).filter(Branch.name == query_name))
        branch = result.scalar_one_or_none()
        if branch:
            return str(branch.id)

        # Fuzzy match
        result = await db.execute(select(Branch).filter(Branch.name.ilike(f"%{query_name}%")))
        branch = result.scalars().first()
        if branch:
            return str(branch.id)

    # 5. Fallback: first active branch via ORM
    result = await db.execute(
        select(Branch).filter(Branch.is_active == True).order_by(Branch.sort_order).limit(1)
    )
    branch = result.scalar_one_or_none()
    if branch:
        return str(branch.id)

    return None


async def get_branch_by_id(db: AsyncSession, branch_id: str) -> Optional[Branch]:
    """Get branch by ID string. Works for both SQLite and PostgreSQL."""
    try:
        bid_str = str(uuid.UUID(str(branch_id).strip()))  # normalize to lowercase UUID string
        result = await db.execute(select(Branch).filter(Branch.id == bid_str))
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
    """Delete branch and unlink employees. Uses CAST to TEXT to avoid asyncpg UUID type issues."""
    try:
        bid = str(branch_id).strip()
        await db.execute(
            text("UPDATE employees SET branch_id = NULL WHERE CAST(branch_id AS TEXT) = :bid"),
            {"bid": bid}
        )
        await db.execute(
            text("DELETE FROM branches WHERE CAST(id AS TEXT) = :bid"),
            {"bid": bid}
        )
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e


async def get_employee_count_in_branch(db: AsyncSession, branch_id: str) -> int:
    """Count employees in branch. Uses CAST to TEXT to avoid asyncpg UUID type issues."""
    try:
        bid = str(branch_id).strip()
        result = await db.execute(
            text("SELECT COUNT(*) FROM employees WHERE CAST(branch_id AS TEXT) = :bid"),
            {"bid": bid}
        )
        return result.scalar() or 0
    except Exception:
        return 0
