"""
Estate OS — Silver Classifier
==============================
Reads files from a staging folder, extracts text, scores each file against
domain keyword lists, suggests a domain folder and filename, prompts MHH
for confirmation, and files to the Silver vault with provenance tracking.

This is the intake pipeline for legacy documents into the Silver vault.
Files are COPIED to Silver — originals in the source folder are never deleted.

TOKEN FORMAT FOR FILENAMES:
  YYYY-MM-DD-{document-type}{.ext}
  e.g.  2018-04-15-tax-return.md
        2019-01-31-bank-statement.pdf
        2017-03-04-document.md       (when type cannot be determined)

USAGE:
  python silver_classifier.py --source "G:\\My Drive\\Staging-Intake\\drive-2026-03-31"
      Dry-run. Shows classification suggestion for every file. Nothing filed.

  python silver_classifier.py --source <path> --confirm
      Interactive. Shows each file one at a time, waits for approval, files to Silver.

  python silver_classifier.py --test
      Dry-run against tests/fake-staging/. No real vault required.

  python silver_classifier.py --test --confirm
      Interactive filing against test folders. No real vault required.

INTERACTIVE COMMANDS (--confirm mode):
  Enter     Accept the suggestion exactly as shown
  1-12      Change the domain folder (keeps suggested filename)
  r         Rename — type a new filename yourself
  s         Skip this file — leave in staging, come back later
  d         Flag for delete-review — moves to _review_delete/ in source folder
  q         Quit — stops after current file, keeps all progress so far

RULES:
  - Default is dry-run. --confirm required to file anything.
  - Files are COPIED to Silver. Source files are never deleted or modified.
  - Low-confidence files (score < 0.15) are suggested for 00_Unsorted.
    You can always override with a domain number.
  - Every filed document gets a provenance record in Silver/_provenance/.
  - Safe to re-run: if a file was already filed, the copy gets a counter suffix
    and both copies are kept. Review and remove duplicates manually.
"""

import sys
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


# ── Domain definitions ────────────────────────────────────────────────────────

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

DOMAIN_KEYWORDS = {
    "01_Financial": [
        "bank statement", "balance", "deposit", "withdrawal", "routing number",
        "checking", "savings", "investment", "brokerage", "statement period",
        "beginning balance", "ending balance", "transaction", "vanguard",
        "fidelity", "schwab", "dividend", "interest earned", "wire transfer",
        "401k", "401(k)", "ira", "roth", "account number", "account ending",
        "direct deposit", "financial statement", "wire",
    ],
    "02_Legal": [
        "agreement", "contract", "plaintiff", "defendant", "attorney", "esq",
        "counsel", "hereby", "whereas", "notary", "affidavit", "power of attorney",
        "warranty", "indemnify", "jurisdiction", "court", "settlement",
        "arbitration", "law firm", "legal notice", "executed", "in witness whereof",
        "the parties", "governing law",
    ],
    "03_Property": [
        "deed", "mortgage", "parcel", "lot number", "survey", "hoa",
        "homeowner association", "assessment", "appraisal", "title",
        "zoning", "easement", "closing", "listing", "square feet",
        "property tax", "escrow", "lien", "rental", "tenant", "lease",
        "real estate", "property address", "recorded",
    ],
    "04_Insurance": [
        "policy number", "premium", "coverage", "deductible", "beneficiary",
        "claim", "insured", "policyholder", "underwriter", "renewal",
        "declaration", "auto insurance", "home insurance", "life insurance",
        "health insurance", "umbrella policy", "rider", "exclusion",
        "policy effective", "policy type", "insurance company",
    ],
    "05_Medical": [
        "patient", "diagnosis", "prescription", "physician", "explanation of benefits",
        "eob", "hospital", "clinic", "medication", "treatment", "procedure",
        "lab result", "copay", "provider", "referral", "specialist",
        "medical record", "date of service", "health plan", "npi",
        "attending", "discharge",
    ],
    "06_Tax": [
        "1040", "w-2", "w2", "1099", "schedule a", "schedule b", "schedule c",
        "schedule d", "irs", "internal revenue service", "tax return", "refund",
        "tax withheld", "adjusted gross income", "federal tax", "state tax",
        "filing status", "taxpayer", "taxable income", "tax deduction",
        "tax credit", "form 1040", "standard deduction",
    ],
    "07_Estate-Planning": [
        "trust", "last will", "testament", "grantor", "trustee",
        "successor trustee", "bequest", "inheritance", "probate", "executor",
        "healthcare proxy", "living will", "revocable", "irrevocable",
        "pour-over", "fiduciary", "beneficiary designation", "decedent",
        "estate plan",
    ],
    "08_Vehicles": [
        "vehicle identification", "vin", "odometer", "make and model",
        "model year", "license plate", "dmv", "motor vehicle", "automobile",
        "service record", "oil change", "dealer", "title transfer",
        "registration renewal", "vehicle registration",
    ],
    "09_Digital": [
        "password", "username", "login", "credential", "api key", "domain name",
        "hosting", "subscription", "software license", "two-factor",
        "authenticator", "digital account", "online account", "secret key",
    ],
    "10_Family": [
        "birth certificate", "marriage certificate", "divorce decree",
        "school transcript", "diploma", "passport", "vaccination record",
        "immunization", "report card", "adoption", "social security card",
        "naturalization", "citizenship",
    ],
    "11_Contacts": [
        "contact information", "address book", "professional directory",
        "business card", "referral list", "contact list",
    ],
    "12_Operations": [
        "system configuration", "backup log", "maintenance schedule",
        "operations manual", "checklist", "procedure manual", "inventory list",
    ],
}

