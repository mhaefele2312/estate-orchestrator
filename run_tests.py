"""
Estate OS — Run All Tests
==========================
Runs behavior scripts in test mode (and the Ops Ledger import check).
Use this any time you want to verify the system is healthy.
Nothing in your real vault is touched.

USAGE:
  python run_tests.py

Run this from the estate-orchestrator root folder.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

TESTS = [
    ("Ops Ledger (imports)",       ROOT / "behaviors" / "ops-ledger"         / "verify_sheets_auth.py", "--test"),
    ("Capture Pipeline (imports)", ROOT / "behaviors" / "capture-pipeline"   / "capture_pipeline.py",   "--test"),
    ("Snapshot (imports)",         ROOT / "behaviors" / "snapshot"           / "snapshot.py",           "--test"),
    ("Weekly Sync (imports)",      ROOT / "behaviors" / "weekly-sync"        / "weekly_sync.py",        "--test"),
    ("Reconciliation (imports)",   ROOT / "behaviors" / "reconciliation"     / "reconciliation.py",     "--test"),
    ("Gate",         ROOT / "behaviors" / "gate"          / "gate.py",         "--test"),
    ("Publish",      ROOT / "behaviors" / "publish"       / "publish.py",      "--test"),
    ("Health Check", ROOT / "behaviors" / "health-check"  / "health_check.py", "--test"),
    ("Backup Check", ROOT / "behaviors" / "backup-check"  / "backup_check.py", "--test"),
    ("E2E Pipeline (imports)", ROOT / "tests" / "e2e_test.py", "--test"),
    ("Staging Sorter (imports)",  ROOT / "behaviors" / "staging-intake" / "staging_sorter.py",  "--test"),
    ("Security Scan (imports)",   ROOT / "behaviors" / "staging-intake" / "security_scan.py",   "--test"),
    ("Staging Router (imports)",  ROOT / "behaviors" / "staging-intake" / "staging_router.py",  "--test"),
    ("Weekly Review (imports)",   ROOT / "behaviors" / "email-intake"   / "weekly_review.py",   "--test"),
]

def run_test(name, script_path, flag):
    """Run one behavior in test mode and return pass/fail."""
    print()
    print(f"{'=' * 60}")
    print(f"  RUNNING: {name}")
    print(f"{'=' * 60}")

    if not script_path.exists():
        print(f"  ERROR: Script not found at {script_path}")
        return False

    result = subprocess.run(
        [sys.executable, str(script_path), flag],
        capture_output=False,
        text=True,
    )

    return result.returncode == 0


def main():
    print()
    print("=" * 60)
    print("  ESTATE OS — FULL TEST RUN")
    print("  All tests run in safe mode. No real vault files touched.")
    print("=" * 60)

    results = []
    for name, script, flag in TESTS:
        # Gate test is interactive — skip in automated run, note it separately
        if name == "Gate":
            print()
            print(f"{'=' * 60}")
            print(f"  SKIPPING: Gate (interactive — run manually to test)")
            print(f"  Command:  cd behaviors/gate && python gate.py --test")
            print(f"{'=' * 60}")
            results.append((name, "SKIPPED (interactive)"))
            continue

        passed = run_test(name, script, flag)
        results.append((name, "PASS" if passed else "FAIL"))

    # Summary
    print()
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, status in results:
        icon = "[OK]  " if status == "PASS" else ("[--]  " if "SKIP" in status else "[!!]  ")
        print(f"  {icon}{name}: {status}")
        if status == "FAIL":
            all_passed = False

    print()
    if all_passed:
        print("  All automated tests passed.")
        print("  Run gate manually to test the interactive flow.")
    else:
        print("  One or more tests FAILED.")
        print("  Paste the output above into Cowork and ask Claude what to fix.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()