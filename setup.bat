@echo off
REM Video Downloader - Quick Start Script for Windows

echo.
echo 🎬 Video Downloader - Quick Start Setup
echo ========================================
echo.

REM Check Python
echo ✓ Checking Python...
python --version
if errorlevel 1 (
    echo ❌ Python not found. Install from: https://www.python.org
    pause
    exit /b 1
)

REM Check ffmpeg
echo ✓ Checking ffmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ❌ ffmpeg not found. Install with:
    echo    winget install ffmpeg
    echo    or download from: https://ffmpeg.org
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo ✓ Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo ✓ Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Summary
echo.
echo ✅ Setup Complete!
echo.
echo To start the server, run:
echo    venv\Scripts\activate.bat
echo    python app.py
echo.
echo Then open: http://localhost:5000
echo.
pause
