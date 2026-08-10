"""
eco-chat.uz — Local Config Override (SQLite + no Redis)
Import qilib ishlatiladi: LOCAL_START.bat tomonidan
"""
import os

# SQLite (Docker/PostgreSQL talab qilmaydi)
os.environ.setdefault("DATABASE_URL",       "sqlite+aiosqlite:///./ecochat_local.db")
os.environ.setdefault("DATABASE_URL_SYNC",  "sqlite:///./ecochat_local.db")
os.environ.setdefault("REDIS_URL",          "")   # Redis yo'q — in-memory fallback

# Secrets
os.environ.setdefault("SECRET_KEY",              "local-eco-chat-secret-2024-xK9mN2pL")
os.environ.setdefault("INTERNAL_API_SECRET",     "local-internal-secret-2024")
os.environ.setdefault("ADMIN_SECRET",            "local-admin-secret-2024")

# Admin credentials
os.environ.setdefault("ADMIN_USERNAME", "user")
os.environ.setdefault("ADMIN_PASSWORD", "12345")
os.environ.setdefault("ADMIN_FULLNAME", "Bosh Administrator")

# Telegram Bot
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "8876479286:AAEmUKZ44FLBZ5-pTwrvgifmYd_E7eiAtgo")

# Environment
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL",   "INFO")
os.environ.setdefault("TZ",          "Asia/Tashkent")
os.environ.setdefault("CORSORIGINS", '["http://localhost","http://localhost:8000","http://127.0.0.1:8000"]')
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
