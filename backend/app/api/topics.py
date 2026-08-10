import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, engine
from app.services import topic_service
from app.seeds.seed import seed_topics_and_questions

logger = logging.getLogger(__name__)

router = APIRouter(tags=["topics"])

@router.get("")
@router.get("/")
async def list_topics(db: AsyncSession = Depends(get_db)):
    try:
        topics = await topic_service.get_active_topics_ordered(db)
        
        # Auto-seed 4 topics and 114 questions if topics list is empty or fewer than 4
        if not topics or len(topics) < 4:
            await seed_topics_and_questions(engine, force=True)
            topics = await topic_service.get_active_topics_ordered(db)

        result = []
        for t in topics:
            q_count = await topic_service.get_topic_active_question_count(db, str(t.id))
            result.append({
                "id": str(t.id),
                "short_name": t.short_name,
                "full_name": t.full_name,
                "q_count": q_count,
                "is_active": t.is_active,
            })
        return result
    except Exception as e:
        logger.error("Error listing topics: %s", e, exc_info=True)
        # Attempt auto-seed and retry once
        try:
            await seed_topics_and_questions(engine, force=True)
            topics = await topic_service.get_active_topics_ordered(db)
            result = []
            for t in topics:
                q_count = await topic_service.get_topic_active_question_count(db, str(t.id))
                result.append({
                    "id": str(t.id),
                    "short_name": t.short_name,
                    "full_name": t.full_name,
                    "q_count": q_count,
                    "is_active": t.is_active,
                })
            return result
        except Exception:
            return []

@router.post("/reseed")
async def reseed_topics():
    res = await seed_topics_and_questions(engine, force=True)
    return {"success": True, "message": "114 та савол қайта юкланди"}

@router.post("")
@router.post("/")
async def create_topic(data: dict, db: AsyncSession = Depends(get_db)):
    short_name = data.get("short_name")
    full_name = data.get("full_name")
    if not short_name or not full_name:
        raise HTTPException(status_code=400, detail="Қисқа ва тўлиқ номлари шарт")
    
    topic = await topic_service.create_topic(db, short_name=short_name, full_name=full_name)
    return {
        "id": str(topic.id),
        "short_name": topic.short_name,
        "full_name": topic.full_name,
        "q_count": 0,
        "is_active": topic.is_active
    }

@router.delete("/{id}")
async def delete_topic(id: str, db: AsyncSession = Depends(get_db)):
    await topic_service.delete_topic_cascade(db, id)
    return {"message": "Мавзу ва барча боғлиқ маълумотлар ўчирилди"}
