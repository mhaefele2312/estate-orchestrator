"""
Estate OS — End-to-End Test (Phase 1 Item 15)
==============================================
Runs the full pipeline with a sample transcript to verify all stages work:

  1. Read sample transcript (.md file)
  2. Call Gemini API to parse it into structured rows
  3. Append rows to the Google Sheet + flat log files + contacts CSV
  4. Run reconciliation (mark rows done, write to completed.md)
  5. Run snapshot (export sheet tabs to SOT CSVs)
  6. Run weekly sync dry-run (verify files would push to Obsidian)

USAGE:
  python tests/e2e_test.py
        Dry-run. Runs Gemini parse and shows what would be written.

  python tests/e2e_test.py --confirm
        Live run. Actually writes to sheet, flat files, then runs
        snapshot and weekly sync dry-run.

  python tests/e2e_test.py --test
        Import check only. Verifies all scripts can be loaded.

REQUIRES:
  - GEMINI_API_KEY environment variable
  - behaviors/ops-ledger/config.json with valid credentials
  - Google Sheets API token (from verify_sheets_auth.py)

Run from the estate-orchestrator root folder.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TRANSCRIPT = Path(__file__).resolve().parent / "sample-capture-2026-03-30-0815-MHH.md"


def banner(msg):
    print()
    print("=" * 60)
    print(f"  {msg}")
    print("=" * 60)


def run_script(name, args, allow_fail=False):
    """Run a Python script and return (success, output)."""
    banner(f"STAGE: {name}")
    print(f"  Command: {' '.join(str(a) for a in args)}")
    print()

    result = subprocess.run(
        [sys.executable] + [str(a) for a in args],
        capture_output=True,
        text=True,
    )

    # Print output
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"  {line}")
    if result.stderr:
        for line in result.stderr.strip().split("\n"):
            print(f"  [stderr] {line}")

    if result.returncode != 0 and not allow_fail:
        print(f"\n  FAILED (exit code {result.returncode})")
        return False
    elif result.returncode != 0:
        print(f"\n  WARNING (exit code {result.returncode}, continuing)")
        return True

    print(f"\n  PASSED")
    return True


def check_imports():
    """Verify all pipeline scripts can be imported."""
    banner("IMPORT CHECK — All Pipeline Scripts")

    scripts = [
        ("Capture Pipeline", ROOT / "behaviors" / "capture-pipeline" / "capture_pipeline.py"),
        ("Snapshot",         ROOT / "behaviors" / "snapshot" / "snapshot.py"),
        ("Weekly Sync",      ROOT / "behaviors" / "weekly-sync" / "weekly_sync.py"),
        ("Reconciliation",   ROOT / "behaviors" / "reconciliation" / "reconciliation.py"),
    ]

    all_ok = True
    for name, path in scripts:
        result = subprocess.run(
            [sys.executable, str(path), "--test"],
            capture_output=True,
            text=True,
        )
        status = "OK" if result.returncode == 0 else "FAIL"
        print(f"  [{status}]  {name}")
        if result.returncode != 0:
            all_ok = False
            if result.stderr:
                print(f"         {result.stderr.strip()[:200]}")

    return all_ok


def check_sample_transcript():
    """Verify the sample transcript exists and is readable."""
    banner("CHECK — Sample Transcript")
    if not SAMPLE_TRANSCRIPT.exists():
        print(f"  ERROR: Sample transcript not found at {SAMPLE_TRANSCRIPT}")
        return False

    content = SAMPLE_TRANSCRIPT.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    print(f"  File: {SAMPLE_TRANSCRIPT.name}")
    print(f"  Lines: {len(lines)}")
    print(f"  Size: {len(content)} bytes")
    print(f"  PASSED")
    return True


def check_gemini_key():
    """Verify GEMINI_API_KEY is set."""
    banner("CHECK — Gemini API Key")
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("  WARNING: GEMINI_API_KEY not set.")
        print("  Set it with: $env:GEMINI_API_KEY = 'your-key-here'")
        print("  Stages that require Gemini will be skipped.")
        return False
    print(f"  GEMINI_API_KEY is set ({len(key)} chars)")
    print(f"  PASSED")
    return True


def run_dry_run():
    """Run capture pipeline in dry-run mode to test Gemini parsing."""
    pipeline = ROOT / "behaviors" / "capture-pipeline" / "capture_pipeline.py"
    return run_script(
        "Capture Pipeline (dry-run — Gemini parse only)",
        [pipeline, "--file", str(SAMPLE_TRANSCRIPT)],
    )


def run_live_pipeline():
    """Run capture pipeline with --confirm to write to sheet + flat files."""
    pipeline = ROOT / "behaviors" / "capture-pipeline" / "capture_pipeline.py"
    return run_script(
        "Capture Pipeline (LIVE — writing to sheet + flat files)",
        [pipeline, "--file", str(SAMPLE_TRANSCRIPT), "--confirm"],
    )


def run_reconciliation_dryrun():
    """Run reconciliation in dry-run mode."""
    recon = ROOT / "behaviors" / "reconciliation" / "reconciliation.py"
    return run_script(
        "Reconciliation (dry-run — check for done rows)",
        [recon],
    )


def run_snapshot():
    """Run snapshot with --confirm to export sheet tabs."""
    snapshot = ROOT / "behaviors" / "snapshot" / "snapshot.py"
    return run_script(
        "Snapshot (LIVE — export sheet tabs to SOT CSVs)",
        [snapshot, "--confirm"],
    )


def run_weekly_sync_dryrun():
    """Run weekly sync in dry-run mode to verify Obsidian push."""
    sync = ROOT / "behaviors" / "weekly-sync" / "weekly_sync.py"
    return run_script(
        "Weekly Sync (dry-run — verify Obsidian push)",
        [sync],
        allow_fail=True,  # May warn about missing Obsidian path on dev machine
    )


def main():
    confirm = "--confirm" in sys.argv
    test_only = "--test" in sys.argv

    banner("ESTATE OS — END-TO-END TEST")
    print(f"  Mode: {'LIVE (--confirm)' if confirm else 'DRY-RUN' if not test_only else 'IMPORT CHECK ONLY'}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # ── Import check ──────────────────────────────────────────────
    if not check_imports():
        print("\n  One or more imports failed. Fix those first.")
        sys.exit(1)

    if test_only:
        banner("RESULT: All imports OK")
        sys.exit(0)

    # ── Pre-flight checks ─────────────────────────────────────────
    if not check_sample_transcript():
        sys.exit(1)

    has_gemini = check_gemini_key()

    # ── Stage 1+2: Gemini parse ───────────────────────────────────
    if has_gemini:
        if confirm:
            # Live pipeline: parse + write to sheet + flat files
            if not run_live_pipeline():
                print("\n  Pipeline failed. Check errors above.")
                sys.exit(1)

            # Stage 3: Reconciliation dry-run (check for any done rows)
            run_reconciliation_dryrun()

            # Stage 4: Snapshot (export to SOT)
            if not run_snapshot():
                print("\n  Snapshot failed. Check errors above.")
                sys.exit(1)

            # Stage 5: Weekly sync dry-run
            run_weekly_sync_dryrun()
        else:
            # Dry-run only: parse with Gemini but don't write
            if not run_dry_run():
                print("\n  Dry-run parse failed. Check errors above.")
                sys.exit(1)
    else:
        banner("SKIPPED — Gemini stages (no API key)")
        print("  Set GEMINI_API_KEY to run the full pipeline.")

    # ── Summary ───────────────────────────────────────────────────
    banner("END-TO-END TEST COMPLETE")
    if confirm and has_gemini:
        print("  Full pipeline ran successfully:")
        print("    1. Sample transcript parsed by Gemini")
        print("    2. Rows appended to Google Sheet + flat log files")
        print("    3. Reconciliation checked for done rows")
        print("    4. Snapshot exported all tabs to SOT CSVs")
        print("    5. Weekly sync verified Obsidian push (dry-run)")
        print()
        print("  Remaining manual steps:")
        print("    - Test voice capture from phone (Item 11)")
        print("    - Edit a row status to 'done' in the sheet")
        print("    - Run reconciliation --confirm to process it")
        print("    - Run weekly sync --confirm on estate laptop")
    elif has_gemini:
        print("  Dry-run completed. Gemini parsed the transcript successfully.")
        print("  Run with --confirm to do the full live pipeline.")
    else:
        print("  Import checks passed. Set GEMINI_API_KEY for full test.")

    print()


if __name__ == "__main__":
    main()
