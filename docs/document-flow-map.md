# Estate OS — Document Flow Map

*How documents enter the system, move through it, and where they end up.*

---

## The Three Document Worlds

Every document in Estate OS lives in one of three worlds:

| World | Where | Who Reads It | Who Writes It |
|-------|-------|-------------|---------------|
| **Ops Ledger** | Google Sheet + flat log files | Gemini (queries) | capture_pipeline.py (appends only) |
| **Obsidian Vault** | Local laptop markdown | MHH only | weekly_sync.py, gate.py |
| **Vaults** | Encrypted (Gold X:\\, Silver Y:\\, Bronze) | Local LLM only (future) | MHH (Gold), staging_router.py (Silver/Bronze) |

Cloud LLMs (Gemini, Claude) never read or write vault content. That is non-negotiable.

---

## Document Types and Their Entry Points

### 1. Voice Captures (daily operations)

```
Phone mic
  → Google Apps Script (capture app on phone)
  → raw .md transcript file
  → Google Drive / MHH-Inbox  or  HBS-Inbox
```

These are the system's daily input. They contain tasks, reminders, contacts, notes —
**never** sensitive data (account numbers, SSNs, etc.). That is a human discipline.

---

### 2. Physical Documents (legacy estate files)

```
Paper or PDF on a scanner / external drive / USB
  → [security_scan.py]  — Windows Defender check before anything moves
  → [staging_sorter.py] — copies to Google Drive Staging-Intake, sorted by type
  → [staging_router.py] — MHH routes each file interactively:
        g = Gold vault (X:\)   — MHH-curated, permanent record
        s = Silver vault (Y:\) — machine-named legacy content
        b = Bronze vault       — Silver overflow on external storage
        o = Obsidian           — reference material
        k = Keep in staging    — skip for now
        d = Delete review      — moves to _review_delete/ subfolder, not deleted
```

Silver and Bronze routing writes a provenance record to `_provenance/ingestion-log.jsonl`
so every routing decision is traceable.

---

### 3. Structured Data (sheet exports)

```
MHH-Ops-Ledger Google Sheet
  → [snapshot.py]  — exports all tabs as timestamped CSVs
  → written simultaneously to three locations:
        G:\My Drive\Estate Ops\Source-of-Truth\   (primary)
        X:\12_Operations\Source-of-Truth\          (Gold vault copy)
        Obsidian Vault\Ops-Ledger\Source-of-Truth\ (Obsidian copy)
```

---

## The Voice Capture Pipeline (daily flow)

```
MHH-Inbox / HBS-Inbox  (Google Drive)
      ↓
  [inbox_pickup.py]
      — moves .md transcripts to Obsidian Vault / Inbox
      ↓
  [gate.py]  — MHH reviews and approves
      — stamps provenance metadata on each file
      — moves approved files to Obsidian Vault / Accepted
      ↓
  [capture_pipeline.py]
      Stage 1: reads raw .md (no LLM)
      Stage 2: sends ONLY the transcript to Gemini → receives JSON rows
      Stage 3: writes simultaneously to:
          ├── Google Sheet       (gspread append_row — never modifies existing rows)
          ├── master-log.md      (append-only flat log)
          ├── GTD topic files    (next-actions.md, projects.md, waiting-for.md, etc.)
          ├── contacts.md
          ├── contact-mentions.md
          └── google-contacts-import.csv
      ↓
  [reconciliation.py]  — user marks rows "done" in sheet
      — appends completion entries to completed.md
      ↓
  [weekly_sync.py]  — weekly push from Google Drive → Obsidian
      — copies flat log files
      — copies latest SOT snapshot
      — builds / updates contact pages  (manual content above
        <!-- mentions-start --> marker is never overwritten)
```

---

## The Vault Tokenizer Pipeline (Layer 4 — local LLM prep)

This pipeline makes vault content safe for a future local LLM to read.
It runs on the estate laptop only. Nothing leaves the laptop.

```
Gold Vault (X:\)  or  Silver Vault (Y:\)
      ↓
  [vault_tokenizer.py]
      — reads each .md or .txt file
      — skips unchanged files (SHA-256 hash check)
      — runs Microsoft Presidio (local, no API call) to detect PII:
            SSNs, account numbers, routing numbers, phone numbers,
            names, addresses, dates, emails, credit cards, and more
      — custom recognizers handle estate-specific patterns:
            US_ROUTING_NUMBER — 9-digit ABA routing numbers
            US_BANK_ACCOUNT   — 8–17 digit account numbers with context
      — replaces each sensitive value with a named token:
            214-77-3901   →  [SSN_0001]
            021000021     →  [ROUTING_0001]
            4402817733    →  [ACCT_0002]
            Martin Haefele→  [NAME_0001]
      — same original value always gets the same token across all documents
        (enables cross-document linking in the RAG layer)
      ↓
  Token Store  (C:\Users\mhhro\Documents\Estate-Token-Store\)
      ├── gold\      — tokenized copies of Gold vault docs
      ├── silver\    — tokenized copies of Silver vault docs
      └── _registry\
          ├── token_registry.json   — maps every token → original value  [SENSITIVE]
          └── file_hashes.json      — tracks which files have been processed
```

