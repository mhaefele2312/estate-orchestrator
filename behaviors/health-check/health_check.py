"""
Estate OS — Health Check Behavior
===================================
Runs a daily check on your vault and reports anything that needs attention.
Never modifies any files — reports only.

Checks performed:
  1. Vault folder structure — are all required folders present?
  2. Inbox age — are there items sitting unreviewed for more than 48 hours?
  3. Conflict files — did Obsidian Sync create any duplicate/conflict files?
  4. Gold boundary — are there any Gold-classified files inside the Obsidian vault?
  5. Orchestrator logs — when did each behavior last run?

USAGE:
  python health_check.py --test     Run against fake test structure (safe)
  python health_check.py            Run against your real vault (reports only, nothing changes)

NOTE: This script never moves, edits, or deletes files. It only reads and reports.
"""

import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path


# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    """Load paths and settings from config.json."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("ERROR: config.json not found next to health_check.py")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Check 1: Vault folder structure ──────────────────────────────────────────

def check_vault_structure(vault_path, required_folders):
    """
    Verify all required vault folders exist.
    Returns (passed, list of missing folders).
    """
    missing = []
    for folder in required_folders:
        if not (vault_path / folder).exists():
            missing.append(folder)
    return len(missing) == 0, missing


# ── Check 2: Stale inbox items ────────────────────────────────────────────────

def check_stale_inbox(vault_path, stale_hours):
    """
    Find Inbox files that have been sitting unreviewed longer than stale_hours.
    Returns (all_fresh, list of stale filenames with age in hours).
    """
    inbox_path = vault_path / "Inbox"
    if not inbox_path.exists():
        return True, []

    now = datetime.now()
    stale = []
    for f in inbox_path.glob("*.md"):
        age = now - datetime.fromtimestamp(f.stat().st_mtime)
        if age > timedelta(hours=stale_hours):
            hours_old = int(age.total_seconds() / 3600)
            stale.append(f"{f.name} ({hours_old} hours old)")

    return len(stale) == 0, stale


# ── Check 3: Obsidian conflict files ──────────────────────────────────────────

def check_conflict_files(vault_path):
    """
    Look for Obsidian Sync conflict files anywhere in the vault.
    Conflict files are created when the same file is edited on two
    devices before sync completes. They appear as duplicate files
    with a number suffix, e.g. 'my-note 1.md' or 'my-note (conflict).md'.
    Returns (no_conflicts, list of conflict file paths).
    """
    conflicts = []
    patterns = [
        re.compile(r'.+ \d+\.md$'),
        re.compile(r'.+\(conflict\).+\.md$', re.IGNORECASE),
        re.compile(r'.+\(conflicted copy\).+\.md$', re.IGNORECASE),
    ]
    for f in vault_path.rglob("*.md"):
        for pattern in patterns:
            if pattern.match(f.name):
                conflicts.append(str(f.relative_to(vault_path)))
                break

    return len(conflicts) == 0, conflicts


# ── Check 4: Gold boundary ────────────────────────────────────────────────────

def check_gold_boundary(vault_path, gold_markers):
    """
    Scan all .md files in the Obsidian vault for Gold classification markers.
    Gold content must NEVER appear in the Obsidian vault — it belongs only
    in the Cryptomator-encrypted Gold vault.
    Returns (boundary_clean, list of files that contain Gold markers).
    """
    violations = []
    for f in vault_path.rglob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for marker in gold_markers:
                if marker.lower() in content.lower():
                    violations.append(str(f.relative_to(vault_path)))
                    break
        except Exception:
            pass

    return len(violations) == 0, violations


# ── Check 5: Orchestrator log currency ───────────────────────────────────────

