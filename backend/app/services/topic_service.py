import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.topic import Topic
from app.models.question import Question

logger = logging.getLogger(__name__)


def _force_str(val) -> str:
    if isinstance(val, uuid.UUID):
        return str(val)
    return str(val).strip()


async def get_active_topics_ordered(db: AsyncSession) -> list[Topic]:
    result = await db.execute(select(Topic).order_by(Topic.sequence_order))
    return result.scalars().all()


async def get_topic_by_id(db: AsyncSession, topic_id: str) -> Topic | None:
    try:
        tid_str = _force_str(topic_id)
        result = await db.execute(select(Topic).filter(Topic.id == tid_str))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def create_topic(db: AsyncSession, short_name: str, full_name: str) -> Topic:
    max_order_result = await db.execute(select(func.max(Topic.sequence_order)))
    max_order = max_order_result.scalar() or 0
    topic = Topic(id=str(uuid.uuid4()), short_name=short_name, full_name=full_name, sequence_order=max_order + 1)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def get_topic_active_question_count(db: AsyncSession, topic_id: str) -> int:
    try:
        tid_str = _force_str(topic_id)
        # Match both string tid and raw tid to be 100% resilient across database types
        cnt = (await db.execute(
            text("SELECT COUNT(*) FROM questions WHERE (topic_id = :tid OR topic_id = :tid_str) AND status = 'ACTIVE'"),
            {"tid": tid_str, "tid_str": topic_id}
        )).scalar()
        return cnt or 0
    except Exception as e:
        logger.error("Error counting questions for topic %s: %s", topic_id, e)
        return 0


async def is_topic_available_for_testing(db: AsyncSession, topic_id: str) -> bool:
    topic = await get_topic_by_id(db, topic_id)
    if not topic or not topic.is_active:
        return False
    cnt = await get_topic_active_question_count(db, topic_id)
    return cnt >= 15


async def get_topic_status_for_employee(db: AsyncSession, employee_id: str, topic_id: str) -> str:
    return "available"


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
        tid = _force_str(topic_id)
        await db.execute(text("""
            DELETE FROM attempt_questions WHERE attempt_id IN (
                SELECT id FROM test_attempts WHERE topic_id = :tid
            )
        """), {"tid": tid})

        await db.execute(text("""
            DELETE FROM employee_topic_questions WHERE assignment_id IN (
                SELECT id FROM employee_topic_assignments WHERE topic_id = :tid
            )
        """), {"tid": tid})

        await db.execute(text("""
            UPDATE employee_topic_assignments
            SET attempt1_id = NULL, attempt2_id = NULL
            WHERE topic_id = :tid
        """), {"tid": tid})

        await db.execute(text("DELETE FROM test_attempts WHERE topic_id = :tid"), {"tid": tid})
        await db.execute(text("DELETE FROM employee_topic_assignments WHERE topic_id = :tid"), {"tid": tid})

        await db.execute(text("""
            DELETE FROM question_answers WHERE question_id IN (
                SELECT id FROM questions WHERE topic_id = :tid
            )
        """), {"tid": tid})

        await db.execute(text("DELETE FROM questions WHERE topic_id = :tid"), {"tid": tid})
        await db.execute(text("DELETE FROM topics WHERE id = :tid"), {"tid": tid})

        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