# Default filename description per domain
DOMAIN_DOC_TYPE = {
    "01_Financial": "financial-document",
    "02_Legal":     "legal-document",
    "03_Property":  "property-document",
    "04_Insurance": "insurance-document",
    "05_Medical":   "medical-record",
    "06_Tax":       "tax-document",
    "07_Estate-Planning": "estate-planning-document",
    "08_Vehicles":  "vehicle-document",
    "09_Digital":   "digital-account-record",
    "10_Family":    "family-record",
    "11_Contacts":  "contact-record",
    "12_Operations":"operations-document",
    "00_Unsorted":  "document",
}

# Specific doc type patterns — checked in order, first match wins
# (regex, filename description)
SPECIFIC_DOC_PATTERNS = [
    (r'\bform\s+1040\b|\btax\s+return\b',                       "tax-return"),
    (r'\bw-?2\b',                                               "w2"),
    (r'\b1099-?\w*\b',                                          "1099"),
    (r'\bbank\s+statement\b',                                   "bank-statement"),
    (r'\b401\s*\(?\s*k\s*\)?\b',                               "401k-statement"),
    (r'\bira\s+statement\b',                                    "ira-statement"),
    (r'\bdeed\b',                                               "deed"),
    (r'\bmortgage\s+(statement|document|notice)\b',             "mortgage-document"),
    (r'\blease\s+agreement\b|\brental\s+agreement\b',           "lease-agreement"),
    (r'\bpolicy\s+declaration\b|\binsurance\s+policy\b',        "insurance-policy"),
    (r'\bexplanation\s+of\s+benefits\b|\beob\b',                "eob"),
    (r'\bprescription\b',                                       "prescription"),
    (r'\blast\s+will\b|\btestament\b',                          "will"),
    (r'\brevocable\s+trust\b|\birrevocable\s+trust\b|\bliving\s+trust\b', "trust-document"),
    (r'\bpower\s+of\s+attorney\b',                              "power-of-attorney"),
    (r'\bvehicle\s+title\b|\bcar\s+title\b',                   "vehicle-title"),
    (r'\bvehicle\s+registration\b|\bregistration\s+renewal\b', "vehicle-registration"),
]

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

# ── Financial statement detail extractors ─────────────────────────────────────
#
# Filename format for financial documents:
#   YYYY_MM_DD_Institution_Type of Statement_account number{.ext}
#   e.g. 2019_01_31_First National Bank_Monthly Statement_3918.pdf
#        2023_12_31_Vanguard_Year End Statement_8823-9910.pdf
#        2023_12_31_Fidelity_1099-DIV_3918.pdf

