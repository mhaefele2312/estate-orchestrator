"""
Estate OS — Vault Tokenizer (Layer 4)
======================================
Reads documents from Gold or Silver vault, detects PII using Microsoft
Presidio, replaces each sensitive value with a named token, and writes
the sanitized version to the Token Store. The Token Registry maps every
token back to its original value and is kept separate from the tokenized
documents.

Tokenized documents are safe for local LLM ingestion (RAG layer).
The Token Registry is sensitive and never leaves the estate laptop.

TOKEN FORMAT:
  [TYPE_NNNN]  e.g. [SSN_0001], [ACCT_0001], [EMAIL_0001], [PHONE_0001]

  Same original value always maps to the same token — across documents.
  If the same SSN appears in 5 files, it gets [SSN_0001] everywhere,
  allowing the RAG system to cross-reference documents by entity.

TOKEN STORE STRUCTURE:
  <token_store>/
  ├── gold/                    Tokenized Gold vault documents (mirrors vault structure)
  │   ├── 06_Tax/
  │   │   └── 2024-federal-tax-return.md   (PII replaced with tokens)
  │   └── ...
  ├── silver/                  Tokenized Silver vault documents
  └── _registry/
      └── token_registry.json  Maps token → original value (SENSITIVE)

USAGE:
  python vault_tokenizer.py --vault gold
      Dry-run. Shows what PII would be found and what tokens would be assigned.
      No files written.

  python vault_tokenizer.py --vault gold --confirm
      Tokenizes all supported files in Gold vault. Writes to Token Store.

  python vault_tokenizer.py --vault silver --confirm
      Tokenizes all supported files in Silver vault.

  python vault_tokenizer.py --vault gold --file 06_Tax/2024-federal-tax-return.md
      Process a single file (relative path from vault root). Dry-run.

  python vault_tokenizer.py --vault gold --file 06_Tax/2024-federal-tax-return.md --confirm
      Process a single file. Write output.

  python vault_tokenizer.py --test
      Run against dummy test documents. No real vault required.

RULES:
  - Default is dry-run. --confirm required to write tokenized files.
  - Gold vault is never modified. Only the Token Store is written to.
  - Token Registry is append-only. New tokens are added; existing tokens
    are never changed or removed.
  - Re-running is safe: if a file has not changed (same SHA-256), it is
    skipped. Changed files are re-tokenized.
  - Unsupported file types (.pdf etc.) are skipped with a note. PDF
    support requires an OCR step (planned for Phase 5).

DEPENDENCIES:
  pip install presidio-analyzer presidio-anonymizer spacy
  python -m spacy download en_core_web_sm
"""

import sys
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider


