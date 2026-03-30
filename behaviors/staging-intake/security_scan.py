"""
Estate OS -- Security Scan (Phase 3)
======================================
Runs Windows Defender (MpCmdRun.exe) against a source folder before
it is ingested into the staging area. Reports clean/threats found.

Run this BEFORE staging_sorter.py when processing an external drive.

USAGE:
  python security_scan.py --source <path>
        Scan the folder. Reports results. No files moved.

  python security_scan.py --test
        Import and Defender availability check only.

RULES:
  - This script never moves, copies, or deletes files.
  - It only invokes Windows Defender and reports the result.
  - If threats are found, it prints a warning and exits with code 1.
  - If Defender is not found, it warns but does not block (some machines
    use third-party AV -- scan manually and proceed with caution).
"""

import sys
import os
import subprocess
from pathlib import Path

# Windows Defender CLI -- standard install path on Windows 10/11
DEFENDER_PATH = Path(
    r"C:\Program Files\Windows Defender\MpCmdRun.exe"
)


def find_defender() -> Path | None:
    """Return path to MpCmdRun.exe if found, else None."""
    if DEFENDER_PATH.exists():
        return DEFENDER_PATH
    # Try via where command as fallback
    try:
        result = subprocess.run(
            ["where", "MpCmdRun.exe"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return Path(result.stdout.strip().splitlines()[0])
    except Exception:
        pass
    return None


def run_scan(source: Path) -> None:
    """Run Defender scan against source. Exits 1 if threats found."""
    print()
    print("=" * 60)
    print("  SECURITY SCAN")
    print("=" * 60)
    print(f"  Source: {source}")
    print()

    if not source.exists():
        print(f"ERROR: Source not found: {source}")
        sys.exit(1)

    defender = find_defender()
    if not defender:
        print("  WARNING: Windows Defender (MpCmdRun.exe) not found.")
        print("  If you are using third-party antivirus, scan the source")
        print("  manually before proceeding.")
        print()
        print("  Proceeding without automated scan.")
        print("=" * 60)
        return

    print(f"  Scanner: {defender}")
    print("  Scanning... (this may take a few minutes for large folders)")
    print()

    try:
        result = subprocess.run(
            [str(defender), "-Scan", "-ScanType", "3",
             "-File", str(source), "-DisableRemediation"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
    except subprocess.TimeoutExpired:
        print("ERROR: Scan timed out after 10 minutes.")
        print("  The folder may be too large. Consider scanning in smaller batches.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not run Defender: {e}")
        sys.exit(1)

    output = result.stdout + result.stderr

    # Defender exit codes: 0 = clean, 2 = threats found, other = error
    if result.returncode == 0:
        print("  RESULT: Clean -- no threats found.")
        print()
        print("  Safe to proceed with staging_sorter.py --confirm")
    elif result.returncode == 2:
        print("  RESULT: THREATS FOUND")
        print()
        print(output)
        print()
        print("  Do NOT proceed with staging. Quarantine or delete the")
        print("  affected files before re-scanning.")
        print("=" * 60)
        sys.exit(1)
    else:
        print(f"  WARNING: Defender returned exit code {result.returncode}")
        print("  This may indicate a scan error, not necessarily a threat.")
        print()
        if output.strip():
            print(output)

    print("=" * 60)


def run_import_test() -> bool:
    """Check imports and Defender availability."""
    print()
    print("=" * 60)
    print("  SECURITY SCAN - IMPORT TEST")
    print("=" * 60)

    try:
        import subprocess  # noqa
        from pathlib import Path  # noqa
    except ImportError as e:
        print(f"  FAIL: {e}")
        return False

    print()
    print("  OK: Imports successful (stdlib only).")

    defender = find_defender()
    if defender:
        print(f"  OK: Windows Defender found at {defender}")
    else:
        print("  WARNING: Windows Defender (MpCmdRun.exe) not found.")
        print("           Scans will warn but not block. Use third-party AV manually.")

    print()
    print("=" * 60)
    return True


# -- CLI entry point ----------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    if "--test" in arg_lower:
        sys.exit(0 if run_import_test() else 1)

    source_path = None
    if "--source" in arg_lower:
        idx = arg_lower.index("--source")
        if idx + 1 < len(args):
            source_path = Path(args[idx + 1])
        else:
            print("\nERROR: --source requires a path.")
            sys.exit(1)

    if not source_path:
        print()
        print("Usage:")
        print("  python security_scan.py --source <path>")
        print("  python security_scan.py --test")
        sys.exit(1)

    run_scan(source_path)