# Known institutions: (regex pattern, display name for filename)
# Checked case-insensitively. First match wins.
KNOWN_INSTITUTIONS = [
    (r'\bvanguard\b',                       "Vanguard"),
    (r'\bfidelity\b',                       "Fidelity"),
    (r'\bcharles\s+schwab\b|\bschwab\b',    "Charles Schwab"),
    (r'\btd\s+ameritrade\b',                "TD Ameritrade"),
    (r'\be[\*\s]?trade\b',                  "E-Trade"),
    (r'\bmerrill\s+(?:lynch|edge)\b',       "Merrill"),
    (r'\bjp\s*morgan\b|\bjpmorgan\b',       "JPMorgan"),
    (r'\bchase\b',                          "Chase"),
    (r'\bbank\s+of\s+america\b',            "Bank of America"),
    (r'\bwells\s+fargo\b',                  "Wells Fargo"),
    (r'\bcitibank\b|\bciti\b',              "Citi"),
    (r'\bus\s+bank\b',                      "US Bank"),
    (r'\btd\s+bank\b',                      "TD Bank"),
    (r'\bpnc\b',                            "PNC"),
    (r'\bcapital\s+one\b',                  "Capital One"),
    (r'\bcitizens\s+bank\b',                "Citizens Bank"),
    (r'\bsantander\b',                      "Santander"),
    (r'\btiaa\b',                           "TIAA"),
    (r'\bprudential\b',                     "Prudential"),
    (r'\blincoln\s+financial\b',            "Lincoln Financial"),
    (r'\bjohn\s+hancock\b',                 "John Hancock"),
    (r'\bprincipal\b',                      "Principal"),
    (r'\brobinhood\b',                      "Robinhood"),
    (r'\bbetterment\b',                     "Betterment"),
    (r'\bwealthfront\b',                    "Wealthfront"),
    (r'\bamerican\s+express\b|\bamex\b',    "American Express"),
    (r'\bdiscover\b',                       "Discover"),
]

# Statement type patterns: (regex, display label)
# Checked in order — more specific patterns first.
STATEMENT_TYPE_PATTERNS = [
    (r'\b1099-int\b',                                   "1099-INT"),
    (r'\b1099-div\b',                                   "1099-DIV"),
    (r'\b1099-b\b',                                     "1099-B"),
    (r'\b1099-r\b',                                     "1099-R"),
    (r'\b1099-misc\b',                                  "1099-MISC"),
    (r'\b1099-nec\b',                                   "1099-NEC"),
    (r'\b1099\b',                                       "1099"),
    (r'\bw-2g\b',                                       "W-2G"),
    (r'\bw-?2\b|\bwage\s+and\s+tax\s+statement\b',     "W-2"),
    (r'\byear[\s-]end\s+statement\b|\bannual\s+statement\b', "Year End Statement"),
    (r'\bquarterly\s+statement\b',                      "Quarterly Statement"),
    (r'\bmonthly\s+statement\b',                        "Monthly Statement"),
]

# Last day of each month (non-leap year; Feb 28 covers most cases)
_MONTH_END = {
    "01": 31, "02": 28, "03": 31, "04": 30, "05": 31, "06": 30,
    "07": 31, "08": 31, "09": 30, "10": 31, "11": 30, "12": 31,
}
# Quarter end months
_QUARTER_END_MONTHS = {"03", "06", "09", "12"}


def _parse_date_match(month_str: str, day_str: str, year_str: str) -> str:
    """Convert month name / day / year strings to YYYY-MM-DD."""
    month = MONTH_MAP.get(month_str.lower(), "00")
    day   = f"{int(day_str):02d}"
    return f"{year_str}-{month}-{day}"


