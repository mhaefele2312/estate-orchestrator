@echo off
title Claude Tokenized
color 1F

echo.
echo  ============================================
echo   Claude Tokenized
echo   Private AI for Your Estate Vault
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
    echo  Ollama not installed -- keyword search only.
)

echo.
echo  Opening Claude Tokenized in your browser.
echo  Keep this window open while using the app.
echo  Close this window to shut down.
echo.

REM Start Streamlit in background, wait for it, then open browser
start /b "" python -m streamlit run behaviors\claude-tokenized\claude_tokenized.py --server.headless true --browser.gatherUsageStats false --server.port 8501

echo  Waiting for server to start...
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -s --max-time 1 http://localhost:8501/_stcore/health >nul 2>&1
if errorlevel 1 goto WAIT_LOOP

echo  Server ready. Opening browser...
start "" http://localhost:8501
echo.
echo  Claude Tokenized is running at http://localhost:8501
echo  Press any key to shut down.
pause >nul
