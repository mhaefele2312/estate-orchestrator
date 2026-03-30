"""
Estate OS -- Staging Router (Phase 3)
=======================================
Lists files in a sorted staging folder and lets you route each one
to its final destination: Gold vault, Obsidian, or skip.

Run AFTER security_scan.py and staging_sorter.py.

USAGE:
  python staging_router.py --staging <path-to-sorted-staging-folder>
        Dry-run. Shows what files are waiting and their suggested routes.

  python staging_router.py --staging <path> --confirm
        Interactive review. For each file you type:
          g  -- route to Gold vault (under a domain subfolder)
          o  -- route to Obsidian vault (under a domain subfolder)
          s  -- skip (leave in staging, decide later)
          d  -- mark as junk/duplicate (moves to staging/_review_delete/)

  python staging_router.py --test
        Import check only.

RULES:
  - Default is dry-run. --confirm required for real routing.
  - Files are COPIED to their destination. Original staging copy kept.
  - Nothing is deleted without your explicit 'd' choice, and even
    then it only moves to a _review_delete/ subfolder for later review.
  - Gold vault: E:\\ (only accessible on estate laptop)
  - Obsidian vault: path from config.json
  - Domain subfolders match the 12 Estate OS domains.
  - Phase 5 will add LLM classification suggestions. For now: manual.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

DOMAINS = [
    "01_Financial",
    "02_Legal",
    "03_Property",
    "04_Insurance",
    "05_Medical",
    "06_Tax",
    "07_Estate-Planning",
    "08_Vehicles",
    "09_Digital",
    "10_Family",
    "11_Contacts",
    "12_Operations",
]

BUCKETS = ["documents", "photos", "video", "spreadsheets", "other"]


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "ops-ledger" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_staged_files(staging_path: Path) -> list[Path]:
    """Return all files in the staging folder, excluding _review_delete."""
    files = []
    for p in staging_path.rglob("*"):
        if p.is_file() and "_review_delete" not in str(p):
            files.append(p)
    return sorted(files)


def pick_domain() -> str | None:
    """Prompt user to pick a domain. Returns domain string or None to go back."""
    print()
    for i, d in enumerate(DOMAINS, 1):
        print(f"    {i:2}. {d}")
    print("     0. Cancel (skip this file)")
    print()
    choice = input("  Domain number: ").strip()
    if choice == "0" or choice == "":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(DOMAINS):
            return DOMAINS[idx]
    except ValueError:
        pass
    print("  Invalid choice.")
    return None


def safe_copy(src: Path, dest_dir: Path) -> Path:
    """Copy src to dest_dir, adding counter suffix if name conflicts."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        stem = src.stem
        suffix = src.suffix
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.copy2(str(src), str(dest))
    return dest


def run_dry_run(staging_path: Path) -> None:
    files = collect_staged_files(staging_path)

    print()
    print("=" * 60)
    print("  STAGING ROUTER (DRY RUN)")
    print("=" * 60)
    print(f"  Staging: {staging_path}")
    print()

    if not files:
        print("  No files waiting for review.")
        print("=" * 60)
        return

    counts = {}
    for f in files:
        bucket = f.parent.name
        counts[bucket] = counts.get(bucket, 0) + 1

    print(f"  Files awaiting routing: {len(files)}")
    for bucket, count in counts.items():
        print(f"    {bucket:<14} {count}")
    print()
    print("  Run with --confirm to start interactive review.")
    print("=" * 60)


def run_confirm(staging_path: Path, config: dict) -> None:
    files = collect_staged_files(staging_path)

    gold_root = Path(config.get("gold_vault_dir", r"E:\\"))
    obsidian_root = Path(config.get("obsidian_vault_dir",
                                    r"C:\Users\mhhro\Documents\Obsidian Vault"))
    review_delete = staging_path / "_review_delete"

    print()
    print("=" * 60)
    print("  STAGING ROUTER (LIVE -- INTERACTIVE REVIEW)")
    print("=" * 60)
    print(f"  Staging:  {staging_path}")
    print(f"  Gold:     {gold_root}")
    print(f"  Obsidian: {obsidian_root}")
    print()

    if not files:
        print("  No files waiting for review.")
        print("=" * 60)
        return

    print(f"  {len(files)} file(s) to review. Commands: g=Gold  o=Obsidian  s=Skip  d=Delete-review")
    print()

    routed_gold = 0
    routed_obsidian = 0
    skipped = 0
    flagged = 0

    for i, f in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {f.parent.name}/{f.name}  ({_size_label(f)})")
        choice = input("  Route [g/o/s/d]: ").strip().lower()

        if choice == "g":
            domain = pick_domain()
            if domain is None:
                print("  Skipped.")
                skipped += 1
                continue
            dest = safe_copy(f, gold_root / domain)
            print(f"  -> Gold: {dest}")
            routed_gold += 1

        elif choice == "o":
            domain = pick_domain()
            if domain is None:
                print("  Skipped.")
                skipped += 1
                continue
            dest = safe_copy(f, obsidian_root / domain)
            print(f"  -> Obsidian: {dest}")
            routed_obsidian += 1

        elif choice == "d":
            review_delete.mkdir(parents=True, exist_ok=True)
            dest = review_delete / f.name
            shutil.move(str(f), str(dest))
            print(f"  -> Flagged for delete review: {dest}")
            flagged += 1

        else:  # s or anything else
            print("  Skipped.")
            skipped += 1

        print()

    print("=" * 60)
    print("  ROUTING COMPLETE")
    print(f"  Routed to Gold:     {routed_gold}")
    print(f"  Routed to Obsidian: {routed_obsidian}")
    print(f"  Skipped:            {skipped}")
    print(f"  Flagged for delete: {flagged}")
    print("=" * 60)


def _size_label(p: Path) -> str:
    """Human-readable file size."""
    try:
        size = p.stat().st_size
        if size < 1024:
            return f"{size}B"
        if size < 1024 ** 2:
            return f"{size // 1024}KB"
        return f"{size // (1024 ** 2)}MB"
    except Exception:
        return "?"


def run_import_test() -> bool:
    print()
    print("=" * 60)
    print("  STAGING ROUTER - IMPORT TEST")
    print("=" * 60)
    try:
        import shutil  # noqa
        import json    # noqa
        from pathlib import Path  # noqa
    except ImportError as e:
        print(f"  FAIL: {e}")
        return False
    print()
    print("  OK: All imports successful (stdlib only).")
    print()
    print("=" * 60)
    return True


# -- CLI entry point ----------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    if "--test" in arg_lower:
        sys.exit(0 if run_import_test() else 1)

    confirm = "--confirm" in arg_lower

    staging_path = None
    if "--staging" in arg_lower:
        idx = arg_lower.index("--staging")
        if idx + 1 < len(args):
            staging_path = Path(args[idx + 1])
        else:
            print("\nERROR: --staging requires a path.")
            sys.exit(1)

    if not staging_path:
        print()
        print("Usage:")
        print("  python staging_router.py --staging <sorted-staging-folder>")
        print("  python staging_router.py --staging <path> --confirm")
        print("  python staging_router.py --test")
        sys.exit(1)

    if not staging_path.exists():
        print(f"\nERROR: Staging folder not found: {staging_path}")
        sys.exit(1)

    config = load_config()

    if confirm:
        run_confirm(staging_path, config)
    else:
        run_dry_run(staging_path)