# ── PDF text extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.

    Strategy:
      1. Try pdfplumber — works for digital PDFs (selectable text).
         If it returns meaningful text (>= 50 chars), use it.
      2. Fall back to easyocr — for scanned PDFs (images of paper).
         Converts each page to an image and runs OCR.

    Returns plain text string. Never raises — returns empty string on failure
    and prints a warning so the file is logged as unreadable rather than
    crashing the run.
    """
    import pdfplumber

    # --- attempt 1: text layer ---
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if len(text) >= 50:
            return text
    except Exception as e:
        print(f"    [pdf-warn] pdfplumber failed on {pdf_path.name}: {e}")

    # --- attempt 2: OCR ---
    print(f"    [pdf-ocr]  no text layer found, running OCR on {pdf_path.name}...")
    try:
        import easyocr
        import fitz  # PyMuPDF — ships with pdfplumber's dependency pypdfium2 is not fitz
        # Use pdfplumber's underlying pypdfium2 to render pages as images
        import pypdfium2 as pdfium
        import io
        from PIL import Image

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        doc = pdfium.PdfDocument(str(pdf_path))
        all_text = []
        for page in doc:
            bitmap = page.render(scale=2)          # 2x scale = ~150 dpi equivalent
            pil_image = bitmap.to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            buf.seek(0)
            results = reader.readtext(buf.read(), detail=0, paragraph=True)
            all_text.append(" ".join(results))
        return "\n".join(all_text).strip()
    except Exception as e:
        print(f"    [pdf-warn] OCR failed on {pdf_path.name}: {e}")
        return ""


# ── Post-Presidio regex: dollar amounts only ──────────────────────────────────
# Amounts are not handled by Presidio built-ins so we catch them after.
# Account and routing numbers are now handled inside Presidio (see below).

AMOUNT_PATTERN = re.compile(
    r'\$[\d,]+(?:\.\d{2})?|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b',
    re.IGNORECASE
)


# ── Token type mapping ────────────────────────────────────────────────────────

PRESIDIO_TO_TOKEN_TYPE = {
    "PERSON":             "NAME",
    "EMAIL_ADDRESS":      "EMAIL",
    "PHONE_NUMBER":       "PHONE",
    "US_SSN":             "SSN",
    "US_BANK_NUMBER":     "ACCT",
    "US_BANK_ACCOUNT":    "ACCT",
    "US_ROUTING_NUMBER":  "ROUTING",
    "CREDIT_CARD":        "CARD",
    "DATE_TIME":          "DATE",
    "LOCATION":           "ADDR",
    "US_ITIN":            "ITIN",
    "MEDICAL_LICENSE":    "MEDLIC",
    "URL":                "URL",
    "IP_ADDRESS":         "IP",
    "US_DRIVER_LICENSE":  "DL",
}


# ── Config loading ────────────────────────────────────────────────────────────

def load_configs():
    behavior_config_path = Path(__file__).parent / "config.json"
    if not behavior_config_path.exists():
        print("ERROR: config.json not found next to vault_tokenizer.py")
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


def resolve_paths(vault_name: str, vault_config: dict, test_mode: bool):
    """Return (vault_root, token_store_root) as Paths."""
    if test_mode:
        test = vault_config.get("_test_vaults", {})
        repo_root = Path(__file__).parent.parent.parent
        vault_root       = repo_root / test.get(f"{vault_name}_vault", f"tests/fake-{vault_name}-vault")
        token_store_root = repo_root / test.get("token_store", "tests/fake-token-store")
    else:
        raw_vault = vault_config.get(f"{vault_name}_vault", "").strip()
        raw_store = vault_config.get("token_store", "").strip()
        if not raw_vault:
            print(f"ERROR: {vault_name}_vault not configured in vault_config.json")
            sys.exit(1)
        if not raw_store:
            print("ERROR: token_store not configured in vault_config.json")
            sys.exit(1)
        vault_root       = Path(raw_vault)
        token_store_root = Path(raw_store)

    if not vault_root.exists():
        print(f"ERROR: Vault not accessible: {vault_root}")
        if not test_mode:
            print("Make sure the Cryptomator vault is unlocked.")
        sys.exit(1)

    return vault_root, token_store_root


# ── Analyzer setup ────────────────────────────────────────────────────────────

def build_custom_recognizers() -> list:
    """
    Return custom PatternRecognizer instances for entity types that Presidio's
    built-ins handle poorly in estate documents.

    US_ROUTING_NUMBER — 9-digit ABA routing numbers.
      Presidio's PHONE_NUMBER recognizer fires on 9-digit strings; our custom
      recognizer wins because it has a higher score and requires routing context.

    US_BANK_ACCOUNT — 8–17 digit account numbers near account-context words.
      Presidio's DATE_TIME recognizer misclassifies long numeric strings (e.g.
      Unix-timestamp-length numbers). Our recognizer scores higher and requires
      account context, so it takes priority.
    """
    routing_recognizer = PatternRecognizer(
        supported_entity="US_ROUTING_NUMBER",
        patterns=[
            Pattern(
                name="routing_number_with_context",
                regex=r"\b\d{9}\b",
                score=0.9,
            )
        ],
        context=["routing", "aba", "transit", "wire"],
    )

    account_recognizer = PatternRecognizer(
        supported_entity="US_BANK_ACCOUNT",
        patterns=[
            Pattern(
                name="account_number_with_context",
                regex=r"\b\d{8,17}\b",
                score=0.9,
            )
        ],
        context=["account", "acct", "checking", "savings", "deposit", "direct"],
    )

    return [routing_recognizer, account_recognizer]


def build_analyzer(pii_types: list, min_score: float) -> AnalyzerEngine:
    """Build and return a configured Presidio AnalyzerEngine."""
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    })
    nlp_engine = provider.create_engine()
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    for recognizer in build_custom_recognizers():
        registry.add_recognizer(recognizer)
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["en"],
    )
    return analyzer


# ── Registry ──────────────────────────────────────────────────────────────────

def load_custom_tokens(registry_dir: Path) -> list:
    """
    Load the user-maintained custom token list from
    <token_store>/_registry/custom_tokens.json.

    Each entry must have:
      "original"  — the exact string to replace (case-insensitive match)
      "type"      — token type, e.g. ADDR, NAME, ACCT, SSN

    Optional fields:
      "token"     — pin this value to a specific token label, e.g. [ADDR_HOME].
                    If omitted, a numbered token is auto-assigned ([ADDR_0001]).
      "note"      — plain-English reminder for your own reference, ignored by code.

    Returns a list of dicts. Returns [] if the file does not exist.
    """
    path = registry_dir / "custom_tokens.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    return entries


def apply_custom_tokens(tokenized: str, source_file: str,
                        custom_entries: list,
                        value_to_token: dict, counters: dict,
                        token_to_meta: dict, findings: list) -> str:
    """
    Apply user-defined custom tokens to the (already Presidio-processed) text.
    Does a case-insensitive exact-string search for each custom entry.
    Skips any span that already contains a token bracket (already replaced).
    Mutates registry dicts and findings list in place.
    """
    for entry in custom_entries:
        original = entry.get("original", "").strip()
        token_type = entry.get("type", "CUSTOM").upper()
        pinned_token = entry.get("token", "").strip()
        if not original:
            continue

        # If a specific token label was pinned by the user, honour it.
        # Pre-register it so assign_token returns the same label.
        if pinned_token and original not in value_to_token:
            value_to_token[original] = pinned_token
            token_to_meta[pinned_token] = {
                "type":       token_type,
                "first_seen": source_file,
                "created":    datetime.now().isoformat(),
                "source":     "custom_tokens",
            }

        # Find all occurrences (case-insensitive) that are not already inside a token
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        matches = list(pattern.finditer(tokenized))
        # Process right-to-left so replacements don't shift earlier offsets
        for m in reversed(matches):
            span = tokenized[m.start():m.end()]
            if "[" in span:
                continue  # already tokenized
            token = assign_token(original, token_type, value_to_token, counters,
                                 token_to_meta, source_file)
            tokenized = tokenized[:m.start()] + token + tokenized[m.end():]
            findings.append({
                "original":    span,
                "token":       token,
                "entity_type": "CUSTOM",
                "score":       1.0,
                "start":       m.start(),
                "end":         m.end(),
            })

    return tokenized


def load_registry(registry_path: Path) -> dict:
    """
    Load existing token registry.
    Returns two dicts:
      value_to_token: {original_value -> token}
      counters:       {token_type -> current_max_int}
    """
    if not registry_path.exists():
        return {}, {}

    with open(registry_path, encoding="utf-8") as f:
        records = json.load(f)

    value_to_token = {}
    counters = {}
    for record in records:
        token     = record["token"]
        original  = record["original"]
        value_to_token[original] = token

        # Parse type and number from token like [SSN_0042]
        m = re.match(r'\[([A-Z]+)_(\d+)\]', token)
        if m:
            ttype, num = m.group(1), int(m.group(2))
            counters[ttype] = max(counters.get(ttype, 0), num)

    return value_to_token, counters


def save_registry(registry_path: Path, value_to_token: dict,
                  token_to_meta: dict) -> None:
    """Write the full registry as a JSON array."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "token":       token,
            "original":    original,
            **token_to_meta.get(token, {}),
        }
        for original, token in sorted(value_to_token.items(), key=lambda x: x[1])
    ]
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def assign_token(original: str, token_type: str,
                 value_to_token: dict, counters: dict,
                 token_to_meta: dict, source_file: str) -> str:
    """
    Return the token for original. Creates a new one if not seen before.
    Mutates value_to_token, counters, and token_to_meta in place.
    """
    if original in value_to_token:
        return value_to_token[original]

    n = counters.get(token_type, 0) + 1
    counters[token_type] = n
    token = f"[{token_type}_{n:04d}]"

    value_to_token[original] = token
    token_to_meta[token] = {
        "type":        token_type,
        "first_seen":  source_file,
        "created":     datetime.now().isoformat(),
    }
    return token


