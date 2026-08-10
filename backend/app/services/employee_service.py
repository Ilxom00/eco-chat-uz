from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.employee import Employee
from datetime import datetime
import pytz


async def get_or_create_employee(db: AsyncSession, telegram_user_id: int) -> tuple[Employee, bool]:
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
    employee = result.scalar_one_or_none()
    
    if employee:
        return employee, False
        
    employee = Employee(
        telegram_user_id=telegram_user_id,
        full_name="Unknown",
        registration_state="PENDING"
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee, True

async def update_registration(db: AsyncSession, telegram_user_id: int, full_name: str, branch_id: str, phone: str) -> Employee:
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
    employee = result.scalar_one_or_none()
    if employee:
        employee.full_name = full_name
        employee.branch_id = branch_id
        employee.phone = phone
        employee.registration_state = "REGISTERED"
        employee.registered_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        await db.commit()
        await db.refresh(employee)
    return employee

async def get_employee_by_telegram_id(db: AsyncSession, telegram_user_id: int) -> Employee | None:
    result = await db.execute(select(Employee).filter(Employee.telegram_user_id == telegram_user_id))
    return result.scalar_one_or_none()

async def get_employee_full_detail(db: AsyncSession, employee_id: str) -> dict:
    # Requires deep joins, simplified mock dict structure here
    return {"employee_id": employee_id}

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
        eid = employee_id
        # 1. attempt_questions → test_attempts (this employee)
        await db.execute(text("""
            DELETE FROM attempt_questions WHERE attempt_id IN (
                SELECT id FROM test_attempts WHERE employee_id = :eid
            )
        """), {"eid": eid})

        # 2. employee_topic_questions → employee_topic_assignments (this employee)
        await db.execute(text("""
            DELETE FROM employee_topic_questions WHERE assignment_id IN (
                SELECT id FROM employee_topic_assignments WHERE employee_id = :eid
            )
        """), {"eid": eid})

        # 3. Null out circular FKs in employee_topic_assignments
        await db.execute(text("""
            UPDATE employee_topic_assignments
            SET attempt1_id = NULL, attempt2_id = NULL
            WHERE employee_id = :eid
        """), {"eid": eid})

        # 4. Delete test_attempts
        await db.execute(text("DELETE FROM test_attempts WHERE employee_id = :eid"), {"eid": eid})

        # 5. Delete employee_topic_assignments
        await db.execute(text("DELETE FROM employee_topic_assignments WHERE employee_id = :eid"), {"eid": eid})

        # 6. Delete employee
        await db.execute(text("DELETE FROM employees WHERE id = :eid"), {"eid": eid})

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
