import uuid
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, engine
from app.services import employee_service, topic_service, test_engine
from app.seeds.seed import seed_topics_and_questions
from app.models.branch import Branch

logger = logging.getLogger(__name__)


async def _get_branch_name(db: AsyncSession, branch_id) -> str:
    """Safely get branch name by UUID using ORM."""
    if not branch_id:
        return "—"
    try:
        bid = branch_id if isinstance(branch_id, uuid.UUID) else uuid.UUID(str(branch_id))
        result = await db.execute(select(Branch).filter(Branch.id == bid))
        branch = result.scalar_one_or_none()
        return branch.name if branch else "—"
    except (ValueError, TypeError):
        return "—"


class BotAPIClient:

    async def get_branches(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Branch).filter(Branch.is_active == True).order_by(Branch.sort_order, Branch.name)
            )
            branches = result.scalars().all()
            return [{"id": str(b.id), "name": b.name} for b in branches]

    async def register_employee(self, telegram_user_id: int, full_name: str, branch_name_or_id: str, phone: Optional[str] = None) -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            emp = await employee_service.register_employee(
                db=db,
                telegram_user_id=telegram_user_id,
                full_name=full_name,
                branch_name_or_id=branch_name_or_id,
                phone=phone
            )
            branch_name = await _get_branch_name(db, emp.branch_id)
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
            branch_name = await _get_branch_name(db, emp.branch_id)
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