# ── File hashing ──────────────────────────────────────────────────────────────

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── Core tokenization ─────────────────────────────────────────────────────────

def tokenize_text(text: str, source_file: str, analyzer: AnalyzerEngine,
                  pii_types: list, min_score: float,
                  value_to_token: dict, counters: dict,
                  token_to_meta: dict,
                  custom_entries: list = None) -> tuple:
    """
    Detect PII in text and return (tokenized_text, findings_list).
    findings_list contains one dict per PII instance found.
    Mutates registry dicts in place.
    """
    # Run Presidio
    results = analyzer.analyze(text=text, language="en", entities=pii_types,
                                score_threshold=min_score)

    # Deduplicate overlapping spans: keep only the highest-scoring result per span.
    # Presidio can return multiple entity types for the same character range (e.g.
    # a 9-digit routing number matched by both PHONE_NUMBER and US_ROUTING_NUMBER).
    # Without deduplication, two replacements on the same offsets corrupt the string.
    seen_spans: dict[tuple, object] = {}
    for r in results:
        key = (r.start, r.end)
        if key not in seen_spans or r.score > seen_spans[key].score:
            seen_spans[key] = r
    # Also remove any result whose span is fully contained within a higher-scoring span
    winners = list(seen_spans.values())
    deduplicated = []
    for r in sorted(winners, key=lambda x: x.score, reverse=True):
        if not any(
            other.start <= r.start and other.end >= r.end and other is not r
            for other in deduplicated
        ):
            deduplicated.append(r)

    # Sort by start position descending so replacements don't shift offsets
    results = sorted(deduplicated, key=lambda r: r.start, reverse=True)

    findings = []
    tokenized = text

    for result in results:
        original = text[result.start:result.end]
        token_type = PRESIDIO_TO_TOKEN_TYPE.get(result.entity_type, result.entity_type[:6])
        token = assign_token(original, token_type, value_to_token, counters,
                             token_to_meta, source_file)
        tokenized = tokenized[:result.start] + token + tokenized[result.end:]
        findings.append({
            "original":    original,
            "token":       token,
            "entity_type": result.entity_type,
            "score":       round(result.score, 3),
            "start":       result.start,
            "end":         result.end,
        })

    # Custom: dollar amounts
    for m in sorted(AMOUNT_PATTERN.finditer(tokenized), key=lambda x: x.start(), reverse=True):
        original = m.group()
        if "[" in original:
            continue  # already tokenized
        token = assign_token(original, "AMOUNT", value_to_token, counters,
                             token_to_meta, source_file)
        tokenized = tokenized[:m.start()] + token + tokenized[m.end():]
        findings.append({"original": original, "token": token,
                         "entity_type": "AMOUNT", "score": 1.0,
                         "start": m.start(), "end": m.end()})

    # Custom: user-defined sensitive values from custom_tokens.json
    if custom_entries:
        tokenized = apply_custom_tokens(tokenized, source_file, custom_entries,
                                        value_to_token, counters, token_to_meta, findings)

    return tokenized, findings


