@echo off
title eco-chat.uz - STOP
color 0E
cd /d "%~dp0"

echo.
echo  ================================================
echo       eco-chat.uz  --  TO'XTATILMOQDA
echo  ================================================
echo.

REM Docker ishlayaptimi?
docker info >nul 2>&1
if not errorlevel 1 (
    echo  [Docker] Konteynerlar to'xtatilmoqda...
    docker-compose down >nul 2>&1
    echo  [Docker] Konteynerlar to'xtatildi.
    echo.
)

REM Mahalliy Python server (port 8000) ni to'xtatish
echo  [Mahalliy] Port 8000 da ishlaydigan jarayon qidirilmoqda...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING 2^>nul') do (
    echo  [Mahalliy] Jarayon topildi ^(PID: %%a^), to'xtatilmoqda...
    taskkill /PID %%a /F >nul 2>&1
    echo  [Mahalliy] Server to'xtatildi.
)

REM "eco-chat.uz SERVER" oynasini yopish
taskkill /FI "WINDOWTITLE eq eco-chat.uz SERVER" /F >nul 2>&1

echo.
echo  ================================================
echo         BARCHA SERVERLAR TO'XTATILDI
echo  ================================================
echo.
timeout /t 2 /nobreak >nul
