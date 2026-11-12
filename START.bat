@echo off
setlocal enabledelayedexpansion
title AI Shorts Studio - 1-Click Launch
chcp 65001 >nul
color 0B

echo =====================================================================
echo                 ⚡ AI SHORTS STUDIO - INITIALIZING ⚡
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Check for Python in .venv or system
set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [✓] Local virtual environment (.venv) detected.
) else (
    echo [!] Virtual environment not found. Checking system Python...
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "SYS_PYTHON=python"
    ) else (
        where py >nul 2>nul
        if %errorlevel% equ 0 (
            set "SYS_PYTHON=py -3"
        ) else (
            echo.
            echo [X] ERROR: Python is not installed or not in your system PATH!
            echo.
            echo To fix this:
            echo 1. Download and install Python from https://www.python.org/downloads/
            echo 2. During installation, CHECK the box: "Add Python to PATH"
            echo 3. Restart START.bat
            echo.
            pause
            exit /b 1
        )
    )

    echo [*] Creating virtual environment (.venv)...
    !SYS_PYTHON! -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [X] Failed to create virtual environment.
        pause
        exit /b 1
    )
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [✓] Virtual environment created successfully.
    echo [*] Installing required dependencies (this may take a couple minutes on first run)...
    "!PYTHON_EXE!" -m pip install --upgrade pip
    "!PYTHON_EXE!" -m pip install -r requirements.txt
)

:: 2. Verify Essential Packages
echo [*] Checking dependencies...
"!PYTHON_EXE!" -c "import streamlit, faster_whisper, cv2, yt_dlp" >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Some dependencies are missing. Installing required packages...
    "!PYTHON_EXE!" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [X] ERROR: Dependency installation failed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo [✓] All Python dependencies verified.

:: 3. Verify FFmpeg
if exist "bin\ffmpeg.exe" (
    echo [✓] High-speed FFmpeg engine ready.
) else (
    echo [!] Bundled FFmpeg not found in bin\ - checking system PATH...
    where ffmpeg >nul 2>nul
    if %errorlevel% equ 0 (
        echo [✓] System FFmpeg found.
    ) else (
        echo [!] WARNING: FFmpeg not detected. Video rendering may fail.
    )
)

:: 4. Clear any old stale processes on port 8501
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>nul
)

echo.
echo =====================================================================
echo           🚀 LAUNCHING AI SHORTS STUDIO IN YOUR BROWSER...
echo =====================================================================
echo.
echo Application will open at: http://localhost:8501
echo Leave this terminal window OPEN while using the studio.
echo Press Ctrl+C in this window anytime to stop the studio.
echo.

:: Automatically open browser
start http://localhost:8501

:: Launch Streamlit app
"!PYTHON_EXE!" -m streamlit run app.py

if %errorlevel% neq 0 (
    echo.
    echo [X] Application stopped with an error (Exit Code: %errorlevel%).
    echo If this was unexpected, review the error log above.
    echo.
    pause
)
