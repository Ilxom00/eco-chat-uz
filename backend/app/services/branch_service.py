import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from app.models.branch import Branch

logger = logging.getLogger(__name__)


def _force_uuid(val) -> Optional[uuid.UUID]:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val).strip())
    except (ValueError, TypeError):
        return None


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
    """Safely resolve valid uuid.UUID for branch from either branch_id or branch_name."""
    try:
        bid_str = str(branch_id).strip() if branch_id else None
        bname_str = branch_name.strip() if branch_name else None

        # 1. Try exact UUID match
        if isinstance(branch_id, uuid.UUID):
            return branch_id

        # 2. Try direct query by string id
        if bid_str:
            res = await db.execute(text("SELECT id FROM branches WHERE id = :bid"), {"bid": bid_str})
            row = res.fetchone()
            if row:
                return _force_uuid(row[0])

        # 3. Try fallback numeric index lookup (e.g. fb_1 -> 1)
        if bid_str and "fb_" in bid_str:
            try:
                sort_num = int(bid_str.split("fb_")[1])
                res_so = await db.execute(text("SELECT id FROM branches WHERE sort_order = :so"), {"so": sort_num})
                row_so = res_so.fetchone()
                if row_so:
                    return _force_uuid(row_so[0])
            except Exception:
                pass

        # 4. Try exact or fuzzy name match
        query_name = bname_str or bid_str
        if query_name:
            res_name = await db.execute(
                text("SELECT id FROM branches WHERE name = :n OR LOWER(name) LIKE LOWER(:ln)"),
                {"n": query_name, "ln": f"%{query_name}%"}
            )
            row_name = res_name.fetchone()
            if row_name:
                return _force_uuid(row_name[0])

        # 5. Fallback to first available branch
        res_first = await db.execute(text("SELECT id FROM branches ORDER BY sort_order ASC LIMIT 1"))
        row_first = res_first.fetchone()
        if row_first:
            return _force_uuid(row_first[0])

        return None
    except Exception as e:
        logger.error("Error resolving branch_id: %s", e)
        return None


async def archive_branch(db: AsyncSession, branch_id: str) -> Branch:
    bid = str(branch_id).strip()
    result = await db.execute(select(Branch).filter(Branch.id == bid))
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
        bid = str(branch_id).strip()
        await db.execute(
            text("UPDATE employees SET branch_id = NULL WHERE branch_id = :bid"),
            {"bid": bid}
        )
        await db.execute(text("DELETE FROM branches WHERE id = :bid"), {"bid": bid})
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e


async def get_employee_count_in_branch(db: AsyncSession, branch_id: str) -> int:
    bid = str(branch_id).strip()
    result = await db.execute(
        text("SELECT COUNT(*) FROM employees WHERE branch_id = :bid"),
        {"bid": bid}
    )
    return result.scalar() or 0
