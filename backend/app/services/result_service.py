from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.employee import Employee
from app.models.attempt import TestAttempt, EmployeeTopicAssignment


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
    """
    Returns employees with per-topic test scores for the rating table.
    """
    try:
        # Count total employees
        total_result = await db.execute(text("SELECT COUNT(*) FROM employees"))
        total = total_result.scalar() or 0

        if total == 0:
            return [], 0

        offset = (page - 1) * page_size

        # Get employees with branch names, paginated
        emp_rows = await db.execute(text("""
            SELECT e.id, e.full_name, COALESCE(b.name, '—') as branch_name
            FROM employees e
            LEFT JOIN branches b ON e.branch_id = b.id
            ORDER BY e.full_name
            LIMIT :limit OFFSET :offset
        """), {"limit": page_size, "offset": offset})
        employees = emp_rows.fetchall()

        # Get all active topics in order
        topic_rows = await db.execute(text("""
            SELECT id, short_name, full_name, sequence_order
            FROM topics
            WHERE is_active = true
            ORDER BY sequence_order
        """))
        topics = topic_rows.fetchall()

        # For each employee, get attempt scores per topic
        items = []
        for emp in employees:
            emp_id = str(emp[0])
            emp_name = emp[1]
            branch_name = emp[2]

            topic_results = []
            scores1 = []
            scores2 = []

            for topic in topics:
                topic_id = str(topic[0])

                # Get attempt 1 and 2 scores
                attempts = await db.execute(text("""
                    SELECT attempt_number, score, status
                    FROM test_attempts
                    WHERE employee_id = :eid AND topic_id = :tid
                    ORDER BY attempt_number
                """), {"eid": emp_id, "tid": topic_id})
                att_rows = attempts.fetchall()

                att1 = next((r for r in att_rows if r[0] == 1), None)
                att2 = next((r for r in att_rows if r[0] == 2), None)

                s1 = att1[1] if att1 else None
                s2 = att2[1] if att2 else None
                diff = (s2 - s1) if (s1 is not None and s2 is not None) else None

                if s1 is not None:
                    scores1.append(s1)
                if s2 is not None:
                    scores2.append(s2)

                # Status
                if att2 and att2[2] == "COMPLETED":
                    holat = "Тугатган"
                elif att1 and att1[2] == "COMPLETED":
                    holat = "1-уринди"
                elif att1 and att1[2] == "IN_PROGRESS":
                    holat = "Жараёнда"
                else:
                    holat = "—"

                topic_results.append({
                    "num": topic[3],
                    "short_name": topic[1],
                    "attempt1": s1,
                    "attempt2": s2,
                    "diff": diff,
                    "holat": holat,
                })

            # Totals
            avg1 = round(sum(scores1) / len(scores1)) if scores1 else None
            avg2 = round(sum(scores2) / len(scores2)) if scores2 else None
            total_diff = (avg2 - avg1) if (avg1 is not None and avg2 is not None) else None

            items.append({
                "id": emp_id,
                "name": emp_name,
                "branch": branch_name,
                "topics": topic_results,
                "total": {
                    "avg1": avg1,
                    "avg2": avg2,
                    "diff": total_diff,
                }
            })

        return items, total

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], 0


async def get_general_stats_for_report(db: AsyncSession, filters: dict) -> list[dict]:
    return []


async def get_topic_stats_for_report(db: AsyncSession, topic_id: str, filters: dict) -> list[dict]:
    return []


async def get_employee_detail_for_report(db: AsyncSession, employee_id: str) -> dict:
    return {}
