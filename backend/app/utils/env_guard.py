"""
eco-chat.uz — Environment Guard
Production database'da destructive operatsiyalarni bloklash.
CODE IS REPLACEABLE. DATA IS NOT.
"""
import os
import sys
from functools import wraps


def is_production() -> bool:
    """Returns True if running in production environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env == "production"


def is_test() -> bool:
    """Returns True if running in test environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env in ("test", "testing")


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "")


def is_production_database() -> bool:
    """
    Heuristic: production DB URL'ni aniqlash.
    postgres:5432 (Docker internal) yoki production hostname bor bo'lsa.
    """
    db_url = get_database_url().lower()
    if "localhost" in db_url or "127.0.0.1" in db_url:
        # localhost odatda development
        return is_production()
    if "sqlite" in db_url:
        return False
    # Docker internal yoki real server — production deb hisoblash
    return True


class ProductionGuardError(RuntimeError):
    """Raised when a destructive operation is attempted in production."""
    pass


def guard_production(operation_name: str = "destructive operation"):
    """
    Decorator: production muhitida destructive operatsiyalarni bloklaydi.

    Usage:
        @guard_production("reset_database")
        def reset_database():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_production() or is_production_database():
                raise ProductionGuardError(
                    f"\n{'=' * 60}\n"
                    f"PRODUCTION GUARD TRIGGERED!\n"
                    f"Operation '{operation_name}' is BLOCKED in production.\n"
                    f"ENVIRONMENT={os.getenv('ENVIRONMENT', 'unknown')}\n"
                    f"DATABASE_URL={get_database_url()[:30]}...\n"
                    f"\nReminder: CODE IS REPLACEABLE. DATA IS NOT.\n"
                    f"{'=' * 60}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def guard_production_async(operation_name: str = "destructive operation"):
    """Async version of guard_production decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if is_production() or is_production_database():
                raise ProductionGuardError(
                    f"\n{'=' * 60}\n"
                    f"PRODUCTION GUARD TRIGGERED!\n"
                    f"Operation '{operation_name}' is BLOCKED in production.\n"
                    f"ENVIRONMENT={os.getenv('ENVIRONMENT', 'unknown')}\n"
                    f"DATABASE_URL={get_database_url()[:30]}...\n"
                    f"\nReminder: CODE IS REPLACEABLE. DATA IS NOT.\n"
                    f"{'=' * 60}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_explicit_confirmation(operation: str, target: str) -> None:
    """
    Foydalanuvchidan aniq tasdiqlash talab qiladi.
    Terminal'dan interaktiv kiritish uchun.
    """
    print(f"\n{'!' * 60}")
    print(f"  DESTRUCTIVE OPERATION: {operation}")
    print(f"  Target: {target}")
    print(f"  Bu operatsiya maʼlumotlarni YOʻQ QILISHI MUMKIN!")
    print(f"{'!' * 60}")
    confirm = input(f"\n  Davom etish uchun '{operation.upper()}' deb yozing: ")
    if confirm.strip() != operation.upper():
        print("  Operatsiya bekor qilindi.")
        sys.exit(0)


# ── GUARDED DANGEROUS FUNCTIONS ─────────────────────────────────────────────
# Bu funksiyalar HECH QACHON production'da chaqirilmasligi kerak.
# Ular faqat development/test muhitida ishlaydi.

@guard_production("drop_all_tables")
def drop_all_tables(engine):
    """Development only: drop all tables. BLOCKED in production."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()


@guard_production("reset_database")
def reset_database(engine, Base):
    """Development only: drop and recreate all tables. BLOCKED in production."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@guard_production("truncate_table")
def truncate_table(engine, table_name: str):
    """Development only: truncate a table. BLOCKED in production."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM {table_name}"))
        conn.commit()


@guard_production("seed_fake_data")
def seed_fake_data(*args, **kwargs):
    """Development only: seed fake/test data. BLOCKED in production."""
    raise NotImplementedError("seed_fake_data must be implemented per use case")
