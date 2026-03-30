@echo off
:: Estate OS -- Weekly Runner
:: Run this once a week (Sunday evening or Monday morning).
::
:: What it does:
::   1. Takes a source-of-truth snapshot (exports sheet to Google Drive + Gold vault + Obsidian)
::   2. Syncs flat logs to Obsidian vault
::   3. Writes this week's review file to Logs/

cd /d "%~dp0"

echo === Step 1: Snapshot ===
python behaviors\snapshot\snapshot.py --confirm

echo.
echo === Step 2: Sync to Obsidian ===
python behaviors\weekly-sync\weekly_sync.py --confirm

echo.
echo === Step 3: Weekly Review ===
python behaviors\email-intake\weekly_review.py --confirm

echo.
echo Done. Press any key to close.
pause > nul
