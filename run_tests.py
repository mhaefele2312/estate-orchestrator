"""
Estate OS — Run All Tests
==========================
Runs all four behavior scripts in test mode.
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
    ("Gate",         ROOT / "behaviors" / "gate"          / "gate.py",         "--test"),
    ("Publish",      ROOT / "behaviors" / "publish"       / "publish.py",      "--test"),
    ("Health Check", ROOT / "behaviors" / "health-check"  / "health_check.py", "--test"),
    ("Backup Check", ROOT / "behaviors" / "backup-check"  / "backup_check.py", "--test"),
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
