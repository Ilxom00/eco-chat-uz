"""
eco-chat.uz — Automatic Data Persistence & Restore Guard
Prevents employee and test result data loss on container restart or database reset.
"""
import json
import os
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

BACKUP_FILE = os.environ.get("BACKUP_JSON_PATH", "/backups/db_backup.json")
LOCAL_BACKUP = "./backups/db_backup.json"


async def auto_backup_data(db: AsyncSession):
    """
    Export all employees, assignments, and test_attempts into persistent JSON backup.
    Runs on employee register, test complete, and app startup.
    """
    try:
        # 1. Get employees
        emp_res = await db.execute(text("SELECT id, telegram_user_id, full_name, phone, branch_id, is_active FROM employees"))
        employees = [dict(r._mapping) for r in emp_res.fetchall()]
        for e in employees:
            e["id"] = str(e["id"])
            e["branch_id"] = str(e["branch_id"]) if e.get("branch_id") else None

        if not employees:
            return

        # 2. Get test attempts
        att_res = await db.execute(text("SELECT id, employee_id, topic_id, attempt_number, score, status, assignment_id FROM test_attempts"))
        attempts = [dict(r._mapping) for r in att_res.fetchall()]
        for a in attempts:
            a["id"] = str(a["id"])
            a["employee_id"] = str(a["employee_id"])
            a["topic_id"] = str(a["topic_id"])
            a["assignment_id"] = str(a["assignment_id"]) if a.get("assignment_id") else None

        # 3. Get assignments
        asgn_res = await db.execute(text("SELECT id, employee_id, topic_id, is_active FROM employee_topic_assignments"))
        assignments = [dict(r._mapping) for r in asgn_res.fetchall()]
        for asg in assignments:
            asg["id"] = str(asg["id"])
            asg["employee_id"] = str(asg["employee_id"])
            asg["topic_id"] = str(asg["topic_id"])

        data = {
            "timestamp": datetime.now().isoformat(),
            "employees": employees,
            "attempts": attempts,
            "assignments": assignments,
        }

        for path in [BACKUP_FILE, LOCAL_BACKUP]:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                logger.debug("Minor backup write error for %s: %s", path, ex)

        logger.info("✅ DataGuard: backed up %d employees & %d attempts", len(employees), len(attempts))
    except Exception as e:
        logger.warning("DataGuard auto_backup error: %s", e)


async def auto_restore_if_empty(db: AsyncSession):
    """
    If employees table is empty on startup, auto-restore from backup JSON.
    """
    try:
        emp_cnt = (await db.execute(text("SELECT COUNT(*) FROM employees"))).scalar() or 0
        if emp_cnt > 0:
            logger.info("ℹ️ DataGuard: DB has %d employees — backing up latest state.", emp_cnt)
            await auto_backup_data(db)
            return

        # Search for valid backup file
        target_path = None
        for path in [BACKUP_FILE, LOCAL_BACKUP]:
            if os.path.exists(path) and os.path.getsize(path) > 10:
                target_path = path
                break

        if not target_path:
            logger.info("ℹ️ DataGuard: No backup JSON found yet.")
            return

        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        employees = data.get("employees", [])
        assignments = data.get("assignments", [])
        attempts = data.get("attempts", [])

        if not employees:
            return

        logger.info("🔄 DataGuard: Restoring %d employees from %s...", len(employees), target_path)

        # 1. Restore employees
        for e in employees:
            await db.execute(text("""
                INSERT INTO employees (id, telegram_user_id, full_name, phone, branch_id, is_active)
                VALUES (:id, :tg_id, :fn, :ph, :bid, :act)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": str(e["id"]),
                "tg_id": int(e["telegram_user_id"]),
                "fn": str(e["full_name"]),
                "ph": str(e.get("phone", "")),
                "bid": str(e["branch_id"]) if e.get("branch_id") else None,
                "act": bool(e.get("is_active", True))
            })

        # 2. Restore assignments
        for asg in assignments:
            await db.execute(text("""
                INSERT INTO employee_topic_assignments (id, employee_id, topic_id, is_active)
                VALUES (:id, :eid, :tid, :act)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": str(asg["id"]),
                "eid": str(asg["employee_id"]),
                "tid": str(asg["topic_id"]),
                "act": bool(asg.get("is_active", True))
            })

        # 3. Restore attempts
        for a in attempts:
            await db.execute(text("""
                INSERT INTO test_attempts (id, employee_id, topic_id, attempt_number, score, status, assignment_id)
                VALUES (:id, :eid, :tid, :num, :score, :st, :asg_id)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": str(a["id"]),
                "eid": str(a["employee_id"]),
                "tid": str(a["topic_id"]),
                "num": int(a["attempt_number"]),
                "score": int(a["score"]) if a.get("score") is not None else 0,
                "st": str(a.get("status", "COMPLETED")),
                "asg_id": str(a["assignment_id"]) if a.get("assignment_id") else None
            })

        await db.commit()
        logger.info("✅ DataGuard: RESTORED SUCCESS %d employees & %d attempts!", len(employees), len(attempts))
    except Exception as e:
        logger.error("❌ DataGuard auto_restore error: %s", e, exc_info=True)
