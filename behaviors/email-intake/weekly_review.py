"""
Estate OS -- Weekly Review (Phase 4)
======================================
Reads the latest source-of-truth snapshot (sot-latest-MHH.csv) and
produces a formatted weekly-review.md file for human review.

The review file shows:
  - All items from the past 7 days, grouped by domain
  - Items flagged as vault-bound (notes, reference, completed actions with notes)
  - Open todos and reminders still pending
  - Contacts added this week

You review the file, move vault-bound items to Obsidian manually,
and close out completed items in the sheet.

USAGE:
  python weekly_review.py
        Dry-run. Shows what would be written. No files created.

  python weekly_review.py --confirm
        Writes weekly-review-YYYY-MM-DD.md to the logs directory.

  python weekly_review.py --days 14
        Look back 14 days instead of the default 7.

  python weekly_review.py --test
        Import check only.

RULES:
  - Default is dry-run. --confirm required to write the file.
  - Reads only sot-latest-MHH.csv. Never writes to the sheet.
  - Output file is append-safe -- a new dated file is created each run.
  - No LLM involved. Pure Python CSV parsing and formatting.
"""

import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Items worth flagging for vault promotion
VAULT_BOUND_TYPES = {"note", "action_log", "health_log"}


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "ops-ledger" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sot(sot_path: Path) -> list[dict]:
    """Read the SOT CSV and return list of row dicts."""
    rows = []
    with open(sot_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def filter_by_date(rows: list[dict], days: int) -> list[dict]:
    """Return rows whose entry_date falls within the past N days."""
    cutoff = datetime.now().date() - timedelta(days=days)
    result = []
    for row in rows:
        try:
            entry_date = datetime.strptime(row.get("entry_date", ""), "%Y-%m-%d").date()
            if entry_date >= cutoff:
                result.append(row)
        except ValueError:
            pass  # skip rows with unparseable dates
    return result


def group_by_domain(rows: list[dict]) -> dict:
    """Group rows by domain. Returns dict of domain -> list of rows."""
    groups = defaultdict(list)
    for row in rows:
        domain = row.get("domain", "Unknown") or "Unknown"
        groups[domain].append(row)
    return dict(sorted(groups.items()))


def format_row(row: dict) -> str:
    """Format a single row as a markdown bullet."""
    item_type = row.get("item_type", "")
    status    = row.get("status", "")
    desc      = row.get("description", "").strip()
    due       = row.get("due_date", "").strip()
    notes     = row.get("notes", "").strip()
    resp      = row.get("responsible", "").strip()

    line = f"- [{item_type}] {desc}"
    if status and status != "open":
        line += f"  *(status: {status})*"
    if due:
        line += f"  *(due: {due})*"
    if resp and resp not in ("MHH", ""):
        line += f"  *(owner: {resp})*"
    if notes:
        line += f"\n  > {notes}"
    return line


def build_review(rows: list[dict], days: int, today_str: str) -> str:
    """Build the full markdown review document."""
    lines = []
    lines.append(f"# Weekly Review -- {today_str}")
    lines.append(f"*Generated from sot-latest-MHH.csv. Covers past {days} days.*")
    lines.append("")

    if not rows:
        lines.append("No items found in this period.")
        return "\n".join(lines)

    # -- Open items (todos, reminders, calendar) --
    open_types = {"todo", "reminder", "calendar"}
    open_items = [r for r in rows
                  if r.get("item_type") in open_types
                  and r.get("status", "open") in ("open", "in_progress", "")]

    if open_items:
        lines.append("## Open Items")
        lines.append("")
        by_domain = group_by_domain(open_items)
        for domain, domain_rows in by_domain.items():
            lines.append(f"### {domain}")
            for row in domain_rows:
                lines.append(format_row(row))
            lines.append("")

    # -- Vault-bound items (notes, logs, completed actions) --
    vault_items = [r for r in rows if r.get("item_type") in VAULT_BOUND_TYPES]
    completed   = [r for r in rows
                   if r.get("status") == "done"
                   and r.get("notes", "").strip()]

    all_vault = vault_items + [r for r in completed if r not in vault_items]

    if all_vault:
        lines.append("## Vault-Bound Items")
        lines.append("*Review these -- consider promoting to Obsidian.*")
        lines.append("")
        by_domain = group_by_domain(all_vault)
        for domain, domain_rows in by_domain.items():
            lines.append(f"### {domain}")
            for row in domain_rows:
                lines.append(format_row(row))
            lines.append("")

    # -- Contacts added this week --
    contacts = [r for r in rows if r.get("item_type") == "contact"]
    if contacts:
        lines.append("## Contacts Added This Week")
        lines.append("")
        for row in contacts:
            given  = row.get("given_name", "").strip()
            family = row.get("family_name", "").strip()
            org    = row.get("organization", "").strip()
            desc   = row.get("description", "").strip()
            name   = " ".join(filter(None, [given, family])) or desc
            if org:
                name += f" ({org})"
            lines.append(f"- {name}")
        lines.append("")

    # -- Summary counts --
    lines.append("---")
    lines.append(f"*Total items this period: {len(rows)}  |  "
                 f"Open: {len(open_items)}  |  "
                 f"Vault-bound: {len(all_vault)}  |  "
                 f"Contacts: {len(contacts)}*")

    return "\n".join(lines)


def run_review(days: int, confirm: bool) -> None:
    config = load_config()
    sot_dir  = Path(config.get("sot_dir",  r"G:\My Drive\Estate Ops\Source-of-Truth"))
    logs_dir = Path(config.get("logs_dir", r"G:\My Drive\Estate Ops\Logs"))
    sot_path = sot_dir / "sot-latest-MHH.csv"

    today_str = datetime.now().strftime("%Y-%m-%d")
    mode_label = "LIVE RUN" if confirm else "DRY RUN"

    print()
    print("=" * 60)
    print(f"  WEEKLY REVIEW ({mode_label})")
    print("=" * 60)
    print(f"  SOT file:  {sot_path}")
    print(f"  Lookback:  {days} days  (since "
          f"{(datetime.now().date() - timedelta(days=days)).isoformat()})")
    print()

    if not sot_path.exists():
        print(f"ERROR: SOT file not found: {sot_path}")
        print("  Run snapshot.py --confirm first to generate it.")
        sys.exit(1)

    all_rows  = load_sot(sot_path)
    week_rows = filter_by_date(all_rows, days)

    print(f"  Rows in SOT:         {len(all_rows)}")
    print(f"  Rows this period:    {len(week_rows)}")

    if not confirm:
        print()
        print("  DRY RUN: Would write weekly-review-" + today_str + ".md")
        print("  Run with --confirm to create the file.")
        print("=" * 60)
        return

    review_md = build_review(week_rows, days, today_str)
    output_path = logs_dir / f"weekly-review-{today_str}.md"
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(review_md, encoding="utf-8")

    print(f"\n  Written: {output_path}")
    print("=" * 60)


def run_import_test() -> bool:
    print()
    print("=" * 60)
    print("  WEEKLY REVIEW - IMPORT TEST")
    print("=" * 60)
    try:
        import csv       # noqa
        import json      # noqa
        from pathlib import Path          # noqa
        from collections import defaultdict  # noqa
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

    days = 7
    if "--days" in arg_lower:
        idx = arg_lower.index("--days")
        if idx + 1 < len(args):
            try:
                days = int(args[idx + 1])
            except ValueError:
                print("ERROR: --days requires an integer.")
                sys.exit(1)

    run_review(days, confirm)
