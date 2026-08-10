# -*- coding: utf-8 -*-
"""
Bot direct DB & service integration layer.
Interacts directly with SQLAlchemy AsyncSession to eliminate port & localhost HTTP dependency.
"""
import logging
from typing import Optional, List, Dict, Any
from app.database import async_session_maker, engine
from app.services import employee_service, branch_service, topic_service, test_engine
from app.seeds.seed import seed_topics_and_questions

logger = logging.getLogger(__name__)


class BotAPIClient:
    async def register_employee(
        self, 
        telegram_user_id: int, 
        full_name: str, 
        branch_id: Optional[str] = None, 
        phone: str = "", 
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        async with async_session_maker() as db:
            emp, is_new = await employee_service.get_or_create_employee(db, telegram_user_id)
            resolved_bid = await branch_service.resolve_branch_id(db, branch_id=branch_id, branch_name=branch_name)
            emp = await employee_service.update_registration(
                db, telegram_user_id, full_name, resolved_bid, phone or ""
            )
            return {"employee_id": str(emp.id), "success": True}

    async def get_employee_status(self, telegram_user_id: int) -> Dict[str, Any]:
        async with async_session_maker() as db:
            emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
            if not emp:
                return {"registration_state": "NOT_REGISTERED"}
            
            topics_raw = await topic_service.get_all_topics_status_for_employee(db, str(emp.id))
            topics_list = []
            for top in topics_raw:
                t_obj = top.get("topic")
                if t_obj:
                    topics_list.append({
                        "id": str(t_obj.id),
                        "short_name": t_obj.short_name,
                        "full_name": t_obj.full_name,
                        "sequence_order": t_obj.sequence_order,
                        "status": top.get("status", "AVAILABLE")
                    })

            return {
                "employee": {
                    "id": str(emp.id),
                    "telegram_user_id": emp.telegram_user_id,
                    "full_name": emp.full_name,
                    "phone": emp.phone,
                    "branch_id": str(emp.branch_id) if emp.branch_id else None,
                    "registration_state": emp.registration_state
                },
                "registration_state": emp.registration_state,
                "topics": topics_list
            }

    async def get_branches(self) -> Dict[str, Any]:
        async with async_session_maker() as db:
            branches = await branch_service.get_all_branches(db, False)
            return {
                "branches": [
                    {"id": str(b.id), "name": b.name, "sort_order": b.sort_order}
                    for b in branches
                ]
            }

    async def get_topics(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        async with async_session_maker() as db:
            emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
            if not emp:
                return []
            
            topics_raw = await topic_service.get_all_topics_status_for_employee(db, str(emp.id))

            # Auto-seed if database is missing topics/questions
            if not topics_raw:
                await seed_topics_and_questions(engine, force=True)
                topics_raw = await topic_service.get_all_topics_status_for_employee(db, str(emp.id))

            result = []
            for item in topics_raw:
                t = item.get("topic")
                if t:
                    result.append({
                        "id": str(t.id),
                        "name": f"{t.short_name} — {t.full_name}",
                        "short_name": t.short_name,
                        "full_name": t.full_name,
                        "status": item.get("status", "available"),
                    })
            return result

    async def get_topic(self, topic_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            topic = await topic_service.get_topic_by_id(db, topic_id)
            if not topic:
                return {"id": topic_id, "name": "Mavzu"}
            return {
                "id": str(topic.id),
                "name": f"{topic.short_name} — {topic.full_name}",
                "short_name": topic.short_name,
                "full_name": topic.full_name,
            }

    async def start_attempt(self, telegram_user_id: int, topic_id: str, attempt_number: int, seminar_confirmed: bool = False) -> Dict[str, Any]:
        async with async_session_maker() as db:
            emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
            if not emp:
                return {"error": "Employee not found"}
            
            from app.redis_client import redis_client
            attempt = await test_engine.start_attempt(db, redis_client, str(emp.id), str(topic_id), attempt_number)
            first_q = await test_engine.get_current_question(db, str(attempt.id))
            return {"attempt_id": str(attempt.id), "first_question": first_q}

    async def get_current_question(self, attempt_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            q = await test_engine.get_current_question(db, attempt_id)
            return {"question": q}

    async def submit_answer(self, attempt_id: str, display_order: int, selected_answer_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            from app.redis_client import redis_client
            res = await test_engine.submit_answer(db, redis_client, attempt_id, display_order, selected_answer_id)
            return res

    async def get_attempt_results(self, attempt_id: str) -> Dict[str, Any]:
        async with async_session_maker() as db:
            res = await test_engine.get_attempt_results(db, attempt_id)
            return res

    async def confirm_seminar(self, attempt_id: str) -> Dict[str, Any]:
        return {"can_start_attempt2": True, "message": "Confirmed"}


bot_api = BotAPIClient()
