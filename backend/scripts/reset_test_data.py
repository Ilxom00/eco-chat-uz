"""
eco-chat.uz — Test ma'lumotlarini tozalash skripti
Saqlanadiganlar: admins, topics, questions, question_answers
O'chiriladiganlar: employees, test results, assignments, audit_logs
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ecochat.db")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def reset():
    print("=" * 50)
    print("  eco-chat.uz — Test ma'lumotlarini tozalash")
    print("=" * 50)

    engine = create_async_engine(DATABASE_URL, echo=False)

    tables_to_clear = [
        "audit_logs",
        "attempt_questions",
        "test_attempts",
        "employee_topic_questions",
        "employee_topic_assignments",
        "employees",
    ]

    async with engine.begin() as conn:
        # SQLite foreign key check off
        try:
            await conn.execute(text("PRAGMA foreign_keys = OFF"))
        except Exception:
            pass

        for table in tables_to_clear:
            try:
                result = await conn.execute(text(f"DELETE FROM {table}"))
                print(f"  ✅ {table}: {result.rowcount} qator o'chirildi")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")

        # SQLite foreign key check on
        try:
            await conn.execute(text("PRAGMA foreign_keys = ON"))
        except Exception:
            pass

    await engine.dispose()
    print("=" * 50)
    print("  Barcha test ma'lumotlari tozalandi!")
    print("  Saqlangan: admins, topics, questions")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(reset())
