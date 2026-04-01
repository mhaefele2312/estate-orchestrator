"""
Estate OS — Silver Vault Review
================================
Interactive tool to review machine-classified files in the Silver vault.
Shows each file's content, its machine classification, and confidence score.
You decide what to do with each one.

COMMANDS (during review):
  Enter / a  Accept — classification and filename are correct, keep as-is
  r          Rename — give the file a new name (stays in same domain)
  m          Move   — reclassify to a different domain folder
  g          Promote to Gold — copy to Gold vault, remove from Silver
  s          Skip — leave unchanged for now, decide later
  q          Quit — stop review session (progress so far is saved)

USAGE:
  python silver_review.py
        Dry-run. Shows Silver vault contents and stats. No changes.

  python silver_review.py --confirm
        Interactive review. Makes changes as you approve them.

  python silver_review.py --domain 01_Financial
        Review only one domain folder (combine with --confirm).

  python silver_review.py --unsorted
        Review only 00_Unsorted (good starting point).

  python silver_review.py --test
        Run against fake test vault. No real vault touched.

RULES:
  - Default is dry-run. --confirm required for real changes.
  - Silver files are MOVED on rename/reclassify. Originals are not kept.
  - Promote to Gold COPIES to Gold, then deletes from Silver.
  - All decisions are logged to _provenance/corrections-log.jsonl.
  - Gold has no 00_Unsorted — Gold promotion always picks a specific domain.
"""

import sys
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Domain list ───────────────────────────────────────────────────────────────

