from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
import asyncio
from app.api.deps import get_current_admin
from app.services.sse_service import broadcaster

router = APIRouter(tags=["sse"])

@router.get("/dashboard")
async def sse_dashboard(request: Request, admin=Depends(get_current_admin)):
    async def event_generator():
        queue = await broadcaster.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield data
        finally:
            await broadcaster.unsubscribe(queue)

    return EventSourceResponse(event_generator())
