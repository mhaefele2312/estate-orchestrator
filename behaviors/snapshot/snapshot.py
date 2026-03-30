"""
Estate OS -- Source-of-Truth Snapshot (Phase 1, Item 4)
======================================================
Exports all worksheets from the MHH-Ops-Ledger Google Sheet as timestamped
CSV files, then copies them to three locations:

  1. Google Drive Estate Ops Source-of-Truth folder (primary)
  2. Gold vault 12_Operations Source-of-Truth (encrypted)
  3. Obsidian Vault Ops-Ledger Source-of-Truth (offline backup)

Also writes a "sot-latest-MHH.csv" pointer file (a copy of the most recent
timestamped snapshot of the Raw Log tab).

USAGE:
  python snapshot.py
        Dry-run. Shows what would be exported. No writes.

  python snapshot.py --confirm
        Live run. Exports sheets and copies to all three locations.

  python snapshot.py --test
        Import check only. No files needed.

REQUIRES:
  - behaviors/ops-ledger/config.json with spreadsheet_id + snapshot paths
    (see config.example.json for all fields)

NON-NEGOTIABLE RULES (from CLAUDE.md):
  - Default is dry-run. --confirm required for real writes.
  - This script READS from Google Sheet and WRITES to local files/folders.
  - No LLM involvement. Pure Python export.
  - Append-only log files are NOT touched by this script.
"""

import sys
import os
import csv
import shutil
import json
from datetime import datetime
from pathlib import Path


# -- Config loading (reuses ops-ledger config.json) -------------------------

def _ops_ledger_dir() -> Path:
    """Return the ops-ledger folder (sibling of snapshot folder)."""
    return Path(__file__).resolve().parent.parent / "ops-ledger"


