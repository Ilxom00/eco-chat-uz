@echo off
title eco-chat.uz - Windows Features Yoqish
color 0B

echo.
echo  ================================================
echo       WINDOWS VIRTUALIZATSIYA SOZLAMALARI
echo  ================================================
echo.
echo  [1/3] Hyper-V yoqilmoqda...
dism /online /enable-feature /featurename:Microsoft-Hyper-V-All /all /norestart >nul 2>&1

echo  [2/3] Virtual Machine Platform yoqilmoqda...
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1

echo  [3/3] WSL2 yoqilmoqda...
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1

echo.
echo  ================================================
echo       WINDOWS SOZLAMALARI TAYYOR!
echo  ================================================
echo.
echo   Endi kompyuterni qayta yoqing (restart)
echo   va Docker Desktop avtomatik ishlaydi.
echo.
echo   RESTART qilishni xohlaysizmi?
echo.
choice /C YN /M "Ha (Y) yoki Yo'q (N)"
if errorlevel 2 goto :no_restart
if errorlevel 1 goto :restart

:restart
echo  Restart bo'lmoqda...
shutdown /r /t 5 /c "eco-chat.uz sozlamalari uchun restart"
goto :end

:no_restart
echo  Keyinroq o'zingiz restart qiling!

:end
echo.
pause
