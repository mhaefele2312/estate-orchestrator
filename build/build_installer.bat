@echo off
title Estate OS — Build Installer
color 1F

echo.
echo  ============================================
echo   Estate OS — Build Windows Installer
echo  ============================================
echo.

cd /d "%~dp0"

REM ── Verify Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not on PATH.
    echo  Install Python from python.org and try again.
    pause
    exit /b 1
)

REM ── Install build tools and app dependencies ──────────────────────────────────
echo  Installing build tools and dependencies...
pip install pyinstaller customtkinter reportlab edge-tts --quiet
echo  Done.
echo.

REM ── Clean previous build artifacts ───────────────────────────────────────────
echo  Cleaning previous build...
if exist dist       rmdir /s /q dist
if exist build_tmp  rmdir /s /q build_tmp
echo  Done.
echo.

REM ── Run PyInstaller ───────────────────────────────────────────────────────────
echo  Building executable — this takes 3 to 6 minutes, please wait...
echo.
pyinstaller estate_interview.spec --noconfirm --workpath build_tmp

if errorlevel 1 (
    echo.
    echo  =============================================
    echo   BUILD FAILED — see errors above
    echo  =============================================
    pause
    exit /b 1
)

echo.
echo  Executable ready: dist\EstateOS\EstateOS.exe
echo.

REM ── Look for Inno Setup ───────────────────────────────────────────────────────
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
    echo  ─────────────────────────────────────────────
    echo   Inno Setup not found.
    echo.
    echo   To create the final installer (.exe):
    echo   1. Download Inno Setup 6 from:
    echo      https://jrsoftware.org/isinfo.php
    echo   2. Install it (free)
    echo   3. Re-run this script
    echo.
    echo   The standalone app folder is at:
    echo     %~dp0dist\EstateOS\
    echo   You can copy that entire folder to a USB drive
    echo   and run EstateOS.exe directly — no install needed.
    echo  ─────────────────────────────────────────────
    pause
    exit /b 0
)

REM ── Create output folder ──────────────────────────────────────────────────────
if not exist output mkdir output

REM ── Compile installer ─────────────────────────────────────────────────────────
echo  Creating installer package...
"%ISCC%" installer.iss

if errorlevel 1 (
    echo.
    echo  Inno Setup failed — see errors above.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   SUCCESS
echo.
echo   Installer:  build\output\EstateOS_Setup.exe
echo.
echo   Copy EstateOS_Setup.exe to a USB drive.
echo   Opa double-clicks it to install.
echo   A desktop shortcut is created automatically.
echo  ============================================
echo.
pause
