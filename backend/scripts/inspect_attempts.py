import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

target_url = os.getenv("DATABASE_URL", "")
if target_url.startswith("postgresql://"):
    target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif target_url.startswith("postgres://"):
    target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)

target_engine = create_async_engine(target_url)
TargetSession = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

async def inspect():
    async with TargetSession() as db:
        print("--- TEST ATTEMPTS ---")
        res = await db.execute(text("SELECT id, employee_id, topic_id, attempt_number, status, current_question_index, score, completed_at FROM test_attempts ORDER BY started_at DESC LIMIT 5"))
        attempts = res.fetchall()
        for att in attempts:
            print(f"Attempt: id={att[0]}, emp={att[1]}, topic={att[2]}, num={att[3]}, status={att[4]}, current_q={att[5]}, score={att[6]}, completed_at={att[7]}")
            
            # Print attempt questions for this attempt
            print("  --- ATTEMPT QUESTIONS ---")
            res_aq = await db.execute(text(f"SELECT id, display_order, answer_status, is_correct, selected_answer_id, question_started_at, question_deadline_at FROM attempt_questions WHERE attempt_id = '{att[0]}' ORDER BY display_order"))
            aqs = res_aq.fetchall()
            for aq in aqs:
                print(f"    AQ: id={aq[0]}, order={aq[1]}, status={aq[2]}, correct={aq[3]}, selected={aq[4]}, started={aq[5]}, deadline={aq[6]}")

if __name__ == "__main__":
    asyncio.run(inspect())
