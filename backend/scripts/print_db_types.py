import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'topics'"))
        for r in res.fetchall():
            print(f"Col: {r[0]} | Type: {r[1]}")

        print("\n--- ATTEMPTS ---")
        res = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'test_attempts'"))
        for r in res.fetchall():
            print(f"Col: {r[0]} | Type: {r[1]}")

if __name__ == "__main__":
    asyncio.run(main())
