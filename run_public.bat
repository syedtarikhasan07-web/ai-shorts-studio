@echo off
setlocal enabledelayedexpansion
title AI Shorts Studio - Public Share Mode
chcp 65001 >nul
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe start_online.py
) else (
    echo [!] Virtual environment not found. Please run START.bat first!
    pause
)
