import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import AsyncSessionLocal, engine
from app.services import employee_service, topic_service, test_engine
from app.seeds.seed import seed_topics_and_questions

logger = logging.getLogger(__name__)


class BotAPIClient:

    async def get_branches(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(text("SELECT id, name FROM branches WHERE is_active = true ORDER BY sort_order, name"))).fetchall()
            return [{"id": str(r[0]), "name": r[1]} for r in rows]

    async def register_employee(self, telegram_user_id: int, full_name: str, branch_name_or_id: str, phone: Optional[str] = None) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            emp = await employee_service.register_employee(
                db=db,
                telegram_user_id=telegram_user_id,
                full_name=full_name,
                branch_name_or_id=branch_name_or_id,
                phone=phone
            )
            # Get branch name from DB
            branch_name = "—"
            if emp.branch_id:
                try:
                    row = (await db.execute(
                        text("SELECT name FROM branches WHERE id = :bid"),
                        {"bid": str(emp.branch_id)}
                    )).fetchone()
                    if row:
                        branch_name = row[0]
                except Exception:
                    pass
            return {
                "id": str(emp.id),
                "full_name": emp.full_name,
                "branch_name": branch_name
            }

    async def get_employee_by_telegram_id(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
            if not emp:
                return None
            branch_name = "—"
            if emp.branch_id:
                try:
                    row = (await db.execute(
                        text("SELECT name FROM branches WHERE id = :bid"),
                        {"bid": str(emp.branch_id)}
                    )).fetchone()
                    if row:
                        branch_name = row[0]
                except Exception:
                    pass
            return {
                "id": str(emp.id),
                "full_name": emp.full_name,
                "branch_name": branch_name,
                "phone": emp.phone,
            }

    async def get_topics(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        """Always return active topics with clickable buttons for Telegram bot."""
        async with AsyncSessionLocal() as db:
            topics = await topic_service.get_active_topics_ordered(db)
            if not topics:
                await seed_topics_and_questions(engine, force=True)
                topics = await topic_service.get_active_topics_ordered(db)

            result = []
            for t in topics:
                result.append({
                    "id": str(t.id),
                    "name": f"{t.short_name} — {t.full_name}",
                    "short_name": t.short_name,
                    "full_name": t.full_name,
                    "status": "available",
                })
            return result

    async def get_topic(self, topic_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            topic = await topic_service.get_topic_by_id(db, topic_id)
            if not topic:
                return {"id": topic_id, "name": "Мавзу"}
            return {
                "id": str(topic.id),
                "name": f"{topic.short_name} — {topic.full_name}",
                "short_name": topic.short_name,
                "full_name": topic.full_name,
            }

    async def start_attempt(self, telegram_user_id: int, topic_id: str, attempt_number: int = 1) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
            if not emp:
                # Auto-register if missing
                emp = await employee_service.register_employee(
                    db=db,
                    telegram_user_id=telegram_user_id,
                    full_name=f"Ходим #{telegram_user_id}",
                    branch_name_or_id=None
                )
            
            try:
                redis_client = None
                try:
                    from app.redis_client import redis_client as _rc
                    redis_client = _rc
                except Exception:
                    pass
                
                attempt = await test_engine.start_attempt(db, redis_client, str(emp.id), str(topic_id), attempt_number)
                first_q = await test_engine.get_current_question_full(db, str(attempt.id))
                return {"attempt_id": str(attempt.id), "first_question": first_q}
            except Exception as e:
                logger.error("Error in start_attempt API: %s", e, exc_info=True)
                return {"error": str(e)}

    async def get_current_question(self, attempt_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            q = await test_engine.get_current_question_full(db, attempt_id)
            return {"question": q}

    async def submit_answer(self, attempt_id: str, display_order: int, selected_answer_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            redis_client = None
            try:
                from app.redis_client import redis_client as _rc
                redis_client = _rc
            except Exception:
                pass
            res = await test_engine.submit_answer(db, redis_client, attempt_id, display_order, selected_answer_id)
            return res

    async def get_attempt_results(self, attempt_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            res = await test_engine.get_attempt_results(db, attempt_id)
            return res


bot_api = BotAPIClient()
