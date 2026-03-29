"""
Estate OS — Weekly Sync to Obsidian (Phase 1, Item 5)
=====================================================
One-way push from Google Drive to Obsidian vault:

  1. Copies all flat log files (Logs/) to Obsidian Ops-Ledger/
  2. Copies latest SOT snapshot to Obsidian Ops-Ledger/Source-of-Truth/
  3. Builds/updates individual contact pages in Obsidian 11_Contacts/
     using marker-based merge (manual content above marker preserved,
     auto-populated mentions below marker rebuilt each sync)

USAGE:
  python weekly_sync.py
        Dry-run. Shows what would be synced. No writes.

  python weekly_sync.py --confirm
        Live run. Copies files and builds contact pages.

  python weekly_sync.py --test
        Import check only. No files needed.

REQUIRES:
  - behaviors/ops-ledger/config.json with obsidian_vault_dir, logs_dir, sot_dir

NON-NEGOTIABLE RULES (from CLAUDE.md):
  - Default is dry-run. --confirm required for real writes.
  - One-way push: Obsidian gets copies. Changes in Obsidian do NOT flow back.
  - No LLM involvement. Pure Python file copy + contact page merge.
  - Contact pages: manual content above <!-- mentions-start --> is NEVER overwritten.
"""

import sys
import os
import json
import shutil
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# ── Config loading (reuses ops-ledger config.json) ─────────────────────────

def _ops_ledger_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "ops-ledger"


def load_config() -> dict:
    config_path = _ops_ledger_dir() / "config.json"
    if not config_path.exists():
        print()
        print("ERROR: config.json not found.")
        print(f"  Expected: {config_path}")
        print("  Copy config.example.json to config.json and fill in your values.")
        print()
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Contact page merge logic ───────────────────────────────────────────────

MENTIONS_MARKER = "<!-- mentions-start"

CONTACT_TEMPLATE = """# {full_name}
## Contact Info
- Organization: {organization}
- Title: {title}
- Phone: {phone}
- Email: {email}
- Google Contact: imported

## Relationship
- How we met:
- Mutual contacts:
- How I can help them:
- How they can help me:

<!-- mentions-start -- everything below this line is auto-populated by weekly_sync.py -->
## Mentions (auto-populated from voice captures)
"""


