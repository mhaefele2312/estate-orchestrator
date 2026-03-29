"""
Estate OS — Gate Behavior
=========================
Moves files from Inbox/ to Accepted/ after your explicit approval.
Stamps each approved file with required provenance information.

USAGE:
  python gate.py --test       Run against fake test files (safe, nothing real touched)
  python gate.py --dry-run    Show what would happen with your real vault (nothing moves)
  python gate.py --confirm    Actually run against your real vault (moves files)

RULES:
  - Default mode is --dry-run. You must type --confirm to make real changes.
  - Nothing moves without your explicit approval of each item.
  - If anything looks wrong, type 's' to skip that item.
  - All actions are logged automatically.
"""

import sys
import os
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    """Load paths and settings from config.json next to this script."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("ERROR: config.json not found. It should be in the same folder as gate.py.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Parse frontmatter ─────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """
    Extract YAML frontmatter from a markdown file.
    Returns (frontmatter_dict, body_text).
    Frontmatter is the section between the first two --- lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, text

    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:]).strip()
    fm = {}
    for line in fm_lines:
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def build_frontmatter(fm_dict):
    """Convert a dict back to YAML frontmatter string."""
    lines = ["---"]
    for key, val in fm_dict.items():
        lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


# ── Display item ──────────────────────────────────────────────────────────────

def display_item(filepath, index, total):
    """Show the operator what is in this inbox item, in plain English."""
    print()
    print("=" * 60)
    print(f"  ITEM {index} OF {total}")
    print(f"  FILE: {filepath.name}")
    print("=" * 60)

    try:
        text = filepath.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)

        if fm:
            print()
            print("  FRONTMATTER (existing info in file):")
            for key, val in fm.items():
                print(f"    {key}: {val}")

        print()
        print("  CONTENT:")
        # Show first 400 characters of body to give operator a sense of it
        preview = body[:400] if len(body) > 400 else body
        for line in preview.splitlines():
            print(f"    {line}")
        if len(body) > 400:
            print(f"    ... [{len(body) - 400} more characters]")

    except Exception as e:
        print(f"  ERROR reading file: {e}")

    print()


# ── Collect provenance fields ─────────────────────────────────────────────────

def ask_provenance(filepath, config):
    """
    Ask the operator for required provenance fields.
    Some fields are filled automatically. Others require operator input.
    """
    fm, body = parse_frontmatter(filepath.read_text(encoding="utf-8"))

    # Auto-filled fields
    now = datetime.now()
    provenance = {
        "review_timestamp": now.strftime("%Y-%m-%dT%H:%M"),
        "reviewer": config.get("reviewer", "MH"),
        "derivation_path": f"Inbox/{filepath.name}",
    }

    # Source — use existing or ask
    existing_source = fm.get("source", "").strip()
    if existing_source:
        print(f"  Source (from file): {existing_source}")
        provenance["source"] = existing_source
    else:
        print("  Who or what is the source of this capture?")
        print("  Examples: MH, HBS, Gemini-capture, email, manual")
        source = input("  source > ").strip()
        provenance["source"] = source if source else "MH"

    # Captured date — use existing or use today
    existing_date = fm.get("captured_date", "").strip()
    if existing_date:
        print(f"  Captured date (from file): {existing_date}")
        provenance["captured_date"] = existing_date
    else:
        today = now.strftime("%Y-%m-%d")
        print(f"  Captured date (press Enter to use today: {today})")
        cap_date = input("  captured_date > ").strip()
        provenance["captured_date"] = cap_date if cap_date else today

    # Visibility
    print()
    print("  Visibility — who can see this?")
    print("  1 = Family   (visible to all family members)")
    print("  2 = MHH      (visible to Marty only)")
    print("  3 = MHH_only (fully restricted, sensitive)")
    vis_choice = input("  choice [1/2/3, default=1] > ").strip()
    vis_map = {"1": "Family", "2": "MHH", "3": "MHH_only", "": "Family"}
    provenance["visibility"] = vis_map.get(vis_choice, "Family")
    print(f"  → visibility: {provenance['visibility']}")

    # Classification
    print()
    print("  Classification — what type of content is this?")
    print("  1=taxes  2=insurance  3=property  4=legal  5=medical  6=general")
    cls_choice = input("  choice [1-6, default=6] > ").strip()
    cls_map = {
        "1": "taxes", "2": "insurance", "3": "property",
        "4": "legal", "5": "medical", "6": "general", "": "general"
    }
    provenance["classification"] = cls_map.get(cls_choice, "general")
    print(f"  → classification: {provenance['classification']}")

    return provenance, fm, body


# ── Write accepted file ───────────────────────────────────────────────────────

def write_accepted_file(source_path, accepted_dir, provenance, existing_fm, body, dry_run):
    """
    Write the file to Accepted/ with full provenance frontmatter.
    In dry-run mode, shows what would happen but writes nothing.
    """
    # Merge existing frontmatter with new provenance (provenance wins on conflicts)
    merged = {**existing_fm, **provenance}

    new_content = build_frontmatter(merged) + "\n\n" + body
    dest_path = accepted_dir / source_path.name

    if dry_run:
        print(f"  DRY RUN: Would write provenance frontmatter to file")
        print(f"  DRY RUN: Would move {source_path.name} → Accepted/{source_path.name}")
        print(f"  DRY RUN: Provenance that would be stamped:")
        for key, val in provenance.items():
            print(f"    {key}: {val}")
    else:
        # Write new content to destination
        accepted_dir.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(new_content, encoding="utf-8")
        # Remove source file
        source_path.unlink()
        print(f"  ACTION: Stamped provenance frontmatter")
        print(f"  ACTION: Moved {source_path.name} → Accepted/{source_path.name}")

    return dest_path


