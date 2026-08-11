# -*- coding: utf-8 -*-
"""
Safe cleanup script for purging loadtest data from PostgreSQL/SQLite.
Only targets entities with 'LOADTEST_' prefix.
"""
import asyncio
from sqlalchemy.future import select
from sqlalchemy import delete
from app.database import AsyncSessionLocal
from app.models.employee import Employee
from app.models.attempt import TestAttempt, AttemptQuestion, EmployeeTopicAssignment, EmployeeTopicQuestion
from loguru import logger

async def cleanup():
    async with AsyncSessionLocal() as db:
        # Find all employees starting with LOADTEST_
        res = await db.execute(select(Employee).where(Employee.full_name.like("LOADTEST_%")))
        employees = res.scalars().all()
        emp_ids = [str(e.id) for e in employees]
        
        if not emp_ids:
            logger.info("No loadtest employees found to clean up.")
            return

        logger.info(f"Found {len(emp_ids)} loadtest employees. Starting purged cascade...")

        # Get all attempts for these employees
        res_att = await db.execute(select(TestAttempt).where(TestAttempt.employee_id.in_(emp_ids)))
        attempts = res_att.scalars().all()
        att_ids = [str(a.id) for a in attempts]

        # Delete Attempt Questions
        if att_ids:
            aq_del = await db.execute(delete(AttemptQuestion).where(AttemptQuestion.attempt_id.in_(att_ids)))
            logger.info(f"Purged {aq_del.rowcount} attempt questions.")

        # Delete Employee Topic Questions
        res_eta = await db.execute(select(EmployeeTopicAssignment.id).where(EmployeeTopicAssignment.employee_id.in_(emp_ids)))
        eta_ids = [str(r) for r in res_eta.scalars().all()]
        if eta_ids:
            etq_del = await db.execute(delete(EmployeeTopicQuestion).where(EmployeeTopicQuestion.assignment_id.in_(eta_ids)))
            logger.info(f"Purged {etq_del.rowcount} employee topic questions.")

        # Delete Test Attempts
        if emp_ids:
            att_del = await db.execute(delete(TestAttempt).where(TestAttempt.employee_id.in_(emp_ids)))
            logger.info(f"Purged {att_del.rowcount} test attempts.")

        # Delete Employee Topic Assignments
        eta_del = await db.execute(delete(EmployeeTopicAssignment).where(EmployeeTopicAssignment.employee_id.in_(emp_ids)))
        logger.info(f"Purged {eta_del.rowcount} employee topic assignments.")

        # Delete Employees
        emp_del = await db.execute(delete(Employee).where(Employee.id.in_(emp_ids)))
        logger.info(f"Purged {emp_del.rowcount} employees.")

        await db.commit()
        logger.info("Cleanup successfully committed!")

if __name__ == "__main__":
    asyncio.run(cleanup())
