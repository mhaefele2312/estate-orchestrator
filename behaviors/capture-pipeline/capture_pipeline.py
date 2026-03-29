"""
Estate OS — Capture Pipeline (Stages 2 + 3)
============================================
Reads a raw voice memo transcript (.md file), calls Gemini API to parse it
into structured rows (Stage 2), then appends to the Ops Ledger Google Sheet
and all flat log files simultaneously (Stage 3).

USAGE:
  python capture_pipeline.py --file <path/to/transcript.md>
        Dry-run. Shows what Gemini would parse. No writes.

  python capture_pipeline.py --file <path/to/transcript.md> --confirm
        Live run. Writes to sheet + all flat files. Moves transcript to archive.

  python capture_pipeline.py --test
        Import check only. No files needed.

REQUIRES:
  - GEMINI_API_KEY environment variable set to your Gemini API key
  - behaviors/ops-ledger/config.json with spreadsheet_id, logs_dir,
    capture_archive_dir (see config.example.json for all fields)

NON-NEGOTIABLE RULES (from CLAUDE.md):
  - Stage 2 (Gemini) receives ONLY the raw transcript. Never the sheet.
  - Stage 3 (Python) writes simultaneously to ALL four targets: sheet,
    flat logs, contacts CSV, contact-mentions.md.
  - No sensitive screening, no bifurcated routing.
  - Default is dry-run. --confirm required for real writes.
  - Append-only. gspread.append_row() only. No row modifications.
"""

import sys
import os
import json
import csv
import shutil
import warnings
import re
from datetime import datetime
from pathlib import Path

# ── Sheet column order (must match Raw Log header row exactly) ──────────────
COLUMNS = [
    "entry_date", "entry_time", "capture_mode", "item_type", "domain",
    "description", "responsible", "due_date", "status", "notes",
    "source_capture", "captured_by",
    "given_name", "family_name", "organization", "title", "phone", "email",
]

# ── item_type → append-only log file ────────────────────────────────────────
ITEM_TYPE_TO_LOG = {
    "todo":       "next-actions.md",
    "reminder":   "next-actions.md",
    "calendar":   "calendar.md",
    "contact":    "contacts.md",
    "note":       "reference-notes.md",
    "health_log": "health.md",
    # action_log goes to master-log.md only (already completed)
}

GOOGLE_CONTACTS_HEADERS = [
    "Given Name", "Family Name", "Organization", "Title",
    "Phone 1 - Value", "Email 1 - Value", "Notes",
]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

GEMINI_PROMPT_TEMPLATE = """\
You are a structured data extractor for a personal estate operating system.

Your task: parse the voice memo transcript below and return a JSON array of
row objects — one object per discrete item.

RULES:
- Output ONLY a valid JSON array. No markdown, no explanation, no preamble.
- Split mixed-topic transcripts into individual items.
- Each item must have exactly these fields (use empty string "" for unknowns):
    item_type, domain, description, responsible, due_date, status, notes,
    given_name, family_name, organization, title, phone, email

ITEM_TYPE values (pick the best match):
  todo        — a specific single-step task to do in the future
  reminder    — something to remember or follow up on
  action_log  — something already done (logging a completed action)
  contact     — a new person to add to contacts
  calendar    — a specific date/time event or hard deadline
  note        — reference information, observation, no action required
  health_log  — how the person is feeling (from "how are you feeling?" prompt)

DOMAIN values (pick the best match from these 12):
  01_Financial, 02_Legal, 03_Property, 04_Insurance, 05_Medical,
  06_Tax, 07_Estate-Planning, 08_Vehicles, 09_Digital, 10_Family,
  11_Contacts, 12_Operations

STATUS values:
  open (default for todo/reminder/calendar)
  in_progress
  done (for action_log items)
  deferred

CONTACT DETECTION:
- If the user mentions any person by name (even if not a "new contact"),
  populate given_name and family_name on that row.
- For item_type=contact, also populate organization, title, phone, email if mentioned.

DUE DATE format: YYYY-MM-DD if a specific date is given or strongly implied.
  Leave blank if uncertain.

RESPONSIBLE: default to "MHH" unless the transcript clearly names someone else.

Today's date for reference: {today}

TRANSCRIPT:
{transcript}
"""


# ───────────────────────────────────────────────────────────────────────────
# Config / helpers
# ───────────────────────────────────────────────────────────────────────────

def _base_dir() -> Path:
    return Path(__file__).resolve().parent