# ── File collection ───────────────────────────────────────────────────────────

def collect_files(vault_root: Path, supported_ext: list,
                  single_file: str = None) -> list:
    """Return list of (vault_relative_path, absolute_path) tuples."""
    if single_file:
        p = vault_root / single_file
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)
        return [(Path(single_file), p)]

    files = []
    for ext in supported_ext:
        for p in vault_root.rglob(f"*{ext}"):
            if "_provenance" not in p.parts and "_registry" not in p.parts:
                files.append((p.relative_to(vault_root), p))
    return sorted(files)


# ── Dry-run ───────────────────────────────────────────────────────────────────

def run_dry_run(vault_name: str, vault_root: Path, token_store_root: Path,
                analyzer: AnalyzerEngine, behavior_config: dict,
                single_file: str = None) -> None:
    pii_types      = behavior_config["pii_types"]
    min_score      = behavior_config["min_score"]
    supported      = behavior_config["supported_extensions"]
    files          = collect_files(vault_root, supported, single_file)
    custom_entries = load_custom_tokens(token_store_root / "_registry")

    print()
    print("=" * 60)
    print(f"  VAULT TOKENIZER — DRY RUN ({vault_name.upper()} VAULT)")
    print(f"  Vault:       {vault_root}")
    print(f"  Token store: {token_store_root}")
    if custom_entries:
        print(f"  Custom tokens: {len(custom_entries)} entries loaded")
    print("=" * 60)
    print()

    if not files:
        print("  No supported files found.")
        print()
        return

    # Temp registry for dry-run (not written anywhere)
    value_to_token, counters = {}, {}
    token_to_meta = {}

    total_pii = 0
    skipped   = 0

    for rel, abs_path in files:
        ext = abs_path.suffix.lower()
        if ext not in supported:
            print(f"  [skip-type]  {rel}")
            skipped += 1
            continue

        if abs_path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(abs_path)
        else:
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
        _, findings = tokenize_text(text, str(rel), analyzer, pii_types, min_score,
                                    value_to_token, counters, token_to_meta,
                                    custom_entries)

        print(f"  {rel}")
        if findings:
            for f in findings:
                masked = f["original"][:4] + "…" if len(f["original"]) > 4 else "…"
                print(f"    {f['entity_type']:<28} {masked:<16} -> {f['token']}")
        else:
            print(f"    (no PII detected)")
        total_pii += len(findings)
        print()

    print("=" * 60)
    print(f"  Files scanned:    {len(files) - skipped}")
    print(f"  Files skipped:    {skipped}")
    print(f"  PII instances:    {total_pii}")
    print(f"  Unique tokens:    {len(value_to_token)}")
    print()
    print("  Run with --confirm to write tokenized files and registry.")
    print()


