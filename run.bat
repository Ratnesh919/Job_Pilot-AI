@echo off
title JobPilot-AI Launcher
color 0a

echo.
echo ===================================================================
echo   Starting JobPilot-AI Desktop Agent...
echo ===================================================================
echo.

if not exist "node_modules\electron" (
    echo [NOTICE] Dependencies not installed yet. Running install.bat first...
    call install.bat
)

:: Launch Electron Application
npx electron .

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application closed with code %errorlevel%.
    pause
)
