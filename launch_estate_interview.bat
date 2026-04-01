@echo off
title Estate OS — Personal Estate Plan
color 1F

echo.
echo  ============================================
echo   Estate OS — Personal Estate Plan
echo   Private  ^|  Local  ^|  Secure
echo  ============================================
echo.

cd /d "%~dp0"

REM ── Check Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not on your PATH.
    pause
    exit /b 1
)

REM ── Install required packages if missing ──────────────────────────────────────
echo  Checking dependencies...
python -c "import customtkinter" 2>nul || pip install customtkinter --quiet
python -c "import reportlab"     2>nul || pip install reportlab     --quiet

REM ── Install voice package (optional) ─────────────────────────────────────────
python -c "import edge_tts" 2>nul || pip install edge-tts --quiet 2>nul

echo  Starting...
echo.

python behaviors\estate-interview\estate_interview.py

echo.
echo  Estate Interview closed.
pause
