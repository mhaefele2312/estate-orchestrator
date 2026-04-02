# Estate OS — Claude Reference Manual: Volume 2 (Active Development)

**Version:** 2.1
**Last updated by:** Dev machine session — April 2, 2026
**Covers through:** Phase 5 complete (RAG + PDF OCR + Cloud LLM) + all prior phases
**Owner:** MHH (mhaefele@gmail.com)
**Repository:** github.com/mhaefele2312/estate-orchestrator

---

## ⚠️ READ THIS WARNING FIRST

This is Volume 2 of the Claude Reference Manual. It covers **scripts, pipelines, automation, and configuration** — all of which are actively developed on the dev machine and migrated to the estate laptop.

**DO NOT TRUST THIS VOLUME BLINDLY.**

Before acting on anything here:
1. Run `git log --oneline -20` — see what changed recently
2. Read the actual code file — it may have been updated since this document was written
3. Run `python run_tests.py` — verify current system health
4. If this document contradicts the code, **THE CODE IS RIGHT**

**Volume 1 (CLAUDE-REFERENCE-MANUAL-V1.md)** is the stable foundation: architecture, rules, schema, folder structures, people, the capture app, the sheet. Read V1 first. Trust V1 completely.

---

## TWO-MACHINE SETUP

**Dev computer:** `C:\Users\mattg\estate-orchestrator\`
- Where Claude Code runs and all code is built
- No vault data here — code only
- Dev vault paths: Gold=X:\, Silver=Y:\, Token Store=C:\Users\mhhro\Documents\Estate-Token-Store

**Estate laptop:** `C:\Users\mhhro\Documents\Claude\Projects\estate-orchstrator\` ← note typo in folder name
- Where vault data lives, pipeline runs, voice capture operates
- All scripts migrate here after being built on dev machine
- See Section 2 for full estate laptop path reference

Scripts use `config/vault_config.json` for all paths. Never hardcode paths.

---

## 1. ESTATE LAPTOP FILE PATHS (for migration planning)

Every script reads paths from config files. These are the live estate laptop values:

| Resource | Path |
|----------|------|
| Repo | C:\Users\mhhro\estate-orchestrator\ |
| Obsidian vault | C:\Users\mhhro\Documents\Obsidian Vault\ |
| Gold vault | E:\ (Cryptomator mount — E: on estate laptop; config key: gold_vault) |
| Gold backup | G:\My Drive\Gold-Backup |
| Silver vault | Y:\ (Cryptomator — config key: silver_vault) |
| Bronze vault | Empty until external storage connected (config key: bronze_vault) |
| Token store | C:\Users\mhhro\Documents\Estate-Token-Store |
| Estate Ops | G:\My Drive\Estate Ops |
| Logs | G:\My Drive\Estate Ops\Logs |
| Source-of-Truth | G:\My Drive\Estate Ops\Source-of-Truth |
| MHH Inbox | G:\My Drive\MHH-Inbox |
| HBS Inbox | G:\My Drive\HBS-Inbox |
| HJH Inbox | G:\My Drive\HJH-Inbox |
| LEH Inbox | G:\My Drive\LEH-Inbox |
| HAH Inbox | G:\My Drive\HAH-Inbox |
| OPA Inbox | G:\My Drive\OPA-Inbox |
| HJH Property Docs | G:\My Drive\HJH-Property-Docs |
| Staging Intake | G:\My Drive\Staging-Intake |
| Capture Archive | G:\My Drive\Capture-Archive |

**Note:** Dev machine config uses X:\ for Gold vault. Estate laptop uses E:\. Always check vault_config.json on the target machine before running vault-aware scripts.

---

## 2. SCRIPTS INVENTORY — COMPLETE

All scripts in `behaviors/`. Status as of this document version — **verify against actual files.**

---

### capture-pipeline/capture_pipeline.py ✅ LIVE on estate laptop

**Purpose:** Three-stage capture processing: read transcript → Gemini parse → write sheet + logs
**Dependencies:** gspread, google-auth, google-generativeai, google-genai
**Flags:** `--inbox` (process all inboxes), `--confirm` (live run), `--test` (import check)

**Three stages:**
1. Stage 1: Read raw .md from inbox (no LLM)
2. Stage 2: Send ONLY transcript to Gemini, receive JSON array
3. Stage 3: Write simultaneously to sheet (append_row) + flat files + contacts CSV + contact-mentions.md
4. Archive processed transcript to Capture-Archive

**Inbox scanning — all 6 users:**
Config keys: `inbox_dir` (MHH), `hbs_inbox_dir`, `hjh_inbox_dir`, `leh_inbox_dir`, `hah_inbox_dir`, `opa_inbox_dir`

**Environment:** Requires GEMINI_API_KEY (in .env or environment)

---

### snapshot/snapshot.py ✅ LIVE on estate laptop

**Purpose:** Export Master Log as timestamped CSVs to 3 locations simultaneously
**Flags:** `--confirm`, `--test`

**Exports to:**
1. `G:\My Drive\Estate Ops\Source-of-Truth\`
2. Gold vault `12_Operations\Source-of-Truth\` (encrypted)
3. Obsidian `Master-Log\Source-of-Truth\` (offline)

**Creates:** `sot-latest-MHH.csv` (pointer to most recent snapshot)
**Also in this folder:** `SheetMenu.gs` — Apps Script custom menu that adds "Take Snapshot (SOT)" to the sheet toolbar

---

### weekly-sync/weekly_sync.py ✅ LIVE on estate laptop

**Purpose:** One-way push of logs + SOT + contact pages to Obsidian
**Dependencies:** stdlib only
**Flags:** `--confirm`, `--test`

**What it does:**
1. Copy flat logs → Obsidian Master-Log/Logs/
2. Copy latest SOT → Obsidian Master-Log/Source-of-Truth/
3. Read contact-mentions.md, rebuild contact pages in 11_Contacts/
4. Marker-based merge: content above `<!-- mentions-start -->` is NEVER overwritten

---

### reconciliation/reconciliation.py ✅ LIVE on estate laptop

**Purpose:** Read sheet, find "done" items, append completions to flat log files
**Dependencies:** gspread, google-auth
**Flags:** `--confirm`, `--test`
**IMPORTANT:** Always run BEFORE snapshot.py so flat logs reflect latest status

---

### gate/gate.py ✅ LIVE on estate laptop

**Purpose:** Move Obsidian Inbox files → Accepted/ with provenance frontmatter metadata
**Flags:** `--test`, `--dry-run` (default), `--confirm`
**Known issue:** Input flushing bug on first prompt — partially fixed, skip stuck items

---

### health-check/health_check.py ✅ LIVE on estate laptop

**Purpose:** Daily system health check: API connectivity, inbox dirs, vault paths
**Dependencies:** stdlib + gspread for sheet check
**No flags needed** (read-only)

---

### backup-check/backup_check.py ✅ LIVE on estate laptop

**Purpose:** Weekly backup verification: Drive sync, Gold backup age, Obsidian freshness
**Dependencies:** stdlib only
**No flags needed** (read-only)

---

### inbox-pickup/inbox_pickup.py ✅ Built

**Purpose:** Detect new files in inbox, prep for pipeline
**Status:** Built and tested in test mode
**Dependencies:** stdlib

---

### staging-intake/ ✅ BUILT — ready to deploy on estate laptop

Three scripts that together form the legacy document intake pipeline:

**staging_sorter.py**
- Scans a staging folder, reads file content, assigns a domain based on keyword scoring
- Outputs a manifest of suggested classifications
- Flags: `--source <path>`, `--confirm`, `--test`

**security_scan.py**
- Runs Windows Defender scan on staged files before intake
- Warns if Windows Defender not found
- Called by staging_router.py before filing anything

**staging_router.py**
- Orchestrates sorter + scan: presents each file to MHH for approval, files to Silver vault
- Interactive commands: Enter (accept), 1-12 (change domain), r (rename), s (skip), d (delete-review), q (quit)
- Files are COPIED to Silver — originals never deleted
- Flags: `--source <path>`, `--confirm`, `--test`

**Run command:**
```
python behaviors/staging-intake/staging_router.py --source "G:\My Drive\Staging-Intake\[folder]"
```

---

### email-intake/ ✅ BUILT — ready to deploy

**EmailIntake.gs** — Google Apps Script for email tagging workflow
- Labels important emails in Gmail for weekly review
- Runs on Apps Script triggers

**weekly_review.py** — Weekly review summary
- Reads staged emails and pending items
- Generates a review summary
- Flags: `--confirm`, `--test`

---

### publish/publish.py ⛔ DEFERRED — Phase 7+

**Status: DO NOT DEVELOP FURTHER.** Built but deferred. Publish assumes the tokenization layer is built and vault content is ready for external sharing. Neither is true yet.

---

### vault-setup/vault_setup.py ✅ BUILT — run once on estate laptop

**Purpose:** Creates the folder structure for Silver vault (Y:\) or Bronze vault
**Run once** after creating a new Cryptomator vault in Cryptomator

```
python behaviors/vault-setup/vault_setup.py --vault silver
    Dry-run. Shows every folder that would be created.

