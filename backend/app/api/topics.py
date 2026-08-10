from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import topic_service

router = APIRouter(tags=["topics"], dependencies=[Depends(get_current_admin)])

@router.get("/")
async def list_topics(db: AsyncSession = Depends(get_db)):
    topics = await topic_service.get_active_topics_ordered(db)
    return topics

@router.post("/")
async def create_topic(data: dict, db: AsyncSession = Depends(get_db)):
    topic = await topic_service.create_topic(db, short_name=data.get("short_name"), full_name=data.get("full_name"))
    return topic

@router.patch("/{id}")
async def update_topic(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    return {"message": "Updated"}

@router.patch("/{id}/archive")
async def archive_topic(id: str, db: AsyncSession = Depends(get_db)):
    return {"message": "Archived"}

@router.patch("/{id}/reorder")
async def reorder_topic(id: str, data: dict, db: AsyncSession = Depends(get_db)):
    return {"message": "Reordered"}