def extract_statement_end_date(text: str) -> str:
    """
    Extract the END date of a financial statement period.
    Looks for explicit end-of-period signals before falling back to any date.

    Signal phrases: "to", "through", "thru", "through", "ending", "as of",
    "statement date", "period end", "closing date".

    Returns YYYY-MM-DD, YYYY-MM, or YYYY. Returns None if nothing found.
    """
    tl = text.lower()
    month_names = (
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)"
    )

    # ── Patterns that signal end-of-period ────────────────────────────────────

    # "to January 31, 2019" / "through January 31 2019" / "thru Jan 31 2019"
    m = re.search(
        rf'\b(?:to|through|thru)\s+{month_names}\s+(\d{{1,2}}),?\s+(20\d{{2}})\b',
        tl,
    )
    if m:
        return _parse_date_match(m.group(1), m.group(2), m.group(3))

    # "to 12/31/2019" / "through 2019-12-31"
    m = re.search(
        r'\b(?:to|through|thru)\s+(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b', tl
    )
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    m = re.search(
        r'\b(?:to|through|thru)\s+(20\d{2})-(\d{2})-(\d{2})\b', tl
    )
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # "ending January 31, 2019" / "period ending 12/31/2019"
    m = re.search(
        rf'\bending\s+{month_names}\s+(\d{{1,2}}),?\s+(20\d{{2}})\b', tl
    )
    if m:
        return _parse_date_match(m.group(1), m.group(2), m.group(3))

    m = re.search(
        r'\bending\s+(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b', tl
    )
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # "as of January 31, 2019" / "as of 12/31/2019"
    m = re.search(
        rf'\bas\s+of\s+{month_names}\s+(\d{{1,2}}),?\s+(20\d{{2}})\b', tl
    )
    if m:
        return _parse_date_match(m.group(1), m.group(2), m.group(3))

    m = re.search(
        r'\bas\s+of\s+(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b', tl
    )
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # "statement date: December 31, 2019" / "closing date: 12/31/2019"
    m = re.search(
        rf'\b(?:statement|closing|period\s+end)\s+date:?\s+{month_names}\s+(\d{{1,2}}),?\s+(20\d{{2}})\b',
        tl,
    )
    if m:
        return _parse_date_match(m.group(1), m.group(2), m.group(3))

    m = re.search(
        r'\b(?:statement|closing|period\s+end)\s+date:?\s+(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b',
        tl,
    )
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # No end-of-period signal found — return None so caller falls back to extract_date()
    return None


def extract_institution(text: str) -> str:
    """
    Return the institution display name from the text, or empty string.
    Checks KNOWN_INSTITUTIONS list first (case-insensitive).
    Falls back to looking for '[Words] Bank' or '[Words] Financial' near
    the top of the document, where institution names typically appear.
    """
    for pattern, name in KNOWN_INSTITUTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return name

    # Fallback: institution name is usually in the first few lines
    first_500 = text[:500]
    m = re.search(
        r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\s+'
        r'(?:Bank|Financial|Credit Union|Savings|Investments?)\b',
        first_500,
    )
    if m:
        return m.group(0).strip()

    return ""


def extract_statement_type(text: str, end_date: str) -> str:
    """
    Return the statement type label for the filename.
    Checks explicit keywords first, then infers from the end date.

    Examples: "Monthly Statement", "Year End Statement", "Quarterly Statement",
              "1099-DIV", "W-2", "Statement"
    """
    tl = text.lower()

    # Check explicit patterns first (most specific to least)
    for pattern, label in STATEMENT_TYPE_PATTERNS:
        if re.search(pattern, tl):
            return label

    # Infer from end date if we have one in YYYY-MM-DD format
    if end_date and len(end_date) == 10:
        month = end_date[5:7]
        day   = end_date[8:10]
        # December 31 → Year End Statement
        if month == "12" and day == "31":
            return "Year End Statement"
        # Last day of a quarter → Quarterly Statement
        if month in _QUARTER_END_MONTHS and int(day) >= _MONTH_END.get(month, 30) - 1:
            return "Quarterly Statement"
        # Last day of any month → Monthly Statement
        if int(day) >= _MONTH_END.get(month, 30) - 1:
            return "Monthly Statement"

    return "Statement"


