from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
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
    # Logic: LOCKED/AVAILABLE/IN_PROGRESS/ATTEMPT1_DONE/COMPLETED
    return "AVAILABLE"

async def get_all_topics_status_for_employee(db: AsyncSession, employee_id: str) -> list[dict]:
    topics = await get_active_topics_ordered(db)
    res = []
    for t in topics:
        res.append({"topic": t, "status": await get_topic_status_for_employee(db, employee_id, str(t.id))})
    return res

async def is_topic_unlocked_for_employee(db: AsyncSession, employee_id: str, topic_id: str) -> bool:
    return True