python behaviors/vault-setup/vault_setup.py --vault silver --confirm
    Creates all folders on Y:\. Safe to re-run — skips existing folders.

python behaviors/vault-setup/vault_setup.py --vault bronze --confirm
    Creates Bronze folder structure (requires bronze_vault path in vault_config.json).

python behaviors/vault-setup/vault_setup.py --test
    Dry-run against tests/fake-silver-vault. No real vault needed.
```

**Vault structure created (14 folders):**
```
Y:\
├── 00_Unsorted/       ← machine-classified, confidence too low for specific domain
├── 01_Financial/
├── 02_Legal/
├── 03_Property/
├── 04_Insurance/
├── 05_Medical/
├── 06_Tax/
├── 07_Estate-Planning/
├── 08_Vehicles/
├── 09_Digital/
├── 10_Family/
├── 11_Contacts/
├── 12_Operations/
└── _provenance/       ← every machine decision logged here
```

**Key difference from Gold vault:** Silver has `00_Unsorted` (Gold does not). Silver is machine-curated; Gold is human-curated.

---

### silver-classifier/silver_classifier.py ✅ BUILT — use for legacy document intake

**Purpose:** Classify legacy documents into Silver vault. Reads files, scores against domain keyword lists, suggests domain + filename, gets human approval, files to Silver with provenance record.

**Filename format:** `YYYY-MM-DD-{document-type}.{ext}` (e.g., `2018-04-15-tax-return.pdf`)

**When to use:** When you have a folder of legacy documents (from old hard drives, scanned docs, etc.) that need to go into the Silver vault.

```
python behaviors/silver-classifier/silver_classifier.py --source "G:\My Drive\Staging-Intake\old-drive-2026"
    Dry-run. Shows classification suggestion for every file.

python behaviors/silver-classifier/silver_classifier.py --source <path> --confirm
    Interactive. Shows each file, waits for approval, files to Silver.

