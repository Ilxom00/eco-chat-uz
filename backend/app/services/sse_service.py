import asyncio

class SSEBroadcaster:
    def __init__(self):
        self.subscribers: list[asyncio.Queue] = []
    
    async def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    async def unsubscribe(self, queue: asyncio.Queue):
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def broadcast(self, event_type: str, data: dict):
        for q in self.subscribers:
            await q.put({"event": event_type, "data": data})

    async def broadcast_employee_update(self, employee_id: str, update_data: dict):
        await self.broadcast("employee_update", {"employee_id": employee_id, **update_data})

    async def broadcast_stats_update(self, stats: dict):
        await self.broadcast("stats_update", stats)

broadcaster = SSEBroadcaster()
