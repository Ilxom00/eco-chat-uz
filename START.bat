@echo off
title eco-chat.uz - START
color 0A
cd /d "%~dp0"

echo.
echo  ================================================
echo       eco-chat.uz  --  ISHGA TUSHIRILMOQDA
echo  ================================================
echo.

REM Python tekshir
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [XATO] Python topilmadi!
    echo  https://www.python.org/downloads/ dan yuklab o'rnating
    pause
    exit /b 1
)

echo  [1/4] Kutubxonalar o'rnatilmoqda...
pip install -r backend\requirements_local.txt -q --disable-pip-version-check
echo         OK.

echo  [2/4] Ma'lumotlar bazasi tayyorlanmoqda...
cd backend
python setup_local_db.py
python scripts\create_superadmin_local.py
cd ..

echo  [3/4] Server ishga tushirilmoqda...
echo         (Bu oyna server ishlayotganida ochiq turishi shart!)
echo.

color 0A
echo  ================================================
echo       TIZIM TAYYOR!
echo  ================================================
echo.
echo   Web Admin Panel : http://localhost:8000
echo   API Docs        : http://localhost:8000/api/docs
echo   Telegram Bot    : @Eco234_bot
echo.
echo   Login  :  user
echo   Parol  :  12345
echo.
echo  ================================================
echo   To'xtatish: bu oynani yoping yoki STOP.bat
echo  ================================================
echo.

REM Server SHU OYNADA ishlasin (yopilmaydi)
cd backend
set DATABASE_URL=sqlite+aiosqlite:///./ecochat_local.db
set REDIS_URL=
set SECRET_KEY=local-eco-chat-secret-2024-xK9mN2pL8v
set INTERNAL_API_SECRET=local-internal-secret-2024
set TELEGRAM_BOT_TOKEN=8876479286:AAEmUKZ44FLBZ5-pTwrvgifmYd_E7eiAtgo
set ENVIRONMENT=development
set CORSORIGINS=[*]
set BACKEND_URL=http://localhost:8000

start http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
