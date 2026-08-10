from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import result_service, excel_service

router = APIRouter(tags=["reports"], dependencies=[Depends(get_current_admin)])

@router.get("/general-stats")
async def general_stats(db: AsyncSession = Depends(get_db)):
    data = await result_service.get_general_stats_for_report(db, {})
    return Response(content=await excel_service.generate_general_stats_excel(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@router.get("/by-topic/{topic_id}")
async def topic_stats(topic_id: str, db: AsyncSession = Depends(get_db)):
    data = await result_service.get_topic_stats_for_report(db, topic_id, {})
    return Response(content=await excel_service.generate_topic_stats_excel("Topic", data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@router.get("/by-employee/{employee_id}")
async def employee_stats(employee_id: str, db: AsyncSession = Depends(get_db)):
    data = await result_service.get_employee_detail_for_report(db, employee_id)
    return Response(content=await excel_service.generate_employee_detail_excel(data), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
