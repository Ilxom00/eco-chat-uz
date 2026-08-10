from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from app.models.question import Question, QuestionAnswer
from datetime import datetime
import pytz

async def create_question_with_answers(db: AsyncSession, topic_id: str, text: str, answers: list[dict]) -> Question:
    if len(answers) != 4:
        raise ValueError("Exactly 4 answers required")
    if sum(1 for a in answers if a.get("is_correct")) != 1:
        raise ValueError("Exactly 1 correct answer required")
        
    question = Question(topic_id=topic_id, text=text, status='ACTIVE')
    db.add(question)
    await db.flush()
    
    for i, ans in enumerate(answers):
        q_ans = QuestionAnswer(
            question_id=question.id,
            text=ans["text"],
            is_correct=ans.get("is_correct", False),
            option_label=ans.get("option_label", ["A", "B", "C", "D"][i]),
            sort_order=i+1
        )
        db.add(q_ans)
    
    await db.commit()
    await db.refresh(question)
    return question

async def delete_question_permanent(db: AsyncSession, question_id: str) -> bool:
    await db.execute(text("DELETE FROM question_answers WHERE question_id = :qid"), {"qid": question_id})
    await db.execute(text("DELETE FROM questions WHERE id = :qid"), {"qid": question_id})
    await db.commit()
    return True

async def archive_question(db: AsyncSession, question_id: str) -> Question:
    result = await db.execute(select(Question).filter(Question.id == question_id))
    question = result.scalar_one_or_none()
    if question:
        question.status = 'ARCHIVED'
        question.archived_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        await db.commit()
        await db.refresh(question)
    return question

async def get_active_questions_for_topic(db: AsyncSession, topic_id: str) -> list[Question]:
    result = await db.execute(select(Question).filter(Question.topic_id == topic_id, Question.status == 'ACTIVE'))
    return result.scalars().all()

async def get_questions_for_topic_paginated(db: AsyncSession, topic_id: str, page: int, page_size: int, include_archived: bool) -> tuple[list, int]:
    query = select(Question).filter(Question.topic_id == topic_id)
    if not include_archived:
        query = query.filter(Question.status == 'ACTIVE')
        
    total_query = select(func.count()).select_from(Question).filter(Question.topic_id == topic_id)
    if not include_archived:
        total_query = total_query.filter(Question.status == 'ACTIVE')
        
    total = (await db.execute(total_query)).scalar() or 0
    query = query.order_by(Question.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    questions_raw = (await db.execute(query)).scalars().all()
    
    result_list = []
    for q in questions_raw:
        ans_rows = (await db.execute(select(QuestionAnswer).filter(QuestionAnswer.question_id == q.id).order_by(QuestionAnswer.sort_order))).scalars().all()
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

async def import_from_excel(db: AsyncSession, topic_id: str, file_bytes: bytes) -> dict:
    return {"success": True, "errors": [], "imported_count": 0}