The Token Registry never leaves the estate laptop. The tokenized documents
are safe for a local LLM (Ollama, future Phase 5) to ingest for RAG queries.

---

## Monitoring and Health

```
[health_check.py]   — daily vault status report (never modifies anything)
    — checks vault folder structure
    — flags inbox files older than 48 hours
    — detects Obsidian Sync conflicts
    — reports behavior last-run times

[backup_check.py]   — Gold backup status report (never performs backup)
    — checks G:\My Drive\Gold-Backup age and file count
    — warns if backup is overdue (default threshold: 168 hours / 7 days)
```

---

## Vault Folder Structure (Gold, Silver, Bronze — identical layout)

```
00_Unsorted          ← staging area; Silver only (Gold routing is always deliberate)
01_Financial
02_Legal
03_Property
04_Insurance
05_Medical
06_Tax
07_Estate-Planning
08_Vehicles
09_Digital
10_Family
11_Contacts
12_Operations
_provenance/         ← machine decision log; Silver and Bronze only
    ingestion-log.jsonl
```

**Gold** — filed by MHH personally. Permanent record going forward.
**Silver** — filed by staging_router or local LLM. Legacy content. Machine provenance tracked.
**Bronze** — Silver overflow on external USB or NAS. Identical structure. Manual management.

---

## Google Drive Layout

```
G:\My Drive\
├── MHH-Inbox\              ← phone captures land here
├── HBS-Inbox\              ← spouse captures (Phase 2)
├── Staging-Intake\         ← external drive content sorted here before routing
├── Capture-Archive\        ← processed transcripts after pipeline
├── Gold-Backup\            ← backup of X:\
├── Silver-Backup\          ← backup of Y:\
└── Estate Ops\
    ├── Logs\               ← append-only flat files (never edited, only appended)
    │   ├── master-log.md
    │   ├── next-actions.md
    │   ├── projects.md
    │   ├── waiting-for.md
    │   ├── calendar.md
    │   ├── someday-maybe.md
    │   ├── reference-notes.md
    │   ├── completed.md
    │   ├── health.md
    │   ├── contacts.md
    │   ├── contact-mentions.md
    │   └── google-contacts-import.csv
    └── Source-of-Truth\    ← timestamped sheet exports
        ├── sot-MHH-YYYY-MM-DD.csv
        └── sot-latest-MHH.csv  (pointer to most recent)
```

---

## Obsidian Vault Layout

```
C:\Users\mhhro\Documents\Obsidian Vault\
├── Inbox\              ← new captures from inbox_pickup.py
├── Accepted\           ← approved by gate.py
├── Published\          ← passed publish checks (Phase 7+)
├── 01_Financial\  through  12_Operations\
├── 11_Contacts\
│   └── [Person-Name].md    ← manual content above <!-- mentions-start -->
│                              auto-populated mentions below (rebuilt weekly)
└── Ops-Ledger\         ← synced from Google Drive by weekly_sync.py
    ├── *.md  (flat log copies)
    └── Source-of-Truth\
```

---

## File Extensions and What Handles Them

| Extension | Where it appears | Who processes it | Notes |
|-----------|-----------------|-----------------|-------|
| `.md` | Everywhere | All scripts | Primary format |
| `.txt` | Vault docs | vault_tokenizer.py | Tokenized same as .md |
| `.pdf` | Vault docs | Not yet handled | Phase 5: pdfplumber (text PDFs) + easyocr (scanned) |
| `.csv` | SOT snapshots | snapshot.py, weekly_sync.py | Sheet exports |
| `.jsonl` | _provenance logs | staging_router.py (writes), human review | Append-only |
| `.json` | Token registry, hash index | vault_tokenizer.py | Sensitive — stays on estate laptop |

---

## Script Inventory

| Script | Behavior | Status |
|--------|---------|--------|
| `behaviors/capture-pipeline/capture_pipeline.py` | Voice capture → Sheet + logs | Active |
| `behaviors/inbox-pickup/inbox_pickup.py` | Drive inbox → Obsidian inbox | Tested |
| `behaviors/gate/gate.py` | Human approval gate | Live (known bug) |
| `behaviors/publish/publish.py` | Obsidian accepted → published | Deferred Phase 7+ |
| `behaviors/reconciliation/reconciliation.py` | Sheet "done" → flat log | Active |
| `behaviors/snapshot/snapshot.py` | Sheet → SOT CSVs | Active |
| `behaviors/weekly-sync/weekly_sync.py` | Drive → Obsidian sync | Active |
| `behaviors/vault-setup/vault_setup.py` | Create Silver/Bronze vault structure | Active |
| `behaviors/vault-tokenizer/vault_tokenizer.py` | Vault docs → Token Store | Active |
| `behaviors/staging-intake/security_scan.py` | Defender scan before staging | Active |
| `behaviors/staging-intake/staging_sorter.py` | External drive → sorted staging | Active |
| `behaviors/staging-intake/staging_router.py` | Staged files → vault destinations | Active |
| `behaviors/health-check/health_check.py` | Daily vault health report | Live |
| `behaviors/backup-check/backup_check.py` | Gold backup status report | Live |

---

*Generated 2026-03-31. Source of truth for project state: `Estate-OS-Master-Plan-v2.md`.*
