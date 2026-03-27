"""
Estate OS — Backup Check Behavior
====================================
Reports the current state of your Gold vault backup.
Never performs a backup. Reports only — you act on the report.

Checks performed:
  1. Gold backup folder exists and is reachable
  2. When the backup was last updated
  3. How many files are in the backup
  4. Whether the backup is overdue (configurable threshold)

USAGE:
  python backup_check.py --test     Run in test mode (checks orchestrator folder as stand-in)
  python backup_check.py            Run against your real Gold backup path

NOTE: This script never copies, moves, or modifies files. Reports only.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path


# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    """Load paths and settings from config.json."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("ERROR: config.json not found next to backup_check.py")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Check backup folder ───────────────────────────────────────────────────────

def check_backup_folder(backup_path, warning_hours):
    """
    Check the Gold backup folder.
    Returns a dict with:
      - exists: bool
      - file_count: int
      - last_modified: datetime or None
      - age_hours: float or None
      - is_overdue: bool
      - status: plain-English status string
    """
    result = {
        "exists": False,
        "file_count": 0,
        "last_modified": None,
        "age_hours": None,
        "is_overdue": False,
        "status": "unknown",
    }

    backup_path = Path(backup_path)

    if not backup_path.exists():
        result["status"] = "FOLDER NOT FOUND — backup path does not exist on this machine"
        return result

    result["exists"] = True

    # Count all files recursively
    all_files = list(backup_path.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]
    result["file_count"] = len(files_only)

    if not files_only:
        result["status"] = "FOLDER EXISTS BUT IS EMPTY — no backup files found"
        result["is_overdue"] = True
        return result

    # Find most recently modified file
    most_recent = max(files_only, key=lambda f: f.stat().st_mtime)
    last_mod = datetime.fromtimestamp(most_recent.stat().st_mtime)
    result["last_modified"] = last_mod

    now = datetime.now()
    age = now - last_mod
    result["age_hours"] = age.total_seconds() / 3600
    result["is_overdue"] = age > timedelta(hours=warning_hours)

    if result["is_overdue"]:
        days = int(age.days)
        result["status"] = f"OVERDUE — last backup was {days} day(s) ago"
    else:
        hours = int(result["age_hours"])
        result["status"] = f"OK — last backup was {hours} hour(s) ago"

    return result


# ── Write log ─────────────────────────────────────────────────────────────────

def write_log(log_path, check_result, test_mode):
    """Write a timestamped log of this backup check."""
    log_path = Path(log_path)
    log_path.mkdir(parents=True, exist_ok=True)

    mode = "TEST" if test_mode else "LIVE"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"backup_check_{mode}_{timestamp}.log"

    lines = [
        f"Backup Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {mode}",
        f"Folder exists: {check_result['exists']}",
        f"File count: {check_result['file_count']}",
        f"Last modified: {check_result['last_modified']}",
        f"Age (hours): {check_result['age_hours']:.1f}" if check_result["age_hours"] else "Age: unknown",
        f"Overdue: {check_result['is_overdue']}",
        f"Status: {check_result['status']}",
    ]

    log_file.write_text("\n".join(lines), encoding="utf-8")
    return log_file


# ── Main backup check ─────────────────────────────────────────────────────────

def run_backup_check(test_mode=False):
    """
    Main backup check function.
    Reads the Gold backup folder and reports its state.
    Never modifies any files.
    """
    config = load_config()
    log_path = Path(__file__).parent.parent.parent / "logs"

    if test_mode:
        # Use the logs folder as a stand-in for the backup folder
        backup_path = Path(__file__).parent.parent.parent / "logs"
        warning_hours = config["warning_after_hours"]
        print()
        print("=" * 60)
        print("  BACKUP CHECK — TEST MODE")
        print("  Checking logs folder as stand-in for Gold backup.")
        print("=" * 60)
    else:
        backup_path = Path(config["gold_backup_path"])
        warning_hours = config["warning_after_hours"]

        if "PLACEHOLDER" in str(backup_path):
            print()
            print("ERROR: Gold backup path not configured yet.")
            print("Steps to configure:")
            print("  1. Set up Google Drive on your laptop (estate account)")
            print("  2. Set up Cryptomator vault syncing to Google Drive Gold-Backup/ folder")
            print("  3. Open behaviors/backup-check/config.json")
            print("  4. Set gold_backup_path to that Gold-Backup/ folder path")
            print()
            print("To test the script now: python backup_check.py --test")
            sys.exit(1)

        print()
        print("=" * 60)
        print(f"  BACKUP CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

    print()
    print(f"  Checking: {backup_path}")
    print()

    result = check_backup_folder(backup_path, warning_hours)

    # Print results
    if not result["exists"]:
        print(f"  [!!] FOLDER NOT FOUND")
        print(f"       Path checked: {backup_path}")
        print(f"       This may mean Google Drive is not synced or the path is wrong.")
    else:
        print(f"  Files in backup: {result['file_count']}")

        if result["last_modified"]:
            print(f"  Last updated:    {result['last_modified'].strftime('%Y-%m-%d %H:%M')}")
            print(f"  Age:             {result['age_hours']:.1f} hours")
        else:
            print(f"  Last updated:    unknown (no files found)")

        print()
        if result["is_overdue"]:
            print(f"  [!!] STATUS: {result['status']}")
            print(f"       Action needed: Run your Cryptomator backup now.")
            print(f"       Threshold: alert after {warning_hours} hours ({warning_hours // 24} days)")
        else:
            print(f"  [OK] STATUS: {result['status']}")

    print()
    print("=" * 60)
    print("  NOTE: This script reports only. It does not perform backups.")
    print("  To back up: open Cryptomator, ensure vault is syncing to Google Drive.")
    print("=" * 60)

    log_file = write_log(log_path, result, test_mode)
    print(f"  Log saved: {log_file.name}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        run_backup_check(test_mode=True)
    else:
        run_backup_check(test_mode=False)
