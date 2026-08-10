from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import question_service

router = APIRouter(tags=["questions"], dependencies=[Depends(get_current_admin)])

@router.get("/topics/{topic_id}/questions")
async def list_questions(topic_id: str, page: int = 1, page_size: int = 10, include_archived: bool = False, db: AsyncSession = Depends(get_db)):
    items, total = await question_service.get_questions_for_topic_paginated(db, topic_id, page, page_size, include_archived)
    return {"items": items, "total": total}

@router.post("/topics/{topic_id}/questions")
async def create_question(topic_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    text = data.get("text")
    answers = data.get("answers")
    if not text or not answers:
        raise HTTPException(status_code=400, detail="Савол матни ва жавоблар зарур")
    try:
        q = await question_service.create_question_with_answers(db, topic_id, text=text, answers=answers)
        return {"message": "Success", "id": str(q.id)}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/questions/{id}")
async def delete_question(id: str, db: AsyncSession = Depends(get_db)):
    await question_service.delete_question_permanent(db, id)
    return {"message": "Question deleted permanently"}

@router.post("/topics/{topic_id}/questions/import")
async def import_questions(topic_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    res = await question_service.import_from_excel(db, topic_id, await file.read())
    return res

@router.patch("/questions/{id}/archive")
async def archive_question(id: str, db: AsyncSession = Depends(get_db)):
    q = await question_service.archive_question(db, id)
    return {"message": "Archived", "id": str(q.id)}