def extract_account_number(text: str) -> str:
    """
    Extract an account identifier for use in the filename.
    Returns only the last 4 digits for long numeric accounts (bank/investment).
    Returns the full identifier for policy numbers and formatted account IDs.
    Returns empty string if nothing found.

    Never returns a value that looks like a full SSN (NNN-NN-NNNN format).
    """
    tl = text.lower()

    # "account ending 3918" / "ending in 3918" / "account number ending 3918"
    m = re.search(r'\baccount\b[^.]{0,30}ending\s+(\d{4})\b', tl)
    if m:
        return m.group(1)

    # "account ending: 3918" or bare "ending XXXX" near account context
    m = re.search(r'\bending\s+(\d{4})\b', tl)
    if m:
        return m.group(1)

    # "policy number: SL-2019-774421" / "policy no: SL-774421"
    m = re.search(r'\bpolicy\s+(?:number|no\.?):?\s*([A-Z0-9][A-Z0-9\-]{3,20})', text)
    if m:
        return m.group(1)

    # "account number: 8823-9910" — formatted with hyphens (investment style)
    m = re.search(r'\baccount\s+(?:number|no\.?):?\s*([0-9]{4}-[0-9\-]{3,12})', tl)
    if m:
        return m.group(1)

    # "account number: 88239910" — long numeric, use last 4
    m = re.search(r'\baccount\s+(?:number|no\.?):?\s*(\d{6,17})\b', tl)
    if m:
        return m.group(1)[-4:]

    # "account: XXXX" near top of document — last 4 if numeric
    m = re.search(r'\baccount:?\s+(\d{4,})\b', tl)
    if m:
        return m.group(1)[-4:]

    return ""


def suggest_financial_filename(text: str, original_path: Path) -> str:
    """
    Build a filename for a financial document.

    Format: YYYY_MM_DD_Institution_Type of Statement_account number{.ext}
    e.g.    2019_01_31_First National Bank_Monthly Statement_3918.pdf
            2023_12_31_Vanguard_Year End Statement_8823-9910.pdf
            2023_12_31_Fidelity_1099-DIV_3918.pdf

    Falls back gracefully when any piece is missing.
    """
    ext         = original_path.suffix.lower()
    end_date    = extract_statement_end_date(text) or extract_date(text)
    institution = extract_institution(text)
    stmt_type   = extract_statement_type(text, end_date or "")
    acct_num    = extract_account_number(text)

    # Format date as YYYY_MM_DD (underscores)
    if end_date:
        date_part = end_date.replace("-", "_")
    else:
        stem = re.sub(r'[^\w]', '_', original_path.stem.lower())[:20]
        date_part = stem

    parts = [date_part]
    if institution:
        parts.append(institution)
    parts.append(stmt_type)
    if acct_num:
        parts.append(acct_num)

    return "_".join(parts) + ext


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(path: Path) -> tuple:
    """
    Extract text from a file.  Returns (text, method_label).
    method_label describes how text was obtained, shown in the UI.

    For PDFs: tries pdfplumber (text layer) first, then easyocr (scanned).
    For .md/.txt: plain read.
    """
    ext = path.suffix.lower()

    if ext in (".md", ".txt"):
        try:
            return path.read_text(encoding="utf-8", errors="ignore"), "text"
        except Exception as e:
            return "", f"error: {e}"

    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages).strip()
            if len(text) >= 50:
                return text, "pdf-text"
        except Exception:
            pass

        # Fall back to OCR — warn the user it may be slow
        print("    [ocr] Scanned PDF — running OCR (may take a moment)...")
        try:
            import easyocr
            import pypdfium2 as pdfium
            import io

            reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            doc = pdfium.PdfDocument(str(path))
            all_text = []
            for page in doc:
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()
                buf = io.BytesIO()
                pil_image.save(buf, format="PNG")
                buf.seek(0)
                results = reader.readtext(buf.read(), detail=0, paragraph=True)
                all_text.append(" ".join(results))
            return "\n".join(all_text).strip(), "pdf-ocr"
        except Exception as e:
            return "", f"pdf-error: {e}"

    return "", "unsupported"


# ── Classification ────────────────────────────────────────────────────────────

def score_domains(text: str) -> list:
    """
    Score text against each domain's keyword list.
    Returns list of (domain, score) sorted descending.
    Score = fraction of the domain's keyword list that was found in the text.
    """
    text_lower = text.lower()
    scores = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        matched = sum(1 for kw in keywords if kw in text_lower)
        score = matched / len(keywords) if keywords else 0.0
        scores.append((domain, round(score, 3)))
    return sorted(scores, key=lambda x: x[1], reverse=True)


