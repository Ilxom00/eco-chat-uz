from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from app.models.employee import Employee
from app.models.test_attempt import TestAttempt
from app.models.employee_topic_assignment import EmployeeTopicAssignment

async def get_employee_topic_result(db: AsyncSession, employee_id: str, topic_id: str) -> dict:
    return {}

async def get_employee_all_results(db: AsyncSession, employee_id: str) -> list[dict]:
    return []

async def get_dashboard_stats(db: AsyncSession) -> dict:
    try:
        total_employees = (await db.execute(select(func.count()).select_from(Employee))).scalar() or 0
        started = (await db.execute(select(func.count()).select_from(TestAttempt))).scalar() or 0
        completed = (await db.execute(
            select(func.count()).select_from(TestAttempt).where(TestAttempt.status == "COMPLETED")
        )).scalar() or 0
        active = (await db.execute(
            select(func.count()).select_from(TestAttempt).where(TestAttempt.status == "IN_PROGRESS")
        )).scalar() or 0
        total_tests = (await db.execute(
            select(func.count()).select_from(EmployeeTopicAssignment).where(EmployeeTopicAssignment.status == "COMPLETED")
        )).scalar() or 0
        return {
            "totalEmployees": total_employees,
            "started": started,
            "completed": completed,
            "active": active,
            "avg1": 0,
            "avg2": 0,
            "growth": 0,
            "totalTests": total_tests,
        }
    except Exception:
        return {"totalEmployees": 0, "started": 0, "completed": 0, "active": 0, "avg1": 0, "avg2": 0, "growth": 0, "totalTests": 0}

async def get_dashboard_employee_table(db: AsyncSession, filters: dict, page: int, page_size: int) -> tuple[list, int]:
    return [], 0

async def get_general_stats_for_report(db: AsyncSession, filters: dict) -> list[dict]:
    return []

async def get_topic_stats_for_report(db: AsyncSession, topic_id: str, filters: dict) -> list[dict]:
    return []

async def get_employee_detail_for_report(db: AsyncSession, employee_id: str) -> dict:
    return {}
