import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.employee import Employee
from app.models.branch import Branch

logger = logging.getLogger(__name__)


async def get_or_create_employee(db: AsyncSession, telegram_user_id: int) -> tuple[Employee, bool]:
    tg_id = int(telegram_user_id)
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == tg_id))
    employee = result.scalar_one_or_none()

    if employee:
        return employee, False

    employee = Employee(
        id=uuid.uuid4(),
        telegram_user_id=tg_id,
        full_name="Unknown",
        registration_state="PENDING"
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee, True


async def register_employee(
    db: AsyncSession,
    telegram_user_id: int,
    full_name: str,
    branch_name_or_id: str | None = None,
    phone: str = ""
) -> Employee:
    """
    Registers or updates an employee in the database.
    Works with BOTH SQLite (String(36) UUID) and PostgreSQL (UUID native).
    """
    import os as _os
    _use_sqlite = _os.getenv("DATABASE_URL", "").startswith("sqlite") or not _os.getenv("DATABASE_URL", "")
    tg_id = int(telegram_user_id)

    # Resolve branch using ORM-safe method
    branch_val = None
    if branch_name_or_id:
        from app.services.branch_service import resolve_branch_id
        try:
            branch_uuid = await resolve_branch_id(db, branch_name_or_id)
            # SQLite needs string, PostgreSQL needs UUID object
            branch_val = str(branch_uuid) if branch_uuid else None
        except Exception as e:
            logger.warning("Could not resolve branch_id for %s: %s", branch_name_or_id, e)

    # Fallback: get first active branch via ORM
    if not branch_val:
        result = await db.execute(
            select(Branch).filter(Branch.is_active == True).order_by(Branch.sort_order).limit(1)
        )
        first_branch = result.scalar_one_or_none()
        if first_branch:
            branch_val = str(first_branch.id)

    # Check if employee already exists
    emp_res = await db.execute(select(Employee).filter(Employee.telegram_user_id == tg_id))
    emp = emp_res.scalar_one_or_none()

    if emp:
        emp.full_name = full_name
        if branch_val:
            emp.branch_id = branch_val
        emp.phone = phone or emp.phone or ""
        emp.registration_state = "REGISTERED"
        emp.registered_at = datetime.now(timezone.utc)
    else:
        new_id = str(uuid.uuid4())  # String — works for both SQLite and PostgreSQL
        emp = Employee(
            id=new_id,
            telegram_user_id=tg_id,
            full_name=full_name,
            branch_id=branch_val,
            phone=phone or "",
            registration_state="REGISTERED",
            registered_at=datetime.now(timezone.utc),
        )
        db.add(emp)

    await db.commit()
    await db.refresh(emp)
    logger.info("Registered employee: %s (TG: %d, branch: %s)", full_name, tg_id, branch_val)
    return emp


async def update_registration(
    db: AsyncSession,
    telegram_user_id: int,
    full_name: str,
    branch_id: str | uuid.UUID | None,
    phone: str
) -> Employee:
    return await register_employee(db, telegram_user_id, full_name, str(branch_id) if branch_id else None, phone)


async def get_employee_by_telegram_id(db: AsyncSession, telegram_user_id: int | str) -> Employee | None:
    try:
        tg_id = int(telegram_user_id)
        result = await db.execute(select(Employee).filter(Employee.telegram_user_id == tg_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching employee by TG ID %s: %s", telegram_user_id, e)
        return None


async def get_employee_full_detail(db: AsyncSession, employee_id: str) -> dict:
    return {"employee_id": str(employee_id)}


async def list_employees(db: AsyncSession, filters: dict, page: int, page_size: int) -> tuple[list, int]:
    query = select(Employee)
    total = await db.execute(select(func.count()).select_from(Employee))
    total_count = total.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total_count


async def delete_employee_cascade(db: AsyncSession, employee_id: str) -> bool:
    """Delete employee and all related data."""
    try:
        eid_uuid = uuid.UUID(str(employee_id).strip())
        eid = str(eid_uuid)

        await db.execute(text("""
            DELETE FROM attempt_questions WHERE attempt_id IN (
                SELECT id FROM test_attempts WHERE employee_id = :eid
            )
        """), {"eid": eid_uuid})

        await db.execute(text("""
            DELETE FROM employee_topic_questions WHERE assignment_id IN (
                SELECT id FROM employee_topic_assignments WHERE employee_id = :eid
            )
        """), {"eid": eid_uuid})

        await db.execute(text("""
            UPDATE employee_topic_assignments
            SET attempt1_id = NULL, attempt2_id = NULL
            WHERE employee_id = :eid
        """), {"eid": eid_uuid})

        await db.execute(text("DELETE FROM test_attempts WHERE employee_id = :eid"), {"eid": eid_uuid})
        await db.execute(text("DELETE FROM employee_topic_assignments WHERE employee_id = :eid"), {"eid": eid_uuid})
        await db.execute(text("DELETE FROM employees WHERE id = :eid"), {"eid": eid_uuid})

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
