# -*- coding: utf-8 -*-
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.api.deps import get_internal_token
from app.services import employee_service, branch_service, topic_service, test_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bot", tags=["internal"], dependencies=[Depends(get_internal_token)])

@router.post("/register")
async def register(data: dict, db: AsyncSession = Depends(get_db)):
    try:
        emp, is_new = await employee_service.get_or_create_employee(db, data.get("telegram_user_id"))
        
        raw_bid = data.get("branch_id")
        raw_bname = data.get("branch_name")
        resolved_bid = await branch_service.resolve_branch_id(db, branch_id=raw_bid, branch_name=raw_bname)

        emp = await employee_service.update_registration(
            db, 
            data.get("telegram_user_id"), 
            data.get("full_name"), 
            resolved_bid, 
            data.get("phone")
        )
        return {"employee_id": str(emp.id), "success": True}
    except Exception as e:
        logger.error("Error registering employee: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee/{telegram_user_id}/status")
async def get_status(telegram_user_id: int, db: AsyncSession = Depends(get_db)):
    emp = await employee_service.get_employee_by_telegram_id(db, telegram_user_id)
    if not emp:
        return {"registration_state": "NOT_REGISTERED"}
    
    emp_dict = {
        "id": str(emp.id),
        "telegram_user_id": emp.telegram_user_id,
        "full_name": emp.full_name,
        "phone": emp.phone,
        "branch_id": str(emp.branch_id) if emp.branch_id else None,
        "registration_state": emp.registration_state
    }
    
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
        "employee": emp_dict,
        "registration_state": emp.registration_state,
        "topics": topics_list
    }

@router.post("/attempt/start")
async def start_attempt(data: dict, db: AsyncSession = Depends(get_db)):
    emp = await employee_service.get_employee_by_telegram_id(db, data.get("telegram_user_id"))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    can_start, reason = await test_engine.can_start_attempt(db, str(emp.id), data.get("topic_id"), data.get("attempt_number"))
    if not can_start:
        raise HTTPException(status_code=400, detail=reason)
    redis = get_redis()
    attempt = await test_engine.start_attempt(db, redis, str(emp.id), data.get("topic_id"), data.get("attempt_number"))
    first_q = await test_engine.get_current_question(db, str(attempt.id))
    return {"attempt_id": str(attempt.id), "first_question": first_q}

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
    return {"can_start_attempt2": True, "message": "Confirmed"}

@router.get("/branches")
async def get_branches(db: AsyncSession = Depends(get_db)):
    branches = await branch_service.get_all_branches(db, False)
    return {
        "branches": [
            {"id": str(b.id), "name": b.name, "sort_order": b.sort_order}
            for b in branches
        ]
    }