python behaviors/silver-classifier/silver_classifier.py --test
    Test against tests/fake-staging. No real vault needed.
```

**Interactive commands:** Enter (accept), 1-12 (change domain), r (rename), s (skip), d (delete-review), q (quit)

**Rules:**
- Files COPIED to Silver — source originals never deleted
- Low-confidence files (score < 0.15) suggested for 00_Unsorted
- Every filing generates a provenance record in `Silver/_provenance/`
- Safe to re-run: duplicates get counter suffix, both copies kept

---

### silver-review/silver_review.py ✅ BUILT — use to review and promote Silver content

**Purpose:** Review machine-classified Silver vault files. Correct classifications, promote good files to Gold vault.

**When to use:** After running silver_classifier.py, or periodically to review what the machine filed.

```
python behaviors/silver-review/silver_review.py
    Dry-run. Shows Silver vault contents and stats.

python behaviors/silver-review/silver_review.py --confirm
    Interactive review. Makes changes as approved.

python behaviors/silver-review/silver_review.py --domain 01_Financial
    Review one domain only.

python behaviors/silver-review/silver_review.py --unsorted
    Review 00_Unsorted first (good starting point).
```

**Interactive commands:** Enter/a (accept), r (rename), m (move domain), g (promote to Gold), s (skip), q (quit)

**Rules:**
- Silver files are MOVED on rename/reclassify. Originals not kept.
- Promote to Gold COPIES to Gold, then deletes from Silver
- All decisions logged to `_provenance/corrections-log.jsonl`
- Gold promotion always picks a specific domain (Gold has no 00_Unsorted)

---

### vault-tokenizer/vault_tokenizer.py ✅ BUILT — Phase 5 pre-processing

**Purpose:** Read Gold or Silver vault documents, detect PII using Microsoft Presidio, replace each sensitive value with a named token, write sanitized documents to Token Store.

**Why:** Tokenized documents are safe for local LLM ingestion (RAG layer). The Token Registry maps tokens back to originals and never leaves the estate laptop.

**Token format:** `[TYPE_NNNN]` — e.g., `[SSN_0001]`, `[ACCT_0001]`, `[EMAIL_0001]`, `[PHONE_0001]`

**Same value = same token:** If the same SSN appears in 5 files, it always gets `[SSN_0001]`. This allows the RAG system to cross-reference documents by entity.

**Token Store structure:**
```
C:\Users\mhhro\Documents\Estate-Token-Store\
├── gold/                  ← mirrors Gold vault structure, PII replaced
│   ├── 06_Tax/
│   │   └── 2024-federal-tax-return.md
│   └── ...
├── silver/                ← mirrors Silver vault structure
└── _registry/
    └── token_registry.json    ← maps token → original value (SENSITIVE — never share)
```

```
python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold
    Dry-run. Shows what PII would be found, what tokens would be assigned.

python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold --confirm
    Tokenizes all supported files in Gold vault. Writes to Token Store.

python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold --file 06_Tax/2024-return.md --confirm
    Process a single file.

python behaviors/vault-tokenizer/vault_tokenizer.py --test
    Run against dummy test documents. No real vault required.
```

**PDF support:** Fully implemented. Two-step extraction:
1. **pdfplumber** — extracts text layer from digital PDFs (fast, no ML needed)
2. **easyocr fallback** — for scanned/image-only PDFs with no text layer. Renders pages via pypdfium2 at 2x scale, runs OCR with GPU=False (CPU-based)

If pdfplumber returns >= 50 characters of text, it's used. Otherwise easyocr kicks in automatically. Never crashes — returns empty string on failure with a warning.

**Rules:**
- Gold vault is NEVER modified. Only Token Store is written to.
- Token Registry is append-only. Existing tokens never changed or removed.
- Re-running is safe: if file unchanged (same SHA-256), it is skipped
- Supported file types: `.md`, `.txt`, `.pdf`

**Dependencies:** presidio-analyzer, presidio-anonymizer, spacy (en_core_web_sm model), pdfplumber, easyocr, pypdfium2, pillow

**Install:**
```
pip install presidio-analyzer presidio-anonymizer spacy pdfplumber easyocr pypdfium2 pillow
python -m spacy download en_core_web_sm
```

---

### estate-interview/ ✅ BUILT — standalone break-glass app

**Purpose:** A standalone Windows desktop app for recording a complete estate plan through a guided voice/text interview. Designed to be handed to a family member (e.g., OPA) on a USB drive.

**This is separate from the main pipeline** — it does not connect to Google Sheets, Obsidian, or any vault. It saves answers locally as JSON and can export a PDF.

**Location:** `behaviors/estate-interview/`

**Key files:**
- `estate_interview.py` — main application (1600+ lines, customtkinter UI)
- `questions.py` — 15 chapters, 138+ questions
- `pdf_generator.py` — generates PDF estate plan from answers
- `profiles/` — local JSON save files per person

**15 chapters:**
1. About You
2. Your Family
3. Key People
4. Documents
5. Finances
6. Property
7. Digital Life
8. Your Wishes
9. Messages
10. Advanced Estate Planning (LLCs, trusts, business entities)
11. Your Main Home (operations, systems, vendors)
12. Vehicles & Other Property
13. Digital Accounts & Media Systems
14. Your Life Story
15. Family History & Lore

**Features:**
- Left sidebar: all chapters with Include/Skip toggle and completion checkmarks
- Chapter landing page: time picker + voice/text mode selector before starting each section
- Voice mode: Windows Speech Recognition via PowerShell (no packages needed)
- Text mode: standard text entry
- "Done for Today" button: saves and opens editable draft review
- Export PDF: generates formatted estate plan document
- Timer: counts down session time
- Fully offline — no internet required

**Launch:**
```
python behaviors/estate-interview/estate_interview.py
```

**Build installer for USB:**
```
cd build
build_installer.bat
```
Requires: PyInstaller, Inno Setup 6. Output: `build/output/EstateOS_Setup.exe`

**Desktop shortcut:** Created at `C:\Users\mattg\OneDrive\Desktop\Estate OS.lnk`

**Dependencies:** customtkinter, reportlab, edge-tts (optional, for voice output)

---

### vault-indexer/vault_indexer.py ✅ BUILT — Phase 5 RAG embedding pipeline

**Purpose:** Reads tokenized documents from the Token Store, chunks them with overlap, generates vector embeddings via Ollama's nomic-embed-text model, and stores them in a LanceDB vector database for semantic search.

**Key files:**
- `vault_indexer.py` — main indexer script

**How it works:**
1. Scans Token Store for `.md` and `.txt` files
2. Chunks each document (~500 words, 50-word overlap for context coherence)
3. Calls Ollama `/api/embed` endpoint with nomic-embed-text (384-dim vectors)
4. Stores chunks + embeddings in LanceDB table `vault_chunks`
5. Tracks file SHA-256 hashes — only re-indexes changed documents

**LanceDB table schema (`vault_chunks`):**

| Column | Type | Purpose |
|--------|------|---------|
| vector | float[384] | Embedding from nomic-embed-text |
| text | string | Chunk text |
| vault | string | "gold", "silver", "bronze" |
| domain | string | Folder name (e.g., "06_Tax") |
| filename | string | Original filename |
| rel_path | string | Relative path in vault |
| chunk_idx | int | Chunk number within document |
| source_key | string | Unique file key for version tracking |

**Index structure:**
```
<token_store>/_vector_index/
├── lance_db/              LanceDB database directory
├── index_hashes.json      SHA-256 tracking (skip unchanged files)
└── index_stats.json       Statistics
```

```
python behaviors/vault-indexer/vault_indexer.py --vault gold
    Dry-run. Shows what would be indexed.