def parse_contact_mentions(mentions_path: Path) -> dict:
    """Parse contact-mentions.md into a dict of person_name -> list of mention lines."""
    mentions = defaultdict(list)
    if not mentions_path.exists():
        return mentions

    with open(mentions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: date | Full Name | capture_mode | description [| notes]
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                date = parts[0]
                name = parts[1]
                desc = parts[3]
                notes = parts[4] if len(parts) > 4 else ""
                mention_line = f"- {date}: {desc}"
                if notes:
                    mention_line += f" ({notes})"
                mentions[name].append(mention_line)

    return mentions


def parse_contacts_log(contacts_path: Path) -> dict:
    """Parse contacts.md to get contact info (org, title, phone, email)."""
    contacts = {}
    if not contacts_path.exists():
        return contacts

    with open(contacts_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format from capture_pipeline: date | Full Name | description | org | title | phone | email [| notes]
            # Actually the format is: date | capture_mode | contact | domain | Full Name [| org | title | phone | email | notes]
            # Let me parse more flexibly — look for the contact item_type lines
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                # Try to extract name and contact details
                # The flat log format from capture_pipeline is:
                # entry_date | capture_mode | item_type=contact | domain | description | responsible | status [| notes]
                # But contacts.md specifically gets contact items, so we need to check
                # what the capture pipeline actually writes there.
                # From capture_pipeline.py, the contact log line is:
                # "{entry_date} | {capture_mode} | {item_type} | {domain} | {desc} | {responsible} | {status} [| {notes}]"
                # And for contacts, given_name/family_name are in the description.
                # We also have the contact-mentions.md for names.
                pass

    return contacts


def parse_contacts_from_mentions_and_csv(logs_dir: Path) -> dict:
    """Build contact info dict from google-contacts-import.csv."""
    contacts = {}
    csv_path = logs_dir / "google-contacts-import.csv"
    if not csv_path.exists():
        return contacts

    import csv
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            given = row.get("Given Name", "").strip()
            family = row.get("Family Name", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                contacts[full_name] = {
                    "organization": row.get("Organization 1 - Name", ""),
                    "title": row.get("Organization 1 - Title", ""),
                    "phone": row.get("Phone 1 - Value", ""),
                    "email": row.get("E-mail 1 - Value", ""),
                }

    return contacts


def build_contact_page(full_name: str, contact_info: dict, mention_lines: list,
                       existing_page: Path | None) -> str:
    """Build the content for a contact page, preserving manual content above marker."""

    if existing_page and existing_page.exists():
        # Read existing page and preserve everything above the marker
        with open(existing_page, "r", encoding="utf-8") as f:
            content = f.read()

        marker_idx = content.find(MENTIONS_MARKER)
        if marker_idx >= 0:
            above_marker = content[:marker_idx]
        else:
            # No marker found — append marker at end
            above_marker = content.rstrip() + "\n\n"
    else:
        # New contact page from template
        info = contact_info or {}
        above_marker = CONTACT_TEMPLATE.format(
            full_name=full_name,
            organization=info.get("organization", ""),
            title=info.get("title", ""),
            phone=info.get("phone", ""),
            email=info.get("email", ""),
        ).split(MENTIONS_MARKER)[0]

    # Build the mentions section
    mentions_section = (
        MENTIONS_MARKER
        + " -- everything below this line is auto-populated by weekly_sync.py -->\n"
        + "## Mentions (auto-populated from voice captures)\n"
    )
    if mention_lines:
        mentions_section += "\n".join(mention_lines) + "\n"
    else:
        mentions_section += "*No mentions yet.*\n"

    return above_marker + mentions_section


def name_to_filename(name: str) -> str:
    """Convert 'Sarah Chen' to 'Sarah-Chen.md'."""
    return name.replace(" ", "-") + ".md"


# ── Sync functions ──────────────────────────────────────────────────────────

def sync_flat_logs(logs_dir: Path, obsidian_ops_dir: Path, confirm: bool) -> int:
    """Copy all flat log files to Obsidian Ops-Ledger/."""
    if not logs_dir.exists():
        print(f"  WARNING: Logs directory not found: {logs_dir}")
        return 0

    count = 0
    for f in sorted(logs_dir.iterdir()):
        if f.is_file():
            dest = obsidian_ops_dir / f.name
            if confirm:
                shutil.copy2(str(f), str(dest))
            count += 1
            print(f"  {'COPY' if confirm else 'WOULD COPY'}: {f.name} -> Ops-Ledger/")

    return count


def sync_sot_latest(sot_dir: Path, obsidian_sot_dir: Path, confirm: bool) -> int:
    """Copy sot-latest-MHH.csv and any recent timestamped SOTs to Obsidian."""
    if not sot_dir.exists():
        print(f"  WARNING: SOT directory not found: {sot_dir}")
        return 0

    count = 0
    for f in sorted(sot_dir.iterdir()):
        if f.is_file() and f.suffix == ".csv":
            dest = obsidian_sot_dir / f.name
            if confirm:
                shutil.copy2(str(f), str(dest))
            count += 1
            print(f"  {'COPY' if confirm else 'WOULD COPY'}: {f.name} -> Ops-Ledger/Source-of-Truth/")

    return count


def sync_contact_pages(logs_dir: Path, contacts_dir: Path, confirm: bool) -> tuple:
    """Build/update individual contact pages in Obsidian 11_Contacts/."""
    mentions = parse_contact_mentions(logs_dir / "contact-mentions.md")
    contact_info = parse_contacts_from_mentions_and_csv(logs_dir)

    # Collect all known contact names (from mentions + CSV)
    all_names = set(mentions.keys()) | set(contact_info.keys())

    created = 0
    updated = 0

    for name in sorted(all_names):
        filename = name_to_filename(name)
        page_path = contacts_dir / filename
        info = contact_info.get(name, {})
        mention_lines = mentions.get(name, [])

        is_new = not page_path.exists()
        content = build_contact_page(name, info, mention_lines, page_path)

        if confirm:
            with open(page_path, "w", encoding="utf-8") as f:
                f.write(content)

        if is_new:
            created += 1
            print(f"  {'CREATE' if confirm else 'WOULD CREATE'}: 11_Contacts/{filename}")
        else:
            updated += 1
            print(f"  {'UPDATE' if confirm else 'WOULD UPDATE'}: 11_Contacts/{filename} (mentions rebuilt)")

    return created, updated


# ── Main logic ──────────────────────────────────────────────────────────────

def run_sync(confirm: bool):
    config = load_config()

    logs_dir = Path(config.get("logs_dir", r"G:\My Drive\Estate Ops\Logs"))
    sot_dir = Path(config.get("sot_dir", r"G:\My Drive\Estate Ops\Source-of-Truth"))
    obsidian_vault = Path(config.get("obsidian_vault_dir",
                          r"C:\Users\mhhro\Documents\Obsidian Vault"))

    obsidian_ops_dir = obsidian_vault / "Ops-Ledger"
    obsidian_sot_dir = obsidian_ops_dir / "Source-of-Truth"
    obsidian_contacts_dir = obsidian_vault / "11_Contacts"

    mode_label = "LIVE RUN" if confirm else "DRY RUN"

    print()
    print("=" * 60)
    print(f"  WEEKLY SYNC TO OBSIDIAN ({mode_label})")
    print("=" * 60)
    print()
    print(f"  Logs source:       {logs_dir}")
    print(f"  SOT source:        {sot_dir}")
    print(f"  Obsidian vault:    {obsidian_vault}")
    print(f"  Ops-Ledger dest:   {obsidian_ops_dir}")
    print(f"  Contacts dest:     {obsidian_contacts_dir}")
    print()

    if confirm:
        # Ensure destination directories exist
        obsidian_ops_dir.mkdir(parents=True, exist_ok=True)
        obsidian_sot_dir.mkdir(parents=True, exist_ok=True)
        obsidian_contacts_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Sync flat log files
    print("  --- STEP 1: Flat log files ---")
    log_count = sync_flat_logs(logs_dir, obsidian_ops_dir, confirm)
    print()

    # Step 2: Sync SOT snapshots
    print("  --- STEP 2: Source-of-truth snapshots ---")
    sot_count = sync_sot_latest(sot_dir, obsidian_sot_dir, confirm)
    print()

    # Step 3: Build/update contact pages
    print("  --- STEP 3: Contact pages ---")
    created, updated = sync_contact_pages(logs_dir, obsidian_contacts_dir, confirm)
    print()

    # Summary
    print("  SUMMARY:")
    print(f"    Log files synced:     {log_count}")
    print(f"    SOT files synced:     {sot_count}")
    print(f"    Contact pages created: {created}")
    print(f"    Contact pages updated: {updated}")
    print()
    if not confirm:
        print("  DRY RUN: No files were written.")
        print("  To run for real:  python weekly_sync.py --confirm")
        print()
    print("=" * 60)


# ── Import test (for run_tests.py) ──────────────────────────────────────────

def run_import_test() -> bool:
    print()
    print("=" * 60)
    print("  WEEKLY SYNC - IMPORT TEST")
    print("=" * 60)
    try:
        import shutil  # noqa: F401
        import csv  # noqa: F401
        import json  # noqa: F401
        from collections import defaultdict  # noqa: F401
    except ImportError as e:
        print(f"  FAIL: Missing dependency: {e}")
        return False
    print()
    print("  OK: All imports successful (stdlib only — no external deps).")
    print()
    print("=" * 60)
    return True


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        sys.exit(0 if run_import_test() else 1)
    elif "--confirm" in args:
        run_sync(confirm=True)
    else:
        run_sync(confirm=False)