# ── Live run ──────────────────────────────────────────────────────────────────

def run_confirm(vault_name: str, vault_root: Path, token_store_root: Path,
                analyzer: AnalyzerEngine, behavior_config: dict,
                log_path: Path, single_file: str = None) -> None:
    pii_types      = behavior_config["pii_types"]
    min_score      = behavior_config["min_score"]
    supported      = behavior_config["supported_extensions"]
    files          = collect_files(vault_root, supported, single_file)
    custom_entries = load_custom_tokens(token_store_root / "_registry")

    registry_path = token_store_root / "_registry" / "token_registry.json"
    value_to_token, counters = load_registry(registry_path)
    token_to_meta = {}

    print()
    print("=" * 60)
    print(f"  VAULT TOKENIZER — LIVE ({vault_name.upper()} VAULT)")
    print(f"  Vault:       {vault_root}")
    print(f"  Token store: {token_store_root}")
    print(f"  Registry:    {registry_path}")
    if custom_entries:
        print(f"  Custom tokens: {len(custom_entries)} entries loaded")
    print("=" * 60)
    print()

    written   = 0
    skipped   = 0
    unchanged = 0
    total_pii = 0
    errors    = []

    hash_index_path = token_store_root / "_registry" / "file_hashes.json"
    hash_index = {}
    if hash_index_path.exists():
        with open(hash_index_path, encoding="utf-8") as f:
            hash_index = json.load(f)

    for rel, abs_path in files:
        rel_str = str(rel)
        ext     = abs_path.suffix.lower()

        if ext not in supported:
            print(f"  [skip-type]  {rel}")
            skipped += 1
            continue

        # Skip unchanged files
        current_hash = file_sha256(abs_path)
        if hash_index.get(rel_str) == current_hash:
            print(f"  [unchanged]  {rel}")
            unchanged += 1
            continue

        try:
            if abs_path.suffix.lower() == ".pdf":
                text = extract_text_from_pdf(abs_path)
            else:
                text = abs_path.read_text(encoding="utf-8", errors="ignore")
            tokenized, findings = tokenize_text(
                text, rel_str, analyzer, pii_types, min_score,
                value_to_token, counters, token_to_meta,
                custom_entries
            )

            # Write tokenized file to token store (mirrors vault structure)
            dest = token_store_root / vault_name / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(tokenized, encoding="utf-8")

            hash_index[rel_str] = current_hash
            total_pii  += len(findings)
            written    += 1

            label = f"[{len(findings)} PII]" if findings else "[no PII]"
            print(f"  [written]    {rel}  {label}")

        except Exception as e:
            errors.append(f"{rel}: {e}")
            print(f"  [ERROR]      {rel}  — {e}")

    # Save updated registry and hash index
    if written > 0:
        save_registry(registry_path, value_to_token, token_to_meta)
        hash_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(hash_index_path, "w", encoding="utf-8") as f:
            json.dump(hash_index, f, indent=2)

    print()
    print("=" * 60)
    print(f"  Written:      {written}")
    print(f"  Unchanged:    {unchanged}")
    print(f"  Skipped:      {skipped}")
    print(f"  PII replaced: {total_pii}")
    print(f"  Registry:     {len(value_to_token)} total tokens")
    if errors:
        print(f"  Errors:       {len(errors)}")
        for e in errors:
            print(f"    {e}")
    print("=" * 60)
    print()

    # Write run log
    write_log(log_path, vault_name, written, unchanged, skipped, total_pii,
              len(value_to_token), errors)


