import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.bot.api_client import bot_api

target_url = os.getenv("DATABASE_URL", "")
if target_url.startswith("postgresql://"):
    target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif target_url.startswith("postgres://"):
    target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)

target_engine = create_async_engine(target_url)
TargetSession = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

async def test_prof():
    async with TargetSession() as db:
        res = await db.execute(text("SELECT telegram_user_id, id, full_name FROM employees LIMIT 5"))
        emps = res.fetchall()
        for emp in emps:
            tg_id, emp_uuid, fn = emp[0], emp[1], emp[2]
            print(f"Testing Profile for: {fn} (tg_id={tg_id}, uuid={emp_uuid})")
            try:
                profile = await bot_api.get_employee_status(tg_id)
                print("PROFILE RESULT:", profile)
            except Exception as e:
                import traceback
                print("EXCEPTION CAUGHT FOR PROFILE:")
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_prof())
