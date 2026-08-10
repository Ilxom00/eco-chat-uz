from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_admin
from app.services import result_service

router = APIRouter(tags=["dashboard"], dependencies=[Depends(get_current_admin)])

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await result_service.get_dashboard_stats(db)

@router.get("/employees")
async def get_dashboard_employees(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db)):
    items, total = await result_service.get_dashboard_employee_table(db, {}, page, page_size)
    return {"items": items, "total": total}

@router.get("/employees/{id}/detail")
async def get_dashboard_employee_detail(id: str, db: AsyncSession = Depends(get_db)):
    return await result_service.get_employee_detail_for_report(db, id)

@router.get("/attempts/{attempt_id}/detail")
async def get_dashboard_attempt_detail(
    attempt_id: str, 
    emp_id: str = None, 
    topic_id: str = None, 
    attempt_num: int = 1, 
    db: AsyncSession = Depends(get_db)
):
    return await result_service.get_attempt_detail_for_dashboard(
        db, attempt_id, emp_id=emp_id, topic_id=topic_id, attempt_num=attempt_num
    )


@router.api_route("/system-update", methods=["GET", "POST"])
async def trigger_system_update():
    import subprocess
    try:
        res = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True, timeout=20)
        return {"success": True, "output": res.stdout, "error": res.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


