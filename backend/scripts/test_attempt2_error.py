import asyncio
import os
from app.bot.api_client import bot_api

async def run_test():
    # Let's find one employee who has finished attempt 1
    from app.database import AsyncSessionLocal
    from app.models.attempt import EmployeeTopicAssignment
    from sqlalchemy.future import select as sa_select

    async with AsyncSessionLocal() as db:
        res = await db.execute(sa_select(EmployeeTopicAssignment).where(EmployeeTopicAssignment.attempt1_id != None))
        asgns = res.scalars().all()
        for asgn in asgns:
            # Let's get employee telegram_user_id
            from app.models.employee import Employee
            emp = (await db.execute(sa_select(Employee).where(Employee.id == asgn.employee_id))).scalar_one_or_none()
            if emp:
                print(f"Testing start_attempt for {emp.full_name} (tg={emp.telegram_user_id}) topic={asgn.topic_id}")
                resp = await bot_api.start_attempt(emp.telegram_user_id, asgn.topic_id, 2)
                print("API RESPONSE:", resp)

if __name__ == "__main__":
    asyncio.run(run_test())
