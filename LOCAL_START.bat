@echo off
title eco-chat.uz - LOCAL START
color 0A
cd /d "%~dp0"

echo.
echo  ================================================
echo    eco-chat.uz -- ISHGA TUSHIRILMOQDA
echo  ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [XATO] Python topilmadi!
    echo  https://www.python.org/downloads/ dan yuklab o'rnating
    pause
    exit /b 1
)

echo  [1/4] Kutubxonalar o'rnatilmoqda...
cd backend
pip install -r requirements_local.txt -q --disable-pip-version-check
echo         Tayyor.

echo  [2/4] Ma'lumotlar bazasi tayyorlanmoqda...
python setup_local_db.py
python scripts/create_superadmin_local.py

echo  [3/4] Server ishga tushirilmoqda...
set DATABASE_URL=sqlite+aiosqlite:///./ecochat_local.db
set REDIS_URL=
set SECRET_KEY=local-eco-chat-secret-2024-xK9mN2pL8v
set INTERNAL_API_SECRET=local-internal-secret-2024
set ADMIN_SECRET=local-admin-secret-2024
set TELEGRAM_BOT_TOKEN=8876479286:AAEmUKZ44FLBZ5-pTwrvgifmYd_E7eiAtgo
set ENVIRONMENT=development
set LOG_LEVEL=INFO
set CORSORIGINS=["*"]
set BACKEND_URL=http://localhost:8000

start "eco-chat Server" cmd /k "cd /d %~dp0backend && set DATABASE_URL=sqlite+aiosqlite:///./ecochat_local.db && set REDIS_URL= && set SECRET_KEY=local-eco-chat-secret-2024-xK9mN2pL8v && set INTERNAL_API_SECRET=local-internal-secret-2024 && set TELEGRAM_BOT_TOKEN=8876479286:AAEmUKZ44FLBZ5-pTwrvgifmYd_E7eiAtgo && set ENVIRONMENT=development && set CORSORIGINS=[*] && set BACKEND_URL=http://localhost:8000 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo  [4/4] Brauzer ochilmoqda...
timeout /t 5 /nobreak >nul
cd ..

echo.
echo  ================================================
echo       TIZIM TAYYOR!
echo  ================================================
echo.
echo   Web Admin Panel : http://localhost:8000
echo   API Docs        : http://localhost:8000/api/docs
echo   Telegram Bot    : @Eco234_bot
echo.
echo   Login : user
echo   Parol : 12345
echo.
echo  ================================================
echo   To'xtatish: LOCAL_STOP.bat yoki Server oynasini yoping
echo  ================================================
echo.
start http://localhost:8000
pause
