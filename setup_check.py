"""
Estate OS -- Setup Check
=========================
Run this once on any new machine to verify the system is ready.
Fix any ERRORs before using the pipeline. WARNINGs are non-blocking.

USAGE:
  python setup_check.py
"""

import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent
OPS_LEDGER = ROOT / "behaviors" / "ops-ledger"

PASS  = "  OK "
WARN  = "  WARN"
FAIL  = "  FAIL"

results = []

def check(label, ok, warning=False, detail=""):
    status = PASS if ok else (WARN if warning else FAIL)
    results.append((status, label, detail))
    print(f"{status}  {label}" + (f"\n        {detail}" if detail and not ok else ""))


# ── Python version ─────────────────────────────────────────────────────────
major, minor = sys.version_info[:2]
check("Python 3.10+", major == 3 and minor >= 10,
      detail=f"Found Python {major}.{minor}. Need 3.10 or newer.")

# ── Required packages ───────────────────────────────────────────────────────
packages = {
    "gspread":               "pip install gspread",
    "google.auth":           "pip install google-auth",
    "google_auth_oauthlib":  "pip install google-auth-oauthlib",
    "google.genai":          "pip install google-genai",
}
for pkg, install_cmd in packages.items():
    try:
        __import__(pkg.replace("-", "_"))
        check(f"Package: {pkg}", True)
    except ImportError:
        check(f"Package: {pkg}", False, detail=f"Run: pip install {install_cmd}")

# ── config.json ─────────────────────────────────────────────────────────────
config_path = OPS_LEDGER / "config.json"
config = {}
if config_path.exists():
    check("config.json exists", True)
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    sheet_id = config.get("spreadsheet_id", "")
    check("config.json: spreadsheet_id set",
          bool(sheet_id) and sheet_id != "YOUR_GOOGLE_SHEET_ID",
          detail="Edit config.json and set spreadsheet_id.")
else:
    check("config.json exists", False,
          detail="Copy behaviors/ops-ledger/config.example.json to config.json and fill in values.")

# ── OAuth credentials ───────────────────────────────────────────────────────
cred_path  = OPS_LEDGER / config.get("credentials_path", "credentials.json")
token_path = OPS_LEDGER / config.get("token_path", "token.json")
check("credentials.json exists", cred_path.exists(),
      detail="Download OAuth credentials from Google Cloud Console and save as behaviors/ops-ledger/credentials.json")
check("token.json exists (authorized)", token_path.exists(),
      detail="Run: cd behaviors/ops-ledger && python verify_sheets_auth.py --confirm  (authorizes Google Sheets access)")

# ── Gemini API key ──────────────────────────────────────────────────────────
env_path = OPS_LEDGER / ".env"
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key and env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("GEMINI_API_KEY="):
            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
check("GEMINI_API_KEY set (.env or environment)",
      bool(api_key) and api_key != "your-gemini-api-key-here",
      detail="Edit behaviors/ops-ledger/.env and set GEMINI_API_KEY=your-key-here")

# ── Google Drive paths ──────────────────────────────────────────────────────
drive_paths = {
    "logs_dir":           config.get("logs_dir", ""),
    "capture_archive_dir":config.get("capture_archive_dir", ""),
    "inbox_dir":          config.get("inbox_dir", ""),
    "sot_dir":            config.get("sot_dir", ""),
}
for key, path_str in drive_paths.items():
    if path_str:
        p = Path(path_str)
        check(f"Drive path: {key}", p.exists(), warning=True,
              detail=f"{path_str} not found. Create it or check Google Drive is signed in.")

# ── Gold vault ──────────────────────────────────────────────────────────────
gold = Path(config.get("gold_vault_dir", "E:\\"))
check("Gold vault (E:\\) accessible", gold.exists(), warning=True,
      detail="Gold vault drive not mounted. Open Cryptomator and unlock the vault before running snapshot.")

# ── Obsidian vault ──────────────────────────────────────────────────────────
obsidian = Path(config.get("obsidian_vault_dir",
                            r"C:\Users\mhhro\Documents\Obsidian Vault"))
check("Obsidian vault accessible", obsidian.exists(), warning=True,
      detail=f"{obsidian} not found. Expected on estate laptop only.")

# ── Summary ─────────────────────────────────────────────────────────────────
print()
print("=" * 60)
errors   = [r for r in results if r[0] == FAIL]
warnings = [r for r in results if r[0] == WARN]

if not errors and not warnings:
    print("  All checks passed. System is ready.")
elif not errors:
    print(f"  {len(warnings)} warning(s) -- system can run but some features limited.")
    print("  (Warnings are normal on the dev machine -- Gold/Obsidian paths are estate-laptop-only.)")
else:
    print(f"  {len(errors)} error(s) must be fixed before running.")
    print()
    for _, label, detail in errors:
        print(f"  FAIL: {label}")
        if detail:
            print(f"        {detail}")
print("=" * 60)

sys.exit(0 if not errors else 1)
