"""
eco-chat.uz вЂ” FastAPI Application Entry Point
Includes: API routes, Telegram bot startup, static files, health check
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
    logger.info("рџЊ± eco-chat.uz starting up...")

    # Create all DB tables (idempotent)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error("❌ Database init failed: {}", e)

    # Create superadmin if not exists (raw SQL - reliable)
    try:
        import uuid as _uuid
        import os as _os
        from sqlalchemy import text as _text
        from app.utils.security import get_password_hash as _gph

        _admin_user = _os.getenv("ADMIN_USERNAME", "user")
        _admin_pass = _os.getenv("ADMIN_PASSWORD", "12345")

        async with engine.begin() as conn:
            row = (await conn.execute(_text("SELECT id FROM admins WHERE username = :u"), {"u": _admin_user})).fetchone()
            if not row:
                _pwd = _gph(_admin_pass)
                _aid = str(_uuid.uuid4())
                await conn.execute(
                    _text("INSERT INTO admins (id, username, password_hash, full_name, is_active) VALUES (:id, :u, :pw, :fn, 1)"),
                    {"id": _aid, "u": _admin_user, "pw": _pwd, "fn": "Bosh Administrator"}
                )
                logger.info("✅ Superadmin '{}' created via raw SQL", _admin_user)
            else:
                logger.info("✅ Superadmin '{}' exists", _admin_user)
    except Exception as e:
        logger.error("❌ Superadmin creation failed: {}", e)

    # Seed branches (official DEE branches of Uzbekistan)
    try:
        _BRANCHES = [
            "Davlat Ekologik ekspertizasi markazi (Markaziy apparat)",
            "Qoraqalpog'iston Respublikasi filiali",
            "Andijon viloyati filiali",
            "Buxoro viloyati filiali",
            "Jizzax viloyati filiali",
            "Qashqadaryo viloyati filiali",
            "Navoiy viloyati filiali",
            "Namangan viloyati filiali",
            "Samarqand viloyati filiali",
            "Surxondaryo viloyati filiali",
            "Sirdaryo viloyati filiali",
            "Farg'ona viloyati filiali",
            "Toshkent viloyati filiali",
            "Xorazm viloyati filiali",
            "Toshkent shahar filiali",
        ]
        async with engine.begin() as conn:
            existing = (await conn.execute(_text("SELECT COUNT(*) FROM branches"))).scalar()
            if not existing:
                for i, bname in enumerate(_BRANCHES, 1):
                    await conn.execute(
                        _text("INSERT INTO branches (id, name, sort_order, is_active) VALUES (:id, :n, :s, 1)"),
                        {"id": str(_uuid.uuid4()), "n": bname, "s": i}
                    )
                logger.info("✅ {} ta filial yaratildi", len(_BRANCHES))
            else:
                logger.info("✅ Filiallar allaqachon bor ({})", existing)
    except Exception as e:
        logger.error("❌ Branch seeding failed: {}", e)

    # Seed topics and questions (4 topics, 115 questions)
    try:
        from app.seeds.seed import seed_topics_and_questions
        result = await seed_topics_and_questions(engine)
        if result:
            logger.info("✅ 4 mavzu va 115 savol yuklandi")
        else:
            logger.info("✅ Savollar allaqachon mavjud")
    except Exception as e:
        logger.error("❌ Question seeding failed: {}", e)

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


# в”Ђв”Ђ Health Endpoint в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
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
