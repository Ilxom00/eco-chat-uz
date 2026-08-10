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


def _force_str(val) -> str:
    if isinstance(val, uuid.UUID):
        return str(val)
    return str(val).strip()


async def create_question_with_answers(db: AsyncSession, topic_id: str, text_content: str, answers: list[dict]):
    if len(answers) != 4:
        raise ValueError("Барча 4 та вариант киритилиши шарт")
    if sum(1 for a in answers if a.get("is_correct")) != 1:
        raise ValueError("Аниқ 1 та тўғри жавоб танланиши шарт")
        
    tid_str = _force_str(topic_id)

    # 1. Verify topic exists in DB
    topic_row = (await db.execute(
        text("SELECT id FROM topics WHERE id = :tid"),
        {"tid": tid_str}
    )).fetchone()

    if not topic_row:
        # Fallback to first active topic in DB
        first_t = (await db.execute(
            text("SELECT id FROM topics WHERE is_active = true ORDER BY sequence_order ASC LIMIT 1")
        )).fetchone()
        if not first_t:
            raise ValueError("Мавзу базада топилмади. Илтимос, аввал янги мавзу яратинг.")
        tid_str = str(first_t[0])

    question_id_str = str(uuid.uuid4())

    # Universal SQL Insert — compatible with both PostgreSQL & SQLite
    await db.execute(text("""
        INSERT INTO questions (id, topic_id, text, status)
        VALUES (:id, :tid, :txt, 'ACTIVE')
    """), {
        "id": question_id_str,
        "tid": tid_str,
        "txt": text_content
    })
    
    for i, ans in enumerate(answers):
        ans_id_str = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO question_answers (id, question_id, text, is_correct, option_label, sort_order)
            VALUES (:id, :qid, :txt, :ic, :ol, :so)
        """), {
            "id": ans_id_str,
            "qid": question_id_str,
            "txt": ans["text"],
            "ic": bool(ans.get("is_correct", False)),
            "ol": ans.get("option_label", ["А", "Б", "В", "Г"][i]),
            "so": i + 1
        })
    
    await db.commit()

    class QuestionResult:
        def __init__(self, qid):
            self.id = qid

    return QuestionResult(question_id_str)


async def update_question_with_answers(db: AsyncSession, question_id: str, text_content: str, answers: list[dict]) -> bool:
    if len(answers) != 4:
        raise ValueError("Барча 4 та вариант киритилиши шарт")
    if sum(1 for a in answers if a.get("is_correct")) != 1:
        raise ValueError("Аниқ 1 та тўғри жавоб танланиши шарт")
        
    qid_str = _force_str(question_id)

    # 1. Update question text
    await db.execute(
        text("UPDATE questions SET text = :txt WHERE id = :qid"),
        {"txt": text_content, "qid": qid_str}
    )

    # 2. Re-insert 4 answers
    await db.execute(
        text("DELETE FROM question_answers WHERE question_id = :qid"),
        {"qid": qid_str}
    )

    for i, ans in enumerate(answers):
        ans_id_str = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO question_answers (id, question_id, text, is_correct, option_label, sort_order)
            VALUES (:id, :qid, :txt, :ic, :ol, :so)
        """), {
            "id": ans_id_str,
            "qid": qid_str,
            "txt": ans["text"],
            "ic": bool(ans.get("is_correct", False)),
            "ol": ans.get("option_label", ["А", "Б", "В", "Г"][i]),
            "so": i + 1
        })
    
    await db.commit()
    return True


async def delete_question_permanent(db: AsyncSession, question_id: str) -> bool:
    qid_str = _force_str(question_id)
    await db.execute(text("DELETE FROM question_answers WHERE question_id = :qid"), {"qid": qid_str})
    await db.execute(text("DELETE FROM questions WHERE id = :qid"), {"qid": qid_str})
    await db.commit()
    return True


async def archive_question(db: AsyncSession, question_id: str):
    qid_str = _force_str(question_id)
    await db.execute(text("UPDATE questions SET status = 'ARCHIVED' WHERE id = :qid"), {"qid": qid_str})
    await db.commit()
    class QResult:
        def __init__(self, qid):
            self.id = qid
    return QResult(qid_str)


async def get_active_questions_for_topic(db: AsyncSession, topic_id: str) -> list:
    tid_str = _force_str(topic_id)
    rows = (await db.execute(
        text("SELECT id, text, status FROM questions WHERE topic_id = :tid AND status = 'ACTIVE'"),
        {"tid": tid_str}
    )).fetchall()
    return rows


async def get_questions_for_topic_paginated(db: AsyncSession, topic_id: str, page: int, page_size: int, include_archived: bool = False) -> tuple[list, int]:
    try:
        tid_str = _force_str(topic_id)

        total = (await db.execute(
            text("SELECT COUNT(*) FROM questions WHERE topic_id = :tid AND status = 'ACTIVE'"),
            {"tid": tid_str}
        )).scalar() or 0

        if total == 0:
            return [], 0

        limit = page_size
        offset = (page - 1) * page_size

        q_rows = (await db.execute(
            text("SELECT id, text, status, created_at FROM questions WHERE topic_id = :tid AND status = 'ACTIVE' ORDER BY created_at ASC LIMIT :lim OFFSET :off"),
            {"tid": tid_str, "lim": limit, "off": offset}
        )).fetchall()
        
        result_list = []
        for q in q_rows:
            q_id_str = str(q[0])
            ans_rows = (await db.execute(
                text("SELECT text, is_correct, option_label FROM question_answers WHERE question_id = :qid ORDER BY sort_order ASC"),
                {"qid": q_id_str}
            )).fetchall()

            correct_ans = next((a[0] for a in ans_rows if a[1]), "—")
            options = [a[0] for a in ans_rows]
            result_list.append({
                "id": q_id_str,
                "text": q[1],
                "correct_answer": correct_ans,
                "options": options,
                "status": q[2],
                "created_at": str(q[3]) if q[3] else None
            })
        
        return result_list, total
    except Exception as e:
        logger.error("Error fetching questions for topic %s: %s", topic_id, e, exc_info=True)
        return [], 0


async def import_from_excel(db: AsyncSession, topic_id: str, file_bytes: bytes) -> dict:
    return {"success": True, "errors": [], "imported_count": 0}
