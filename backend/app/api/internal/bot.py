from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.api.deps import get_internal_token
from app.services import employee_service, branch_service, topic_service, test_engine

router = APIRouter(prefix="/bot", tags=["internal"], dependencies=[Depends(get_internal_token)])

@router.post("/register")
async def register(data: dict, db: AsyncSession = Depends(get_db)):
    emp, is_new = await employee_service.get_or_create_employee(db, data.get("telegram_user_id"))
    emp = await employee_service.update_registration(db, data.get("telegram_user_id"), data.get("full_name"), data.get("branch_id"), data.get("phone"))
    return {"employee_id": emp.id, "success": True}

@router.get("/employee/{telegram_user_id}/status")
async def get_status(telegram_user_id: int, db: AsyncSession = Depends(get_db)):
    emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
    if not emp:
        return {"registration_state": "NOT_REGISTERED"}
    topics = await topic_service.get_all_topics_status_for_employee(db, str(emp.id))
    return {"employee": emp, "registration_state": emp.registration_state, "topics": topics}

@router.post("/attempt/start")
async def start_attempt(data: dict, db: AsyncSession = Depends(get_db)):
    emp = await employee_service.get_employee_by_telegram_id(db, data.get("telegram_user_id"))
    can_start, reason = await test_engine.can_start_attempt(db, str(emp.id), data.get("topic_id"), data.get("attempt_number"))
    if not can_start:
        raise HTTPException(status_code=400, detail=reason)
    redis = get_redis()
    attempt = await test_engine.start_attempt(db, redis, str(emp.id), data.get("topic_id"), data.get("attempt_number"))
    first_q = await test_engine.get_current_question(db, str(attempt.id))
    return {"attempt_id": attempt.id, "first_question": first_q}

@router.get("/attempt/{attempt_id}/current-question")
async def get_current_question(attempt_id: str, db: AsyncSession = Depends(get_db)):
    q = await test_engine.get_current_question(db, attempt_id)
    return {"question": q}

@router.post("/attempt/{attempt_id}/answer")
async def answer_question(attempt_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    redis = get_redis()
    res = await test_engine.submit_answer(db, redis, attempt_id, data.get("display_order"), data.get("selected_answer_id"))
    return res

@router.get("/attempt/{attempt_id}/results")
async def get_results(attempt_id: str, db: AsyncSession = Depends(get_db)):
    res = await test_engine.get_attempt_results(db, attempt_id)
    return res

@router.post("/attempt/{attempt_id}/confirm-seminar")
async def confirm_seminar(attempt_id: str, db: AsyncSession = Depends(get_db)):
    # Simple mock for this
    return {"can_start_attempt2": True, "message": "Confirmed"}

@router.get("/branches")
async def get_branches(db: AsyncSession = Depends(get_db)):
    branches = await branch_service.get_all_branches(db, False)
    return {"branches": branches}
