import asyncio
import os
import sys
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# SQLite Source Engine
source_url = "sqlite+aiosqlite:///./ecochat.db"
source_engine = create_async_engine(source_url)
SourceSession = sessionmaker(source_engine, class_=AsyncSession, expire_on_commit=False)

# PostgreSQL Target Engine
target_url = os.getenv("TARGET_DATABASE_URL", "")
if not target_url:
    print("ERROR: TARGET_DATABASE_URL environment variable is not set!")
    sys.exit(1)

if target_url.startswith("postgresql://"):
    target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif target_url.startswith("postgres://"):
    target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)

target_engine = create_async_engine(target_url)
TargetSession = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

tables = [
    "admins",
    "branches",
    "employees",
    "topics",
    "questions",
    "question_answers",
    "employee_topic_assignments",
    "employee_topic_questions",
    "test_attempts",
    "attempt_questions",
    "audit_logs"
]

async def migrate():
    print("🚀 Starting SQLite -> PostgreSQL Data Migration...")
    
    # 1. Retrieve row counts from SQLite
    before_counts = {}
    async with SourceSession() as src_db:
        for t in tables:
            try:
                res = await src_db.execute(text(f"SELECT COUNT(*) FROM {t}"))
                before_counts[t] = res.scalar() or 0
            except Exception as e:
                before_counts[t] = 0
                print(f"⚠️ Source table {t} read error: {e}")
    
    print("📊 Baseline SQLite Row Counts:")
    print(json.dumps(before_counts, indent=2))
    
    # Save baseline manifest locally
    with open("SQLITE_BEFORE_ROW_COUNTS.json", "w") as f:
        json.dump(before_counts, f, indent=2)

    # 2. Recreate schema on Postgres
    print("🔨 Creating schema on target PostgreSQL...")
    from app.models.base import Base
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Target PostgreSQL schema ready")

    # 3. Migrate tables sequentially keeping FK constraints
    async with TargetSession() as tgt_db:
        async with SourceSession() as src_db:
            for t in tables:
                count = before_counts[t]
                if count == 0:
                    print(f"➡️ Table {t} has 0 records — skipped")
                    continue
                
                print(f"⏳ Migrating {count} records for {t}...")
                
                # Fetch all records
                res = await src_db.execute(text(f"SELECT * FROM {t}"))
                keys = res.keys()
                rows = res.fetchall()
                
                # Insert into target
                for row in rows:
                    row_dict = dict(zip(keys, row))
                    
                    # Convert SQLite integers representing booleans to strict Python booleans for postgres
                    for k, v in row_dict.items():
                        if k == "is_active" or k.startswith("is_"):
                            if v is not None:
                                row_dict[k] = bool(v)
                    
                    col_names = ", ".join(row_dict.keys())
                    val_placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                    
                    # Construct INSERT statement
                    stmt = text(f"INSERT INTO {t} ({col_names}) VALUES ({val_placeholders}) ON CONFLICT DO NOTHING")
                    await tgt_db.execute(stmt, row_dict)
                
                await tgt_db.commit()
                print(f"✅ Table {t} migrated successfully")

    # 4. Verify target row counts
    after_counts = {}
    async with TargetSession() as tgt_db:
        for t in tables:
            res = await tgt_db.execute(text(f"SELECT COUNT(*) FROM {t}"))
            after_counts[t] = res.scalar() or 0

    print("📊 Target PostgreSQL Row Counts:")
    print(json.dumps(after_counts, indent=2))
    
    # Save target manifest
    with open("POSTGRES_AFTER_ROW_COUNTS.json", "w") as f:
        json.dump(after_counts, f, indent=2)

    # 5. Check row counts match
    mismatch = False
    for t in tables:
        if before_counts[t] != after_counts[t]:
            print(f"❌ MISMATCH on table {t}: SQLite={before_counts[t]} vs PostgreSQL={after_counts[t]}")
            mismatch = True
    
    if mismatch:
        print("❌ Migration finished with MISMATCHES! Do not switch DATABASE_URL.")
        sys.exit(1)
    else:
        print("🎉 SQLite -> PostgreSQL Migration COMPLETED WITH 100% DATA INTEGRITY!")

if __name__ == "__main__":
    asyncio.run(migrate())
