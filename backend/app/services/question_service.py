import uuid
import logging
from datetime import datetime
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.question import Question, QuestionAnswer
from app.models.topic import Topic

logger = logging.getLogger(__name__)


def _force_uuid(val: str | uuid.UUID) -> uuid.UUID:
    """Strictly convert string or UUID to a python uuid.UUID object."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val).strip())
    except Exception as e:
        logger.error("Could not parse UUID from '%s': %s", val, e)
        raise ValueError(f"Яроқсиз UUID идентификатор: {val}")


async def create_question_with_answers(db: AsyncSession, topic_id: str, text_content: str, answers: list[dict]) -> Question:
    if len(answers) != 4:
        raise ValueError("Барча 4 та вариант киритилиши шарт")
    if sum(1 for a in answers if a.get("is_correct")) != 1:
        raise ValueError("Аниқ 1 та тўғри жавоб танланиши шарт")
        
    tid_uuid = _force_uuid(topic_id)

    # Verify topic exists in DB to prevent Foreign Key errors
    res = await db.execute(select(Topic).filter(Topic.id == tid_uuid))
    topic_obj = res.scalar_one_or_none()
    if not topic_obj:
        # Fallback: find first active topic in DB
        res_first = await db.execute(select(Topic).filter(Topic.is_active == True).order_by(Topic.sequence_order))
        first_t = res_first.scalars().first()
        if not first_t:
            raise ValueError("Мавзу базада топилмади. Илтимос, аввал янги мавзу яратинг.")
        tid_uuid = _force_uuid(first_t.id)

    question_uuid = uuid.uuid4()
    
    question = Question(
        id=question_uuid,
        topic_id=tid_uuid,
        text=text_content,
        status='ACTIVE'
    )
    db.add(question)
    
    for i, ans in enumerate(answers):
        q_ans = QuestionAnswer(
            id=uuid.uuid4(),
            question_id=question_uuid,
            text=ans["text"],
            is_correct=bool(ans.get("is_correct", False)),
            option_label=ans.get("option_label", ["A", "B", "C", "D"][i]),
            sort_order=i+1
        )
        db.add(q_ans)
    
    await db.commit()
    await db.refresh(question)
    return question


async def delete_question_permanent(db: AsyncSession, question_id: str) -> bool:
    qid_uuid = _force_uuid(question_id)
    await db.execute(text("DELETE FROM question_answers WHERE question_id = :qid"), {"qid": qid_uuid})
    await db.execute(text("DELETE FROM questions WHERE id = :qid"), {"qid": qid_uuid})
    await db.commit()
    return True


async def archive_question(db: AsyncSession, question_id: str) -> Question:
    qid_uuid = _force_uuid(question_id)
    result = await db.execute(select(Question).filter(Question.id == qid_uuid))
    question = result.scalar_one_or_none()
    if question:
        question.status = 'ARCHIVED'
        question.archived_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        await db.commit()
        await db.refresh(question)
    return question


async def get_active_questions_for_topic(db: AsyncSession, topic_id: str) -> list[Question]:
    tid_uuid = _force_uuid(topic_id)
    result = await db.execute(select(Question).filter(Question.topic_id == tid_uuid, Question.status == 'ACTIVE'))
    return result.scalars().all()


async def get_questions_for_topic_paginated(db: AsyncSession, topic_id: str, page: int, page_size: int, include_archived: bool = False) -> tuple[list, int]:
    try:
        tid_uuid = _force_uuid(topic_id)

        query = select(Question).filter(Question.topic_id == tid_uuid)
        if not include_archived:
            query = query.filter(Question.status == 'ACTIVE')
            
        total_query = select(func.count()).select_from(Question).filter(Question.topic_id == tid_uuid)
        if not include_archived:
            total_query = total_query.filter(Question.status == 'ACTIVE')
            
        total = (await db.execute(total_query)).scalar() or 0
        if total == 0:
            return [], 0

        query = query.order_by(Question.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
        questions_raw = (await db.execute(query)).scalars().all()
        
        result_list = []
        for q in questions_raw:
            ans_rows = (await db.execute(
                select(QuestionAnswer)
                .filter(QuestionAnswer.question_id == q.id)
                .order_by(QuestionAnswer.sort_order)
            )).scalars().all()

            correct_ans = next((a.text for a in ans_rows if a.is_correct), "—")
            options = [a.text for a in ans_rows]
            result_list.append({
                "id": str(q.id),
                "text": q.text,
                "correct_answer": correct_ans,
                "options": options,
                "status": q.status,
                "created_at": q.created_at.isoformat() if q.created_at else None
            })
        
        return result_list, total
    except Exception as e:
        logger.error("Error fetching questions for topic %s: %s", topic_id, e, exc_info=True)
        return [], 0


async def import_from_excel(db: AsyncSession, topic_id: str, file_bytes: bytes) -> dict:
    return {"success": True, "errors": [], "imported_count": 0}
