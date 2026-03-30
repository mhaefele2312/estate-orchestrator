# Estate OS — Project Context for Claude Code

## How to Work With MHH (read this first)

MHH is not a developer. These behavior rules are non-negotiable:

- **Silent problem solving.** If you hit an error, try to fix it yourself first. Attempt at least 3 different approaches before asking MHH anything. MHH has zero technical knowledge — asking him technical questions does not help and slows everything down.
- **Never ask MHH technical questions.** Do not ask about file paths, API keys, config values, Python versions, package names, error codes, or anything requiring technical knowledge. Figure it out yourself by reading config files, checking the environment, or trying alternatives.
- **The only things worth stopping for:** (1) you need MHH to click something in a browser or app, (2) you need a credential or password only he has, (3) you have tried everything and are completely stuck. In those cases, ask ONE plain-English question only.
- **Key milestones only.** Report only when a major phase completes. Skip all play-by-play.
- **Real writes: use judgment.** Dry-run for anything touching real data. Go live for low-risk steps (installs, config, test runs). Never --confirm on the real sheet without a one-line heads-up first.
- **Safe by default.** Log all errors to file. Validate config before running. Check dependencies exist. Write a plain-English summary of what went wrong to a debug log so problems are traceable even if you keep going.
- **Plain English only.** One or two sentences max when you do communicate. No jargon, no stack traces unless asked.

---

> **This file is auto-loaded by Claude Code on every session start.**
> **Full specification:** `Estate-OS-Master-Plan-v2.md` in the repo root.
> **Read the full master plan before making any architectural decisions.**

---

## What This Project Is

Estate OS is a personal and family estate operating system with three layers:

1. **Ops Ledger** (Google Sheet) — non-sensitive daily operations, LLM-visible, append-only
2. **Obsidian Vault** (local markdown) — dark to all LLMs, institutional memory
3. **Gold Vault** (Cryptomator-encrypted) — LLMs never read or write

The system captures voice memos from a phone, parses them with Gemini into structured rows, appends them to a Google Sheet, and syncs weekly to Obsidian. It replaces tools like Quicken LifeHub with a local-first, family-aware, privacy-hardened system.

**Owner:** MHH (mhaefele@gmail.com)
**Repo:** github.com/mhaefele2312/estate-orchestrator

---

## Non-Negotiable Rules

**Violating any of these rules is a build-breaking error. Stop and ask MHH before proceeding if you're unsure.**

1. **Zero LLM write.** No LLM ever writes to any document except appending rows to the Ops Ledger Google Sheet via `gspread.append_row()`. LLMs never write to Obsidian. LLMs never write to Gold vault. LLMs never modify existing sheet rows.

2. **Business communication rules for voice capture.** Voice captures contain no sensitive data (no account numbers, SSNs, financial figures). This is a human discipline, not a software feature. **Do not build any sensitivity screening, PII detection, content filtering, or bifurcated routing in the capture pipeline.** Everything goes to the Ops Ledger. Period.

3. **Vaults are dark.** Cloud LLMs never read or write to the Obsidian vault or Gold vault. Only future local LLMs with tokenization (Phase 5+) may access vault data.

4. **Fail-closed.** Every script defaults to dry-run mode. Real actions require `--confirm` flag.

5. **Append-only.** The Ops Ledger sheet is append-only by architecture. `gspread.append_row()` cannot modify existing rows. The flat log files are append-only. Nothing is ever deleted from any log.

6. **Three-stage pipeline isolation.** Stage 2 (Gemini) receives ONLY the raw transcript — never the sheet, never flat files. Stage 2 outputs ONLY JSON. Stage 3 (Python) writes to four targets simultaneously (sheet, flat files, contacts CSV, contact-mentions.md). The LLM has no write path to any persistent document except sheet append.

7. **Gemini for daily ops, Claude for building.** Do not build features that use Claude API for daily operations. Gemini handles captures and queries. Claude (you) builds and maintains the system.

---

## Architecture at a Glance

```
Phone → Google Apps Script web app → raw .md transcript → Google Drive

Laptop Python pipeline (Phase 1) / Apps Script pipeline (Phase 1b):
  Stage 1: Read raw .md (no LLM)
  Stage 2: Gemini API → JSON array of rows (no sensitive screening)
  Stage 3: Python writes simultaneously to:
    ├── Google Sheet (gspread append_row)
    ├── Flat log files (master-log.md + GTD topic files)
    ├── google-contacts-import.csv (contact items only)
    └── contact-mentions.md (any person name detected)

Weekly sync: Python pushes logs + SOT snapshots + contact pages → Obsidian
```

---

## Sheet Schema (18 columns, flat)

All items share the same row shape. Contact fields are blank for non-contacts.

| Column | Description |
|--------|-------------|
| entry_date | Date captured (YYYY-MM-DD) |
| entry_time | Time captured (HH:MM) |
| capture_mode | morning_sweep / quick_note / evening_sweep |
| item_type | todo / reminder / action_log / contact / calendar / note / health_log |
| domain | One of 12 domains (01_Financial through 12_Operations) |
| description | The actual item, one sentence |
| responsible | Who owns this |
| due_date | When (blank if N/A) |
| status | open / in_progress / done / deferred |
| notes | Additional context |
| source_capture | Which .md file this came from |
| captured_by | Which family member (MHH, HBS, etc.) |
| given_name | Contact first name (blank for non-contacts) |
| family_name | Contact last name (blank for non-contacts) |
| organization | Contact organization (blank for non-contacts) |
| title | Contact title (blank for non-contacts) |
| phone | Contact phone (blank for non-contacts) |
| email | Contact email (blank for non-contacts) |

---

