from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.topic import Topic
from app.models.question import Question

async def get_active_topics_ordered(db: AsyncSession) -> list[Topic]:
    result = await db.execute(select(Topic).filter(Topic.is_active == True).order_by(Topic.sequence_order))
    return result.scalars().all()

async def create_topic(db: AsyncSession, short_name: str, full_name: str) -> Topic:
    max_order_result = await db.execute(select(func.max(Topic.sequence_order)))
    max_order = max_order_result.scalar() or 0
    topic = Topic(short_name=short_name, full_name=full_name, sequence_order=max_order + 1)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

async def get_topic_active_question_count(db: AsyncSession, topic_id: str) -> int:
    result = await db.execute(select(func.count(Question.id)).filter(Question.topic_id == topic_id, Question.status == "ACTIVE"))
    return result.scalar() or 0

async def is_topic_available_for_testing(db: AsyncSession, topic_id: str) -> bool:
    topic_res = await db.execute(select(Topic).filter(Topic.id == topic_id))
    topic = topic_res.scalar_one_or_none()
    if not topic or not topic.is_active:
        return False
    cnt = await get_topic_active_question_count(db, topic_id)
    return cnt >= 15

async def get_topic_status_for_employee(db: AsyncSession, employee_id: str, topic_id: str) -> str:
    return "AVAILABLE"

async def get_all_topics_status_for_employee(db: AsyncSession, employee_id: str) -> list[dict]:
    topics = await get_active_topics_ordered(db)
    res = []
    for t in topics:
        res.append({"topic": t, "status": await get_topic_status_for_employee(db, employee_id, str(t.id))})
    return res

async def is_topic_unlocked_for_employee(db: AsyncSession, employee_id: str, topic_id: str) -> bool:
    return True

async def delete_topic_cascade(db: AsyncSession, topic_id: str) -> bool:
    """Mavzuni va barcha bog'liq ma'lumotlarni to'liq o'chiradi."""
    try:
        tid = topic_id
        # 1. attempt_questions → test_attempts (this topic)
        await db.execute(text("""
            DELETE FROM attempt_questions WHERE attempt_id IN (
                SELECT id FROM test_attempts WHERE topic_id = :tid
            )
        """), {"tid": tid})

        # 2. employee_topic_questions → employee_topic_assignments (this topic)
        await db.execute(text("""
            DELETE FROM employee_topic_questions WHERE assignment_id IN (
                SELECT id FROM employee_topic_assignments WHERE topic_id = :tid
            )
        """), {"tid": tid})

        # 3. Null out circular FKs in employee_topic_assignments
        await db.execute(text("""
            UPDATE employee_topic_assignments
            SET attempt1_id = NULL, attempt2_id = NULL
            WHERE topic_id = :tid
        """), {"tid": tid})

        # 4. Delete test_attempts for this topic
        await db.execute(text("DELETE FROM test_attempts WHERE topic_id = :tid"), {"tid": tid})

        # 5. Delete employee_topic_assignments for this topic
        await db.execute(text("DELETE FROM employee_topic_assignments WHERE topic_id = :tid"), {"tid": tid})

        # 6. Delete question_answers for questions in this topic
        await db.execute(text("""
            DELETE FROM question_answers WHERE question_id IN (
                SELECT id FROM questions WHERE topic_id = :tid
            )
        """), {"tid": tid})

        # 7. Delete questions
        await db.execute(text("DELETE FROM questions WHERE topic_id = :tid"), {"tid": tid})

        # 8. Delete topic
        await db.execute(text("DELETE FROM topics WHERE id = :tid"), {"tid": tid})

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