# ── Log run ───────────────────────────────────────────────────────────────────

def write_log(log_dir, results, dry_run, test_mode):
    """Write a timestamped log of this gate run."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    mode = "TEST" if test_mode else ("DRY-RUN" if dry_run else "LIVE")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"gate_{mode}_{timestamp}.log"

    lines = [
        f"Gate run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {mode}",
        f"Items reviewed: {results['reviewed']}",
        f"Approved: {results['approved']}",
        f"Rejected/Skipped: {results['skipped']}",
        "",
        "Detail:",
    ]
    for item in results["items"]:
        lines.append(f"  {item['decision'].upper()}: {item['file']}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Log saved: {log_path.name}")


# ── Main gate function ────────────────────────────────────────────────────────

def run_gate(dry_run=True, test_mode=False):
    """
    Main gate function.
    Scans inbox, shows each item, asks for approval,
    stamps provenance, and moves approved items to Accepted.
    """
    config = load_config()

    # Choose paths based on mode
    if test_mode:
        inbox_path = Path(__file__).parent.parent.parent / "tests" / "fake-inbox"
        accepted_path = Path(__file__).parent.parent.parent / "tests" / "fake-accepted"
        log_path = Path(__file__).parent.parent.parent / "logs"
        print()
        print("=" * 60)
        print("  GATE — TEST MODE")
        print("  Running against fake test files. Your real vault is untouched.")
        print("=" * 60)
    else:
        inbox_path = Path(config["inbox_path"])
        accepted_path = Path(config["accepted_path"])
        log_path = Path(__file__).parent.parent.parent / "logs"

        if "PLACEHOLDER" in str(inbox_path):
            print()
            print("ERROR: Vault paths are not configured yet.")
            print("Open behaviors/gate/config.json and set inbox_path and accepted_path")
            print("to your Obsidian vault folders. Then run again.")
            print()
            print("To run safely against test data first, use: python gate.py --test")
            sys.exit(1)

        if dry_run:
            print()
            print("=" * 60)
            print("  GATE — DRY RUN MODE")
            print("  Showing what would happen. Nothing will move.")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("  GATE — LIVE MODE")
            print("  Files will actually move. This is real.")
            print("=" * 60)

    # Scan inbox
    if not inbox_path.exists():
        print(f"  ERROR: Inbox folder not found at: {inbox_path}")
        print("  Create the folder or check your config.json paths.")
        sys.exit(1)

    inbox_files = sorted(inbox_path.glob("*.md"))

    if not inbox_files:
        print()
        print("  Inbox is empty. Nothing to review.")
        print("  DONE: 0 items reviewed.")
        return

    print()
    print(f"  Found {len(inbox_files)} item(s) in Inbox.")
    print()

    results = {"reviewed": 0, "approved": 0, "skipped": 0, "items": []}

    for i, filepath in enumerate(inbox_files, start=1):
        display_item(filepath, i, len(inbox_files))

        print("  What do you want to do with this item?")
        print("  a = Approve and move to Accepted")
        print("  r = Reject (leave in Inbox, mark as rejected)")
        print("  s = Skip for now (leave in Inbox, decide later)")
        print()
        decision = input("  Your choice [a/r/s] > ").strip().lower()

        results["reviewed"] += 1

        if decision == "a":
            print()
            print("  --- Provenance fields ---")
            provenance, existing_fm, body = ask_provenance(filepath, config)
            write_accepted_file(
                filepath, accepted_path, provenance,
                existing_fm, body, dry_run=(dry_run and not test_mode)
            )
            results["approved"] += 1
            results["items"].append({"file": filepath.name, "decision": "approved"})
            print(f"  APPROVED: {filepath.name}")

        elif decision == "r":
            print(f"  DRY RUN: Would mark as rejected — {filepath.name}" if dry_run else f"  ACTION: Marked as rejected — {filepath.name}")
            results["skipped"] += 1
            results["items"].append({"file": filepath.name, "decision": "rejected"})

        else:
            print(f"  Skipped: {filepath.name}")
            results["skipped"] += 1
            results["items"].append({"file": filepath.name, "decision": "skipped"})

        print()

    # Summary
    print("=" * 60)
    print(f"  DONE: Reviewed {results['reviewed']} item(s)")
    print(f"        Approved: {results['approved']}")
    print(f"        Skipped/Rejected: {results['skipped']}")
    print("=" * 60)

    write_log(log_path, results, dry_run, test_mode)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        run_gate(dry_run=True, test_mode=True)
    elif "--confirm" in args:
        print()
        confirm = input("You are about to run the LIVE gate against your real vault. Type YES to continue: ")
        if confirm.strip() == "YES":
            run_gate(dry_run=False, test_mode=False)
        else:
            print("Cancelled. Nothing changed.")
    elif "--dry-run" in args or len(args) == 0:
        run_gate(dry_run=True, test_mode=False)
    else:
        print()
        print("Usage:")
        print("  python gate.py --test      Safe: run against fake test files")
        print("  python gate.py --dry-run   Show what would happen (real vault, no changes)")
        print("  python gate.py --confirm   Actually run against real vault")
