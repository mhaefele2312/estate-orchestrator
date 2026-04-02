@echo off
title Estate Local LLM — Document Search + AI
color 1F

echo.
echo  ============================================
echo   Estate Local LLM — Document Search + AI Q^&A
echo   Private  ^|  Local  ^|  Secure
echo  ============================================
echo.

cd /d "%~dp0"

REM Start Ollama in background if installed but not yet running
where ollama >nul 2>&1
if %errorlevel% == 0 (
    curl -s --max-time 1 http://localhost:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo  Starting Ollama in background...
        start /b "" ollama serve
        timeout /t 3 /nobreak >nul
    ) else (
        echo  Ollama already running.
    )
) else (
    echo  Ollama not installed -- AI tab will show setup instructions.
)

echo.
echo  Opening Estate Local LLM in your browser.
echo  Keep this window open while using the app.
echo  Close this window to shut down.
echo.

python -m streamlit run behaviors\estate-assistant\estate_assistant.py --server.headless true --browser.gatherUsageStats false

echo.
echo  Estate Local LLM has stopped.
pause