def load_config() -> dict:
    config_path = _ops_ledger_dir() / "config.json"
    if not config_path.exists():
        print()
        print("ERROR: config.json not found.")
        print(f"  Expected: {config_path}")
        print("  Copy config.example.json to config.json and fill in your values.")
        print()
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_path(base: Path, p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (base / path).resolve()


# -- Google Sheets auth (same pattern as verify_sheets_auth.py) --------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials(credentials_path: Path, token_path: Path):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not credentials_path.exists():
        print(f"ERROR: credentials file not found: {credentials_path}")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


# -- Export functions --------------------------------------------------------

def export_worksheet_to_csv(worksheet, output_path: Path):
    """Export a single worksheet to a CSV file."""
    rows = worksheet.get_all_values()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def copy_to_destination(source: Path, dest_dir: Path, filename: str) -> bool:
    """Copy a file to a destination directory. Returns True on success."""
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        shutil.copy2(str(source), str(dest))
        return True
    except Exception as e:
        print(f"  WARNING: Could not copy to {dest_dir}: {e}")
        return False


# -- Main logic --------------------------------------------------------------

def run_snapshot(confirm: bool):
    config = load_config()
    base = _ops_ledger_dir()

    sheet_id = (config.get("spreadsheet_id") or "").strip()
    if not sheet_id or sheet_id == "YOUR_GOOGLE_SHEET_ID":
        print("ERROR: Set spreadsheet_id in config.json.")
        sys.exit(1)

    # Paths from config
    sot_dir = Path(config.get("sot_dir", r"G:\My Drive\Estate Ops\Source-of-Truth"))
    gold_sot_dir = Path(config.get("gold_sot_dir", r"E:\12_Operations\Source-of-Truth"))
    obsidian_sot_dir = Path(config.get("obsidian_sot_dir",
                            r"C:\Users\mhhro\Documents\Obsidian Vault\Ops-Ledger\Source-of-Truth"))

    cred_path = _resolve_path(base, config.get("credentials_path", "credentials.json"))
    token_path = _resolve_path(base, config.get("token_path", "token.json"))

    today = datetime.now().strftime("%Y-%m-%d")
    mode_label = "LIVE RUN" if confirm else "DRY RUN"

    print()
    print("=" * 60)
    print(f"  SNAPSHOT -- SOURCE-OF-TRUTH PROMOTION ({mode_label})")
    print("=" * 60)
    print()
    print(f"  Date:              {today}")
    print(f"  Spreadsheet ID:    {sheet_id}")
    print(f"  SOT folder:        {sot_dir}")
    print(f"  Gold vault copy:   {gold_sot_dir}")
    print(f"  Obsidian copy:     {obsidian_sot_dir}")
    print()

    if not confirm:
        print("  DRY RUN: Would connect to Google Sheets, export all tabs as CSVs,")
        print("  copy to SOT folder + Gold vault + Obsidian, and update sot-latest pointer.")
        print()
        print("  To run for real:  python snapshot.py --confirm")
        print()
        print("=" * 60)
        return

    # -- Connect to Google Sheets --
    import gspread

    print("  Connecting to Google Sheets...")
    creds = _get_credentials(cred_path, token_path)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    worksheets = sh.worksheets()
    print(f"  Found {len(worksheets)} worksheet(s): {', '.join(ws.title for ws in worksheets)}")
    print()

    # -- Export each worksheet --
    exported_files = []
    raw_log_csv = None  # Track the Raw Log export for sot-latest pointer

    for ws in worksheets:
        # Sanitize worksheet name for filename
        safe_name = ws.title.replace(" ", "-").replace("/", "-").lower()
        filename = f"sot-MHH-{today}-{safe_name}.csv"
        output_path = sot_dir / filename

        print(f"  Exporting '{ws.title}' -> {filename}")
        export_worksheet_to_csv(ws, output_path)
        exported_files.append((output_path, filename))
        print(f"    OK Saved to {output_path}")

        # Track the Raw Log tab specifically
        if ws.title.lower().replace(" ", "") in ("rawlog", "raw-log", "rawlog"):
            raw_log_csv = (output_path, filename)

    # If no "Raw Log" tab found, use the first worksheet
    if raw_log_csv is None and exported_files:
        raw_log_csv = exported_files[0]
        print(f"\n  Note: No 'Raw Log' tab found. Using first tab ({worksheets[0].title}) for sot-latest.")

    # -- Write sot-latest-MHH.csv pointer --
    if raw_log_csv:
        latest_path = sot_dir / "sot-latest-MHH.csv"
        shutil.copy2(str(raw_log_csv[0]), str(latest_path))
        print(f"\n  OK Updated sot-latest-MHH.csv -> {raw_log_csv[1]}")

    # -- Copy all exported files to Gold vault and Obsidian --
    print()
    gold_ok = True
    obsidian_ok = True

    for source_path, filename in exported_files:
        if not copy_to_destination(source_path, gold_sot_dir, filename):
            gold_ok = False
        if not copy_to_destination(source_path, obsidian_sot_dir, filename):
            obsidian_ok = False

    # Also copy the sot-latest pointer
    if raw_log_csv:
        if not copy_to_destination(sot_dir / "sot-latest-MHH.csv", gold_sot_dir, "sot-latest-MHH.csv"):
            gold_ok = False
        if not copy_to_destination(sot_dir / "sot-latest-MHH.csv", obsidian_sot_dir, "sot-latest-MHH.csv"):
            obsidian_ok = False

    # -- Summary --
    print()
    print("  SUMMARY:")
    print(f"    Worksheets exported: {len(exported_files)}")
    print(f"    SOT folder:         OK {sot_dir}")
    if gold_ok:
        print(f"    Gold vault copy:    OK {gold_sot_dir}")
    else:
        print(f"    Gold vault copy:    WARNING Some files failed (drive may not be mounted)")
    if obsidian_ok:
        print(f"    Obsidian copy:      OK {obsidian_sot_dir}")
    else:
        print(f"    Obsidian copy:      WARNING Some files failed (vault path may differ on this machine)")
    print()
    print("=" * 60)


# -- Import test (for run_tests.py) ------------------------------------------

def run_import_test() -> bool:
    """Ensure dependencies are installed (safe for run_tests.py)."""
    print()
    print("=" * 60)
    print("  SNAPSHOT - IMPORT TEST")
    print("=" * 60)
    try:
        import gspread  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from google.auth.transport.requests import Request  # noqa: F401
        import csv  # noqa: F401
        import shutil  # noqa: F401
    except ImportError as e:
        print(f"  FAIL: Missing dependency: {e}")
        print("  Install: pip install -r requirements.txt")
        return False
    print()
    print("  OK: gspread, google-auth, google-auth-oauthlib, csv, shutil import.")
    print()
    print("=" * 60)
    return True


# -- CLI entry point ---------------------------------------------------------

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        sys.exit(0 if run_import_test() else 1)
    elif "--confirm" in args:
        run_snapshot(confirm=True)
    else:
        run_snapshot(confirm=False)