# ── Logging ───────────────────────────────────────────────────────────────────

def write_log(log_path: Path, vault_name: str, written: int, unchanged: int,
              skipped: int, pii_count: int, registry_size: int,
              errors: list) -> None:
    log_path.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"vault_tokenizer_{vault_name.upper()}_{ts}.log"
    lines = [
        f"Vault Tokenizer — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Vault:         {vault_name.upper()}",
        f"Written:       {written}",
        f"Unchanged:     {unchanged}",
        f"Skipped:       {skipped}",
        f"PII replaced:  {pii_count}",
        f"Registry size: {registry_size} tokens",
        f"Errors:        {len(errors)}",
    ]
    for e in errors:
        lines.append(f"  ERROR: {e}")
    (log_path / name).write_text("\n".join(lines), encoding="utf-8")
    print(f"  Log saved: {name}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    arg_lower = [a.lower() for a in args]

    behavior_config, vault_config = load_configs()
    log_path = Path(__file__).parent / behavior_config["log_path"]

    test_mode   = "--test" in arg_lower
    confirm     = "--confirm" in arg_lower
    vault_name  = None
    single_file = None

    if "--vault" in arg_lower:
        idx = arg_lower.index("--vault")
        if idx + 1 < len(args):
            vault_name = args[idx + 1].lower()

    if "--file" in arg_lower:
        idx = arg_lower.index("--file")
        if idx + 1 < len(args):
            single_file = args[idx + 1]

    if not test_mode and vault_name not in ("gold", "silver", "bronze"):
        print()
        print("Usage:")
        print("  python vault_tokenizer.py --vault gold|silver|bronze")
        print("  python vault_tokenizer.py --vault gold --confirm")
        print("  python vault_tokenizer.py --vault gold --file 06_Tax/return.md")
        print("  python vault_tokenizer.py --test")
        print("  python vault_tokenizer.py --test --confirm")
        print()
        sys.exit(1)

    if test_mode and vault_name is None:
        vault_name = "gold"

    vault_root, token_store_root = resolve_paths(vault_name, vault_config, test_mode)

    print()
    print("  Loading Presidio analyzer… ", end="", flush=True)
    analyzer = build_analyzer(behavior_config["pii_types"], behavior_config["min_score"])
    print("ready.")

    if confirm:
        run_confirm(vault_name, vault_root, token_store_root, analyzer,
                    behavior_config, log_path, single_file)
    else:
        run_dry_run(vault_name, vault_root, token_store_root, analyzer,
                    behavior_config, single_file)
