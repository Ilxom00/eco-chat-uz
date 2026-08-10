"""
Seed topics & questions into DB on startup.
Safe Upsert: Never deletes existing topics, user data, or questions.
"""
import uuid
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def seed_topics_and_questions(engine, force: bool = False):
    """Insert or update default 4 topics and 114 questions without deleting user topics or employee data."""
    try:
        from app.seeds.questions_seed_data import TOPICS_AND_QUESTIONS
    except Exception as e:
        logger.error("[SEED ERROR] Failed to import seed data: %s", e)
        return False

    try:
        async with engine.begin() as conn:
            # 1. Check if seed questions already exist
            q_count = (await conn.execute(text("SELECT COUNT(*) FROM questions"))).scalar() or 0
            if not force and q_count >= 100:
                logger.info("[SEED] Questions already present (%d found). Skipping.", q_count)
                return False

            logger.info("[SEED] Safe upserting default 4 topics and 114 questions (found %d existing)...", q_count)

            for topic_data in TOPICS_AND_QUESTIONS:
                # Find or create topic by sequence_order or short_name
                t_row = (await conn.execute(
                    text("SELECT id FROM topics WHERE sequence_order = :so OR short_name = :sn"),
                    {"so": topic_data["sequence_order"], "sn": topic_data["short_name"]}
                )).fetchone()

                if t_row:
                    topic_id = str(t_row[0])
                    await conn.execute(
                        text("UPDATE topics SET short_name = :sn, full_name = :fn, is_active = true WHERE id = :id"),
                        {"sn": topic_data["short_name"], "fn": topic_data["full_name"], "id": topic_id}
                    )
                else:
                    topic_id = str(uuid.uuid4())
                    await conn.execute(
                        text("INSERT INTO topics (id, short_name, full_name, sequence_order, is_active) "
                             "VALUES (:id, :sn, :fn, :so, true)"),
                        {
                            "id": topic_id,
                            "sn": topic_data["short_name"],
                            "fn": topic_data["full_name"],
                            "so": topic_data["sequence_order"],
                        }
                    )

                # Insert questions for this topic if not existing
                for q in topic_data["questions"]:
                    q_exists = (await conn.execute(
                        text("SELECT id FROM questions WHERE topic_id = :tid AND text = :txt"),
                        {"tid": topic_id, "txt": q["text"]}
                    )).scalar()

                    if not q_exists:
                        q_id = str(uuid.uuid4())
                        await conn.execute(
                            text("INSERT INTO questions (id, topic_id, text, status) "
                                 "VALUES (:id, :tid, :txt, 'ACTIVE')"),
                            {"id": q_id, "tid": topic_id, "txt": q["text"]}
                        )

                        for ans in q["answers"]:
                            a_id = str(uuid.uuid4())
                            await conn.execute(
                                text("INSERT INTO question_answers (id, question_id, text, is_correct, option_label, sort_order) "
                                     "VALUES (:id, :qid, :txt, :ic, :ol, :so)"),
                                {
                                    "id": a_id,
                                    "qid": q_id,
                                    "txt": ans["text"],
                                    "ic": bool(ans["is_correct"]),
                                    "ol": str(ans["label"]),
                                    "so": int(ans["sort_order"]),
                                }
                            )

        logger.info("[SEED] Safe upsert finished successfully!")
        return True

    except Exception as e:
        logger.error("[SEED ERROR] %s", e, exc_info=True)
        return False
