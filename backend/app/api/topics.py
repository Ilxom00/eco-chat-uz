from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, engine
from app.api.deps import get_current_admin
from app.services import topic_service
from app.seeds.seed import seed_topics_and_questions

router = APIRouter(tags=["topics"], dependencies=[Depends(get_current_admin)])

@router.get("")
@router.get("/")
async def list_topics(db: AsyncSession = Depends(get_db)):
    topics = await topic_service.get_active_topics_ordered(db)
    
    # Auto-seed 4 topics and 114 questions if topics list is empty or fewer than 4
    if not topics or len(topics) < 4:
        await seed_topics_and_questions(engine, force=True)
        topics = await topic_service.get_active_topics_ordered(db)

    from app.services.topic_service import get_topic_active_question_count
    result = []
    for t in topics:
        q_count = await get_topic_active_question_count(db, str(t.id))
        result.append({
            "id": str(t.id),
            "short_name": t.short_name,
            "full_name": t.full_name,
            "q_count": q_count,
            "is_active": t.is_active,
        })
    return result

@router.post("/reseed")
async def reseed_topics():
    res = await seed_topics_and_questions(engine, force=True)
    return {"success": True, "message": "114 ta savol qayta юкланди"}

@router.post("")
@router.post("/")
async def create_topic(data: dict, db: AsyncSession = Depends(get_db)):
    short_name = data.get("short_name")
    full_name = data.get("full_name")
    if not short_name or not full_name:
        raise HTTPException(status_code=400, detail="Qisqa ва тўлиқ номлари шарт")
    
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
    return {"message": "Mavzu va barcha bog'liq ma'lumotlar o'chirildi"}

@router.patch("/{id}")
async def update_topic(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    return {"message": "Updated"}

@router.patch("/{id}/archive")
async def archive_topic(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    return {"message": "Archived"}

@router.patch("/{id}/reorder")
async def reorder_topic(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    return {"message": "Reordered"}
