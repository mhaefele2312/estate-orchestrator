"""
Estate OS -- Staging Router (Phase 3)
=======================================
Interactive tool for routing staged files to their final vault destination.
Run after staging_sorter.py has sorted files into a Staging-Intake subfolder.

DESTINATIONS:
  g = Gold vault (X:\\)       You personally reviewed, named, and filed this.
  s = Silver vault (Y:\\)     Legacy content. Goes in as-is, provenance recorded.
  b = Bronze vault (USB)      Silver overflow. Must be configured and connected.
  o = Obsidian vault          Working knowledge, not a sensitive original.
  k = Keep (skip for now)     Leave in staging, decide later.
  d = Delete-review           Move to _review_delete/ for later cleanup.

USAGE:
  python staging_router.py --staging <path>
      Dry-run. Shows files waiting and their counts. No changes.

  python staging_router.py --staging <path> --confirm
      Interactive review. Shows each file, you type a destination.

  python staging_router.py --test
      Config check. No files needed.

RULES:
  - Default is dry-run. --confirm required for real routing.
  - Files are COPIED to destination. Originals in staging are preserved.
  - Nothing deleted without your 'd' choice. Even then, only moved to
    _review_delete/ subfolder -- never permanently deleted.
  - Silver and Bronze routing writes a provenance record automatically.
  - Bronze requires bronze_vault path set in config/vault_config.json
    and the drive connected. Script stops clearly if not available.
  - Gold has no 00_Unsorted -- Gold routing is always deliberate.
"""

import sys
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Domain list (matches all vault structures) ────────────────────────────────

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

# Gold never gets 00_Unsorted — Gold routing is always a deliberate decision
GOLD_DOMAINS = DOMAINS[1:]


# ── Config loading ────────────────────────────────────────────────────────────

