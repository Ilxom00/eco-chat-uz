"""
eco-chat.uz — Persistent DataGuard Engine
Writes the database backup directly to the persistent host volume /backups/db_backup.json.
This volume is mapped to /opt/ecochat-data/backups on the host SSD, ensuring 100% persistence.
"""
import json
import os
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# Absolute path on the persistent volume
PERSISTENT_BACKUP_PATH = "/backups/db_backup.json"
LOCAL_FALLBACK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db_backup.json")


def get_backup_path() -> str:
    """Returns the most appropriate persistent backup path."""
    if os.path.exists("/backups") or os.path.exists(os.path.dirname(PERSISTENT_BACKUP_PATH)):
        return PERSISTENT_BACKUP_PATH
    return LOCAL_FALLBACK_PATH


async def auto_backup_data(db: AsyncSession):
    """
    Export all employees, assignments, and test_attempts into persistent JSON backup on host SSD.
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
        asgn_res = await db.execute(text("SELECT id, employee_id, topic_id, status FROM employee_topic_assignments"))
        assignments = [dict(r._mapping) for r in asgn_res.fetchall()]
        for asg in assignments:
            asg["id"] = str(asg["id"])
            asg["employee_id"] = str(asg["employee_id"])
            asg["topic_id"] = str(asg["topic_id"])
            asg["status"] = str(asg.get("status", "ASSIGNED"))

        data = {
            "timestamp": datetime.now().isoformat(),
            "employees": employees,
            "attempts": attempts,
            "assignments": assignments,
        }

        # Write to persistent volume
        target_path = get_backup_path()
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("💾 DataGuard: successfully backed up %d employees & %d attempts to %s", len(employees), len(attempts), target_path)
    except Exception as e:
        logger.warning("DataGuard auto_backup error: %s", e)


async def auto_restore_if_empty(db: AsyncSession):
    """
    If employees table is empty on startup, auto-restore from persistent backup JSON.
    """
    try:
        # Environment Guard
        is_prod = (
            os.getenv("APP_ENV") == "production" or 
            os.getenv("ENVIRONMENT") == "production"
        )

        emp_cnt = (await db.execute(text("SELECT COUNT(*) FROM employees"))).scalar() or 0
        if emp_cnt > 0:
            logger.info("ℹ️ DataGuard: DB has %d employees — backing up latest state.", emp_cnt)
            await auto_backup_data(db)
            return

        # Empty Database Safety Lock (warn only, do not crash to keep system online)
        topic_cnt = 0
        try:
            topic_cnt = (await db.execute(text("SELECT COUNT(*) FROM topics"))).scalar() or 0
        except Exception:
            pass

        if is_prod and emp_cnt == 0 and topic_cnt > 0:
            logger.warning("⚠️ WARNING: Empty production database detected. DataGuard is starting restore...")



        target_path = get_backup_path()
        if not os.path.exists(target_path) or os.path.getsize(target_path) < 10:
            # Check fallback path
            if target_path == PERSISTENT_BACKUP_PATH and os.path.exists(LOCAL_FALLBACK_PATH) and os.path.getsize(LOCAL_FALLBACK_PATH) >= 10:
                target_path = LOCAL_FALLBACK_PATH
            else:
                logger.info("ℹ️ DataGuard: No backup JSON found at %s", target_path)
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
                INSERT INTO employee_topic_assignments (id, employee_id, topic_id, status)
                VALUES (:id, :eid, :tid, :st)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": str(asg["id"]),
                "eid": str(asg["employee_id"]),
                "tid": str(asg["topic_id"]),
                "st": str(asg.get("status", "ASSIGNED"))
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
