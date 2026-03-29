"""
Estate OS — Reconciliation Script (Phase 1, Item 6)
====================================================
Reads the MHH-Ops-Ledger Google Sheet, finds rows where status has been
changed to "done" by the user, and appends completion entries to the
flat log files (completed.md and master-log.md).

Run this weekly BEFORE running snapshot.py so that the flat logs reflect
the latest status edits before the source-of-truth snapshot is taken.

USAGE:
  python reconciliation.py
        Dry-run. Shows what completions would be recorded. No writes.

  python reconciliation.py --confirm
        Live run. Appends completions to flat log files.

  python reconciliation.py --test
        Import check only. No files needed.

REQUIRES:
  - behaviors/ops-ledger/config.json with spreadsheet_id, logs_dir

NON-NEGOTIABLE RULES (from CLAUDE.md):
  - Default is dry-run. --confirm required for real writes.
  - This script READS from Google Sheet and APPENDS to flat log files.
  - No LLM involvement. Pure Python read + append.
  - Flat log files are append-only. Nothing is ever deleted.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# ── Sheet column indices (0-based, matching the 18-column schema) ──────────
COL_ENTRY_DATE   = 0
COL_ENTRY_TIME   = 1
COL_CAPTURE_MODE = 2
COL_ITEM_TYPE    = 3
COL_DOMAIN       = 4
COL_DESCRIPTION  = 5
COL_RESPONSIBLE  = 6
COL_DUE_DATE     = 7
COL_STATUS       = 8
COL_NOTES        = 9
COL_SOURCE       = 10
COL_CAPTURED_BY  = 11


# ── Config loading (reuses ops-ledger config.json) ─────────────────────────

def _ops_ledger_dir() -> Path:
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


# ── Google Sheets auth (same pattern as other scripts) ──────────────────────

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


# ── Reconciliation logic ───────────────────────────────────────────────────

def load_already_reconciled(completed_path: Path) -> set:
    """Read completed.md and extract descriptions already recorded,
    so we don't double-append the same completion."""
    seen = set()
    if not completed_path.exists():
        return seen

    with open(completed_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("- "):
                continue
            # Lines look like: "- 2026-03-29 | done | 12_Operations | Call plumber about leak"
            # Extract description as a dedup key
            parts = [p.strip() for p in line[2:].split("|")]
            if len(parts) >= 4:
                # key = date + description (to handle same desc on different dates)
                seen.add(f"{parts[0]}|{parts[3]}")

    return seen


def find_completed_rows(worksheet) -> list[dict]:
    """Read all rows from the Raw Log tab and return those with status='done'."""
    all_rows = worksheet.get_all_values()
    completed = []

    for i, row in enumerate(all_rows):
        if i == 0:  # skip header
            continue
        if len(row) <= COL_STATUS:
            continue

        status = (row[COL_STATUS] or "").strip().lower()
        if status != "done":
            continue

        completed.append({
            "row_num": i + 1,
            "entry_date": (row[COL_ENTRY_DATE] or "").strip(),
            "entry_time": (row[COL_ENTRY_TIME] or "").strip(),
            "item_type": (row[COL_ITEM_TYPE] or "").strip(),
            "domain": (row[COL_DOMAIN] or "").strip(),
            "description": (row[COL_DESCRIPTION] or "").strip(),
            "responsible": (row[COL_RESPONSIBLE] or "").strip(),
            "due_date": (row[COL_DUE_DATE] or "").strip(),
            "notes": (row[COL_NOTES] or "").strip(),
            "source_capture": (row[COL_SOURCE] or "").strip() if len(row) > COL_SOURCE else "",
        })

    return completed


def reconcile(confirm: bool):
    config = load_config()
    base = _ops_ledger_dir()

    sheet_id = (config.get("spreadsheet_id") or "").strip()
    if not sheet_id or sheet_id == "YOUR_GOOGLE_SHEET_ID":
        print("ERROR: Set spreadsheet_id in config.json.")
        sys.exit(1)

    logs_dir = Path(config.get("logs_dir", r"G:\My Drive\Estate Ops\Logs"))
    cred_path = _resolve_path(base, config.get("credentials_path", "credentials.json"))
    token_path = _resolve_path(base, config.get("token_path", "token.json"))

    today = datetime.now().strftime("%Y-%m-%d")
    mode_label = "LIVE RUN" if confirm else "DRY RUN"

    print()
    print("=" * 60)
    print(f"  RECONCILIATION ({mode_label})")
    print("=" * 60)
    print()
    print(f"  Date:           {today}")
    print(f"  Spreadsheet ID: {sheet_id}")
    print(f"  Logs dir:       {logs_dir}")
    print()

    if not confirm:
        print("  DRY RUN: Would connect to Google Sheets, find rows marked 'done',")
        print("  and append completion entries to completed.md and master-log.md.")
        print()
        print("  To run for real:  python reconciliation.py --confirm")
        print()
        print("=" * 60)
        return

    # ── Connect and read ──
    import gspread

    print("  Connecting to Google Sheets...")
    creds = _get_credentials(cred_path, token_path)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    # Find the Raw Log tab
    raw_log = None
    for ws in sh.worksheets():
        if ws.title.lower().replace(" ", "") in ("rawlog", "raw-log"):
            raw_log = ws
            break
    if raw_log is None:
        raw_log = sh.sheet1
        print(f"  Note: No 'Raw Log' tab found. Using first tab ({raw_log.title}).")

    print(f"  Reading '{raw_log.title}' tab...")
    completed_rows = find_completed_rows(raw_log)
    print(f"  Found {len(completed_rows)} row(s) with status = 'done'.")

    if not completed_rows:
        print()
        print("  Nothing to reconcile. All clear.")
        print()
        print("=" * 60)
        return

    # ── Dedup against already-recorded completions ──
    logs_dir.mkdir(parents=True, exist_ok=True)
    completed_path = logs_dir / "completed.md"
    already_done = load_already_reconciled(completed_path)

    new_completions = []
    for row in completed_rows:
        key = f"{row['entry_date']}|{row['description']}"
        if key not in already_done:
            new_completions.append(row)

    print(f"  Already reconciled: {len(completed_rows) - len(new_completions)}")
    print(f"  New completions:    {len(new_completions)}")
    print()

    if not new_completions:
        print("  All completed items already in flat logs. Nothing new to append.")
        print()
        print("=" * 60)
        return

    # ── Append to completed.md and master-log.md ──
    completed_lines = []
    master_lines = []

    for row in new_completions:
        entry_date = row["entry_date"]
        item_type  = row["item_type"]
        domain     = row["domain"]
        desc       = row["description"]
        responsible = row["responsible"]
        notes      = row["notes"]

        completed_line = (
            f"- {entry_date} | done | {domain} | {desc}"
            + (f" | {responsible}" if responsible else "")
            + (f" | {notes}" if notes else "")
        )
        completed_lines.append(completed_line)

        master_line = (
            f"- {today} | reconciled | {item_type} | {domain} | {desc}"
            + (f" | originally: {entry_date}" if entry_date else "")
        )
        master_lines.append(master_line)

        print(f"  APPEND: {desc[:60]}...")

    # Write completed.md
    with open(completed_path, "a", encoding="utf-8") as f:
        f.write("\n".join(completed_lines) + "\n")
    print(f"\n  LOG: Appended {len(completed_lines)} line(s) to completed.md")

    # Write master-log.md
    master_log = logs_dir / "master-log.md"
    with open(master_log, "a", encoding="utf-8") as f:
        f.write("\n".join(master_lines) + "\n")
    print(f"  LOG: Appended {len(master_lines)} reconciliation entry/entries to master-log.md")

    print()
    print("  SUMMARY:")
    print(f"    Completions recorded: {len(new_completions)}")
    print(f"    completed.md updated: {completed_path}")
    print(f"    master-log.md updated: {master_log}")
    print()
    print("=" * 60)


# ── Import test (for run_tests.py) ──────────────────────────────────────────

def run_import_test() -> bool:
    print()
    print("=" * 60)
    print("  RECONCILIATION - IMPORT TEST")
    print("=" * 60)
    try:
        import gspread  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from google.auth.transport.requests import Request  # noqa: F401
    except ImportError as e:
        print(f"  FAIL: Missing dependency: {e}")
        print("  Install: pip install -r requirements.txt")
        return False
    print()
    print("  OK: gspread, google-auth, google-auth-oauthlib import.")
    print()
    print("=" * 60)
    return True


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        sys.exit(0 if run_import_test() else 1)
    elif "--confirm" in args:
        reconcile(confirm=True)
    else:
        reconcile(confirm=False)
