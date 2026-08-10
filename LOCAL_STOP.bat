@echo off
title eco-chat.uz - LOCAL STOP
color 0C

echo.
echo  ================================================
echo       eco-chat.uz -- TO'XTATILMOQDA
echo  ================================================
echo.

echo  Server jarayonlari to'xtatilmoqda...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im uvicorn.exe >nul 2>&1

echo.
echo  ================================================
echo       BARCHA SERVISLAR TO'XTATILDI!
echo  ================================================
echo.
pause
