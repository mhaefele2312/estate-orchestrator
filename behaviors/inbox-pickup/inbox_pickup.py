"""
inbox-pickup.py
---------------
Moves new capture files from Google Drive inboxes into your Obsidian Vault Inbox.

Sources checked:
  - G:\My Drive\MHH-Inbox\   (your Android captures)
  - G:\My Drive\HBS-Inbox\   (spouse captures, Phase 2)

Destination:
  - C:\Users\mhhro\Documents\Obsidian Vault\Inbox\

Rules:
  - Only moves .md and .txt files
  - Skips files already in the destination
  - Renames conflicts by appending a counter
  - Logs every action
  - NEVER deletes source files until move is confirmed
  - Reports only in dry-run (default). Use --confirm to move files.

Usage:
  python inbox_pickup.py            # dry-run: shows what would move
  python inbox_pickup.py --confirm  # live: moves files
  python inbox_pickup.py --test     # test mode: uses fake folders
"""

import os
import sys
import shutil
import json
import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ── HELPERS ───────────────────────────────────────────────────────────────────

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")

def datestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def safe_dest_path(dest_folder, filename):
    """Return a destination path, adding a counter if the filename already exists."""
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dest_folder, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dest_folder, f"{base}_{counter}{ext}")
        counter += 1
    return candidate

def prepend_frontmatter(filepath, source_label):
    """
    If a .txt file has no YAML frontmatter, prepend basic estate OS frontmatter.
    .md files from the capture app already have frontmatter — leave them alone.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if content.startswith("---"):
        return  # already has frontmatter

    today = datetime.date.today().isoformat()
    frontmatter = (
        f"---\n"
        f"source: {source_label}\n"
        f"captured_date: {today}\n"
        f"visibility: MHH\n"
        f"classification: general\n"
        f"---\n\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)

# ── CORE LOGIC ────────────────────────────────────────────────────────────────

def scan_source(source_path, source_label, dest_path, dry_run, log_lines):
    """Scan one source inbox and move eligible files to dest."""
    moved   = 0
    skipped = 0
    errors  = 0

    if not os.path.isdir(source_path):
        msg = f"  [SKIP] Source not found: {source_path}"
        print(msg)
        log_lines.append(msg)
        return moved, skipped, errors

    files = [
        f for f in os.listdir(source_path)
        if f.lower().endswith((".md", ".txt"))
        and os.path.isfile(os.path.join(source_path, f))
    ]

    if not files:
        msg = f"  [OK]   {source_label}: No new files"
        print(msg)
        log_lines.append(msg)
        return moved, skipped, errors

    for filename in sorted(files):
        src = os.path.join(source_path, filename)
        dst = safe_dest_path(dest_path, filename)
        dest_filename = os.path.basename(dst)

        if dry_run:
            msg = f"  DRY RUN: Would move {filename} → Inbox/{dest_filename}"
            print(msg)
            log_lines.append(msg)
            skipped += 1
        else:
            try:
                # Copy to destination first
                shutil.copy2(src, dst)

                # Add frontmatter if missing (for plain .txt files)
                prepend_frontmatter(dst, source_label)

                # Remove from source only after confirmed copy
                os.remove(src)

                msg = f"  ACTION: Moved {filename} → Inbox/{dest_filename}"
                print(msg)
                log_lines.append(msg)
                moved += 1

            except Exception as e:
                msg = f"  ERROR:  {filename} — {e}"
                print(msg)
                log_lines.append(msg)
                errors += 1

    return moved, skipped, errors

# ── WRITE LOG ─────────────────────────────────────────────────────────────────

def write_log(config, lines, dry_run):
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    mode    = "DRYRUN" if dry_run else "LIVE"
    logfile = os.path.join(log_dir, f"inbox_pickup_{mode}_{datestamp()}.log")
    with open(logfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  Log saved: {os.path.basename(logfile)}")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def run_pickup():
    config   = load_config()
    args     = sys.argv[1:]
    dry_run  = "--confirm" not in args
    test_mode = "--test" in args

    if test_mode:
        sources = config.get("test_sources", [])
        dest    = config.get("test_dest_path", "")
        print("=" * 60)
        print("  INBOX PICKUP — TEST MODE")
        print("  Using fake folders. Real vault untouched.")
        print("=" * 60)
    else:
        sources = config.get("sources", [])
        dest    = config.get("obsidian_inbox_path", "")
        mode_label = "DRY RUN — no files will be moved" if dry_run else "LIVE — files will be moved"
        print("=" * 60)
        print(f"  INBOX PICKUP — {timestamp()}")
        print(f"  {mode_label}")
        print("=" * 60)

    if not os.path.isdir(dest):
        print(f"\n  ERROR: Destination not found: {dest}")
        print("  Check obsidian_inbox_path in config.json")
        sys.exit(1)

    log_lines = [
        f"inbox-pickup {'TEST' if test_mode else 'LIVE' if not dry_run else 'DRYRUN'} {timestamp()}",
        f"destination: {dest}"
    ]

    total_moved   = 0
    total_skipped = 0
    total_errors  = 0

    for source in sources:
        label = source.get("label", "unknown")
        path  = source.get("path", "")
        print(f"\n  Checking: {label}")
        print(f"  Path:     {path}")
        m, s, e = scan_source(path, label, dest, dry_run, log_lines)
        total_moved   += m
        total_skipped += s
        total_errors  += e

    print("\n" + "=" * 60)
    if dry_run and not test_mode:
        print(f"  DRY RUN COMPLETE")
        print(f"  Would move: {total_skipped} file(s)")
        print(f"  Run with --confirm to move files for real.")
    else:
        print(f"  DONE")
        print(f"  Moved:  {total_moved} file(s)")
        print(f"  Errors: {total_errors}")

    print("=" * 60)

    log_lines.append(f"moved={total_moved} errors={total_errors}")
    write_log(config, log_lines, dry_run)

if __name__ == "__main__":
    run_pickup()
