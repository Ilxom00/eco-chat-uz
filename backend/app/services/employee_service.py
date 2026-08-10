import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.employee import Employee

logger = logging.getLogger(__name__)


def _force_uuid(val):
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val).strip())
    except (ValueError, TypeError):
        return None


async def get_or_create_employee(db: AsyncSession, telegram_user_id: int) -> tuple[Employee, bool]:
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
    employee = result.scalar_one_or_none()
    
    if employee:
        return employee, False
        
    employee = Employee(
        id=uuid.uuid4(),
        telegram_user_id=telegram_user_id,
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
    Registers or updates an employee in the database using exact UUID objects.
    Guarantees zero-deletion persistence.
    """
    try:
        branch_uuid = None
        if branch_name_or_id:
            from app.services.branch_service import resolve_branch_id
            try:
                raw_b = await resolve_branch_id(db, str(branch_name_or_id))
                branch_uuid = _force_uuid(raw_b)
            except Exception as e:
                logger.warning("Could not resolve branch_id for %s: %s", branch_name_or_id, e)

        if not branch_uuid:
            # Fallback to first branch
            b_res = await db.execute(text("SELECT id FROM branches ORDER BY sort_order ASC LIMIT 1"))
            b_row = b_res.fetchone()
            if b_row:
                branch_uuid = _force_uuid(b_row[0])

        emp_res = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
        emp = emp_res.scalar_one_or_none()

        if emp:
            emp.full_name = full_name
            if branch_uuid:
                emp.branch_id = branch_uuid
            emp.phone = phone or emp.phone or ""
            emp.registration_state = "REGISTERED"
            emp.registered_at = datetime.now(timezone.utc)
        else:
            emp = Employee(
                id=uuid.uuid4(),
                telegram_user_id=telegram_user_id,
                full_name=full_name,
                branch_id=branch_uuid,
                phone=phone or "",
                registration_state="REGISTERED",
                registered_at=datetime.now(timezone.utc),
            )
            db.add(emp)

        await db.commit()
        await db.refresh(emp)
        logger.info("Successfully registered/updated employee in DB: %s (TG: %d)", full_name, telegram_user_id)
        return emp

    except Exception as e:
        await db.rollback()
        logger.error("Error in register_employee service: %s", e, exc_info=True)
        raise e


async def update_registration(
    db: AsyncSession, 
    telegram_user_id: int, 
    full_name: str, 
    branch_id: str | uuid.UUID | None, 
    phone: str
) -> Employee:
    return await register_employee(db, telegram_user_id, full_name, str(branch_id) if branch_id else None, phone)


async def get_employee_by_telegram_id(db: AsyncSession, telegram_user_id: int) -> Employee | None:
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
    return result.scalar_one_or_none()


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
    """Xodimni va unga tegishli barcha ma'lumotlarni to'liq o'chiradi."""
    try:
        eid = str(employee_id).strip()
        await db.execute(text("""
            DELETE FROM attempt_questions WHERE attempt_id IN (
                SELECT id FROM test_attempts WHERE employee_id = :eid
            )
        """), {"eid": eid})

        await db.execute(text("""
            DELETE FROM employee_topic_questions WHERE assignment_id IN (
                SELECT id FROM employee_topic_assignments WHERE employee_id = :eid
            )
        """), {"eid": eid})

        await db.execute(text("""
            UPDATE employee_topic_assignments
            SET attempt1_id = NULL, attempt2_id = NULL
            WHERE employee_id = :eid
        """), {"eid": eid})

        await db.execute(text("DELETE FROM test_attempts WHERE employee_id = :eid"), {"eid": eid})
        await db.execute(text("DELETE FROM employee_topic_assignments WHERE employee_id = :eid"), {"eid": eid})
        await db.execute(text("DELETE FROM employees WHERE id = :eid"), {"eid": eid})

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
