@echo off
:: Estate OS -- Daily Pipeline Runner
:: Double-click this file each morning to process all captures from your inbox.
::
:: What it does:
::   1. Processes all new voice captures from MHH-Inbox (and HBS-Inbox)
::   2. Writes rows to your Google Sheet + flat log files
::   3. Archives processed transcripts to Capture-Archive

cd /d "%~dp0"
python behaviors\capture-pipeline\capture_pipeline.py --inbox --confirm

echo.
echo Done. Press any key to close.
pause > nul
