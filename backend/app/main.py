"""
eco-chat.uz — FastAPI Application Entry Point
Includes: API routes, Telegram bot startup, static files, health check
Full Server Redeploy & Rebuild Triggered: 2026-08-11
"""
from contextlib import asynccontextmanager
import datetime

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from loguru import logger
import sys
import os

from app.config import settings
from app.database import engine, Base

# в”Ђв”Ђ Logging setup в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
logger.remove()
# Windows console UTF-8 uchun
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    level=settings.log_level,
)


# в”Ђв”Ђ Lifespan в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, connect services, start bot. Shutdown: cleanup."""
    logger.info("🌿 eco-chat.uz starting up...")

    # Create all DB tables (idempotent)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error("❌ Database init failed: {}", e)

    # Auto restore employee & attempt data if DB was reset
    try:
        from app.database import AsyncSessionLocal
        from app.services.data_guard import auto_restore_if_empty
        async with AsyncSessionLocal() as _db_guard:
            await auto_restore_if_empty(_db_guard)
    except Exception as e:
        logger.warning("DataGuard startup restore check failed: {}", e)


    # Auto-backup employee data on every startup (protects against accidental data loss)
    try:
        import subprocess, os
        from sqlalchemy import text as _text2
        async with engine.begin() as conn:
            emp_count = (await conn.execute(_text2("SELECT COUNT(*) FROM employees"))).scalar() or 0
        if emp_count > 0:
            backup_dir = os.environ.get("BACKUP_DIR", "/backups")
            os.makedirs(backup_dir, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/startup_backup_{ts}_emp{emp_count}.sql"
            db_url = os.environ.get("DATABASE_URL_SYNC", "")
            if db_url and "postgresql" in db_url:
                result = subprocess.run(
                    ["pg_dump", db_url, "-f", backup_file, "--no-password"],
                    capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    logger.info("✅ Startup backup: {} ({} employees)", backup_file, emp_count)
                else:
                    logger.warning("⚠️ Startup backup failed: {}", result.stderr.decode())
            else:
                logger.info("✅ {} employees in DB (SQLite — no pg_dump needed)", emp_count)
        else:
            logger.info("ℹ️ No employees yet — backup skipped")
    except Exception as e:
        logger.warning("⚠️ Startup backup error (non-critical): {}", e)

    # Create or update superadmin accounts (user / admin -> 12345)
    try:
        import uuid as _uuid
        import os as _os
        from sqlalchemy import text as _text
        from app.utils.security import get_password_hash as _gph

        _admin_pass = _os.getenv("ADMIN_PASSWORD", "12345")
        _pwd_hash = _gph(_admin_pass)

        async with engine.begin() as conn:
            try:
                await conn.execute(_text("DROP INDEX IF EXISTS ix_question_answer_correct"))
            except Exception:
                pass

            for u in ["user", "admin"]:
                row = (await conn.execute(_text("SELECT id FROM admins WHERE username = :u"), {"u": u})).fetchone()
                if row:
                    await conn.execute(
                        _text("UPDATE admins SET password_hash = :pw, is_active = 1 WHERE username = :u"),
                        {"pw": _pwd_hash, "u": u}
                    )
                else:
                    _aid = str(_uuid.uuid4())
                    await conn.execute(
                        _text("INSERT INTO admins (id, username, password_hash, full_name, is_active) VALUES (:id, :u, :pw, :fn, 1)"),
                        {"id": _aid, "u": u, "pw": _pwd_hash, "fn": "Bosh Administrator"}
                    )
            logger.info("✅ Superadmin accounts ('user' & 'admin') updated with active status")
    except Exception as e:
        logger.error("❌ Superadmin creation failed: {}", e)

    # Seed & Sync branches (official DEE branches of Uzbekistan in Cyrillic)
    try:
        _BRANCHES = [
            "Давлат Экологик экспертизаси маркази (Марказий аппарат)",
            "Қорақалпоғистон Республикаси филиали",
            "Андижон вилояти филиали",
            "Бухоро вилояти филиали",
            "Жиззах вилояти филиали",
            "Қашқадарё вилояти филиали",
            "Навоий вилояти филиали",
            "Наманган вилояти филиали",
            "Самарқанд вилояти филиали",
            "Сурхондарё вилояти филиали",
            "Сирдарё вилояти филиали",
            "Фарғона вилояти филиали",
            "Тошкент вилояти филиали",
            "Хоразм вилояти филиали",
            "Тошкент шаҳар филиали",
        ]
        async with engine.begin() as conn:
            # Upsert all 15 branches by sort_order
            for i, bname in enumerate(_BRANCHES, 1):
                existing_id = (await conn.execute(_text("SELECT id FROM branches WHERE sort_order = :s"), {"s": i})).scalar()
                if existing_id:
                    await conn.execute(
                        _text("UPDATE branches SET name = :n, is_active = true WHERE id = :id"),
                        {"n": bname, "id": existing_id}
                    )
                else:
                    await conn.execute(
                        _text("INSERT INTO branches (id, name, sort_order, is_active) VALUES (:id, :n, :s, true)"),
                        {"id": str(_uuid.uuid4()), "n": bname, "s": i}
                    )

            # Auto-fix existing employees with NULL branch_id
            await conn.execute(_text("""
                UPDATE employees
                SET branch_id = (SELECT id FROM branches ORDER BY sort_order ASC LIMIT 1)
                WHERE branch_id IS NULL
            """))

            logger.info("✅ 15 ta филиал ва ходимлар филиаллари синк қилинди")
    except Exception as e:
        logger.error("❌ Branch seeding failed: {}", e)

    # Seed topics and questions (4 topics, 114 questions)
    try:
        _OFFICIAL_TOPICS = [
            (1, "1-Мавзу", "Экологик экспертиза"),
            (2, "2-Мавзу", "Атроф муҳитга таъсирни баҳолаш"),
            (3, "3-Мавзу", "Давлат экологик экспертизасини ўтказиш ва эксперт"),
            (4, "4-Мавзу", "Давлат экологик экспертизаси субъектлари"),
        ]
        async with engine.begin() as conn:
            for seq, sn, fn in _OFFICIAL_TOPICS:
                row_t = (await conn.execute(_text("SELECT id FROM topics WHERE sequence_order = :s"), {"s": seq})).fetchone()
                if row_t:
                    await conn.execute(
                        _text("UPDATE topics SET short_name = :sn, full_name = :fn, is_active = true WHERE id = :id"),
                        {"sn": sn, "fn": fn, "id": row_t[0]}
                    )

        from app.seeds.seed import seed_topics_and_questions
        await seed_topics_and_questions(engine, force=True)
        logger.info("✅ 4 та кирилл мавзу ва 114 та савол (А, Б, В, Г вариантлар) пўлиқ инвентаризация ва синк қилинди")
    except Exception as e:
        logger.error("❌ Topic seeding failed: {}", e)

    # Redis connectivity check
    try:
        from app.redis_client import redis_client
        await redis_client.ping()
        logger.info("вњ… Redis connected")
    except Exception as e:
        logger.warning("вљ пёЏ  Redis unavailable: {}. Proceeding without cache.", e)

    # Start Telegram bot
    if settings.telegram_bot_token and settings.telegram_bot_token != "dummy_token":
        try:
            from app.bot.bot import create_application
            bot_app = await create_application()
            await bot_app.initialize()
            await bot_app.start()
            await bot_app.updater.start_polling(drop_pending_updates=True)
            app.state.bot_app = bot_app
            logger.info("вњ… Telegram bot @Eco234_bot started polling")
        except Exception as e:
            logger.error("вќЊ Telegram bot failed to start: {}", e)
    else:
        logger.warning("вљ пёЏ  TELEGRAM_BOT_TOKEN not set вЂ” bot not started")

    yield

    # Shutdown
    logger.info("рџ›‘ eco-chat.uz shutting down...")
    if hasattr(app.state, "bot_app"):
        try:
            await app.state.bot_app.updater.stop()
            await app.state.bot_app.stop()
            await app.state.bot_app.shutdown()
            logger.info("вњ… Telegram bot stopped")
        except Exception as e:
            logger.warning("Bot shutdown error: {}", e)
    await engine.dispose()
    logger.info("вњ… Shutdown complete")


# в”Ђв”Ђ FastAPI App в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
app = FastAPI(
    title="eco-chat.uz API",
    version="1.0.0",
    description="Davlat ekologik ekspertizasi markazi вЂ” bilim o'lchash tizimi",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# в”Ђв”Ђ API Routers в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
from app.api import auth, branches, employees, topics, questions, dashboard, reports, audit, sse
from app.api.internal import bot as internal_bot

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(branches.router, prefix="/api/branches", tags=["Branches"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(topics.router, prefix="/api/topics", tags=["Topics"])
app.include_router(questions.router, prefix="/api", tags=["Questions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(audit.router, prefix="/api/audit-logs", tags=["Audit"])
app.include_router(sse.router, prefix="/api/sse", tags=["SSE"])
app.include_router(internal_bot.router, prefix="/internal/bot", tags=["Internal Bot API"])


@app.api_route("/api/system-deploy", methods=["GET", "POST"])
async def public_system_deploy(secret: str = ""):
    """Public system deploy trigger for pulling latest git commits on live server."""
    import subprocess
    if secret != "eco2026":
        return JSONResponse(status_code=403, content={"detail": "Invalid secret key"})
    try:
        res = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True, timeout=30)
        return {"success": True, "stdout": res.stdout, "stderr": res.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Debug Endpoint (REMOVE IN PRODUCTION) ────────────────────────────────────

@app.get("/api/debug/test-flow", tags=["Debug"])
async def debug_test_flow(tg_id: int = 999999999):
    """Debug: test employee registration + attempt start to expose exact errors."""
    import traceback
    results = {}
    
    try:
        from app.database import AsyncSessionLocal
        from app.services import employee_service, topic_service, test_engine
        
        # Step 1: Test employee creation
        try:
            async with AsyncSessionLocal() as db:
                emp = await employee_service.register_employee(
                    db=db, telegram_user_id=tg_id,
                    full_name="Test Debug User",
                    branch_name_or_id=None, phone=""
                )
                results["step1_register"] = {"ok": True, "employee_id": str(emp.id), "branch_id": str(emp.branch_id)}
        except Exception as e:
            results["step1_register"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}
            return results
        
        # Step 2: Get topics
        try:
            async with AsyncSessionLocal() as db:
                topics = await topic_service.get_active_topics_ordered(db)
                results["step2_topics"] = {"ok": True, "count": len(topics), "first_id": str(topics[0].id) if topics else None}
        except Exception as e:
            results["step2_topics"] = {"ok": False, "error": str(e)}
            return results
        
        # Step 3: Test attempt start
        if topics:
            topic_id = str(topics[0].id)
            emp_id = results["step1_register"]["employee_id"]
            try:
                async with AsyncSessionLocal() as db:
                    attempt = await test_engine.start_attempt(db, None, emp_id, topic_id, 1)
                    results["step3_attempt"] = {"ok": True, "attempt_id": str(attempt.id)}
            except Exception as e:
                results["step3_attempt"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-800:]}
        
        # Step 4: Count employees in DB
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import func
                from sqlalchemy.future import select
                from app.models.employee import Employee
                count = (await db.execute(select(func.count()).select_from(Employee))).scalar()
                results["step4_count"] = {"ok": True, "total_employees": count}
        except Exception as e:
            results["step4_count"] = {"ok": False, "error": str(e)}
            
    except Exception as e:
        results["fatal"] = str(e)
    
    return results


# ── Health Endpoint ─────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for load balancer / monitoring."""
    import pytz
    now = datetime.datetime.now(pytz.timezone(settings.tz)).isoformat()
    result = {"status": "ok", "timestamp": now, "version": "1.0.0"}

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {str(e)}"
        result["status"] = "degraded"

    # Redis check
    try:
        from app.redis_client import redis_client
        await redis_client.ping()
        result["redis"] = "ok"
    except Exception:
        result["redis"] = "unavailable"

    # Bot check
    result["bot"] = "running" if hasattr(app.state, "bot_app") else "not_started"

    return result


# в”Ђв”Ђ Exception Handlers в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login.html")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # SPA uchun: API bo'lmagan yo'llar login.html ga yo'naltirilsin
    if not str(request.url.path).startswith("/api") and not str(request.url.path).startswith("/internal"):
        from fastapi.responses import FileResponse
        import os as _os
        fp = _os.path.join(_os.path.dirname(__file__), "..", "..", "frontend", "login.html")
        if _os.path.exists(fp):
            return FileResponse(fp)
    return JSONResponse(status_code=404, content={"error": "Not found", "path": str(request.url)})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("Internal server error: {} вЂ” {}", request.url, exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# в”Ђв”Ђ Static Frontend Files в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# Static frontend — must come AFTER all API routes
# backend/app/main.py -> ../../frontend
_here = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.normpath(os.path.join(_here, "..", "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static-assets")
    # Also serve frontend files at root
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
