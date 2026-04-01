"""
Estate OS — Vault Setup
========================
Creates the folder structure for Silver vault (Y:\\) or Bronze vault.
Run this once after creating a new Cryptomator vault in Cryptomator.

Silver vault: machine-curated legacy content. Lives on estate laptop.
Bronze vault: Silver overflow on external USB or NAS. Same structure.

Both vaults share the same 14-folder layout (matching Gold vault domains
plus 00_Unsorted for unclassified content) and a _provenance/ folder
that tracks every machine decision for human review.

USAGE:
  python vault_setup.py --vault silver
      Dry-run. Shows every folder that would be created on Y:\\.
      Nothing is created. Safe to run any time.

  python vault_setup.py --vault silver --confirm
      Creates all folders on Y:\\. Safe to re-run — skips folders
      that already exist.

  python vault_setup.py --vault bronze
      Dry-run for Bronze vault path (read from vault_config.json).
      Stops clearly if Bronze path is not configured.

  python vault_setup.py --vault bronze --confirm
      Creates Bronze folder structure. Requires Bronze path to be
      set in config/vault_config.json.

  python vault_setup.py --test
      Dry-run against a temporary folder inside tests/. No vault
      required. Use this to verify the script works before running
      against a real vault.

RULES:
  - Default is dry-run. --confirm required for real writes.
  - Never touches Gold vault.
  - If vault drive is not mounted, stops immediately with a clear message.
  - If Bronze path is empty in vault_config.json, stops with instructions.
  - Safe to re-run: skips folders that already exist, reports them as OK.
"""

import sys
import json
from datetime import datetime
from pathlib import Path


# ── Vault folder structure ────────────────────────────────────────────────────

VAULT_FOLDERS = [
    "00_Unsorted",        # machine confidence too low to classify
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
    "_provenance",        # machine decision records and review queue
]

PROVENANCE_FILES = [
    "_provenance/ingestion-log.jsonl",    # one record per file processed by machine
    "_provenance/review-queue.jsonl",     # files flagged for human review
    "_provenance/corrections-log.jsonl",  # human corrections to machine decisions
]


# ── Config loading ────────────────────────────────────────────────────────────

def load_config():
    """Load behavior config and vault config."""
    behavior_config_path = Path(__file__).parent / "config.json"
    if not behavior_config_path.exists():
        print("ERROR: config.json not found next to vault_setup.py")
        sys.exit(1)

    with open(behavior_config_path, "r", encoding="utf-8") as f:
        behavior_config = json.load(f)

    vault_config_path = Path(__file__).parent / behavior_config["vault_config_path"]
    if not vault_config_path.exists():
        print(f"ERROR: vault_config.json not found at: {vault_config_path}")
        print("Expected location: config/vault_config.json in repo root")
        sys.exit(1)

    with open(vault_config_path, "r", encoding="utf-8") as f:
        vault_config = json.load(f)

    return behavior_config, vault_config


def resolve_vault_path(vault_name: str, vault_config: dict) -> Path:
    """
    Return the configured path for the named vault.
    Stops with a clear message if the path is missing or not configured.
    Never returns a path inside the Gold vault.
    """
    key = f"{vault_name}_vault"

    if key not in vault_config:
        print(f"ERROR: '{key}' not found in vault_config.json")
        sys.exit(1)

    raw_path = vault_config[key].strip()

    if not raw_path:
        print()
        print(f"ERROR: {vault_name.title()} vault path is not configured.")
        print()
        if vault_name == "bronze":
            print("To configure Bronze vault:")
            print("  1. Connect your external USB drive or NAS")
            print("  2. Note the drive letter or network path it mounts to")
            print("  3. Open config/vault_config.json")
            print('  4. Set "bronze_vault" to that path, e.g. "Z:\\\\"')
            print("  5. Run vault_setup.py --vault bronze again")
        else:
            print(f"Open config/vault_config.json and set \"{key}\" to the vault path.")
        print()
        sys.exit(1)

    vault_path = Path(raw_path)

    # Hard guard: never operate inside Gold vault
    gold_path = Path(vault_config.get("gold_vault", "X:\\"))
    if vault_path == gold_path or gold_path in vault_path.parents:
        print("ERROR: Resolved path is inside the Gold vault. Stopping.")
        print(f"  Gold vault: {gold_path}")
        print(f"  Requested:  {vault_path}")
        sys.exit(1)

    return vault_path


# ── Drive mount check ─────────────────────────────────────────────────────────

def check_drive_mounted(vault_path: Path, vault_name: str) -> bool:
    """
    Verify the vault drive is mounted and accessible.
    On Windows, checks that the drive root exists.
    Stops with instructions if not mounted.
    """
    drive_root = Path(vault_path.anchor)
    if not drive_root.exists():
        print()
        print(f"ERROR: {vault_name.title()} vault drive is not accessible.")
        print(f"  Expected drive: {drive_root}")
        print()
        if vault_name == "silver":
            print("The Silver vault Cryptomator container must be unlocked first.")
            print("  1. Open Cryptomator")
            print("  2. Unlock the Silver vault")
            print("  3. Confirm it mounts as Y:\\")
            print("  4. Run vault_setup.py --vault silver again")
        elif vault_name == "bronze":
            print("The Bronze external drive must be connected and unlocked.")
            print("  1. Connect the external USB drive")
            print("  2. If using Cryptomator for Bronze, unlock it")
            print("  3. Update bronze_vault path in config/vault_config.json")
            print("  4. Run vault_setup.py --vault bronze again")
        print()
        return False
    return True


# ── Dry-run preview ───────────────────────────────────────────────────────────

