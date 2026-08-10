"""
Seed topics & questions into DB on startup.
Checks topics table (not questions) to handle partial seed situations.
"""
import uuid
from sqlalchemy import text


async def seed_topics_and_questions(engine):
    """Insert 4 topics and 114+ questions if DB has fewer than 4 topics."""
    try:
        from app.seeds.questions_seed_data import TOPICS_AND_QUESTIONS
    except SyntaxError as e:
        print(f"[SEED ERROR] questions_seed_data.py syntax error: {e}")
        return False
    except Exception as e:
        print(f"[SEED ERROR] Failed to import seed data: {e}")
        return False

    try:
        async with engine.begin() as conn:
            # Check if topics already seeded
            t_count = (await conn.execute(text("SELECT COUNT(*) FROM topics"))).scalar() or 0
            if t_count >= len(TOPICS_AND_QUESTIONS):
                print(f"[SEED] Topics already seeded ({t_count} topics found). Skipping.")
                return False  # Already seeded

            # If partial seed, clean up orphaned data
            if t_count > 0:
                print(f"[SEED] Partial seed detected ({t_count} topics). Cleaning up...")
                await conn.execute(text("""
                    DELETE FROM question_answers
                    WHERE question_id IN (
                        SELECT id FROM questions WHERE topic_id IN (SELECT id FROM topics)
                    )
                """))
                await conn.execute(text("DELETE FROM questions WHERE topic_id IN (SELECT id FROM topics)"))
                await conn.execute(text("DELETE FROM topics"))

            print(f"[SEED] Inserting {len(TOPICS_AND_QUESTIONS)} topics...")
            for topic_data in TOPICS_AND_QUESTIONS:
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

                q_count_t = 0
                for q in topic_data["questions"]:
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
                                "ic": ans["is_correct"],
                                "ol": ans["label"],
                                "so": ans["sort_order"],
                            }
                        )
                    q_count_t += 1

                print(f"[SEED] {topic_data['short_name']}: {q_count_t} savollar inserted.")

        total_q = sum(len(t["questions"]) for t in TOPICS_AND_QUESTIONS)
        print(f"[SEED] ✅ Done! {len(TOPICS_AND_QUESTIONS)} topics, {total_q} questions seeded.")
        return True

    except Exception as e:
        import traceback
        print(f"[SEED ERROR] {e}")
        traceback.print_exc()
        return False