DOMAINS = [
    "00_Unsorted",
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

GOLD_DOMAINS = DOMAINS[1:]  # Gold has no 00_Unsorted


# ── Config / path loading ─────────────────────────────────────────────────────

def load_vault_config() -> dict:
    config_path = (
        Path(__file__).resolve().parent.parent.parent
        / "config" / "vault_config.json"
    )
    if not config_path.exists():
        print(f"ERROR: vault_config.json not found at: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_paths(test_mode: bool) -> tuple:
    """Return (silver_root, gold_root) as Path objects."""
    cfg = load_vault_config()

    if test_mode:
        repo_root   = Path(__file__).resolve().parent.parent.parent
        test_cfg    = cfg.get("_test_vaults", {})
        silver_root = repo_root / test_cfg.get("silver_vault", "tests/fake-silver-vault")
        gold_root   = repo_root / test_cfg.get("gold_vault",   "tests/fake-gold-vault")
    else:
        silver_root = Path(cfg.get("silver_vault", "Y:\\"))
        gold_root   = Path(cfg.get("gold_vault",   "X:\\"))

    if not silver_root.exists():
        print(f"ERROR: Silver vault not accessible: {silver_root}")
        if not test_mode:
            print("  Unlock the Silver vault in Cryptomator first.")
        sys.exit(1)

    return silver_root, gold_root


# ── Provenance ────────────────────────────────────────────────────────────────

def load_provenance(silver_root: Path) -> dict:
    """
    Load ingestion-log.jsonl into a dict keyed by filed filename.
    If the same filename appears more than once, keep the most recent record.
    """
    log_path = silver_root / "_provenance" / "ingestion-log.jsonl"
    records = {}
    if not log_path.exists():
        return records
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = Path(rec.get("destination", rec.get("filed_name", ""))).name
                if key:
                    records[key] = rec
            except json.JSONDecodeError:
                pass
    return records


def write_correction(silver_root: Path, record: dict) -> None:
    """Append one correction record to corrections-log.jsonl."""
    log_path = silver_root / "_provenance" / "corrections-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── File collection ───────────────────────────────────────────────────────────

def collect_files(silver_root: Path,
                  domain_filter: str = None,
                  unsorted_only: bool = False) -> list:
    """
    Collect files from Silver vault. 00_Unsorted always comes first.
    Excludes _provenance folder and hidden files.
    """
    if unsorted_only:
        folders = [silver_root / "00_Unsorted"]
    elif domain_filter:
        folders = [silver_root / domain_filter]
    else:
        folders = [silver_root / "00_Unsorted"] + [
            silver_root / d for d in DOMAINS[1:]
        ]

    files = []
    for folder in folders:
        if folder.exists():
            for p in sorted(folder.iterdir()):
                if p.is_file() and not p.name.startswith("."):
                    files.append(p)
    return files


# ── Display ───────────────────────────────────────────────────────────────────

def show_file(path: Path, prov: dict, index: int, total: int) -> None:
    """Print file details — location, provenance, and content preview."""
    conf  = prov.get("confidence")
    orig  = prov.get("original_name", "")
    ts    = prov.get("timestamp", "")[:10] if prov.get("timestamp") else ""

    print()
    print("=" * 64)
    print(f"  [{index}/{total}]  {path.name}")
    print(f"  Domain:  {path.parent.name}")
    if prov:
        conf_str = f"{conf:.0%}" if conf is not None else "n/a"
        print(f"  Machine confidence: {conf_str}")
        if orig and orig != path.name:
            print(f"  Original filename:  {orig}")
        if ts:
            print(f"  Filed: {ts}")
    else:
        print("  No provenance record for this file.")
    print("=" * 64)

    try:
        text    = path.read_text(encoding="utf-8", errors="ignore")
        preview = text[:500].strip()
        if preview:
            print()
            for line in preview.splitlines()[:12]:
                print(f"    {line}")
            if len(text) > 500:
                print(f"    ... [{len(text) - 500} more characters]")
    except Exception as e:
        print(f"  [Could not read file: {e}]")
    print()


# ── Domain picker ─────────────────────────────────────────────────────────────

def pick_domain(include_unsorted: bool = True):
    """Prompt for a domain. Returns domain string or None to cancel."""
    domain_list = DOMAINS if include_unsorted else GOLD_DOMAINS
    print()
    for i, d in enumerate(domain_list, 1):
        print(f"    {i:2}. {d}")
    print("     0. Cancel")
    print()
    while True:
        raw = input("  Domain number: ").strip()
        if raw in ("0", ""):
            return None
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(domain_list):
                return domain_list[idx]
        except ValueError:
            pass
        print("  Enter a number from the list.")


# ── Safe path helper ──────────────────────────────────────────────────────────

def safe_dest(dest_dir: Path, filename: str) -> Path:
    """Return a path inside dest_dir, adding a counter if name is taken."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    ext  = Path(filename).suffix
    n = 1
    while True:
        candidate = dest_dir / f"{stem}_{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(counts: dict) -> None:
    print(f"  Accepted:     {counts['accepted']}")
    print(f"  Renamed:      {counts['renamed']}")
    print(f"  Reclassified: {counts['moved']}")
    print(f"  -> Gold:      {counts['promoted']}")
    print(f"  Skipped:      {counts['skipped']}")


# ── Interactive review loop ───────────────────────────────────────────────────

def review_loop(files: list, silver_root: Path, gold_root: Path, prov: dict) -> None:
    """
    Core interactive review loop. Shared by run_confirm() and the scoped
    --domain / --unsorted variants.
    """
    counts = {"accepted": 0, "renamed": 0, "moved": 0, "promoted": 0,
              "skipped": 0}

    for i, path in enumerate(files, 1):
        rec = prov.get(path.name, {})
        show_file(path, rec, i, len(files))

        while True:
            raw = input("  Action [Enter/a/r/m/g/s/q]: ").strip().lower()

            # Accept ──────────────────────────────────────────────────────────
            if raw in ("", "a"):
                write_correction(silver_root, {
                    "timestamp":   datetime.now().isoformat(),
                    "action":      "accepted",
                    "path":        str(path),
                    "domain":      path.parent.name,
                    "reviewed_by": "MHH",
                })
                print(f"  Accepted: {path.name}")
                counts["accepted"] += 1
                break

            # Rename ──────────────────────────────────────────────────────────
            elif raw == "r":
                print(f"  Current name: {path.name}")
                new_name = input("  New name: ").strip()
                if not new_name:
                    print("  No name entered — skipping.")
                    counts["skipped"] += 1
                    break
                if not new_name.endswith(path.suffix):
                    new_name += path.suffix
                dest = safe_dest(path.parent, new_name)
                shutil.move(str(path), str(dest))
                write_correction(silver_root, {
                    "timestamp":     datetime.now().isoformat(),
                    "action":        "renamed",
                    "original_path": str(path),
                    "new_path":      str(dest),
                    "domain":        path.parent.name,
                    "reviewed_by":   "MHH",
                })
                print(f"  Renamed: {path.name} -> {dest.name}")
                counts["renamed"] += 1
                break

            # Move / reclassify ───────────────────────────────────────────────
            elif raw == "m":
                print(f"  Current domain: {path.parent.name}")
                print("  Move to:")
                domain = pick_domain(include_unsorted=True)
                if domain is None:
                    print("  Cancelled — skipping.")
                    counts["skipped"] += 1
                    break
                dest_dir = silver_root / domain
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = safe_dest(dest_dir, path.name)
                shutil.move(str(path), str(dest))
                write_correction(silver_root, {
                    "timestamp":     datetime.now().isoformat(),
                    "action":        "reclassified",
                    "original_path": str(path),
                    "new_path":      str(dest),
                    "from_domain":   path.parent.name,
                    "to_domain":     domain,
                    "reviewed_by":   "MHH",
                })
                print(f"  Moved: {path.parent.name} -> {domain}/{dest.name}")
                counts["moved"] += 1
                break

            # Promote to Gold ─────────────────────────────────────────────────
            elif raw == "g":
                if not gold_root.exists():
                    print(f"  Gold vault not accessible: {gold_root}")
                    print("  Unlock Gold in Cryptomator first, or pick another action.")
                    continue
                print("  Promote to Gold — choose destination domain:")
                domain = pick_domain(include_unsorted=False)
                if domain is None:
                    print("  Cancelled — skipping.")
                    counts["skipped"] += 1
                    break
                print(f"  Filename for Gold: {path.name}")
                rename_raw = input("  Press Enter to keep, or type a new name: ").strip()
                gold_name  = rename_raw if rename_raw else path.name
                if rename_raw and not gold_name.endswith(path.suffix):
                    gold_name += path.suffix
                dest_dir = gold_root / domain
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = safe_dest(dest_dir, gold_name)
                shutil.copy2(str(path), str(dest))
                path.unlink()
                write_correction(silver_root, {
                    "timestamp":     datetime.now().isoformat(),
                    "action":        "promoted_to_gold",
                    "original_path": str(path),
                    "gold_path":     str(dest),
                    "silver_domain": path.parent.name,
                    "gold_domain":   domain,
                    "reviewed_by":   "MHH",
                })
                print(f"  Promoted to Gold/{domain}/{dest.name}")
                counts["promoted"] += 1
                break

            # Skip ────────────────────────────────────────────────────────────
            elif raw == "s":
                print("  Skipped.")
                counts["skipped"] += 1
                break

            # Quit ────────────────────────────────────────────────────────────
            elif raw == "q":
                print()
                print("=" * 64)
                print("  SESSION ENDED")
                print_summary(counts)
                print("=" * 64)
                sys.exit(0)

            else:
                print("  Type: Enter/a=Accept  r=Rename  m=Move  g=Gold  s=Skip  q=Quit")

        print()

    print("=" * 64)
    print("  REVIEW COMPLETE")
    print_summary(counts)
    print("=" * 64)


# ── Dry-run ───────────────────────────────────────────────────────────────────

def run_dry_run(silver_root: Path,
                domain_filter: str = None,
                unsorted_only: bool = False) -> None:
    files = collect_files(silver_root, domain_filter, unsorted_only)
    prov  = load_provenance(silver_root)
    scope = domain_filter or ("00_Unsorted" if unsorted_only else "all domains")

    print()
    print("=" * 64)
    print(f"  SILVER VAULT REVIEW — DRY RUN  ({scope})")
    print(f"  Silver vault: {silver_root}")
    print("=" * 64)
    print()

    if not files:
        print(f"  No files in {scope}.")
        print()
        return

    if domain_filter or unsorted_only:
        print(f"  {len(files)} file(s) in {scope}:")
        for f in files:
            rec      = prov.get(f.name, {})
            conf     = rec.get("confidence")
            conf_str = f"  [{conf:.0%}]" if conf is not None else ""
            print(f"    {f.name}{conf_str}")
    else:
        counts: dict = {}
        for f in files:
            d = f.parent.name
            counts[d] = counts.get(d, 0) + 1
        low_conf = sum(
            1 for f in files
            if prov.get(f.name, {}).get("confidence", 1.0) < 0.3
        )
        print(f"  Total files: {len(files)}")
        print()
        for domain in DOMAINS:
            n = counts.get(domain, 0)
            if n:
                flag = "  <- start here" if domain == "00_Unsorted" else ""
                print(f"    {domain:<22} {n}{flag}")
        if low_conf:
            print()
            print(f"  Low-confidence files (< 30%): {low_conf}")

    print()
    print("  Run with --confirm to start interactive review.")
    print("  Use --unsorted to review 00_Unsorted only.")
    print()


# ── Test mode ─────────────────────────────────────────────────────────────────

def run_test() -> None:
    print()
    print("=" * 64)
    print("  SILVER VAULT REVIEW — TEST")
    print("=" * 64)
    silver_root, gold_root = resolve_paths(test_mode=True)
    print(f"  Silver: {silver_root}  ({'OK' if silver_root.exists() else 'NOT found'})")
    print(f"  Gold:   {gold_root}  ({'OK' if gold_root.exists() else 'NOT found'})")
    prov  = load_provenance(silver_root)
    files = collect_files(silver_root)
    print(f"  Files in test Silver vault: {len(files)}")
    print(f"  Provenance records loaded:  {len(prov)}")
    print()
    print("  Test complete. No files changed.")
    print()


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    if "--test" in arg_lower:
        run_test()
        sys.exit(0)

    unsorted_only = "--unsorted" in arg_lower
    domain_filter = None
    if "--domain" in arg_lower:
        idx = arg_lower.index("--domain")
        if idx + 1 < len(args):
            domain_filter = args[idx + 1]
        else:
            print("ERROR: --domain requires a folder name, e.g. --domain 01_Financial")
            sys.exit(1)

    confirm = "--confirm" in arg_lower

    silver_root, gold_root = resolve_paths(test_mode=False)

    if confirm:
        files = collect_files(silver_root, domain_filter, unsorted_only)
        if not files:
            scope = domain_filter or ("00_Unsorted" if unsorted_only else "Silver vault")
            print(f"\n  No files found in {scope}.")
            sys.exit(0)

        prov  = load_provenance(silver_root)
        scope = domain_filter or ("00_Unsorted" if unsorted_only else "all domains")

        print()
        print("=" * 64)
        print(f"  SILVER VAULT REVIEW — LIVE  ({scope})")
        print(f"  Silver vault: {silver_root}")
        print(f"  Gold vault:   {gold_root}")
        print()
        print("  Commands:  Enter/a=Accept  r=Rename  m=Move  g=Gold  s=Skip  q=Quit")
        print("=" * 64)
        print(f"\n  {len(files)} file(s) to review.\n")

        review_loop(files, silver_root, gold_root, prov)
    else:
        run_dry_run(silver_root, domain_filter, unsorted_only)