def check_log_currency(log_path):
    """
    Report when each behavior last ran by reading log filenames.
    Logs are named: behavior_MODE_YYYYMMDD_HHMMSS.log
    Returns a dict of behavior -> last run info.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        return {}

    behaviors = ["gate", "publish", "health_check", "backup_check", "digest"]
    last_runs = {}

    for behavior in behaviors:
        logs = sorted(log_path.glob(f"{behavior}_*.log"), reverse=True)
        live_logs = [l for l in logs if "TEST" not in l.name and "DRY" not in l.name]
        if live_logs:
            # Parse timestamp from filename
            parts = live_logs[0].stem.split("_")
            if len(parts) >= 3:
                try:
                    date_str = parts[-2]
                    time_str = parts[-1]
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    days_ago = (datetime.now() - dt).days
                    last_runs[behavior] = f"{dt.strftime('%Y-%m-%d')} ({days_ago} days ago)"
                except Exception:
                    last_runs[behavior] = f"log found: {live_logs[0].name}"
        else:
            last_runs[behavior] = "never run live"

    return last_runs


# ── Write session note ────────────────────────────────────────────────────────

def write_session_note(log_path, report_lines):
    """
    Write a timestamped session note to the logs folder.
    This is a plain-text record of what the health check found.
    """
    log_path = Path(log_path)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    note_path = log_path / f"health_check_{timestamp}.log"
    note_path.write_text("\n".join(report_lines), encoding="utf-8")
    return note_path


# ── Print section ─────────────────────────────────────────────────────────────

def section(title, passed, items=None, ok_message="OK"):
    """Print a formatted check section."""
    status = "OK" if passed else "ATTENTION NEEDED"
    icon = "[OK]" if passed else "[!!]"
    print(f"  {icon} {title}: {status}")
    if not passed and items:
        for item in items:
            print(f"       - {item}")
    elif passed:
        print(f"       {ok_message}")
    print()


# ── Main health check ─────────────────────────────────────────────────────────

def run_health_check(test_mode=False):
    """
    Run all health checks and print a plain-English report.
    Write a timestamped log regardless of results.
    Never modifies vault files.
    """
    config = load_config()
    log_path = Path(__file__).parent.parent.parent / "logs"

    if test_mode:
        # Use the orchestrator folder itself as a stand-in vault for testing
        vault_path = Path(__file__).parent.parent.parent
        print()
        print("=" * 60)
        print("  HEALTH CHECK — TEST MODE")
        print("  Checking orchestrator folder structure (not real vault).")
        print("=" * 60)
    else:
        vault_path = Path(config["vault_path"])
        if "PLACEHOLDER" in str(vault_path):
            print()
            print("ERROR: Vault path not configured yet.")
            print("Open behaviors/health-check/config.json and set vault_path")
            print("to your Obsidian vault root folder.")
            print()
            print("To test the script now: python health_check.py --test")
            sys.exit(1)

        if not vault_path.exists():
            print(f"ERROR: Vault path does not exist: {vault_path}")
            sys.exit(1)

        print()
        print("=" * 60)
        print(f"  HEALTH CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

    print()
    report_lines = [
        f"Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {'TEST' if test_mode else 'LIVE'}",
        f"Vault: {vault_path}",
        "",
    ]

    all_clear = True

    # ── Check 1: Vault structure ──
    if test_mode:
        # In test mode check for orchestrator folders instead
        test_required = ["behaviors", "tests", "logs"]
        passed, missing = check_vault_structure(vault_path, test_required)
    else:
        passed, missing = check_vault_structure(
            vault_path, config["required_vault_folders"]
        )

    section(
        "Vault folder structure",
        passed,
        [f"Missing: {f}" for f in missing],
        "All required folders present"
    )
    report_lines.append(f"Folder structure: {'OK' if passed else 'MISSING: ' + ', '.join(missing)}")
    if not passed:
        all_clear = False

    # ── Check 2: Stale inbox ──
    passed, stale = check_stale_inbox(
        vault_path, config["stale_inbox_hours"]
    )
    section(
        f"Inbox items (stale = over {config['stale_inbox_hours']} hours)",
        passed,
        stale,
        "Inbox is clear or all items are recent"
    )
    report_lines.append(f"Stale inbox: {'OK' if passed else str(len(stale)) + ' stale items'}")
    if not passed:
        all_clear = False

    # ── Check 3: Conflict files ──
    passed, conflicts = check_conflict_files(vault_path)
    section(
        "Obsidian sync conflict files",
        passed,
        conflicts,
        "No conflict files found"
    )
    report_lines.append(f"Conflict files: {'OK' if passed else str(len(conflicts)) + ' conflicts found'}")
    if not passed:
        all_clear = False

    # ── Check 4: Gold boundary (skip in test mode) ──
    if not test_mode:
        passed, violations = check_gold_boundary(
            vault_path, config["gold_classification_markers"]
        )
        section(
            "Gold boundary (Gold content must NOT be in Obsidian vault)",
            passed,
            [f"VIOLATION: {v}" for v in violations],
            "No Gold content found in Obsidian vault"
        )
        report_lines.append(f"Gold boundary: {'OK' if passed else 'VIOLATIONS: ' + str(len(violations))}")
        if not passed:
            all_clear = False

    # ── Check 5: Log currency ──
    last_runs = check_log_currency(log_path)
    if last_runs:
        print("  Last live run of each behavior:")
        for behavior, when in last_runs.items():
            print(f"       {behavior}: {when}")
        print()
        report_lines.append("Behavior log currency:")
        for behavior, when in last_runs.items():
            report_lines.append(f"  {behavior}: {when}")

    # ── Overall result ──
    print("=" * 60)
    if all_clear:
        print("  OVERALL: All clear. No action needed.")
    else:
        print("  OVERALL: Attention needed. See items marked [!!] above.")
    print("=" * 60)

    report_lines.append("")
    report_lines.append(f"Overall: {'All clear' if all_clear else 'Attention needed'}")

    note_path = write_session_note(log_path, report_lines)
    print(f"  Session note saved: {note_path.name}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        run_health_check(test_mode=True)
    else:
        run_health_check(test_mode=False)