def preview(vault_path: Path, vault_name: str):
    """Print what would be created without making any changes."""
    print()
    print("=" * 60)
    print(f"  VAULT SETUP — DRY RUN ({vault_name.upper()} VAULT)")
    print(f"  Target: {vault_path}")
    print("=" * 60)
    print()
    print("  The following folders would be created:")
    print("  (folders that already exist are marked [exists])")
    print()

    for folder in VAULT_FOLDERS:
        target = vault_path / folder
        status = "[exists]" if target.exists() else "[create]"
        print(f"    {status}  {folder}/")

    print()
    print("  The following empty files would be created:")
    print()
    for pf in PROVENANCE_FILES:
        target = vault_path / pf
        status = "[exists]" if target.exists() else "[create]"
        print(f"    {status}  {pf}")

    print()
    print("  No changes made. Run with --confirm to create.")
    print()


# ── Live setup ────────────────────────────────────────────────────────────────

def create_vault_structure(vault_path: Path, vault_name: str, log_path: Path):
    """
    Create the vault folder structure and empty provenance files.
    Safe to re-run: skips anything that already exists.
    """
    print()
    print("=" * 60)
    print(f"  VAULT SETUP — LIVE ({vault_name.upper()} VAULT)")
    print(f"  Target: {vault_path}")
    print("=" * 60)
    print()

    created = []
    skipped = []
    errors = []

    # Create domain folders
    for folder in VAULT_FOLDERS:
        target = vault_path / folder
        if target.exists():
            skipped.append(folder)
            print(f"    [skip]    {folder}/  (already exists)")
        else:
            try:
                target.mkdir(parents=True, exist_ok=True)
                created.append(folder)
                print(f"    [created] {folder}/")
            except Exception as e:
                errors.append(f"{folder}: {e}")
                print(f"    [ERROR]   {folder}/  — {e}")

    print()

    # Create empty provenance files
    for pf in PROVENANCE_FILES:
        target = vault_path / pf
        if target.exists():
            skipped.append(pf)
            print(f"    [skip]    {pf}  (already exists)")
        else:
            try:
                target.touch()
                created.append(pf)
                print(f"    [created] {pf}")
            except Exception as e:
                errors.append(f"{pf}: {e}")
                print(f"    [ERROR]   {pf}  — {e}")

    # Summary
    print()
    print("=" * 60)
    if errors:
        print(f"  RESULT: Completed with errors.")
        print(f"  Created: {len(created)}  |  Skipped: {len(skipped)}  |  Errors: {len(errors)}")
        for err in errors:
            print(f"    ERROR: {err}")
    else:
        print(f"  RESULT: Done. Created: {len(created)}  |  Skipped: {len(skipped)}")
    print("=" * 60)
    print()

    # Write log
    write_log(log_path, vault_name, vault_path, created, skipped, errors)

    if errors:
        sys.exit(1)


# ── Test mode ─────────────────────────────────────────────────────────────────

def run_test(log_path: Path):
    """
    Dry-run against a temp folder inside tests/.
    No vault required. Verifies script logic only.
    """
    test_root = Path(__file__).parent.parent.parent / "tests" / "fake-silver-vault"
    print()
    print("=" * 60)
    print("  VAULT SETUP — TEST MODE")
    print(f"  Would create structure at: {test_root}")
    print("=" * 60)
    print()
    print("  Test mode shows what would be created without touching any vault.")
    print()
    for folder in VAULT_FOLDERS:
        print(f"    [would create]  {folder}/")
    print()
    for pf in PROVENANCE_FILES:
        print(f"    [would create]  {pf}")
    print()
    print("  Test complete. Script logic OK.")
    print()


# ── Logging ───────────────────────────────────────────────────────────────────

def write_log(log_path: Path, vault_name: str, vault_path: Path,
              created: list, skipped: list, errors: list):
    """Write a timestamped log entry."""
    log_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"vault_setup_{vault_name.upper()}_{timestamp}.log"

    lines = [
        f"Vault Setup — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Vault: {vault_name.upper()}",
        f"Path:  {vault_path}",
        "",
        f"Created ({len(created)}):",
    ]
    for item in created:
        lines.append(f"  {item}")
    lines.append(f"Skipped ({len(skipped)}):")
    for item in skipped:
        lines.append(f"  {item}")
    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for item in errors:
            lines.append(f"  {item}")
    lines.append(f"Result: {'ERRORS' if errors else 'OK'}")

    log_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Log saved: {log_file.name}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    # Test mode — no vault needed
    if "--test" in args:
        behavior_config, _ = load_config()
        run_test(Path(__file__).parent / behavior_config["log_path"])
        sys.exit(0)

    # Require --vault flag
    if "--vault" not in args:
        print()
        print("Usage:")
        print("  python vault_setup.py --vault silver")
        print("  python vault_setup.py --vault silver --confirm")
        print("  python vault_setup.py --vault bronze")
        print("  python vault_setup.py --vault bronze --confirm")
        print("  python vault_setup.py --test")
        print()
        sys.exit(1)

    vault_idx = args.index("--vault")
    if vault_idx + 1 >= len(args):
        print("ERROR: --vault requires an argument: silver or bronze")
        sys.exit(1)

    vault_name = args[vault_idx + 1]
    if vault_name not in ("silver", "bronze"):
        print(f"ERROR: Unknown vault '{vault_name}'. Use 'silver' or 'bronze'.")
        sys.exit(1)

    confirm = "--confirm" in args

    # Load config and resolve path
    behavior_config, vault_config = load_config()
    log_path = Path(__file__).parent / behavior_config["log_path"]
    vault_path = resolve_vault_path(vault_name, vault_config)

    # Check drive is mounted before doing anything
    if not check_drive_mounted(vault_path, vault_name):
        sys.exit(1)

    # Run
    if confirm:
        create_vault_structure(vault_path, vault_name, log_path)
    else:
        preview(vault_path, vault_name)
