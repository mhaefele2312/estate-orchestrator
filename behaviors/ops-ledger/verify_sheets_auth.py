"""
Estate OS — Verify Google Sheets authentication (Ops Ledger)
=============================================================
Checks that OAuth client files are in place and (with --confirm) opens the
configured spreadsheet via gspread.

USAGE:
  python verify_sheets_auth.py --test       Import check only (no config needed)
  python verify_sheets_auth.py            Dry-run: validate config + files only
  python verify_sheets_auth.py --dry-run  Same as default
  python verify_sheets_auth.py --confirm  Live: OAuth if needed, then read sheet title

RULES:
  - Default is dry-run. No network calls unless you pass --confirm.
  - OAuth client JSON from Google Cloud Console → save as credentials.json (gitignored).
  - First --confirm run may open a browser to authorize; token.json is then reused.
"""

import sys
import json
import warnings
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _base_dir() -> Path:
    return Path(__file__).resolve().parent


def load_config():
    config_path = _base_dir() / "config.json"
    if not config_path.exists():
        print()
        print("ERROR: config.json not found.")
        print(f"  Expected: {config_path}")
        print("  Copy config.example.json to config.json and set spreadsheet_id.")
        print()
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_path(base: Path, p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def run_import_test():
    """Ensure dependencies are installed (safe for run_tests.py)."""
    print()
    print("=" * 60)
    print("  OPS LEDGER - IMPORT TEST")
    print("=" * 60)
    try:
        import gspread  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from google.auth.transport.requests import Request  # noqa: F401
        # CLAUDE.md: capture_pipeline will use google-generativeai; package shows a FutureWarning.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as genai  # noqa: F401
    except ImportError as e:
        print()
        print(f"  FAIL: Missing dependency: {e}")
        print("  Install: pip install -r requirements.txt")
        print()
        return False
    example = _base_dir() / "config.example.json"
    if not example.exists():
        print("  FAIL: config.example.json missing from behaviors/ops-ledger/")
        return False
    print()
    print("  OK: gspread, google-auth, google-auth-oauthlib, google-generativeai import.")
    print("  OK: config.example.json present.")
    print()
    print("=" * 60)
    return True


def run_dry_run():
    config = load_config()
    base = _base_dir()
    sheet_id = (config.get("spreadsheet_id") or "").strip()
    if not sheet_id or sheet_id == "YOUR_GOOGLE_SHEET_ID":
        print()
        print("ERROR: Set spreadsheet_id in config.json to your MHH-Ops-Ledger sheet ID.")
        sys.exit(1)

    cred_path = _resolve_path(base, config.get("credentials_path", "credentials.json"))
    token_path = _resolve_path(base, config.get("token_path", "token.json"))

    print()
    print("=" * 60)
    print("  OPS LEDGER - DRY RUN")
    print("  No network calls. Only checking local configuration.")
    print("=" * 60)
    print()
    print(f"  spreadsheet_id: {sheet_id}")
    print(f"  credentials_path: {cred_path}")
    print(f"  token_path:       {token_path}")
    print()

    if not cred_path.exists():
        print("  credentials.json is MISSING.")
        print("  In Google Cloud Console, create an OAuth desktop client and download")
        print("  the JSON. Save it as credentials.json next to this script (or set")
        print("  credentials_path in config.json).")
        sys.exit(1)
    print("  OK: OAuth client file exists.")

    if token_path.exists():
        print("  OK: token.json exists (authorized user cache).")
    else:
        print("  Note: token.json not found yet - first --confirm will run the browser OAuth flow.")

    print()
    print("  DRY RUN: Would open the spreadsheet and read its title (use --confirm).")
    print()
    print("=" * 60)


def _get_credentials(credentials_path: Path, token_path: Path):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not credentials_path.exists():
        print(f"ERROR: credentials file not found: {credentials_path}")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def run_confirm():
    import gspread

    config = load_config()
    base = _base_dir()
    sheet_id = (config.get("spreadsheet_id") or "").strip()
    if not sheet_id or sheet_id == "YOUR_GOOGLE_SHEET_ID":
        print()
        print("ERROR: Set spreadsheet_id in config.json to your MHH-Ops-Ledger sheet ID.")
        sys.exit(1)

    cred_path = _resolve_path(base, config.get("credentials_path", "credentials.json"))
    token_path = _resolve_path(base, config.get("token_path", "token.json"))

    print()
    print("=" * 60)
    print("  OPS LEDGER - LIVE VERIFY (--confirm)")
    print("  Contacting Google Sheets API.")
    print("=" * 60)
    print()

    creds = _get_credentials(cred_path, token_path)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.sheet1
        title = ws.title
    except Exception:
        title = "(could not read first sheet title)"

    print(f"  Spreadsheet title: {sh.title}")
    print(f"  First worksheet:   {title}")
    print()
    print("  OK: Authenticated and opened the Ops Ledger spreadsheet.")
    print("=" * 60)


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        sys.exit(0 if run_import_test() else 1)
    if "--confirm" in args:
        run_confirm()
    elif "--dry-run" in args or len(args) == 0:
        run_dry_run()
    else:
        print()
        print("Usage:")
        print("  python verify_sheets_auth.py --test       Import check only")
        print("  python verify_sheets_auth.py              Dry-run (default)")
        print("  python verify_sheets_auth.py --confirm    Open sheet via API")
        sys.exit(1)
