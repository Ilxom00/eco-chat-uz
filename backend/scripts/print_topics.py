import asyncio
from app.database import AsyncSessionLocal
from app.models.topic import Topic
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Topic))
        for t in res.scalars().all():
            print(f"ID: {t.id} SHORT: {t.short_name} FULL: {t.full_name}")

if __name__ == "__main__":
    asyncio.run(main())
