@echo off
setlocal enabledelayedexpansion
title JobPilot-AI — One-Click Setup & Installer
color 0b

echo.
echo  ===================================================================
echo      __      _     ___  _ _       _          _    ___ 
echo   \ \    / /_ _ _ _ _ _ _  ^| _ \(_) ^| ___  ^| ^|_       /_\  ^|_ _^|
echo    \ \/\/ / -_) '_^| '_/ -_) ^|  _/ ^| ^|/ _ \ ^|  _^|     / _ \  ^| ^| 
echo     \_/\_/\___^|_^| ^|_^| \___^| ^|_^| ^|_^|_^|\___/  \__^|    /_/ \_\^|___^|
echo.
echo     Autonomous AI Job Application Agent & Multi-Portal Auto-Applier
echo  ===================================================================
echo.

:: 1. Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
python --version

:: 2. Check Node.js
echo.
echo [2/5] Checking Node.js & npm installation...
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not found in your PATH!
    echo Please install Node.js (LTS version) from https://nodejs.org/
    pause
    exit /b 1
)
node -v

:: 3. Install Python Dependencies
echo.
echo [3/5] Installing Python requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Encountered minor pip install notice, continuing...
)

:: 4. Install Playwright Chromium Browser
echo.
echo [4/5] Installing Playwright Chromium browser automation engine...
python -m playwright install chromium

:: 5. Install Node.js NPM Dependencies
echo.
echo [5/5] Installing Electron & UI dependencies...
call npm install

:: Initialize Data & Config files
if not exist "data" mkdir data
if not exist "data\applications_db.json" echo [] > data\applications_db.json
if not exist "config.json" copy config.example.json config.json

echo.
echo  ===================================================================
echo   [SUCCESS] JobPilot-AI installed successfully!
echo.
echo   Next Steps:
echo   1. Double click "run.bat" to launch the desktop application.
echo   2. Place your "Resume.pdf" in this folder.
echo   3. Configure your API keys and target roles in the app Settings tab.
echo  ===================================================================
echo.
pause