def extract_date(text: str) -> str:
    """
    Find the most useful date in the text.
    Returns a YYYY-MM-DD string, a YYYY-MM string, or a YYYY string.
    Returns None if no date is found.
    Prefers full dates over year-only. Uses the first full date found.
    """
    text_lower = text.lower()

    # YYYY-MM-DD
    m = re.search(r'\b(20[0-2]\d)[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b', text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # MM/DD/YYYY or MM-DD-YYYY
    m = re.search(r'\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](20[0-2]\d)\b', text)
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"

    # Month DD, YYYY or Month DD YYYY
    m = re.search(
        r'\b(january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\s+(\d{1,2}),?\s+(20[0-2]\d)\b',
        text_lower,
    )
    if m:
        return f"{m.group(3)}-{MONTH_MAP[m.group(1)]}-{int(m.group(2)):02d}"

    # Month YYYY
    m = re.search(
        r'\b(january|february|march|april|may|june|july|august|'
        r'september|october|november|december)\s+(20[0-2]\d)\b',
        text_lower,
    )
    if m:
        return f"{m.group(2)}-{MONTH_MAP[m.group(1)]}"

    # Year only — last resort
    m = re.search(r'\b(20[0-2]\d)\b', text)
    if m:
        return m.group(1)

    return None


def suggest_doc_type(text: str, domain: str) -> str:
    """Return a specific document type description if the text matches a known pattern."""
    text_lower = text.lower()
    for pattern, description in SPECIFIC_DOC_PATTERNS:
        if re.search(pattern, text_lower):
            return description
    return DOMAIN_DOC_TYPE.get(domain, "document")


def suggest_filename(text: str, domain: str, original_path: Path) -> str:
    """
    Build a suggested filename for any domain.

    Financial documents (01_Financial) get a richer format:
      YYYY-MM-DD-{institution}-{account-type}{.ext}
      e.g. 2019-01-31-first-national-bank-checking.pdf

    All other domains use:
      YYYY-MM-DD-{doc-type}{.ext}
      e.g. 2018-04-15-tax-return.pdf
    """
    if domain == "01_Financial":
        return suggest_financial_filename(text, original_path)

    date     = extract_date(text)
    doc_type = suggest_doc_type(text, domain)
    ext      = original_path.suffix.lower()

    if date:
        return f"{date}-{doc_type}{ext}"
    else:
        stem = re.sub(r'[^\w-]', '-', original_path.stem.lower())[:30]
        return f"{stem}-{doc_type}{ext}"


# ── Config loading ────────────────────────────────────────────────────────────

def load_configs() -> tuple:
    behavior_config_path = Path(__file__).parent / "config.json"
    if not behavior_config_path.exists():
        print("ERROR: config.json not found next to silver_classifier.py")
        sys.exit(1)
    with open(behavior_config_path, encoding="utf-8") as f:
        behavior_config = json.load(f)

    vault_config_path = Path(__file__).parent / behavior_config["vault_config_path"]
    if not vault_config_path.exists():
        print(f"ERROR: vault_config.json not found at: {vault_config_path}")
        sys.exit(1)
    with open(vault_config_path, encoding="utf-8") as f:
        vault_config = json.load(f)

    return behavior_config, vault_config


def resolve_silver_path(vault_config: dict, test_mode: bool) -> Path:
    if test_mode:
        repo_root = Path(__file__).parent.parent.parent
        p = repo_root / vault_config.get("_test_vaults", {}).get("silver_vault", "tests/fake-silver-vault")
        if not p.exists():
            print(f"ERROR: Test silver vault not found: {p}")
            sys.exit(1)
        return p

    raw = vault_config.get("silver_vault", "").strip()
    if not raw:
        print("ERROR: silver_vault not configured in vault_config.json")
        sys.exit(1)
    p = Path(raw)
    if not p.exists():
        print(f"ERROR: Silver vault not accessible: {p}")
        print("Unlock the Silver Cryptomator vault (Y:\\) and try again.")
        sys.exit(1)
    return p


# ── File utilities ────────────────────────────────────────────────────────────

def collect_files(source_path: Path, supported_ext: list) -> list:
    """Return all supported files in source_path, excluding _review_delete."""
    return sorted(
        p for p in source_path.rglob("*")
        if p.is_file()
        and p.suffix.lower() in supported_ext
        and "_review_delete" not in p.parts
    )


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


def write_provenance(vault_root: Path, record: dict) -> None:
    log_path = vault_root / "_provenance" / "ingestion-log.jsonl"
    if not log_path.parent.exists():
        return
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def size_label(p: Path) -> str:
    try:
        b = p.stat().st_size
        if b < 1024:       return f"{b}B"
        if b < 1024 ** 2:  return f"{b // 1024}KB"
        return f"{b // (1024 ** 2)}MB"
    except Exception:
        return "?"


# ── Dry-run ───────────────────────────────────────────────────────────────────

def run_dry_run(source_path: Path, silver_root: Path,
                behavior_config: dict) -> None:
    supported = behavior_config["supported_extensions"]
    low_conf  = behavior_config["unsorted_threshold"]
    files     = collect_files(source_path, supported)

    print()
    print("=" * 60)
    print("  SILVER CLASSIFIER — DRY RUN")
    print(f"  Source:  {source_path}")
    print(f"  Silver:  {silver_root}")
    print("=" * 60)
    print()

    if not files:
        print("  No supported files found in source folder.")
        print()
        return

    print(f"  {len(files)} file(s) to classify:\n")

    for f in files:
        text, method = extract_text(f)
        scores = score_domains(text)
        best_domain, best_score = scores[0]

        if best_score < low_conf:
            best_domain = "00_Unsorted"

        suggested = suggest_filename(text, best_domain, f)
        conf_label = f"{best_score:.2f}"

        print(f"  {f.name}  ({size_label(f)})  [{method}]")
        print(f"    Suggested: {best_domain} / {suggested}")
        print(f"    Confidence: {conf_label}", end="")
        if best_score < low_conf:
            print("  (low — routed to 00_Unsorted)")
        else:
            print()

        # Show runner-up if close
        if len(scores) > 1 and scores[1][1] > 0:
            print(f"    Runner-up:  {scores[1][0]}  ({scores[1][1]:.2f})")
        print()

    print("  Run with --confirm to classify interactively.")
    print()


# ── Live interactive run ──────────────────────────────────────────────────────

def run_confirm(source_path: Path, silver_root: Path,
                behavior_config: dict, log_path: Path) -> None:
    supported = behavior_config["supported_extensions"]
    low_conf  = behavior_config["unsorted_threshold"]
    files     = collect_files(source_path, supported)
    review_delete = source_path / "_review_delete"

    print()
    print("=" * 60)
    print("  SILVER CLASSIFIER — LIVE")
    print(f"  Source:  {source_path}")
    print(f"  Silver:  {silver_root}")
    print("=" * 60)
    print()

    if not files:
        print("  No supported files found in source folder.")
        return

    print(f"  {len(files)} file(s) to review.")
    print("  Commands: Enter=Accept  1-12=Change domain  r=Rename  s=Skip  d=Delete-review  q=Quit")

    counts = {"filed": 0, "skipped": 0, "flagged": 0}

    for i, f in enumerate(files, 1):
        print()
        print(f"  {'-' * 56}")
        print(f"  [{i}/{len(files)}]  {f.name}  ({size_label(f)})")
        print()

        text, method = extract_text(f)

        # Show text preview
        preview_lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:6]
        if preview_lines:
            print("  Preview:")
            for ln in preview_lines:
                print(f"    {ln[:72]}")
        else:
            print("  Preview: (no text extracted)")
        print()

        # Classification
        scores = score_domains(text)
        best_domain, best_score = scores[0]
        if best_score < low_conf:
            best_domain = "00_Unsorted"

        suggested_name = suggest_filename(text, best_domain, f)
        conf_label = f"{best_score:.2f}"

        print(f"  Suggested domain:    {best_domain}")
        print(f"  Suggested filename:  {suggested_name}")
        print(f"  Confidence:          {conf_label}", end="")
        if best_score < low_conf:
            print("  (low — defaulting to 00_Unsorted)")
        else:
            print()
        if len(scores) > 1 and scores[1][1] > 0:
            print(f"  Runner-up:           {scores[1][0]}  ({scores[1][1]:.2f})")

        # Interactive decision loop
        final_domain   = best_domain
        final_filename = suggested_name

        while True:
            print()
            raw = input("  [Enter/1-12/r/s/d/q]: ").strip().lower()

            if raw == "":
                # Accept suggestion
                break

            elif raw in ("q", "quit"):
                print()
                print("  Quitting. Progress saved.")
                _print_summary(counts)
                _write_log(log_path, source_path, counts)
                return

            elif raw == "s":
                print("  Skipped — left in staging.")
                counts["skipped"] += 1
                final_domain = None
                break

            elif raw == "d":
                review_delete.mkdir(parents=True, exist_ok=True)
                dest = review_delete / f.name
                shutil.move(str(f), str(dest))
                print(f"  Moved to delete-review: {dest.name}")
                counts["flagged"] += 1
                final_domain = None
                break

            elif raw == "r":
                new_name = input("  New filename (with extension): ").strip()
                if new_name:
                    final_filename = new_name
                    print(f"  Filename set to: {final_filename}")
                else:
                    print("  No name entered — keeping suggestion.")

            elif raw.isdigit() and 1 <= int(raw) <= 12:
                final_domain = DOMAINS[int(raw)]
                print(f"  Domain changed to: {final_domain}")

            else:
                print("  Type Enter, a number 1-12, r, s, d, or q.")

        if final_domain is None:
            continue

        # File the document
        dest_dir  = silver_root / final_domain
        src_copy  = Path(f.parent) / final_filename      # temp rename for copy
        dest_path = safe_copy(f, dest_dir)

        # Rename the destination file to the suggested name if different
        if dest_path.name != final_filename:
            renamed = dest_path.parent / final_filename
            counter = 1
            while renamed.exists():
                stem = Path(final_filename).stem
                ext  = Path(final_filename).suffix
                renamed = dest_path.parent / f"{stem}_{counter}{ext}"
                counter += 1
            dest_path.rename(renamed)
            dest_path = renamed

        write_provenance(silver_root, {
            "timestamp":          datetime.now().isoformat(),
            "original_name":      f.name,
            "filed_name":         dest_path.name,
            "source_path":        str(f),
            "destination":        str(dest_path),
            "vault":              "silver",
            "domain":             final_domain,
            "method":             "silver_classifier",
            "extraction_method":  method,
            "confidence":         best_score,
            "classifier_version": "phase-a-keyword",
        })

        print(f"  Filed -> Silver/{final_domain}/{dest_path.name}")
        counts["filed"] += 1

    print()
    _print_summary(counts)
    _write_log(log_path, source_path, counts)


