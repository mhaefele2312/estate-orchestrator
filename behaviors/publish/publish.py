"""
Estate OS — Publish Behavior
=============================
Moves files from Accepted/ to Published/ after passing two checks:
  1. All required provenance fields are present
  2. No PII patterns detected in the file content

Files that fail either check are BLOCKED and stay in Accepted/.
Nothing is published without passing both checks.

USAGE:
  python publish.py --test       Run against fake test files (safe, nothing real touched)
  python publish.py --dry-run    Show what would happen with real vault (nothing moves)
  python publish.py --confirm    Actually publish to your real vault

RULES:
  - Default mode is --dry-run. You must type --confirm to make real changes.
  - A single PII match blocks the entire file. Fix it in Accepted/ first.
  - Missing provenance fields block the file. Complete them in gate first.
  - Published files get a published_date field added automatically.
  - Logs are always written regardless of mode.
"""

import sys
import re
import json
import shutil
from datetime import datetime
from pathlib import Path


# ── Load config ───────────────────────────────────────────────────────────────

def load_config():
    """Load paths, PII patterns, and allowlists from config.json."""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("ERROR: config.json not found next to publish.py")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Parse frontmatter ─────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """
    Extract YAML frontmatter from a markdown file.
    Returns (frontmatter_dict, body_text).
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


# ── Check 1: Provenance ───────────────────────────────────────────────────────

def check_provenance(fm, required_fields):
    """
    Verify all required provenance fields are present and non-empty.
    Returns (passed: bool, missing_fields: list).
    """
    missing = []
    for field in required_fields:
        val = fm.get(field, "").strip()
        if not val or val.upper().startswith("PLACEHOLDER"):
            missing.append(field)
    return (len(missing) == 0), missing


# ── Check 2: PII scan ─────────────────────────────────────────────────────────

def check_pii(text, patterns):
    """
    Scan full file text for PII patterns.
    Returns (passed: bool, matches_found: list of descriptions).
    Never prints the matched text itself — only reports that a match was found.
    """
    matches = []
    pii_labels = {
        0: "SSN pattern (###-##-####)",
        1: "9-digit number (possible SSN)",
        2: "Text 'SSN' or 'ssn'",
        3: "Text 'social security'",
        4: "Credit card pattern (####-####-####-####)",
        5: "Account number label with digits",
        6: "Routing number label with digits",
        7: "Phone number pattern",
    }

    for i, pattern in enumerate(patterns):
        try:
            if re.search(pattern, text):
                label = pii_labels.get(i, f"Pattern {i}")
                matches.append(label)
        except re.error:
            pass  # Skip invalid regex patterns silently

    return (len(matches) == 0), matches


# ── Strip financial data from body ────────────────────────────────────────────

def sanitize_body(body, financial_allowlist):
    """
    Replace any financial figures in the body text with [REDACTED].
    This is a conservative pass — removes dollar amounts and large numbers
    that are not part of normal prose.
    Allowed financial field NAMES (from allowlist) are not stripped —
    only raw financial figures in the body text.
    """
    # Dollar amounts: $1,234.56 or $1234
    body = re.sub(r'\$[\d,]+(?:\.\d{1,2})?', '[REDACTED-AMOUNT]', body)
    # Large standalone numbers (possible account numbers, balances): 7+ digit numbers
    body = re.sub(r'\b\d{7,}\b', '[REDACTED-NUMBER]', body)
    return body


def sanitize_frontmatter(fm, financial_allowlist):
    """
    In frontmatter, keep only fields that are either:
    - Required provenance fields
    - In the financial field allowlist
    - Non-financial general fields (visibility, classification, etc.)
    Removes any frontmatter field that looks like a raw financial figure.
    """
    safe_fm = {}
    financial_value_pattern = re.compile(r'^\$?[\d,]+(?:\.\d{1,2})?$')

    for key, val in fm.items():
        # Always keep these
        if key in ["source", "captured_date", "review_timestamp", "reviewer",
                   "derivation_path", "visibility", "classification",
                   "published_date", "decision_rationale"]:
            safe_fm[key] = val
        # Keep allowed financial field names
        elif key in financial_allowlist:
            safe_fm[key] = val
        # Keep if value does not look like a raw financial figure
        elif not financial_value_pattern.match(val.replace(",", "")):
            safe_fm[key] = val
        else:
            # Strip it — log that it was removed
            safe_fm[f"_STRIPPED_{key}"] = "[REMOVED-BY-PUBLISH]"

    return safe_fm


# ── Process one file ──────────────────────────────────────────────────────────

def process_file(filepath, published_dir, config, dry_run):
    """
    Run both checks on a single file and publish it if it passes.
    Returns a result dict describing what happened.
    """
    result = {
        "file": filepath.name,
        "status": None,
        "provenance_ok": False,
        "pii_ok": False,
        "blocked_reasons": [],
        "published_to": None,
    }

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        result["status"] = "ERROR"
        result["blocked_reasons"].append(f"Could not read file: {e}")
        return result

    fm, body = parse_frontmatter(text)

    # Check 1: Provenance
    prov_ok, missing_fields = check_provenance(fm, config["required_provenance_fields"])
    result["provenance_ok"] = prov_ok
    if not prov_ok:
        result["blocked_reasons"].append(
            f"Missing required fields: {', '.join(missing_fields)}"
        )

    # Check 2: PII scan (scan both frontmatter values and body)
    full_text_for_scan = " ".join(fm.values()) + " " + body
    pii_ok, pii_matches = check_pii(full_text_for_scan, config["pii_patterns"])
    result["pii_ok"] = pii_ok
    if not pii_ok:
        result["blocked_reasons"].append(
            f"PII detected ({len(pii_matches)} pattern(s)): {'; '.join(pii_matches)}"
        )

    # If either check failed — block
    if not prov_ok or not pii_ok:
        result["status"] = "BLOCKED"
        return result

    # Both checks passed — sanitize and publish
    clean_fm = sanitize_frontmatter(fm, config["financial_field_allowlist"])
    clean_fm["published_date"] = datetime.now().strftime("%Y-%m-%d")
    clean_body = sanitize_body(body, config["financial_field_allowlist"])
    clean_content = build_frontmatter(clean_fm) + "\n\n" + clean_body

    dest_path = published_dir / filepath.name
    result["published_to"] = str(dest_path)

    if dry_run:
        result["status"] = "WOULD-PUBLISH"
    else:
        published_dir.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(clean_content, encoding="utf-8")
        result["status"] = "PUBLISHED"

    return result


# ── Print result ──────────────────────────────────────────────────────────────

def print_result(result, dry_run):
    """Print a human-readable summary of one file's publish result."""
    status = result["status"]
    name = result["file"]

    if status == "BLOCKED":
        print(f"  BLOCKED: {name}")
        for reason in result["blocked_reasons"]:
            print(f"    Reason: {reason}")
        print(f"    Action needed: Fix this file in Accepted/ then run publish again.")

    elif status == "WOULD-PUBLISH":
        print(f"  DRY RUN: Would publish {name}")
        print(f"    Provenance: OK")
        print(f"    PII scan: OK")

    elif status == "PUBLISHED":
        print(f"  ACTION: Published {name}")
        print(f"    Provenance: OK")
        print(f"    PII scan: OK")

    elif status == "ERROR":
        print(f"  ERROR: {name}")
        for reason in result["blocked_reasons"]:
            print(f"    {reason}")


