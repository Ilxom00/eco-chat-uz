import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.employee import Employee
from app.models.attempt import TestAttempt, EmployeeTopicAssignment

logger = logging.getLogger(__name__)


async def get_employee_topic_result(db: AsyncSession, employee_id: str, topic_id: str) -> dict:
    return {}


async def get_employee_all_results(db: AsyncSession, employee_id: str) -> list[dict]:
    return []


async def get_dashboard_stats(db: AsyncSession) -> dict:
    try:
        # Real employee count
        total_employees = (await db.execute(select(func.count()).select_from(Employee))).scalar() or 0

        # Tests started by existing employees
        started = (await db.execute(text("""
            SELECT COUNT(DISTINCT ta.id) FROM test_attempts ta
            JOIN employees e ON ta.employee_id = e.id
        """))).scalar() or 0

        # Tests completed by existing employees
        completed = (await db.execute(text("""
            SELECT COUNT(DISTINCT ta.id) FROM test_attempts ta
            JOIN employees e ON ta.employee_id = e.id
            WHERE ta.status = 'COMPLETED'
        """))).scalar() or 0

        # Currently active tests
        active = (await db.execute(text("""
            SELECT COUNT(DISTINCT ta.id) FROM test_attempts ta
            JOIN employees e ON ta.employee_id = e.id
            WHERE ta.status = 'IN_PROGRESS'
        """))).scalar() or 0

        total_tests = (await db.execute(text("""
            SELECT COUNT(*) FROM employee_topic_assignments eta
            JOIN employees e ON eta.employee_id = e.id
            WHERE eta.status = 'COMPLETED'
        """))).scalar() or 0

        # Per-topic averages
        topic_stats_raw = await db.execute(text("""
            SELECT
                t.sequence_order,
                t.short_name,
                ROUND(AVG(CASE WHEN ta.attempt_number = 1 AND ta.status = 'COMPLETED' THEN ta.score END), 1) as avg1,
                ROUND(AVG(CASE WHEN ta.attempt_number = 2 AND ta.status = 'COMPLETED' THEN ta.score END), 1) as avg2
            FROM topics t
            LEFT JOIN test_attempts ta ON ta.topic_id = t.id
            WHERE t.is_active = true
            GROUP BY t.id, t.sequence_order, t.short_name
            ORDER BY t.sequence_order
        """))
        topic_stats = []
        for row in topic_stats_raw.fetchall():
            a1 = float(row[2]) if row[2] is not None else None
            a2 = float(row[3]) if row[3] is not None else None
            diff = round(a2 - a1, 1) if (a1 is not None and a2 is not None) else None
            topic_stats.append({
                "seq": row[0],
                "name": row[1],
                "avg1": a1,
                "avg2": a2,
                "diff": diff,
            })

        # Overall averages
        all_avg1 = [t["avg1"] for t in topic_stats if t["avg1"] is not None]
        all_avg2 = [t["avg2"] for t in topic_stats if t["avg2"] is not None]
        overall_avg1 = round(sum(all_avg1) / len(all_avg1), 1) if all_avg1 else None
        overall_avg2 = round(sum(all_avg2) / len(all_avg2), 1) if all_avg2 else None
        overall_diff = round(overall_avg2 - overall_avg1, 1) if (overall_avg1 is not None and overall_avg2 is not None) else None

        return {
            "totalEmployees": total_employees,
            "started": started,
            "completed": completed,
            "active": active,
            "totalTests": total_tests,
            "topicStats": topic_stats,
            "overallAvg1": overall_avg1,
            "overallAvg2": overall_avg2,
            "overallDiff": overall_diff,
        }
    except Exception as e:
        logger.error("Error fetching dashboard stats: %s", e, exc_info=True)
        return {"totalEmployees": 0, "started": 0, "completed": 0, "active": 0, "totalTests": 0, "topicStats": [], "overallAvg1": None, "overallAvg2": None, "overallDiff": None}


async def get_dashboard_employee_table(db: AsyncSession, filters: dict, page: int, page_size: int) -> tuple[list, int]:
    """
    Returns employees with per-topic test scores for the rating table.
    Guaranteed zero-deletion data safety.
    """
    try:
        search = (filters.get("search") or "").strip() if filters else ""
        branch_id = filters.get("branch_id") if filters else None

        where_clause = "WHERE 1=1"
        params = {"limit": page_size, "offset": (page - 1) * page_size}

        if search:
            where_clause += " AND (e.full_name LIKE :search OR b.name LIKE :search)"
            params["search"] = f"%{search}%"

        if branch_id and str(branch_id).strip():
            where_clause += " AND e.branch_id = :branch_id"
            params["branch_id"] = str(branch_id)

        # Count total matching employees
        total_sql = f"""
            SELECT COUNT(*) FROM employees e
            LEFT JOIN branches b ON e.branch_id = b.id
            {where_clause}
        """
        total = (await db.execute(text(total_sql), params)).scalar() or 0

        if total == 0:
            return [], 0

        # Get employees ordered by creation date descending
        emp_sql = f"""
            SELECT e.id, e.full_name, COALESCE(b.name, '—') as branch_name
            FROM employees e
            LEFT JOIN branches b ON e.branch_id = b.id
            {where_clause}
            ORDER BY e.created_at DESC, e.full_name ASC
            LIMIT :limit OFFSET :offset
        """
        emp_rows = await db.execute(text(emp_sql), params)
        employees = emp_rows.fetchall()

        # Get all active topics in order
        topic_rows = await db.execute(text("""
            SELECT id, short_name, full_name, sequence_order
            FROM topics
            WHERE is_active = true
            ORDER BY sequence_order
        """))
        topics = topic_rows.fetchall()

        # Build rating table for each employee
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
        logger.error("Error fetching dashboard employee table: %s", e, exc_info=True)
        return [], 0


async def get_general_stats_for_report(db: AsyncSession, filters: dict) -> list[dict]:
    return []


async def get_topic_stats_for_report(db: AsyncSession, topic_id: str, filters: dict) -> list[dict]:
    return []


async def get_employee_detail_for_report(db: AsyncSession, employee_id: str) -> dict:
    return {}