def _print_summary(counts: dict) -> None:
    print("=" * 60)
    print(f"  Filed:        {counts['filed']}")
    print(f"  Skipped:      {counts['skipped']}")
    print(f"  Delete-review:{counts['flagged']}")
    print("=" * 60)
    print()


# ── Logging ───────────────────────────────────────────────────────────────────

def _write_log(log_path: Path, source_path: Path, counts: dict) -> None:
    try:
        log_path.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"silver_classifier_{ts}.log"
        lines = [
            f"Silver Classifier — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source:        {source_path}",
            f"Filed:         {counts['filed']}",
            f"Skipped:       {counts['skipped']}",
            f"Delete-review: {counts['flagged']}",
        ]
        (log_path / name).write_text("\n".join(lines), encoding="utf-8")
        print(f"  Log saved: {name}")
    except Exception as e:
        print(f"  (log not saved: {e})")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    behavior_config, vault_config = load_configs()
    log_path = Path(__file__).parent / behavior_config["log_path"]

    test_mode   = "--test" in arg_lower
    confirm     = "--confirm" in arg_lower
    source_path = None

    if "--source" in arg_lower:
        idx = arg_lower.index("--source")
        if idx + 1 < len(args):
            source_path = Path(args[idx + 1])

    if not test_mode and source_path is None:
        print()
        print("Usage:")
        print("  python silver_classifier.py --source <staging-folder>")
        print("  python silver_classifier.py --source <path> --confirm")
        print("  python silver_classifier.py --test")
        print("  python silver_classifier.py --test --confirm")
        print()
        sys.exit(1)

    if test_mode and source_path is None:
        source_path = Path(__file__).parent.parent.parent / "tests" / "fake-staging"

    if not source_path.exists():
        print(f"ERROR: Source folder not found: {source_path}")
        sys.exit(1)

    silver_root = resolve_silver_path(vault_config, test_mode)

    if confirm:
        run_confirm(source_path, silver_root, behavior_config, log_path)
    else:
        run_dry_run(source_path, silver_root, behavior_config)