python behaviors/vault-indexer/vault_indexer.py --vault gold --confirm
    Index Gold vault tokenized documents into LanceDB.

python behaviors/vault-indexer/vault_indexer.py --all --confirm
    Index all vaults (gold + silver + bronze) in one pass.

python behaviors/vault-indexer/vault_indexer.py --stats
    Show current index statistics without modifying anything.

python behaviors/vault-indexer/vault_indexer.py --test
    Dry-run against fake-token-store test data.
```

**Dependencies:** lancedb, ollama (external server, not pip)
**Requires:** Ollama running locally with nomic-embed-text model installed

---

### estate-assistant/ ✅ BUILT — Phase 5 local-first search + AI Q&A

**Purpose:** Streamlit web app with two tabs — keyword search (no AI needed) and natural-language Q&A (powered by local Ollama). All processing happens locally. No data leaves the machine.

**Key files:**
- `estate_assistant.py` — main Streamlit app (Search tab + Ask tab)
- `search.py` — hybrid search engine (keyword + vector via LanceDB)
- `ollama_client.py` — Ollama streaming wrapper
- `config.json` — behavior config

**Search tab (works without Ollama):**
- Keyword search over tokenized documents
- Vault scope filter (Gold / Silver / Bronze / All)
- Domain filter (01_Financial through 12_Operations)
- De-tokenizes results locally — real values visible in search results
- Source cards with file location and domain

**Ask tab (requires Ollama):**
- Natural-language questions about vault documents
- Finds relevant passages via keyword search, sends to Ollama
- Streams response in real time
- If Ollama not running: shows setup instructions, Search tab still works

**Ollama model preference order:** mistral > llama3 > llama2 > gemma > phi3 > phi

**Hybrid search engine (search.py):**
- Keyword search: tokenized text scanning with word frequency + proximity scoring
- Vector search: LanceDB semantic search via Ollama embeddings (when available)
- Merging: Reciprocal Rank Fusion (RRF) with k=60 constant
- Falls back to keyword-only if LanceDB or Ollama unavailable

**Launch:**
```
streamlit run behaviors/estate-assistant/estate_assistant.py
```
Or double-click: `launch_estate_assistant.bat`

**Dependencies:** streamlit, lancedb (optional, for vector search), ollama (external, optional for Search tab)

---

### claude-tokenized/ ✅ BUILT — Phase 5 cloud LLM vault query interface

**Purpose:** ChatGPT-style Streamlit web app for querying vault documents via cloud LLMs (Gemini, Claude, ChatGPT). Tokenized text is sent to cloud; de-tokenization happens locally. Sensitive values never leave the machine.

**Key files:**
- `claude_tokenized.py` — main Streamlit app (dark ChatGPT-style UI)
- `cloud_client.py` — cloud LLM provider integration (functional, not class-based)

**Security model (critical):**
1. Search engine finds relevant tokenized passages locally
2. Passages sent to cloud LLM with tokens intact (e.g., `[SSN_0001]`, `[ACCT_0002]`)
3. Cloud LLM responds using token labels
4. Response de-tokenized locally before display
5. Real values NEVER transmitted to any cloud provider

**Supported cloud providers:**

| Provider | Models | Env Var |
|----------|--------|---------|
| Gemini | gemini-2.0-flash, gemini-1.5-pro | GEMINI_API_KEY |
| Claude | claude-sonnet-4-20250514, claude-haiku-4-5-20251001 | ANTHROPIC_API_KEY |
| ChatGPT | gpt-4o, gpt-4o-mini | OPENAI_API_KEY |

**Features:**
- Provider and model selector in sidebar
- Vault scope filter (Gold / Silver / All)
- Streaming responses
- Dark themed UI
- Custom Ruschlikon rose icon

**Launch:**
```
streamlit run behaviors/claude-tokenized/claude_tokenized.py
```
Or double-click: `launch_claude_tokenized.bat` (runs on port 8502)

**Dependencies:** streamlit, google-genai (Gemini), anthropic (Claude), openai (ChatGPT)

**Note:** Only one API key is needed — whichever provider you want to use. All three are optional.

---

### setup_check.py ✅ BUILT — run before first use on any machine

**Purpose:** Verifies all dependencies, paths, credentials, and config are correct before running the pipeline.

```
python setup_check.py
```

Checks: Python version, pip packages, config.json keys, Google credentials, vault paths, inbox dirs, Gemini API key, write permissions.

---

## 3. BATCH FILES

### run_daily.bat ✅ LIVE
```batch
python behaviors\capture-pipeline\capture_pipeline.py --inbox --confirm
```
Double-click each morning. Processes all captures from all 6 inboxes.

### run_weekly.bat ✅ LIVE
```batch
Step 1: python behaviors\reconciliation\reconciliation.py --confirm
Step 2: python behaviors\snapshot\snapshot.py --confirm
Step 3: python behaviors\weekly-sync\weekly_sync.py --confirm
Step 4: python behaviors\email-intake\weekly_review.py --confirm
```
Run Sunday evening or Monday morning.

### run_silver_intake.bat ✅ BUILT
```batch
python behaviors\silver-classifier\silver_classifier.py --source "%1" --confirm
```
Pass a staging folder path as argument. Used for legacy document intake sessions.

### launch_estate_assistant.bat ✅ BUILT
Starts Ollama in background (if installed), launches Streamlit Estate Assistant on default port.
Double-click to open search + AI Q&A interface in browser. Search tab works even without Ollama.

### launch_claude_tokenized.bat ✅ BUILT
Starts Ollama in background (if installed), launches Claude Tokenized Streamlit app on port 8502.
Double-click to open cloud LLM query interface. Requires at least one API key (Gemini, Claude, or ChatGPT).

### launch_estate_interview.bat ✅ BUILT
Checks Python, auto-installs missing packages (customtkinter, reportlab, edge-tts), launches the desktop interview app.
Double-click to start guided estate interview. Fully offline.

---

## 4. CONFIG REFERENCE

### behaviors/ops-ledger/config.json (DO NOT COMMIT)

| Key | Purpose |
|-----|---------|
| spreadsheet_id | MHH Master Log Google Sheet ID (18OVdgdFLHd1qBUMIP4iWoZAGSrSfrV-WLjFQ7980b-w) |
| credentials_path | Google OAuth credentials file |
| token_path | Google OAuth token file |
| logs_dir | Flat log files path |
| inbox_dir | MHH inbox |
| hbs_inbox_dir | HBS inbox |
| hjh_inbox_dir | HJH inbox |
| leh_inbox_dir | LEH inbox |
| hah_inbox_dir | HAH inbox |
| opa_inbox_dir | OPA inbox |
| spreadsheet_id_hbs | HBS sheet ID |
| spreadsheet_id_hjh | HJH sheet ID |
| spreadsheet_id_leh | LEH sheet ID |
| spreadsheet_id_hah | HAH sheet ID |
| spreadsheet_id_opa | OPA sheet ID |
| capture_archive_dir | Processed transcript archive |
| sot_dir | Source-of-Truth snapshot folder |
| gold_vault_dir | Cryptomator mount (E:\ on estate laptop) |
| staging_dir | Legacy document staging |
| gold_sot_dir | Gold vault SOT copy location |
| obsidian_sot_dir | Obsidian SOT copy location |
| obsidian_vault_dir | Obsidian vault root |
| obsidian_contacts_dir | 11_Contacts/ in Obsidian |
| obsidian_logs_dir | Master-Log/Logs/ in Obsidian |

### config/vault_config.json (DO NOT COMMIT)

| Key | Purpose |
|-----|---------|
| gold_vault | Gold vault mount path (E:\ on estate laptop) |
| silver_vault | Silver vault mount path (Y:\) |
| bronze_vault | Bronze vault path (empty until external storage connected) |
| gold_backup | Google Drive encrypted backup path |
| silver_backup | Google Drive Silver backup path |
| token_store | Token Store path for vault-tokenizer output |

### Credentials Setup

**Google Sheets API (OAuth 2.0):**
1. Google Cloud project with Sheets API + Drive API enabled
2. OAuth 2.0 Desktop credentials → `behaviors/ops-ledger/credentials.json`
3. First run triggers browser auth → creates `token.json`
4. Scopes: spreadsheets, drive

**Gemini API:**
- Key from Google AI Studio (ai.google.dev)
- Store in .env file as `GEMINI_API_KEY=...`
- Never commit .env

**Security note:** After the security lockdown (V1 Section 15), OAuth credentials were rotated. If auth fails, delete token.json and re-run any script to trigger fresh auth.

---

## 5. FLAT FILE ARCHITECTURE

### Type 1: Append-Only Logs
**Location:** `G:\My Drive\Estate Ops\Logs\`
**Written by:** capture_pipeline.py (Stage 3) and reconciliation.py
**Rule:** IMMUTABLE. No LLM ever modifies these files.

| File | What Gets Appended |
|------|-------------------|
| master-log.md | Every item ever captured |
| next-actions.md | Todos and reminders |
| projects.md | Multi-step efforts |
| waiting-for.md | Delegated items |
| calendar.md | Calendar events |
| someday-maybe.md | Ideas, not committed |
| reference-notes.md | Notes, observations |
| completed.md | Items marked done (via reconciliation.py) |
| health.md | Health check-in responses |
| contacts.md | People with contact info |
| contact-mentions.md | Any person name from any capture |
| google-contacts-import.csv | CSV for Google Contacts import |

### Type 2: Source-of-Truth Snapshots
**Location:** `G:\My Drive\Estate Ops\Source-of-Truth\`
**Written by:** snapshot.py

| File | Purpose |
|------|---------|
| sot-MHH-YYYY-MM-DD-[tab].csv | Per-tab export on that date |
| sot-latest-MHH.csv | Pointer to most recent Raw Log export |

---

## 6. GEMINI GEMS

### Processing Gem (capture parsing)
**Called by:** capture_pipeline.py Stage 2
**Input:** Raw transcript text ONLY
**Output:** JSON array — fields: item_type, domain, description, responsible, due_date, status, notes, contact fields
**Location:** `gemini-gems/` folder in repo

### Query Gem (daily questions)
**Called by:** User via Gemini chat (not by any script)
**Input:** User question + sot-latest-MHH.csv attached
**Output:** Natural language answer citing specific sheet rows
**Never reads:** live sheet, logs, vaults

---

## 7. PHASE ROADMAP — CURRENT STATUS

### Phase 1: Foundation ✅ COMPLETE
All 15 items done. Capture app deployed for 6 users. Pipeline live on estate laptop.

### Phase 2: Multi-User Routing ✅ COMPLETE
All 6 user inboxes scanning. Per-user sheet IDs in config. Family setup guides written.

### Phase 3: Staging Intake ✅ BUILT — deploy and use on estate laptop
Scripts: staging_sorter.py, security_scan.py, staging_router.py
Status: Built and tested. Ready to run against real staging folders on estate laptop.

### Phase 4: Email Intake + Weekly Review ✅ BUILT — ready to deploy
Scripts: EmailIntake.gs (needs Apps Script deployment), weekly_review.py
Status: Built. EmailIntake.gs needs to be pasted into Apps Script and deployed.

### Vault Infrastructure ✅ BUILT — run on estate laptop
Scripts: vault_setup.py, silver_classifier.py, silver_review.py
Status: vault_setup.py creates Silver structure. silver_classifier.py for legacy intake.
Order: vault_setup.py first (creates Y:\ structure), then silver_classifier.py as needed.

### Phase 5: Local LLM + RAG ✅ BUILT — deploy and test on estate laptop

**Full pipeline is operational on dev machine.** All components built and tested.

**What's built:**
- vault_tokenizer.py ✅ — Presidio PII tokenization + PDF OCR (pdfplumber + easyocr)
- vault_indexer.py ✅ — document chunking + LanceDB vector embeddings via Ollama
- estate_assistant/ ✅ — Streamlit local search + Ollama Q&A (Search tab works without Ollama)
- claude_tokenized/ ✅ — Streamlit cloud LLM interface (Gemini, Claude, ChatGPT) with tokenization boundary
- Token Store structure ✅ — mirrors vault layout with _registry and _vector_index
- Launch batch files ✅ — double-click launchers for both apps

**Full data flow:**
```
Vault docs → vault_tokenizer.py (PII → tokens) → Token Store
Token Store → vault_indexer.py (chunk + embed) → LanceDB
LanceDB + Search → estate_assistant (local Ollama) OR claude_tokenized (cloud LLM)
```

**Deployment to estate laptop:**
- Install Ollama + nomic-embed-text model (for embeddings and local Q&A)
- Set API keys in .env (GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY — whichever providers desired)
- Run vault_tokenizer.py --vault gold --confirm (tokenize vault docs)
- Run vault_indexer.py --vault gold --confirm (build vector index)
- Double-click launch_estate_assistant.bat or launch_claude_tokenized.bat

**Hardware plan (revised):**
- Phase 5a: Run Ollama on estate laptop (slow but functional)
- Phase 5b: Migrate to always-on mini PC when hardware arrives
- Syncthing considered for vault sync to mini PC (open design question)

### Phase 6: Property + Health + Tax Automations 🔜 Not started
### Phase 7: Executor Package + Break-Glass Handoff 🔜 Not started
Note: Estate Interview App (behaviors/estate-interview/) is the Phase 7 break-glass tool. It is BUILT already, ahead of schedule. See Section 2 for details.

### Phase 8: Publish + Sharing 🔜 Not started (deferred)

---

## 8. DECISION LOG — DEVELOPMENT AND TOOLING

Decisions made during build sessions that explain why the code works the way it does.

### iOS Safari Microphone — Keyboard Dictation Workaround
**Problem:** iPhone Safari blocks Web Speech API mic in Apps Script sandboxed iframes (Apple security policy).
**Decision:** Detect `not-allowed` errors, fall back to typing mode, prompt user to use iOS keyboard dictation.
**Code:** `enableTypingMode()` in Index.html, called from `recognition.onerror` when `e.error === 'not-allowed'`.

### python-docx Over docx-js for Document Generation
**Problem:** npm blocked by 403 proxy in the Cowork sandbox.
**Decision:** python-docx — already installed, produces valid .docx, handles all formatting needs. All setup guides and manuals generated this way.

### Gemini SDK: google-genai Over google-generativeai
**Problem:** The older `google-generativeai` SDK was deprecated. Model calls started failing.
**Decision:** Migrated to `google-genai` SDK. Both are in requirements.txt for compatibility. New sessions should use `google-genai`.

### Capture Pipeline Inbox Scanning — All 6 Users
**Decision:** All 6 inbox config keys scanned in `run_inbox()`: inbox_dir, hbs_inbox_dir, hjh_inbox_dir, leh_inbox_dir, hah_inbox_dir, opa_inbox_dir. Config.json and config.example.json updated with all paths and placeholder sheet IDs.

### Silver Vault Separate From Gold Vault
**Decision:** Silver vault (Y:\) is a completely separate Cryptomator container from Gold (E:\). Machine-curated content is never mixed with human-curated content. Silver can be deleted/rebuilt if machine classification goes wrong — Gold is permanent. This is the key reason they're separate encrypted containers, not just separate folders.

### vault_tokenizer: Token Stability Across Runs
**Decision:** Tokens are stable — same input value always produces the same token ([SSN_0001] in file A and file B refer to the same SSN). The token_registry.json is append-only. Re-running tokenizer on a changed file re-tokenizes it while reusing existing tokens for known values. This allows the RAG layer to cross-reference entities across documents.

### Ollama on Estate Laptop First (Revised from Mini PC)
**Decision:** Originally the plan called for a dedicated always-on mini PC to host Ollama (see V1, Section 11). Revised to: build Ollama on the estate laptop first, then migrate to mini PC when hardware arrives. Reason: gets Phase 5 functional sooner. The tokenization pipeline (vault_tokenizer.py) is already built and hardware-independent. Only the RAG query layer needs Ollama.

### Estate Interview App Built Ahead of Schedule
**Decision:** The break-glass estate interview app (Phase 7 item) was built early because OPA (elder family member) needs it now. It's standalone, completely offline, and does not touch any pipeline component. Building it early does not affect pipeline development timeline. It is a separate tool that happens to live in the same repo.

### Two Claude Reference Manual Volumes
**Decision:** V1 = stable gospel (architecture through Gold vault). V2 = active development guide (scripts, pipelines, config, decisions). Reason: a single manual would require future Claude sessions to guess which parts are trustworthy. Two volumes with clear trust levels prevent drift. If V1 and code disagree, V1 is probably right. If V2 and code disagree, code is right.

### Desktop Shortcut Creation for Estate Interview App
**Problem:** MHH couldn't find how to open the app.
**Decision:** Created a Windows `.lnk` shortcut at `C:\Users\mattg\OneDrive\Desktop\Estate OS.lnk` pointing to `launch_estate_interview.bat`. Uses the estate rose icon. Double-click launches the app.

### Share Google Drive With HBS — All Items at Once
**Problem:** Google Drive doesn't allow sharing "My Drive" as a single item — each item must be shared individually.
**Decision:** MHH selected all 16 items in Drive root → Share → add hbs.rosevale.west@gmail.com as Editor in one batch. Then HBS installs Google Drive for Desktop and everything appears under "Shared with me." One step instead of sixteen.

### PDF OCR Strategy: pdfplumber + easyocr Two-Step
**Problem:** vault_tokenizer.py needed to handle both digital PDFs (with text layers) and scanned PDFs (image-only).
**Decision:** Two-step approach: (1) pdfplumber extracts text layer first — fast, no ML. (2) If pdfplumber returns < 50 chars, fall back to easyocr for OCR. easyocr chosen over Tesseract because it's pip-installable with no external binary, runs on CPU (GPU=False), and handles varied scan quality well. pypdfium2 renders PDF pages to images for easyocr.

### RAG Architecture: LanceDB + nomic-embed-text
**Problem:** Phase 5 needed a vector store for semantic search over tokenized vault documents.
**Decision:** LanceDB chosen over Pinecone/Weaviate/Chroma because: (1) fully local — no cloud service needed, (2) Python-native, pip-installable, (3) embedded (no separate server process), (4) good enough for estate-scale document collections. Embedding model: Ollama's nomic-embed-text (384-dim vectors, free, runs locally). LlamaIndex was considered but dropped in favor of a simpler custom chunker + direct LanceDB writes.

### Cloud LLM Provider Support: Gemini + Claude + ChatGPT
**Problem:** Local Ollama is slow on laptop hardware. Users may want faster cloud-based answers.
**Decision:** Support all three major providers (Gemini, Claude, ChatGPT) behind a tokenization boundary. Tokenized text is sent to cloud; de-tokenization happens locally. Each provider is optional — only needs one API key. This gives flexibility without lock-in.

### Two Separate Phase 5 UIs
**Problem:** Different use cases need different tools — quick local search vs. conversational cloud AI.
**Decision:** Two apps instead of one: (1) estate-assistant = local-first, Search tab works without any AI, Ask tab uses Ollama. Good for quick lookups and air-gapped use. (2) claude-tokenized = cloud-first with ChatGPT-style conversational interface. Better for complex questions requiring reasoning. Both share the same search engine (search.py) and Token Store.

### Streamlit for Web UI
**Problem:** Needed a web UI framework for the Phase 5 query interfaces.
**Decision:** Streamlit over FastAPI+React or Flask. Reason: rapid prototyping, single-file apps, built-in streaming support, zero frontend build step. Both apps are single Python files with < 600 lines each. The trade-off (less customization) is acceptable for an internal tool.

---

## 9. KNOWN ISSUES

| Issue | Status | Workaround |
|-------|--------|------------|
| gate.py input flushing bug | Partially fixed | Skip stuck items |
| iOS Safari mic permission denied | Platform limitation, not a bug | Use iOS keyboard dictation |
| Gold vault path varies by machine | Expected — E:\ on estate laptop, X:\ in dev config | Check vault_config.json before running |
| ~~vault_tokenizer PDF support missing~~ | ✅ RESOLVED | pdfplumber + easyocr implemented |
| silver_classifier confidence scores | Heuristic keyword scoring, not ML | Low confidence goes to 00_Unsorted; override with 1-12 |
| Apps Script "Page Not Found" on dev machine | Google account/proxy issue on dev machine only | Not a bug; works on real devices |
| estate-interview customtkinter place() width issue | Fixed | width= must be in constructor, not place() call |
| ~~Ollama not yet installed~~ | ✅ RESOLVED | Apps work with or without Ollama; Search tab is Ollama-free |
| requirements.txt incomplete | Missing Phase 5 deps | All packages installed but not listed in requirements.txt |
| .env missing on dev machine | Expected | API keys live on estate laptop only |
| Ollama not yet deployed to estate laptop | Phase 5 deployment pending | estate-assistant Search tab and cloud providers work without it |

---

## 10. TESTING

### Test Runner
```
python run_tests.py
```
Runs import checks + safe-mode tests for all scripts.

### Individual tests
```
python behaviors/health-check/health_check.py
python behaviors/backup-check/backup_check.py
python behaviors/ops-ledger/verify_sheets_auth.py
python behaviors/vault-tokenizer/vault_tokenizer.py --test
python behaviors/silver-classifier/silver_classifier.py --test
python behaviors/silver-review/silver_review.py --test
python behaviors/vault-setup/vault_setup.py --test
python behaviors/vault-indexer/vault_indexer.py --test
```

---

## 11. TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| "gspread not found" | `pip install gspread google-auth google-genai` |
| "credentials.json not found" | Set up Google Cloud project, download OAuth creds |
| "token.json invalid / expired" | Delete token.json, re-run any script to re-auth |
| "API quota exceeded" | Check for loops, reduce capture frequency |
| "Gold vault not found" | Update `gold_vault` in config/vault_config.json |
| "Silver vault not found" | Check Y:\ is mounted in Cryptomator |
| "presidio not found" | `pip install presidio-analyzer presidio-anonymizer` |
| "spacy model missing" | `python -m spacy download en_core_web_sm` |
| "Obsidian not synced" | Run weekly_sync.py manually |
| "Sheet formula errors" | Column order changed — restore A-R order |
| Tests fail with gspread error | Expected on dev machine (no credentials) — normal |
| Estate interview app won't launch | Check customtkinter installed: `pip install customtkinter reportlab` |
| "lancedb not found" | `pip install lancedb` |
| "streamlit not found" | `pip install streamlit` |
| "pdfplumber not found" | `pip install pdfplumber easyocr pypdfium2 pillow` |
| Estate assistant Search shows no results | Run vault_tokenizer.py + vault_indexer.py first |
| Claude Tokenized "no providers available" | Set at least one API key in .env (GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY) |
| Ollama "connection refused" | Install Ollama, run `ollama serve`, pull model: `ollama pull nomic-embed-text` |

---

## 12. DEPENDENCIES — FULL LIST

**requirements.txt is incomplete.** All packages below are installed on the dev machine but not all are in requirements.txt. Install everything with:

```
pip install gspread google-auth google-auth-oauthlib google-generativeai google-genai
pip install presidio-analyzer presidio-anonymizer spacy
pip install pdfplumber easyocr pypdfium2 pillow
pip install lancedb streamlit customtkinter reportlab
pip install anthropic openai edge-tts
python -m spacy download en_core_web_sm
```

**Optional (only needed for specific features):**
- `anthropic` — only if using Claude as cloud provider in claude-tokenized
- `openai` — only if using ChatGPT as cloud provider in claude-tokenized
- `edge-tts` — only for voice output in estate-interview app
- `easyocr` — only for scanned PDF OCR (pdfplumber handles digital PDFs alone)

**External (not pip):**
- **Ollama** — local LLM server. Install from ollama.com. Required for: vault-indexer embeddings, estate-assistant Ask tab. NOT required for: vault-tokenizer, estate-assistant Search tab, claude-tokenized (uses cloud LLMs).

---

## 13. SESSION CONTINUITY CHECKLIST

When starting a new build session:

1. Read CLAUDE-REFERENCE-MANUAL-V1.md (stable foundation — trust completely)
2. Read this file (V2 — treat as guide, verify against code)
3. Read CLAUDE.md (how to work with MHH — non-negotiable rules)
4. Run `git log --oneline -20` (what changed recently)
5. Run `python run_tests.py` (system health)
6. Check the Phase Roadmap above — identify what needs work
7. Check config/vault_config.json — correct for the machine you're on
8. Ask: is this session on the dev machine or estate laptop? Different paths.

---

## 14. CRITICAL BOUNDARIES (FROM V1 — REPEATED FOR EMPHASIS)

- **LLM Write:** Only gspread.append_row(). No modifications. No vault writes.
- **Vault Access:** Cloud LLMs NEVER read or write Obsidian, Gold, Silver, or Bronze vault.
- **Gemini Isolation:** Stage 2 sees ONLY raw transcript. Outputs ONLY JSON.
- **Dry-Run Default:** All scripts default to dry-run. `--confirm` required for real actions.
- **Config Security:** Never commit config.json, vault_config.json, credentials.json, token.json, .env.
- **Publish Deferred:** Do not develop publish.py further until Phase 7+.

---

**⚠️ This volume describes ACTIVE DEVELOPMENT. Always verify against the actual codebase.**
