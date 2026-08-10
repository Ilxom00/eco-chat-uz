import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.services import test_engine

target_url = os.getenv("DATABASE_URL", "")
if target_url.startswith("postgresql://"):
    target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif target_url.startswith("postgres://"):
    target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)

target_engine = create_async_engine(target_url)
TargetSession = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

async def test_submit():
    async with TargetSession() as db:
        attempt_id = "ccd78329-eecb-4ee4-8508-f2500c53dce4"
        display_order = 15
        
        # Get AQ row
        res = await db.execute(text(f"SELECT id, assignment_question_id, answer_display_order FROM attempt_questions WHERE attempt_id = '{attempt_id}' AND display_order = {display_order}"))
        row = res.fetchone()
        if not row:
            print("AQ not found!")
            return
            
        aq_id, assignment_q_id, answer_display_order = row[0], row[1], row[2]
        print(f"AQ ID: {aq_id}, Assignment Q ID: {assignment_q_id}")
        print(f"Answer options: {answer_display_order}")
        
        # Choose the first option ID
        opt_id = answer_display_order[0]["id"]
        print(f"Submitting option_id={opt_id} for question 15...")
        
        try:
            # We don't pass redis so it falls back to DB idempotency
            res = await test_engine.submit_answer(db, None, attempt_id, display_order, opt_id)
            print("SUBMIT RESULT:", res)
        except Exception as e:
            import traceback
            print("EXCEPTION CAUGHT:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_submit())
