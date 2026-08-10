import pytest
import os
import sys
from sqlalchemy import text
from app.config import settings
from app.database import engine, Base

@pytest.mark.asyncio
async def test_postgres_normalization():
    """Verify postgresql:// URLs are normalized to postgresql+asyncpg://"""
    from app.database import settings as db_settings
    orig_url = "postgresql://user:pass@localhost/db"
    
    # Save original settings URL
    old_url = db_settings.database_url
    try:
        db_settings.database_url = orig_url
        from importlib import reload
        import app.database
        # Inject dummy asyncpg to sys.modules if not present
        if "asyncpg" not in sys.modules:
            import types
            sys.modules["asyncpg"] = types.ModuleType("asyncpg")
        reload(app.database)
        assert app.database._db_url.startswith("postgresql+asyncpg://")
    finally:
        db_settings.database_url = old_url
        import app.database
        reload(app.database)


@pytest.mark.asyncio
async def test_production_sqlite_blocked():
    """Verify that SQLite URLs are blocked in production mode."""
    import os
    from importlib import reload
    import app.database

    old_env = os.environ.get("ENVIRONMENT")
    old_app_env = os.environ.get("APP_ENV")
    old_url = settings.database_url

    os.environ["ENVIRONMENT"] = "production"
    settings.database_url = "sqlite:///test.db"

    try:
        with pytest.raises(RuntimeError) as excinfo:
            reload(app.database)
        assert "Production PostgreSQL unavailable" in str(excinfo.value)
    finally:
        if old_env:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        if old_app_env:
            os.environ["APP_ENV"] = old_app_env
        settings.database_url = old_url
        reload(app.database)


@pytest.mark.asyncio
async def test_employee_persistence_simulation():
    """Verify that adding an employee persists across session lifespans."""
    from app.database import AsyncSessionLocal
    
    # Initialize schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Write to local test DB
    async with AsyncSessionLocal() as db:
        # Check table
        await db.execute(text("DELETE FROM employees WHERE telegram_user_id = 999999"))
        await db.commit()
        
        # Add employee
        from app.models.employee import Employee
        emp = Employee(id="99999999-9999-9999-9999-999999999999", telegram_user_id=999999, full_name="Persistence Test User", registration_state="COMPLETED")
        db.add(emp)
        await db.commit()

    # Re-open session simulating restart
    async with AsyncSessionLocal() as db:
        res = (await db.execute(text("SELECT full_name FROM employees WHERE telegram_user_id = 999999"))).scalar()
        assert res == "Persistence Test User"
        
        # Cleanup
        await db.execute(text("DELETE FROM employees WHERE telegram_user_id = 999999"))
        await db.commit()