## 12 Domains

01_Financial, 02_Legal, 03_Property, 04_Insurance, 05_Medical, 06_Tax, 07_Estate-Planning, 08_Vehicles, 09_Digital, 10_Family, 11_Contacts, 12_Operations

---

## Flat File Architecture

**Type 1 — Append-only logs** (in `G:\My Drive\Estate Ops\Logs\`):
master-log.md, next-actions.md, projects.md, waiting-for.md, calendar.md, someday-maybe.md, reference-notes.md, completed.md, health.md, contacts.md, contact-mentions.md, google-contacts-import.csv

**Type 2 — Source-of-truth snapshots** (in `G:\My Drive\Estate Ops\Source-of-Truth\`):
sot-MHH-YYYY-MM-DD.csv, sot-latest-MHH.csv (pointer to most recent)

---

## Contact Pages in Obsidian

Location: `11_Contacts/[Person-Name].md`
Merge strategy: `<!-- mentions-start -->` marker comment
- **Above marker:** Manual content (Contact Info + Relationship sections). Never overwritten by scripts.
- **Below marker:** Auto-populated mentions section, rebuilt weekly from contact-mentions.md.
- **New contacts:** Created from template with blank Relationship fields.

---

## What Already Exists in This Repo

| Behavior | File | Status |
|----------|------|--------|
| Gate | behaviors/gate/gate.py | Tested live — has visibility input bug (fix in Phase 1) |
| Publish | behaviors/publish/publish.py | **Deferred to Phase 7+** — do not develop further |
| Health Check | behaviors/health-check/health_check.py | Tested live |
| Backup Check | behaviors/backup-check/backup_check.py | Tested live |
| Inbox Pickup | behaviors/inbox-pickup/inbox_pickup.py | Tested (test mode) |
| Capture App | behaviors/capture/Code.gs + Index.html | Built, not deployed — needs rebuild |
| Test Runner | run_tests.py | All passing |

---

## What Needs to Be Built (Phase 1)

Build these in order. Each builds on the previous.

1. **Create MHH-Ops-Ledger Google Sheet** — schema from above, 7 tabs (Raw Log + 6 FILTER views)
2. **Install gspread** + Google Sheets API OAuth credentials
3. **Build capture_pipeline.py** — reads .md transcripts, calls Gemini API, writes to sheet + flat files + contacts CSV + contact-mentions.md simultaneously
4. **Build snapshot.py** — source-of-truth promotion (exports edited sheets to Gold vault + Obsidian + SOT folder). Requires `--confirm` flag.
5. **Build weekly_sync.py** — pushes logs + latest SOT + contact pages to Obsidian. Handles marker-based contact page merge.
6. **Build reconciliation.py** — reads sheet status changes, appends completion entries to flat log files
7. **Create folder structure** — Logs/ and Source-of-Truth/ in Google Drive; Ops-Ledger/ and domain folders in Obsidian + Gold vault
8. **Draft Gemini Processing Gem prompt** — capture parsing with GTD categories, contact extraction, flat JSON output
9. **Draft Gemini Query Gem prompt** — reads SOT snapshots for daily conversational answers
10. **Update capture app** (Code.gs + Index.html) — text prompts, time-based mode detection, voice recording
11. **Deploy capture app** + Android home screen shortcut
12. **Add snapshot button** to Google Sheet (Apps Script custom menu)
13. **Fix gate.py** visibility input bug
14. **Create templates** — property template, Property-Index.md, contact page template
15. **End-to-end test** — voice → parse → sheet + logs → edit sheet → snapshot → query SOT → weekly sync to Obsidian

---

## File Paths on the Estate Laptop

```
Obsidian vault:    C:\Users\mhhro\Documents\Obsidian Vault
Gold vault:        E:\
Gold backup:       G:\My Drive\Gold-Backup
Estate Ops:        G:\My Drive\Estate Ops
MHH Inbox:         G:\My Drive\MHH-Inbox
HBS Inbox:         G:\My Drive\HBS-Inbox
Staging Intake:    G:\My Drive\Staging-Intake
Capture Archive:   G:\My Drive\Capture-Archive
```

Note: These paths are for the estate laptop, not the dev machine. Scripts should use config files or environment variables for paths so they work on both machines.

---

## Key Dependencies

- **gspread** — Google Sheets API (append_row for sheet writes)
- **google-auth** — OAuth for Google APIs
- **google-generativeai** — Gemini API for capture parsing
- **Python 3** — all scripts

---

## Things NOT to Build

- No sensitivity screening, PII detection, or content filtering in the capture pipeline
- No bifurcated routing (everything goes to one place — the Ops Ledger)
- No Claude API calls in daily operations (Gemini handles daily ops)
- No Publish behavior development (deferred to Phase 7+)
- No direct LLM writes to Obsidian or Gold vault
- No database — Google Sheets is the database
- No custom UI beyond the Google Apps Script capture app

---

## Context on MHH (the Builder/Owner)

- Non-developer, mid-career professional managing a multi-property family estate
- Comfortable with tech but not a programmer — clear, documented steps over clever abstractions
- Wife (HBS) must be able to use the capture system — if she won't use it, it doesn't ship
- Two children (LEH, HAH) will be added to the system later
- Building toward a permanent estate operating manual that survives any one person
- Entire family uses Gemini for daily AI interactions

---

## How to Start a Build Session

1. Read this file (you just did)
2. Read `Estate-OS-Master-Plan-v2.md` for full specification details
3. Run `git log --oneline -20` to see what's already been done
4. Check what phase we're on by examining existing code against the Phase 1 build order above
5. Pick up where the last session left off
6. Build one step at a time, show diffs, get approval before moving on