# ── Log run ───────────────────────────────────────────────────────────────────

def write_log(log_dir, results, dry_run, test_mode):
    """Write a timestamped log of this publish run."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    mode = "TEST" if test_mode else ("DRY-RUN" if dry_run else "LIVE")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"publish_{mode}_{timestamp}.log"

    published = [r for r in results if r["status"] in ("PUBLISHED", "WOULD-PUBLISH")]
    blocked = [r for r in results if r["status"] == "BLOCKED"]
    errors = [r for r in results if r["status"] == "ERROR"]

    lines = [
        f"Publish run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {mode}",
        f"Files reviewed: {len(results)}",
        f"Published: {len(published)}",
        f"Blocked: {len(blocked)}",
        f"Errors: {len(errors)}",
        "",
    ]

    if blocked:
        lines.append("BLOCKED FILES:")
        for r in blocked:
            lines.append(f"  {r['file']}")
            for reason in r["blocked_reasons"]:
                lines.append(f"    - {reason}")
        lines.append("")

    if published:
        lines.append("PUBLISHED FILES:")
        for r in published:
            lines.append(f"  {r['file']}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Log saved: {log_path.name}")


# ── Main publish function ─────────────────────────────────────────────────────

def run_publish(dry_run=True, test_mode=False):
    """
    Main publish function.
    Scans Accepted/, runs checks on each file, publishes passing files.
    """
    config = load_config()

    if test_mode:
        accepted_path = Path(__file__).parent.parent.parent / "tests" / "fake-accepted"
        published_path = Path(__file__).parent.parent.parent / "tests" / "fake-published"
        log_path = Path(__file__).parent.parent.parent / "logs"
        print()
        print("=" * 60)
        print("  PUBLISH — TEST MODE")
        print("  Running against fake test files. Your real vault is untouched.")
        print("=" * 60)
    else:
        accepted_path = Path(config["accepted_path"])
        published_path = Path(config["published_path"])
        log_path = Path(__file__).parent.parent.parent / "logs"

        if "PLACEHOLDER" in str(accepted_path):
            print()
            print("ERROR: Vault paths are not configured yet.")
            print("Open behaviors/publish/config.json and set accepted_path")
            print("and published_path to your Obsidian vault folders.")
            print()
            print("To run safely against test data: python publish.py --test")
            sys.exit(1)

        if dry_run:
            print()
            print("=" * 60)
            print("  PUBLISH — DRY RUN MODE")
            print("  Showing what would happen. Nothing will be published.")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("  PUBLISH — LIVE MODE")
            print("  Files that pass checks will be copied to Published/.")
            print("=" * 60)

    # Scan accepted folder
    if not accepted_path.exists():
        if test_mode:
            print()
            print("  Test Accepted/ folder is empty.")
            print("  Run the gate in test mode first and approve some items.")
            print("  Then run publish --test again.")
            print()
            print("  DONE: 0 files reviewed.")
            return
        else:
            print(f"  ERROR: Accepted/ folder not found at: {accepted_path}")
            sys.exit(1)

    accepted_files = sorted(accepted_path.glob("*.md"))

    if not accepted_files:
        print()
        print("  Accepted/ folder is empty. Nothing to publish.")
        print("  Run the gate first to move items from Inbox to Accepted.")
        print()
        print("  DONE: 0 files reviewed.")
        return

    print()
    print(f"  Found {len(accepted_files)} file(s) in Accepted/.")
    print()

    results = []
    for filepath in accepted_files:
        result = process_file(
            filepath, published_path, config,
            dry_run=(dry_run and not test_mode)
        )
        print_result(result, dry_run)
        results.append(result)
        print()

    # Summary
    published_count = sum(1 for r in results if r["status"] in ("PUBLISHED", "WOULD-PUBLISH"))
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED")

    print("=" * 60)
    print(f"  DONE: Reviewed {len(results)} file(s)")
    print(f"        Published: {published_count}")
    print(f"        Blocked (need fixes): {blocked_count}")
    if blocked_count > 0:
        print(f"        Fix blocked files in Accepted/ and run publish again.")
    print("=" * 60)

    write_log(log_path, results, dry_run, test_mode)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--test" in args:
        run_publish(dry_run=True, test_mode=True)
    elif "--confirm" in args:
        print()
        confirm = input("You are about to publish to your REAL vault. Type YES to continue: ")
        if confirm.strip() == "YES":
            run_publish(dry_run=False, test_mode=False)
        else:
            print("Cancelled. Nothing published.")
    elif "--dry-run" in args or len(args) == 0:
        run_publish(dry_run=True, test_mode=False)
    else:
        print()
        print("Usage:")
        print("  python publish.py --test      Safe: run against fake test files")
        print("  python publish.py --dry-run   Show what would happen (real vault, no changes)")
        print("  python publish.py --confirm   Actually publish to real vault")
