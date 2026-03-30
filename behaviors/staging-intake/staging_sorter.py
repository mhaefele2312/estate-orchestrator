"""
Estate OS -- Staging Sorter (Phase 3)
======================================
Copies files from a source folder (e.g. an external drive) into a dated
staging subfolder on Google Drive, sorted by file type.

After sorting, files sit in:
  G:/My Drive/Staging-Intake/[drive-name-YYYY-MM-DD]/
    documents/    (PDF, DOC, DOCX, TXT, RTF, ODT)
    photos/       (JPG, JPEG, PNG, HEIC, HEIF, GIF, BMP, TIFF, TIF, WEBP)
    video/        (MP4, MOV, AVI, MKV, M4V, WMV, FLV)
    spreadsheets/ (XLSX, XLS, CSV, ODS)
    other/        (everything else)

USAGE:
  python staging_sorter.py --source <path>
        Dry-run. Shows what would be copied and where. No files moved.

  python staging_sorter.py --source <path> --name <label> --confirm
        Live run. Copies files into staging. Originals are never deleted.

  python staging_sorter.py --test
        Import check only. No files needed.

RULES:
  - Default is dry-run. --confirm required for real writes.
  - Originals are NEVER deleted or moved. Only copies are made.
  - Duplicate filenames get a counter suffix (file_1.pdf, file_2.pdf).
  - Subdirectories are recursed -- all files found, regardless of depth.
  - Symlinks are skipped.
  - Hidden files (starting with .) are skipped.
  - The staging folder name is: [--name or source folder name]-YYYY-MM-DD
"""

import sys
import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# -- File type buckets --------------------------------------------------------

BUCKETS = {
    "documents":    {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
                     ".pages", ".md"},
    "photos":       {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif",
                     ".bmp", ".tiff", ".tif", ".webp", ".raw", ".cr2",
                     ".nef", ".arw"},
    "video":        {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv",
                     ".flv", ".3gp", ".webm"},
    "spreadsheets": {".xlsx", ".xls", ".csv", ".ods", ".numbers"},
    "other":        set(),  # catch-all
}


def classify(path: Path) -> str:
    """Return the bucket name for a file based on its extension."""
    ext = path.suffix.lower()
    for bucket, extensions in BUCKETS.items():
        if bucket == "other":
            continue
        if ext in extensions:
            return bucket
    return "other"


def safe_dest(dest_dir: Path, filename: str) -> Path:
    """Return a destination path, adding a counter if the name already exists."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def collect_files(source: Path) -> list[Path]:
    """Recursively collect all non-hidden, non-symlink files under source."""
    files = []
    for p in source.rglob("*"):
        if p.is_symlink():
            continue
        if p.is_file() and not p.name.startswith("."):
            files.append(p)
    return sorted(files)


def load_config() -> dict:
    """Load ops-ledger config.json for staging_dir path."""
    config_path = Path(__file__).resolve().parent.parent / "ops-ledger" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_sort(source: Path, staging_name: str, confirm: bool) -> None:
    """Core sort logic. If confirm=False, prints plan without writing."""
    config = load_config()
    staging_root = Path(config.get("staging_dir",
                                   r"G:\My Drive\Staging-Intake"))
    dest_base = staging_root / staging_name

    mode_label = "LIVE RUN" if confirm else "DRY RUN"
    print()
    print("=" * 60)
    print(f"  STAGING SORTER ({mode_label})")
    print("=" * 60)
    print(f"  Source:     {source}")
    print(f"  Staging:    {dest_base}")
    print()

    files = collect_files(source)
    if not files:
        print("  No files found in source. Nothing to do.")
        print("=" * 60)
        return

    # Tally by bucket for the summary
    counts = {b: 0 for b in BUCKETS}
    plan = []  # list of (src, dest_dir, filename, bucket)

    for f in files:
        bucket = classify(f)
        counts[bucket] += 1
        dest_dir = dest_base / bucket
        plan.append((f, dest_dir, f.name, bucket))

    # Print plan
    print(f"  Files found: {len(files)}")
    for bucket, count in counts.items():
        if count:
            print(f"    {bucket:<14} {count}")
    print()

    if not confirm:
        print("  DRY RUN: No files copied.")
        print("  Run with --confirm to execute.")
        print("=" * 60)
        return

    # Execute
    copied = 0
    skipped = 0
    for src, dest_dir, filename, bucket in plan:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = safe_dest(dest_dir, filename)
        try:
            shutil.copy2(str(src), str(dest))
            print(f"  COPY: {src.name} -> {bucket}/")
            copied += 1
        except Exception as e:
            print(f"  ERROR: {src.name}: {e}")
            skipped += 1

    print()
    print(f"  DONE: {copied} copied, {skipped} errors.")
    print(f"  Staging folder: {dest_base}")
    print("=" * 60)


def run_import_test() -> bool:
    """Ensure all imports work (safe for run_tests.py)."""
    print()
    print("=" * 60)
    print("  STAGING SORTER - IMPORT TEST")
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

    # --source is required
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
        print("  python staging_sorter.py --source <path>")
        print("  python staging_sorter.py --source <path> --name <label> --confirm")
        print("  python staging_sorter.py --test")
        sys.exit(1)

    if not source_path.exists():
        print(f"\nERROR: Source not found: {source_path}")
        sys.exit(1)

    # --name overrides the staging subfolder label
    staging_name = None
    if "--name" in arg_lower:
        idx = arg_lower.index("--name")
        if idx + 1 < len(args):
            staging_name = args[idx + 1]

    if not staging_name:
        today = datetime.now().strftime("%Y-%m-%d")
        staging_name = f"{source_path.name}-{today}"

    run_sort(source_path, staging_name, confirm)