def _ops_ledger_dir() -> Path:
    return _base_dir().parent / "ops-ledger"


def load_config():
    config_path = _ops_ledger_dir() / "config.json"
    if not config_path.exists():
        print(f"\nERROR: config.json not found at {config_path}")
        print("  Copy behaviors/ops-ledger/config.example.json to config.json and fill it in.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def detect_capture_mode(timestamp: datetime) -> str:
    hour = timestamp.hour
    if hour < 11:
        return "morning_sweep"
    elif hour < 17:
        return "quick_note"
    else:
        return "evening_sweep"


def parse_timestamp_from_filename(filename: str) -> datetime:
    """Extract datetime from capture-YYYY-MM-DD-HHMM-WHO.md pattern."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})", filename)
    if m:
        y, mo, d, h, mi = (int(x) for x in m.groups())
        return datetime(y, mo, d, h, mi)
    return datetime.now()


def extract_captured_by(filename: str) -> str:
    """Extract family member ID from filename (e.g. MHH, HBS)."""
    m = re.search(r"-([A-Z]{2,4})\.md$", filename, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return "MHH"


# ───────────────────────────────────────────────────────────────────────────
# Stage 2 — Gemini parsing
# ───────────────────────────────────────────────────────────────────────────

def call_gemini(transcript: str, today_str: str) -> list[dict]:
    """Send transcript to Gemini; return list of row dicts."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("\nERROR: GEMINI_API_KEY environment variable is not set.")
        print("  Set it with: $env:GEMINI_API_KEY = 'your-key-here'  (PowerShell)")
        print("  Or add it to your system environment variables.")
        sys.exit(1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        today=today_str,
        transcript=transcript.strip(),
    )

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Gemini returned invalid JSON: {e}")
        print("Raw response:")
        print(raw[:1000])
        sys.exit(1)

    if not isinstance(rows, list):
        print("\nERROR: Gemini returned JSON but not a list. Expected a JSON array.")
        sys.exit(1)

    return rows


def normalize_row(row: dict, entry_date: str, entry_time: str,
                  capture_mode: str, source_capture: str, captured_by: str) -> dict:
    """Fill in pipeline-generated fields and ensure all 18 columns exist."""
    normalized = {}
    for col in COLUMNS:
        normalized[col] = str(row.get(col, "") or "").strip()
    normalized["entry_date"] = entry_date
    normalized["entry_time"] = entry_time
    normalized["capture_mode"] = capture_mode
    normalized["source_capture"] = source_capture
    normalized["captured_by"] = captured_by
    if not normalized["status"]:
        if normalized["item_type"] == "action_log":
            normalized["status"] = "done"
        else:
            normalized["status"] = "open"
    if not normalized["responsible"]:
        normalized["responsible"] = captured_by
    return normalized


# ───────────────────────────────────────────────────────────────────────────
# Stage 3 — Write to all four targets
# ───────────────────────────────────────────────────────────────────────────

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
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def write_to_sheet(rows: list[dict], config: dict) -> None:
    """Append all rows to the Raw Log tab via gspread.append_row()."""
    import gspread
    base = _ops_ledger_dir()

    def rp(p):
        path = Path(p)
        return path if path.is_absolute() else (base / path).resolve()

    cred_path = rp(config.get("credentials_path", "credentials.json"))
    token_path = rp(config.get("token_path", "token.json"))
    sheet_id = config["spreadsheet_id"]

    creds = _get_credentials(cred_path, token_path)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    raw_log = sh.worksheet("Raw Log")

    for row in rows:
        values = [row[col] for col in COLUMNS]
        raw_log.append_row(values, value_input_option="USER_ENTERED")

    print(f"  SHEET: Appended {len(rows)} row(s) to Raw Log.")


def write_to_flat_logs(rows: list[dict], logs_dir: Path) -> None:
    """Append all rows to master-log.md and the appropriate topic file."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    master_log = logs_dir / "master-log.md"
    contact_mentions = logs_dir / "contact-mentions.md"

    master_lines = []
    topic_lines = {}       # filename → list of lines
    mention_lines = []
    contacts_rows = []

    for row in rows:
        item_type  = row["item_type"]
        entry_date = row["entry_date"]
        entry_time = row["entry_time"]
        desc       = row["description"]
        domain     = row["domain"]
        responsible= row["responsible"]
        due_date   = row["due_date"]
        status     = row["status"]
        notes      = row["notes"]
        source     = row["source_capture"]
        capture_mode = row["capture_mode"]
        given      = row["given_name"]
        family     = row["family_name"]
        org        = row["organization"]
        title_     = row["title"]
        phone      = row["phone"]
        email      = row["email"]

        # master-log.md — every item
        master_lines.append(
            f"- {entry_date} {entry_time} | {item_type} | {domain} | {desc}"
            + (f" | due: {due_date}" if due_date else "")
            + (f" | {responsible}" if responsible else "")
            + (f" | [{source}]" if source else "")
        )

        # topic file (not action_log — already done)
        log_file = ITEM_TYPE_TO_LOG.get(item_type)
        if log_file:
            if log_file not in topic_lines:
                topic_lines[log_file] = []
            if item_type == "contact":
                line = (
                    f"- {entry_date} | {given} {family}".strip()
                    + (f" | {org}" if org else "")
                    + (f" | {title_}" if title_ else "")
                    + (f" | {phone}" if phone else "")
                    + (f" | {email}" if email else "")
                    + (f" | {notes}" if notes else "")
                )
            else:
                line = (
                    f"- {entry_date} | {desc}"
                    + (f" | due: {due_date}" if due_date else "")
                    + (f" | {status}" if status else "")
                    + (f" | {notes}" if notes else "")
                )
            topic_lines[log_file].append(line)

        # contact-mentions.md — any row with a named person
        if given or family:
            full_name = f"{given} {family}".strip()
            mention_lines.append(
                f"{entry_date} | {full_name} | {capture_mode} | {desc}"
                + (f" | {notes}" if notes else "")
            )

        # google-contacts-import.csv — contact items only
        if item_type == "contact":
            contacts_rows.append({
                "Given Name": given,
                "Family Name": family,
                "Organization": org,
                "Title": title_,
                "Phone 1 - Value": phone,
                "Email 1 - Value": email,
                "Notes": notes or desc,
            })

    # Write master-log.md
    with open(master_log, "a", encoding="utf-8") as f:
        f.write("\n".join(master_lines) + "\n")
    print(f"  LOG:   Appended {len(master_lines)} line(s) to master-log.md")

    # Write topic files
    for filename, lines in topic_lines.items():
        path = logs_dir / filename
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  LOG:   Appended {len(lines)} line(s) to {filename}")

    # Write contact-mentions.md
    if mention_lines:
        with open(contact_mentions, "a", encoding="utf-8") as f:
            f.write("\n".join(mention_lines) + "\n")
        print(f"  LOG:   Appended {len(mention_lines)} mention(s) to contact-mentions.md")

    # Write google-contacts-import.csv
    if contacts_rows:
        csv_path = logs_dir / "google-contacts-import.csv"
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=GOOGLE_CONTACTS_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerows(contacts_rows)
        print(f"  LOG:   Appended {len(contacts_rows)} row(s) to google-contacts-import.csv")


def archive_transcript(transcript_path: Path, archive_dir: Path) -> None:
    """Move processed transcript to the Capture-Archive folder."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / transcript_path.name
    shutil.move(str(transcript_path), str(dest))
    print(f"  ARCHIVE: Moved transcript to {dest}")


# ───────────────────────────────────────────────────────────────────────────
# Run modes
# ───────────────────────────────────────────────────────────────────────────

def run_import_test() -> bool:
    print()
    print("=" * 60)
    print("  CAPTURE PIPELINE - IMPORT TEST")
    print("=" * 60)
    try:
        import gspread  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from google.auth.transport.requests import Request  # noqa: F401
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import google.generativeai as genai  # noqa: F401
    except ImportError as e:
        print(f"  FAIL: Missing dependency: {e}")
        print("  Install: pip install -r requirements.txt")
        return False
    print()
    print("  OK: All imports successful.")
    print("=" * 60)
    return True


def run_dry_run(transcript_path: Path) -> None:
    config = load_config()

    print()
    print("=" * 60)
    print("  CAPTURE PIPELINE - DRY RUN")
    print(f"  File: {transcript_path.name}")
    print("=" * 60)

    if not transcript_path.exists():
        print(f"\nERROR: Transcript file not found: {transcript_path}")
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")
    ts = parse_timestamp_from_filename(transcript_path.name)
    today_str = ts.strftime("%Y-%m-%d")
    captured_by = extract_captured_by(transcript_path.name)
    capture_mode = detect_capture_mode(ts)

    print(f"\n  entry_date:    {today_str}")
    print(f"  entry_time:    {ts.strftime('%H:%M')}")
    print(f"  capture_mode:  {capture_mode}")
    print(f"  captured_by:   {captured_by}")
    print(f"  source_capture:{transcript_path.name}")
    print(f"\n  Transcript ({len(transcript)} chars):")
    preview = transcript[:400].replace("\n", " ")
    print(f"  {preview}{'...' if len(transcript) > 400 else ''}")

    logs_dir_str = config.get("logs_dir", "")
    archive_dir_str = config.get("capture_archive_dir", "")
    print(f"\n  logs_dir:      {logs_dir_str or '(not set in config.json)'}")
    print(f"  archive_dir:   {archive_dir_str or '(not set in config.json)'}")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    print(f"\n  GEMINI_API_KEY: {'set (' + str(len(api_key)) + ' chars)' if api_key else 'NOT SET'}")

    print()
    print("  DRY RUN: Would call Gemini and write to sheet + flat files.")
    print("  Run with --confirm to execute.")
    print("=" * 60)


def run_confirm(transcript_path: Path) -> None:
    config = load_config()

    print()
    print("=" * 60)
    print("  CAPTURE PIPELINE - LIVE RUN (--confirm)")
    print(f"  File: {transcript_path.name}")
    print("=" * 60)

    if not transcript_path.exists():
        print(f"\nERROR: Transcript file not found: {transcript_path}")
        sys.exit(1)

    # Validate config paths
    logs_dir_str = config.get("logs_dir", "").strip()
    archive_dir_str = config.get("capture_archive_dir", "").strip()
    if not logs_dir_str:
        print("\nERROR: logs_dir is not set in config.json.")
        print("  Set it to the path of your G:\\My Drive\\Estate Ops\\Logs\\ folder.")
        sys.exit(1)

    logs_dir = _resolve_path(logs_dir_str)
    archive_dir = _resolve_path(archive_dir_str) if archive_dir_str else None

    # Stage 1 — Read transcript
    transcript = transcript_path.read_text(encoding="utf-8")
    ts = parse_timestamp_from_filename(transcript_path.name)
    today_str = ts.strftime("%Y-%m-%d")
    entry_time = ts.strftime("%H:%M")
    captured_by = extract_captured_by(transcript_path.name)
    capture_mode = detect_capture_mode(ts)
    source_capture = transcript_path.name

    print(f"\n  entry_date:   {today_str}")
    print(f"  capture_mode: {capture_mode}")
    print(f"  captured_by:  {captured_by}")

    # Stage 2 — Gemini
    print("\n  Stage 2: Calling Gemini API...")
    raw_rows = call_gemini(transcript, today_str)
    print(f"  Gemini returned {len(raw_rows)} row(s).")

    # Normalize rows (fill pipeline-generated fields)
    rows = [
        normalize_row(r, today_str, entry_time, capture_mode,
                      source_capture, captured_by)
        for r in raw_rows
    ]

    # Preview what will be written
    print()
    for i, row in enumerate(rows, 1):
        print(f"  Row {i}: [{row['item_type']}] {row['description'][:70]}")

    # Stage 3 — Write to all four targets simultaneously
    print()
    print("  Stage 3: Writing to all targets...")
    write_to_sheet(rows, config)
    write_to_flat_logs(rows, logs_dir)

    # Archive transcript
    if archive_dir:
        archive_transcript(transcript_path, archive_dir)
    else:
        print("  ARCHIVE: capture_archive_dir not set — transcript left in place.")

    print()
    print("  OK: Capture pipeline complete.")
    print("=" * 60)


# ───────────────────────────────────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    if "--test" in arg_lower:
        sys.exit(0 if run_import_test() else 1)

    # Get --file argument
    transcript_path = None
    if "--file" in arg_lower:
        idx = arg_lower.index("--file")
        if idx + 1 < len(args):
            transcript_path = _resolve_path(args[idx + 1])
        else:
            print("\nERROR: --file requires a path argument.")
            print("  Example: python capture_pipeline.py --file transcript.md --confirm")
            sys.exit(1)
    else:
        print()
        print("Usage:")
        print("  python capture_pipeline.py --file <transcript.md>")
        print("  python capture_pipeline.py --file <transcript.md> --confirm")
        print("  python capture_pipeline.py --test")
        sys.exit(1)

    if "--confirm" in arg_lower:
        run_confirm(transcript_path)
    else:
        run_dry_run(transcript_path)
