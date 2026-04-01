@echo off
title Estate OS — Silver Intake
color 1F

echo.
echo  ============================================
echo   Estate OS — Legacy Document Intake
echo   Sorts, Classifies, and Files to Silver
echo  ============================================
echo.

cd /d "%~dp0"

REM ── If a folder was dragged onto this .bat, use it directly ──────────────────
set "SOURCE_PATH=%~1"

if not "%SOURCE_PATH%"=="" goto :have_source

REM ── Otherwise prompt the user ─────────────────────────────────────────────────
echo  Drag your folder of old documents onto this window,
echo  then press Enter. Or type the full folder path.
echo.
set /p SOURCE_PATH="  Folder path: "

:have_source

REM Strip surrounding quotes if drag-dropped
set SOURCE_PATH=%SOURCE_PATH:"=%

if "%SOURCE_PATH%"=="" (
    echo.
    echo  No folder given. Nothing to do.
    pause
    exit /b 1
)

if not exist "%SOURCE_PATH%" (
    echo.
    echo  Folder not found: %SOURCE_PATH%
    echo  Check the path and try again.
    pause
    exit /b 1
)

echo.
echo  ────────────────────────────────────────────────────────────
echo   STEP 1 OF 3 — SORT BY FILE TYPE
echo  ────────────────────────────────────────────────────────────
echo.
echo  Scanning: %SOURCE_PATH%
echo.

python behaviors\staging-intake\staging_sorter.py --source "%SOURCE_PATH%"

echo.
set /p CONFIRM_SORT="  Sort these files into Staging? [Y/N]: "
if /i not "%CONFIRM_SORT%"=="Y" (
    echo  Cancelled.
    pause
    exit /b 0
)

REM Derive a drive label from the last folder name + today's date
for %%F in ("%SOURCE_PATH%") do set "DRIVE_LABEL=%%~nxF"
for /f "tokens=1-3 delims=/-. " %%a in ('date /t') do (
    set "TODAY=%%c-%%a-%%b"
)
REM Fallback: just use raw date string
if "%TODAY%"=="" for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
if "%TODAY%"=="" set "TODAY=%DT:~0,4%-%DT:~4,2%-%DT:~6,2%"

set "STAGING_NAME=%DRIVE_LABEL%-%TODAY%"

python behaviors\staging-intake\staging_sorter.py --source "%SOURCE_PATH%" --name "%STAGING_NAME%" --confirm

if errorlevel 1 (
    echo.
    echo  Sorting failed. Check the error above.
    pause
    exit /b 1
)

REM ── Determine the documents subfolder that was just created ───────────────────
REM Read staging_dir from ops-ledger config.json if possible, else use default
set "STAGING_ROOT=G:\My Drive\Staging-Intake"
set "DOCS_FOLDER=%STAGING_ROOT%\%STAGING_NAME%\documents"

echo.
echo  ────────────────────────────────────────────────────────────
echo   STEP 2 OF 3 — CLASSIFY DOCUMENTS INTO SILVER VAULT
echo  ────────────────────────────────────────────────────────────
echo.
echo  Documents folder: %DOCS_FOLDER%
echo.

if not exist "%DOCS_FOLDER%" (
    echo  No documents folder found at: %DOCS_FOLDER%
    echo  If your files are PDFs or text, check that folder exists.
    echo  Non-document files (photos, video) are in separate subfolders
    echo  and must be handled manually.
    pause
    exit /b 1
)

python behaviors\silver-classifier\silver_classifier.py --source "%DOCS_FOLDER%"

echo.
set /p CONFIRM_CLASSIFY="  Classify these documents interactively? [Y/N]: "
if /i not "%CONFIRM_CLASSIFY%"=="Y" (
    echo.
    echo  Skipped classification. Documents are in:
    echo    %DOCS_FOLDER%
    echo  Run silver_classifier.py --source "%DOCS_FOLDER%" --confirm when ready.
    pause
    exit /b 0
)

python behaviors\silver-classifier\silver_classifier.py --source "%DOCS_FOLDER%" --confirm

if errorlevel 1 (
    echo.
    echo  Classification stopped. Any files accepted so far are in Silver.
    pause
    exit /b 1
)

echo.
echo  ────────────────────────────────────────────────────────────
echo   STEP 3 OF 3 — REVIEW SILVER VAULT
echo  ────────────────────────────────────────────────────────────
echo.
echo  All classified files are now in the Silver vault.
echo  You can review them now: accept, rename, move to correct folder,
echo  or promote directly to Gold.
echo.

set /p CONFIRM_REVIEW="  Open Silver vault review now? [Y/N]: "
if /i not "%CONFIRM_REVIEW%"=="Y" (
    echo.
    echo  Done. Run silver_review.py when you are ready to review Silver.
    pause
    exit /b 0
)

python behaviors\silver-review\silver_review.py --confirm

echo.
echo  ============================================
echo   Intake complete.
echo  ============================================
echo.
pause