def load_vault_config() -> dict:
    """Load vault paths from the central vault_config.json."""
    config_path = (
        Path(__file__).resolve().parent.parent.parent
        / "config" / "vault_config.json"
    )
    if not config_path.exists():
        print(f"ERROR: vault_config.json not found at: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_destination(dest_key: str, vault_config: dict):
    """
    Return Path for a vault destination, or None if not available.
    Prints a plain-English explanation if unavailable.
    """
    if dest_key == "obsidian":
        return Path(r"C:\Users\mhhro\Documents\Obsidian Vault")

    raw = vault_config.get(f"{dest_key}_vault", "").strip()

    if not raw:
        if dest_key == "bronze":
            print()
            print("  Bronze vault is not configured.")
            print("  To enable Bronze routing:")
            print("    1. Connect the BronzeVault USB drive")
            print("    2. Note its drive letter in Windows Explorer")
            print("    3. Open config/vault_config.json")
            print('    4. Set "bronze_vault" to the drive letter, e.g. "D:\\\\"')
            print("    5. Re-run the router")
        else:
            print(f"  ERROR: {dest_key}_vault not set in vault_config.json")
        return None

    p = Path(raw)
    if not p.exists():
        if dest_key == "bronze":
            print()
            print(f"  Bronze vault drive not accessible: {p}")
            print("  Connect the BronzeVault USB drive and try again.")
        else:
            print(f"  ERROR: {dest_key} vault path not accessible: {p}")
        return None

    return p


# ── File collection ───────────────────────────────────────────────────────────

def collect_files(staging_path: Path) -> list:
    """Collect all files in staging, excluding _review_delete."""
    return sorted(
        p for p in staging_path.rglob("*")
        if p.is_file() and "_review_delete" not in p.parts
    )


# ── Domain picker ─────────────────────────────────────────────────────────────

def pick_domain(include_unsorted=True):
    """Prompt for domain selection. Returns domain string or None to cancel."""
    domain_list = DOMAINS if include_unsorted else GOLD_DOMAINS
    print()
    for i, d in enumerate(domain_list, 1):
        print(f"    {i:2}. {d}")
    print("     0. Cancel (skip this file)")
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


# ── Safe copy ─────────────────────────────────────────────────────────────────

def safe_copy(src: Path, dest_dir: Path) -> Path:
    """Copy src to dest_dir. Appends counter if filename already exists."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    shutil.copy2(str(src), str(dest))
    return dest


# ── Provenance writer ─────────────────────────────────────────────────────────

def write_provenance(vault_root: Path, record: dict) -> None:
    """
    Append one JSON line to the vault's ingestion-log.jsonl.
    Silently skips if _provenance folder does not exist.
    """
    log_path = vault_root / "_provenance" / "ingestion-log.jsonl"
    if not log_path.parent.exists():
        return
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── Size label ────────────────────────────────────────────────────────────────

def size_label(p: Path) -> str:
    try:
        b = p.stat().st_size
        if b < 1024:
            return f"{b}B"
        if b < 1024 ** 2:
            return f"{b // 1024}KB"
        return f"{b // (1024 ** 2)}MB"
    except Exception:
        return "?"


# ── Dry-run ───────────────────────────────────────────────────────────────────

def run_dry_run(staging_path: Path, vault_config: dict) -> None:
    files = collect_files(staging_path)

    print()
    print("=" * 60)
    print("  STAGING ROUTER — DRY RUN")
    print(f"  Staging: {staging_path}")
    print("=" * 60)
    print()

    if not files:
        print("  No files waiting for routing.")
        print()
        return

    counts: dict = {}
    for f in files:
        bucket = f.parent.name if f.parent != staging_path else "root"
        counts[bucket] = counts.get(bucket, 0) + 1

    print(f"  Files waiting: {len(files)}")
    for bucket, n in sorted(counts.items()):
        print(f"    {bucket:<16} {n}")

    print()
    print("  Configured destinations:")
    for key, label in [
        ("gold",    "Gold vault   (X:\\)"),
        ("silver",  "Silver vault (Y:\\)"),
        ("bronze",  "Bronze vault (USB) "),
    ]:
        raw = vault_config.get(f"{key}_vault", "").strip()
        p = Path(raw) if raw else None
        if not raw:
            status = "not configured"
        elif p and p.exists():
            status = f"ready — {raw}"
        else:
            status = f"NOT accessible — {raw}"
        print(f"    {label:<26} {status}")

    print()
    print("  Run with --confirm to start interactive routing.")
    print()


# ── Live interactive routing ──────────────────────────────────────────────────

def run_confirm(staging_path: Path, vault_config: dict) -> None:
    files = collect_files(staging_path)

    gold_root     = resolve_destination("gold",     vault_config)
    silver_root   = resolve_destination("silver",   vault_config)
    bronze_root   = resolve_destination("bronze",   vault_config)
    obsidian_root = resolve_destination("obsidian", vault_config)
    review_delete = staging_path / "_review_delete"

    print()
    print("=" * 60)
    print("  STAGING ROUTER — LIVE")
    print(f"  Staging:  {staging_path}")
    print()
    print(f"  Gold:     {gold_root    or 'NOT AVAILABLE'}")
    print(f"  Silver:   {silver_root  or 'NOT AVAILABLE'}")
    print(f"  Bronze:   {bronze_root  or 'not configured'}")
    print(f"  Obsidian: {obsidian_root or 'NOT AVAILABLE'}")
    print("=" * 60)
    print()

    if not files:
        print("  No files waiting for routing.")
        return

    print(f"  {len(files)} file(s) to route.")
    print("  Commands: g=Gold  s=Silver  b=Bronze  o=Obsidian  k=Keep  d=Delete-review")
    print()

    counts = {"gold": 0, "silver": 0, "bronze": 0, "obsidian": 0, "kept": 0, "flagged": 0}

    for i, f in enumerate(files, 1):
        bucket = f.parent.name if f.parent != staging_path else ""
        label  = f"{bucket}/{f.name}" if bucket else f.name
        print(f"  [{i}/{len(files)}]  {label}  ({size_label(f)})")

        while True:
            choice = input("  Route [g/s/b/o/k/d]: ").strip().lower()

            if choice == "g":
                if not gold_root:
                    print("  Gold not available. Pick another destination.")
                    continue
                domain = pick_domain(include_unsorted=False)
                if domain is None:
                    print("  Skipped.")
                    counts["kept"] += 1
                    break
                dest = safe_copy(f, gold_root / domain)
                print(f"  → Gold/{domain}/{dest.name}")
                counts["gold"] += 1
                break

            elif choice == "s":
                if not silver_root:
                    print("  Silver not available. Pick another destination.")
                    continue
                domain = pick_domain(include_unsorted=True)
                if domain is None:
                    print("  Skipped.")
                    counts["kept"] += 1
                    break
                dest = safe_copy(f, silver_root / domain)
                write_provenance(silver_root, {
                    "timestamp":     datetime.now().isoformat(),
                    "original_name": f.name,
                    "routed_name":   dest.name,
                    "source_path":   str(f),
                    "destination":   str(dest),
                    "vault":         "silver",
                    "domain":        domain,
                    "method":        "human_routed",
                    "confidence":    1.0,
                })
                print(f"  → Silver/{domain}/{dest.name}")
                counts["silver"] += 1
                break

            elif choice == "b":
                if not bronze_root:
                    print("  Bronze not available. Configure it first or pick another.")
                    continue
                domain = pick_domain(include_unsorted=True)
                if domain is None:
                    print("  Skipped.")
                    counts["kept"] += 1
                    break
                dest = safe_copy(f, bronze_root / domain)
                write_provenance(bronze_root, {
                    "timestamp":     datetime.now().isoformat(),
                    "original_name": f.name,
                    "routed_name":   dest.name,
                    "source_path":   str(f),
                    "destination":   str(dest),
                    "vault":         "bronze",
                    "domain":        domain,
                    "method":        "human_routed",
                    "confidence":    1.0,
                })
                print(f"  → Bronze/{domain}/{dest.name}")
                counts["bronze"] += 1
                break

            elif choice == "o":
                if not obsidian_root:
                    print("  Obsidian not accessible.")
                    continue
                domain = pick_domain(include_unsorted=False)
                if domain is None:
                    print("  Skipped.")
                    counts["kept"] += 1
                    break
                dest = safe_copy(f, obsidian_root / domain)
                print(f"  → Obsidian/{domain}/{dest.name}")
                counts["obsidian"] += 1
                break

            elif choice == "k":
                print("  Kept in staging.")
                counts["kept"] += 1
                break

            elif choice == "d":
                review_delete.mkdir(parents=True, exist_ok=True)
                dest = review_delete / f.name
                shutil.move(str(f), str(dest))
                print(f"  → Delete-review: {dest.name}")
                counts["flagged"] += 1
                break

            else:
                print("  Type one letter: g s b o k d")

        print()

    print("=" * 60)
    print("  ROUTING COMPLETE")
    print(f"  → Gold:          {counts['gold']}")
    print(f"  → Silver:        {counts['silver']}")
    print(f"  → Bronze:        {counts['bronze']}")
    print(f"  → Obsidian:      {counts['obsidian']}")
    print(f"  Kept in staging: {counts['kept']}")
    print(f"  Delete-review:   {counts['flagged']}")
    print("=" * 60)
    print()


# ── Test mode ─────────────────────────────────────────────────────────────────

def run_test() -> None:
    print()
    print("=" * 60)
    print("  STAGING ROUTER — TEST")
    print("=" * 60)
    print()
    config = load_vault_config()
    print("  vault_config.json loaded OK")
    print()
    for key, label in [
        ("gold",   "Gold vault"),
        ("silver", "Silver vault"),
        ("bronze", "Bronze vault"),
    ]:
        raw = config.get(f"{key}_vault", "").strip()
        if not raw:
            print(f"  {label:<16} not configured")
        else:
            status = "accessible" if Path(raw).exists() else "NOT accessible"
            print(f"  {label:<16} {raw}  ({status})")
    print()
    print("  Test complete.")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    if "--test" in arg_lower:
        run_test()
        sys.exit(0)

    confirm = "--confirm" in arg_lower

    staging_path = None
    if "--staging" in arg_lower:
        idx = arg_lower.index("--staging")
        if idx + 1 < len(args):
            staging_path = Path(args[idx + 1])
        else:
            print("\nERROR: --staging requires a path argument.")
            sys.exit(1)

    if not staging_path:
        print()
        print("Usage:")
        print("  python staging_router.py --staging <sorted-staging-folder>")
        print("  python staging_router.py --staging <path> --confirm")
        print("  python staging_router.py --test")
        print()
        sys.exit(1)

    if not staging_path.exists():
        print(f"\nERROR: Staging folder not found: {staging_path}")
        sys.exit(1)

    vault_config = load_vault_config()

    if confirm:
        run_confirm(staging_path, vault_config)
    else:
        run_dry_run(staging_path, vault_config)
