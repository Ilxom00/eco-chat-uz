"""
Seed questions into the database on startup.
Only runs if there are no questions in the DB.
"""
import uuid
from sqlalchemy import text


async def seed_topics_and_questions(engine):
    """Insert 4 topics and 115 questions if DB is empty."""
    try:
        from app.seeds.questions_seed_data import TOPICS_AND_QUESTIONS

        async with engine.begin() as conn:
            q_count = (await conn.execute(text("SELECT COUNT(*) FROM questions"))).scalar()
            if q_count and q_count > 0:
                return  # Already seeded

            for topic_data in TOPICS_AND_QUESTIONS:
                topic_id = str(uuid.uuid4())
                await conn.execute(
                    text("INSERT INTO topics (id, short_name, full_name, sequence_order, is_active) VALUES (:id, :sn, :fn, :so, 1)"),
                    {
                        "id": topic_id,
                        "sn": topic_data["short_name"],
                        "fn": topic_data["full_name"],
                        "so": topic_data["sequence_order"],
                    }
                )

                for q in topic_data["questions"]:
                    q_id = str(uuid.uuid4())
                    await conn.execute(
                        text("INSERT INTO questions (id, topic_id, text, status) VALUES (:id, :tid, :txt, 'ACTIVE')"),
                        {"id": q_id, "tid": topic_id, "txt": q["text"]}
                    )

                    for ans in q["answers"]:
                        a_id = str(uuid.uuid4())
                        await conn.execute(
                            text("INSERT INTO question_answers (id, question_id, text, is_correct, option_label, sort_order) VALUES (:id, :qid, :txt, :ic, :ol, :so)"),
                            {
                                "id": a_id,
                                "qid": q_id,
                                "txt": ans["text"],
                                "ic": 1 if ans["is_correct"] else 0,
                                "ol": ans["label"],
                                "so": ans["sort_order"],
                            }
                        )

        return True
    except Exception as e:
        import traceback
        print(f"[SEED ERROR] {e}")
        traceback.print_exc()
        return False
