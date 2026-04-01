# Estate OS — Claude Reference Manual: Volume 1 (Stable Foundation)

**Version:** 1.0
**Date:** April 1, 2026
**Status:** STABLE — this volume covers the built, tested, and locked-down parts of the system
**Owner:** MHH (mhaefele@gmail.com)
**Repository:** github.com/mhaefele2312/estate-orchestrator

---

## VOLUME STRUCTURE — READ THIS FIRST

This reference manual is split into two volumes:

**Volume 1 (this file: CLAUDE-REFERENCE-MANUAL-V1.md)**
Covers: System identity, non-negotiable rules, design principles, three-layer architecture, people and access tiers, the 18-column schema, 12 domains, folder structures (Obsidian and Gold vault), the capture app (Apps Script), the Google Sheet structure, and how to work with MHH. These are STABLE and BUILT. Trust this volume completely.

**Volume 2 (CLAUDE-REFERENCE-MANUAL-V2.md)**
Covers: All Python scripts (capture pipeline, snapshot, weekly sync, reconciliation, gate, health check, backup check, staging), batch files, config reference, flat file architecture, known issues, phase roadmap, and session continuity. These are ACTIVELY BEING DEVELOPED on the dev machine. DO NOT trust Volume 2 blindly — always verify against the actual codebase before making changes.

**HOW TO USE THESE VOLUMES:**

1. Read Volume 1 first. This is your ground truth. Do not modify anything Volume 1 describes without reading it carefully first.
2. Read Volume 2 second. Treat Volume 2 as a GUIDE, not gospel — check `git log` and the actual code before acting on what it says.
3. If Volume 1 and the codebase disagree, Volume 1 is probably right (flag the discrepancy to MHH).
4. If Volume 2 and the codebase disagree, the codebase is right (Volume 2 may be stale).

---

## 1. SYSTEM IDENTITY

**What Estate OS is:**

Estate OS is a personal and family estate operating system comprising three layers: the Master Log (Google Sheets workspace), Obsidian Vault (institutional memory), and Gold Vault (Cryptomator-encrypted sensitive records). It captures voice memos from a phone via Google Apps Script, parses them with Gemini into structured rows, appends them to Google Sheets, and syncs weekly to local markdown. It replaces Quicken LifeHub with a local-first, family-aware, privacy-hardened system that survives any one person and runs the estate year after year.

**Long-term vision:** A family knowledge base that future generations can query. Phase 5+ will add a local LLM (Ollama) with PII tokenization (Presidio) and a RAG layer (ChromaDB + LlamaIndex) so the family can ask natural language questions against the full estate dataset — without any cloud LLM ever seeing sensitive data.

**Owner:** MHH (mhaefele@gmail.com)
**Repository:** github.com/mhaefele2312/estate-orchestrator
**Platform:** Windows estate laptop + Android/iPhone phones + Google Drive + Obsidian local
**Current Phase:** Phase 1 (foundation)

---

## 2. NON-NEGOTIABLE RULES (VERBATIM FROM CLAUDE.MD)

These 7 rules are immutable. Violating any is a build-breaking error. Stop and ask MHH before proceeding if unsure.

1. **Zero LLM write.** No LLM ever writes to any document except appending rows to the Master Log Google Sheet via `gspread.append_row()`. LLMs never write to Obsidian. LLMs never write to Gold vault. LLMs never modify existing sheet rows.

2. **Business communication rules for voice capture.** Voice captures contain no sensitive data (no account numbers, SSNs, financial figures). This is a human discipline, not a software feature. **Do not build any sensitivity screening, PII detection, content filtering, or bifurcated routing in the capture pipeline.** Everything goes to the Master Log. Period.

3. **Vaults are dark.** Cloud LLMs never read or write to the Obsidian vault or Gold vault. Only future local LLMs with tokenization (Phase 5+) may access vault data.

4. **Fail-closed.** Every script defaults to dry-run mode. Real actions require `--confirm` flag.

5. **Workspace + snapshot architecture.** The Master Log sheet is a working workspace — the pipeline appends rows and MHH edits freely. The sheet is NOT the source of truth. The source of truth is the snapshot CSV (sot-latest-MHH.csv), created only when MHH clicks "Take Snapshot." The flat log files are append-only and immutable — no LLM ever modifies them.

6. **Three-stage pipeline isolation.** Stage 2 (Gemini) receives ONLY the raw transcript — never the sheet, never flat files. Stage 2 outputs ONLY JSON. Stage 3 (Python) writes to four targets simultaneously (sheet, flat files, contacts CSV, contact-mentions.md). The LLM has no write path to any persistent document except sheet append.

7. **Gemini for daily ops, Claude for building.** Do not build features that use Claude API for daily operations. Gemini handles captures and queries. Claude (you) builds and maintains the system.

---

## 3. 12 DESIGN PRINCIPLES (VERBATIM FROM MASTER PLAN)

1. **Zero LLM write — the supreme rule.** With the sole exception of appending parsed rows to the Master Log Google Sheet, no LLM ever writes, modifies, or deletes any document.
2. **Business communication rules for voice capture.** Professional-grade content — no sensitive data (account numbers, SSNs, financial figures) spoken. This is human discipline, not software.
3. **Vaults are dark.** Anything in Obsidian or Gold Vault is treated as sensitive by definition. Cloud LLMs never access.
4. **Ease of use beats features.** If the wife won't use it, it doesn't exist.
5. **Fail-closed.** Every script defaults to dry-run. Real actions require `--confirm`.
6. **Workspace + snapshot architecture.** Master Log is workspace; source of truth is snapshot CSV.
7. **One LLM for daily operations: Gemini.** Claude builds; Gemini handles captures and queries.
8. **Minimum custom code.** Google Sheets over database. Gemini Gems over custom prompts. Off-the-shelf tools over custom behaviors.
9. **Human in the loop.** Every piece of data reviewed by human before becoming institutional memory.
10. **No heartbeat requirement.** System works daily or weekly. Nothing breaks if you skip a day.
11. **Nothing is deleted.** Raw transcripts archived, not destroyed. Some captures have future archival value.
12. **Three copies minimum.** Critical data exists in at least three places (3-2-1 backup rule).

---

## 4. THREE-LAYER ARCHITECTURE

```
LAYER 1: OPS LEDGER (Master Log)
  Google Sheet in Estate Google Drive
  Append-only captures, user edits, filtered views
  Cloud LLM-visible (non-sensitive by design)
  ↓ (weekly one-way sync)

LAYER 2: OBSIDIAN VAULT
  Local markdown C:\Users\mhhro\Documents\Obsidian Vault\
  Institutional memory, SOPs, project notes, summaries
  Dark to all cloud LLMs

LAYER 3: GOLD VAULT
  Cryptomator-encrypted E:\
  Tax returns, deeds, trusts, policies, medical records
  LLMs NEVER access this layer
```

### Data Flow

```
Phone voice capture
  ↓
Google Apps Script web app (transcribes)
  ↓
Raw .md transcript → G:\My Drive\[USER]-Inbox
  ↓
Python Stage 1 (read transcript, no LLM)
  ↓
Python Stage 2 (send transcript to Gemini API only, receive JSON)
  ↓
Python Stage 3 (write simultaneously to 4 places):
  ├── Google Sheet (gspread append_row)
  ├── Flat log files (master-log.md + GTD topic files)
  ├── google-contacts-import.csv (contact items)
  └── contact-mentions.md (person names)
  ↓
Weekly sync (Python):
  ├── All logs → Obsidian Master-Log/
  ├── Latest SOT → Obsidian Master-Log/Source-of-Truth/
  ├── Contact pages rebuilt in Obsidian 11_Contacts/
  └── Nothing flows back to Google Drive (one-way)
```

### Routing Decision

One question determines where non-voice content goes:

> "Could this expose my accounts, identity, or financial position to someone unauthorized?"

**If YES → Gold Vault (Layer 3)**
**If NO → Obsidian Vault (Layer 2)**

Voice captures always go to Layer 1 (Master Log). No exceptions. No routing decision needed.

---

## 5. PEOPLE AND ACCESS TIERS

### User Table

| ID | Tier | Email | Sheet Name | Device | Inbox Dir | Capture URL Param | Notes |
|-----|------|-------|-----------|--------|-----------|-------------------|-------|
| MHH | Owner | mhaefele@gmail.com | MHH Master Log | Desktop + Android | G:\My Drive\MHH-Inbox | ?user=MHH (default) | Estate operator, system builder |
| HBS | Owner | hbs.rosevale.west@gmail.com | HBS Master Log | Mac + iPhone | G:\My Drive\HBS-Inbox | ?user=HBS | Co-operator, estate partner |
| LEH | Family | lhaefele@gmail.com | LEH Master Log | TBD | G:\My Drive\LEH-Inbox | ?user=LEH | Child, promotable to Owner when adult |
| HAH | Family | hahaefele@gmail.com | HAH Master Log | TBD | G:\My Drive\HAH-Inbox | ?user=HAH | Child, promotable to Owner when adult |
| HJH | Family | hollyhaefele@gmail.com | HJH Master Log | Android | G:\My Drive\HJH-Inbox | ?user=HJH | Property manager (2312, Rental 1 TX, Mule), promotable |
| OPA | Family | (TBD) | OPA Master Log | Android | G:\My Drive\OPA-Inbox | ?user=OPA | Elder, Family tier |

**Capture Base URL (all users):**
`https://script.google.com/macros/s/AKfycbwBPjHdP1fhPrW5fGaklbQLgJy2Tq3i_j20_jWyyO17oDQvzX8NYaK05VZF8fpD9DJLvQ/exec`

Append `?user=XXX` for each person. The app saves to `[USER]-Inbox` in Google Drive.

### Tier Rules

**Owner (MHH, HBS):**
- Full mutual visibility, all sheets, Family Master Log
- Snapshot authority over all sheets
- Obsidian access (manual read/write)
- Gold vault access (full)

**Family (LEH, HAH, HJH, OPA):**
- Own sheet only; rows also appear in MHH Master Log with `captured_by` tag
- No access to other users' sheets, Family Master Log, Obsidian, or Gold vault
- May receive access to designated shared items (e.g., HJH-Property-Docs)
- Promotable to Owner when appropriate (MHH decides)

**Contributor (future non-family):**
- Own sheet only; strictly isolated
- Never promoted; access can be time-limited or revoked

---

## 6. SCHEMA — 18 COLUMNS, FLAT

All items share the same row shape. Contact fields are blank for non-contacts.

| Column | Type | Description | Editable |
|--------|------|-------------|----------|
| entry_date | Date (YYYY-MM-DD) | Date captured | No (pipeline sets) |
| entry_time | Time (HH:MM) | Time captured | No (pipeline sets) |
| capture_mode | Enum | morning_sweep / quick_note / evening_sweep | No (pipeline sets) |
| item_type | Enum | todo / reminder / action_log / contact / calendar / note / health_log | Yes |
| domain | Enum (01-12) | One of 12 domains | Yes |
| description | Text | The actual item, one sentence | Yes |
| responsible | Text | Who owns this | Yes |
| due_date | Date or blank | When (blank if N/A) | Yes |
| status | Enum | open / in_progress / done / deferred | Yes |
| notes | Text | Additional context | Yes |
| source_capture | Text | Which .md file this came from | No |
| captured_by | Text | Which family member (MHH, HBS, etc.) | No |
| given_name | Text | Contact first name (blank for non-contacts) | Yes |
| family_name | Text | Contact last name (blank for non-contacts) | Yes |
| organization | Text | Contact organization (blank for non-contacts) | Yes |
| title | Text | Contact title (blank for non-contacts) | Yes |
| phone | Text | Contact phone (blank for non-contacts) | Yes |
| email | Text | Contact email (blank for non-contacts) | Yes |

### 12 Domains

| Code | Name |
|------|------|
| 01 | Financial |
| 02 | Legal |
| 03 | Property |
| 04 | Insurance |
| 05 | Medical |
| 06 | Tax |
| 07 | Estate-Planning |
| 08 | Vehicles |
| 09 | Digital |
| 10 | Family |
| 11 | Contacts |
| 12 | Operations |

### Item Types and GTD Routing

| item_type | GTD Category | Flat File | Sheet Tab |
|-----------|--------------|-----------|-----------|
| todo | Next Actions | next-actions.md | Open Todos |
| reminder | Calendar | calendar.md | Calendar |
| action_log | Done | completed.md | Action Log |
| contact | Contacts | contacts.md | Contacts |
| calendar | Calendar | calendar.md | Calendar |
| note | Reference | reference-notes.md | (none) |
| health_log | Health | health.md | Health Log |

---

## 7. GOOGLE SHEET STRUCTURE (MASTER LOG)

**Sheet ID (MHH):** 18OVdgdFLHd1qBUMIP4iWoZAGSrSfrV-WLjFQ7980b-w

### 7 Tabs

| Tab | Type | Filter | Purpose |
|-----|------|--------|---------|
| Raw Log | Data | (none) | All data; editable |
| Action Log | View | item_type = "action_log" | Completed actions |
| Open Todos | View | item_type = "todo" AND status = "open" | Current tasks |
| This Week | View | due_date between TODAY and TODAY+7 | Due this week |
| Contacts | View | item_type = "contact" | People captured |
| Calendar | View | item_type = "calendar" OR "reminder" | Events/reminders |
| Health Log | View | item_type = "health_log" | Wellness check-ins |

### Edit Rules

- **Safe to edit:** status, notes, due_date, responsible, domain, description, contact fields
- **Never edit:** entry_date, entry_time, capture_mode, source_capture, captured_by
- **Never delete rows.** Mark as "deferred" instead.
- **Never reorder columns.** Pipeline depends on A-R column order.
- **The sheet is a WORKSPACE, not the source of truth.** Source of truth is the snapshot CSV.

### Estate OS Menu (Apps Script)

Custom menu in the Google Sheets toolbar:
- "Take Snapshot (SOT)" — triggers snapshot.py --confirm via Apps Script → local terminal

---

## 8. CAPTURE APP (APPS SCRIPT)

### Files

| File | Location | Purpose |
|------|----------|---------|
| Code.gs | behaviors/capture/Code.gs | Backend — saves .md to Google Drive |
| Index.html | behaviors/capture/Index.html | Frontend — prompts, recording, transcript |
| manifest.json | behaviors/capture/manifest.json | Apps Script manifest |
| DEPLOY.md | behaviors/capture/DEPLOY.md | Deployment instructions |

### How It Works

1. User opens URL on phone (via home screen shortcut)
2. `?user=XXX` parameter determines which inbox folder to save to
3. Time-of-day auto-detects capture mode
4. Text prompts displayed (not read aloud)
5. User speaks into phone mic (or types)
6. Transcript saved as .md file to `[USER]-Inbox` in Google Drive
7. File format: `capture-YYYY-MM-DD-HHMM-[USER].md`

### Three Capture Modes

**Morning Sweep (before 11am) — 9 prompts:**
1. How are you feeling?
2. What's on your mind right now that you haven't written down?
3. What did you promise someone yesterday?
4. Who's waiting on something from you?
5. What's the one thing that would make today a win?
6. What are you avoiding?
7. What's worrying you that you haven't dealt with?
8. Anything coming up this week you haven't planned for?
9. What longer-term projects do you need to start on?

**Quick Note (11am-5pm) — 5 prompts:**
1. Who?
2. What?
3. Where?
4. When?
5. Why?

**Evening Sweep (after 5pm) — 6 prompts:**
1. How are you feeling?
2. What did you actually do today?
3. What did you say you'd do that you didn't?
4. Who did you talk to and what did you commit to?
5. What came up today that isn't captured yet?
6. What's nagging at you that you need to put somewhere so you can sleep?

### iOS Safari Workaround

iOS Safari blocks Web Speech API mic access in Apps Script sandboxed iframes. The app detects `not-allowed` errors and automatically switches to typing mode with a prompt to use the iOS keyboard's built-in dictation button. This is not a bug — it's an Apple platform limitation.

### Deployment

Deployed as a Google Apps Script web app. Current version: 9.
Execute as: estate Google account (mhh.rosevale.west@gmail.com)
Who has access: Anyone (URL is long/unguessable; app executes as estate account)

---

## 9. OBSIDIAN VAULT STRUCTURE

**Location:** `C:\Users\mhhro\Documents\Obsidian Vault\`
**LLM access:** NEVER. Cloud LLMs never read or write.

### Folder Tree (20 folders)

```
Obsidian Vault/
├── Inbox/              ← incoming items from gate (scans, clips, manual drops)
├── Accepted/           ← gate-approved, waiting for filing
├── Published/          ← sanitized for sharing (deferred Phase 7+)
├── Master-Log/         ← weekly sync of Master Log sheets + SOT snapshots
│   ├── Logs/           ← flat log copies
│   └── Source-of-Truth/ ← SOT snapshot CSVs
├── 01_Financial/
├── 02_Legal/
├── 03_Property/        ← home operating manual lives here
│   ├── Property-Index.md
│   ├── _property-template/
│   └── [property folders] — each with systems/, rooms/, exterior/, assets/, etc.
├── 04_Insurance/
├── 05_Medical/
├── 06_Tax/
├── 07_Estate-Planning/
├── 08_Vehicles/
├── 09_Digital/
├── 10_Family/
├── 11_Contacts/        ← auto-populated contact pages (weekly sync)
├── 12_Operations/      ← system docs, build logs, Estate OS notes
├── _prompts/           ← saved Gemini Gems
├── _archive/           ← old/completed projects
└── _views/             ← saved searches, index pages
```

### Contact Page Format

```markdown
# [Given Name] [Family Name]

## Contact Info
- Organization: [org]
- Title: [title]
- Phone: [phone]
- Email: [email]

## Relationship
- How we met: [manually filled in]
- Mutual contacts: [manually filled in]
- How I can help them: [manually filled in]
- How they can help me: [manually filled in]

<!-- mentions-start — everything below this line is auto-populated weekly -->
## Mentions
- [date]: [context from captures]
```

**Merge rule:** Everything ABOVE `<!-- mentions-start -->` is manual and NEVER overwritten. Everything BELOW is rebuilt each weekly sync from contact-mentions.md.

### Property Template Structure

```
03_Property/[Property-Name]/
├── overview.md              ← address, purchase date, key contacts, utilities
├── systems/                 ← hvac.md, plumbing.md, electrical.md, security.md, internet.md, etc.
├── rooms/                   ← kitchen.md, living-room.md, bedrooms, etc.
├── exterior/                ← garden.md, garage.md, pool.md, etc.
├── assets/                  ← vehicles.md, valuables.md, safes.md, etc.
├── contacts/                ← contractors.md, neighbors.md
├── maintenance-log.md       ← chronological record of repairs/upgrades
├── seasonal-checklist.md    ← spring/fall tasks
└── documents/               ← links (not copies) to Gold vault originals
    └── README.md            ← "Originals in Gold vault at E:\03_Property\..."
```

---

## 10. GOLD VAULT STRUCTURE

**Location:** `E:\` (Cryptomator mount — drive letter may vary, check config.json `gold_vault_dir`)
**Backup:** Encrypted ciphertext auto-syncs to `G:\My Drive\Gold-Backup\` via Google Drive for Desktop
**LLM access:** NEVER. Absolute boundary. No exceptions.
**Password:** Exists only on estate laptop and in executor package. Never stored digitally. Never sent electronically.

### Folder Tree (12 folders)

```
E:\
├── 01_Financial/      ← bank/brokerage statements, account records
├── 02_Legal/          ← contracts, agreements, legal correspondence
├── 03_Property/       ← deeds, title docs, closing statements, appraisals
├── 04_Insurance/      ← policy documents, claims, coverage summaries
├── 05_Medical/        ← medical records, lab results, prescriptions
├── 06_Tax/            ← tax returns, W-2s, 1099s, tax correspondence
├── 07_Estate-Planning/ ← wills, trusts, POA, beneficiary designations
├── 08_Vehicles/       ← titles, registration, purchase agreements
├── 09_Digital/        ← digital asset records, password vault exports, 2FA backups
├── 10_Family/         ← birth/marriage certificates, passports, SSN cards
├── 11_Contacts/       ← professional contact records with sensitive detail
└── 12_Operations/     ← system configs, API credentials, backup keys, SOT copies
```

### Filing Rules

- Drag and drop files directly into folders — this is safe and won't break anything
- Use descriptive filenames: `2026-Federal-Tax-Return.pdf`, `Chase-Checking-Statement-2026-03.pdf`
- Create subfolders within any domain if needed (e.g., `06_Tax/2026/`, `03_Property/2312/`)
- If a document spans two domains, put it in the primary domain and note the cross-reference
- Always lock the vault in Cryptomator when done

### What Does NOT Go in Gold Vault

- Voice captures (those go to Master Log automatically)
- Notes and summaries without sensitive data (those go in Obsidian)
- Working documents being actively edited (keep in Google Drive)

---

## 11. FILE PATHS ON ESTATE LAPTOP

| Resource | Path | Notes |
|----------|------|-------|
| Obsidian Vault | C:\Users\mhhro\Documents\Obsidian Vault | Local, never in cloud |
| Gold Vault | E:\ | Cryptomator mount; letter may vary |
| Gold Backup | G:\My Drive\Gold-Backup | Encrypted ciphertext only |
| Estate Ops | G:\My Drive\Estate Ops | Master folder for shared data |
| Logs | G:\My Drive\Estate Ops\Logs | Flat log files |
| Source-of-Truth | G:\My Drive\Estate Ops\Source-of-Truth | Snapshot CSVs |
| MHH Inbox | G:\My Drive\MHH-Inbox | MHH captures land here |
| HBS Inbox | G:\My Drive\HBS-Inbox | HBS captures |
| LEH Inbox | G:\My Drive\LEH-Inbox | LEH captures |
| HAH Inbox | G:\My Drive\HAH-Inbox | HAH captures |
| HJH Inbox | G:\My Drive\HJH-Inbox | HJH captures |
| OPA Inbox | G:\My Drive\OPA-Inbox | OPA captures |
| HJH Property Docs | G:\My Drive\HJH-Property-Docs | Shared property folder |
| Staging Intake | G:\My Drive\Staging-Intake | Legacy docs awaiting routing |
| Capture Archive | G:\My Drive\Capture-Archive | Processed transcripts |

---

## 12. DECISION LOG — WHY X OVER Y

This section captures the reasoning behind key decisions so future sessions don't re-litigate them or accidentally reverse them.

### Architecture Decisions

**Why Google Sheets over a database?**
MHH is not a developer. Google Sheets is visible, editable, shareable, and requires zero setup. A database would add complexity, require a UI layer, and make it harder for the family to interact with data. Sheets IS the database. The flat log files and SOT snapshots provide the immutability and backup that Sheets alone can't guarantee.

**Why Gemini for daily ops, Claude for building?**
The whole family is on Gemini already. Claude is used for building and maintaining the system — it's too expensive and complex for daily voice capture parsing. Gemini handles the repetitive parsing and querying. Claude handles the one-time architecture, code, and troubleshooting.

**Why three layers instead of one encrypted vault?**
Layer 1 (Master Log) needs to be LLM-visible for voice capture parsing and daily queries — it can't be encrypted. Layer 2 (Obsidian) is the institutional memory that humans curate — dark to LLMs by policy. Layer 3 (Gold Vault) is the truly sensitive stuff that gets hardware encryption. One vault can't serve all three needs.

**Why the estate laptop stays as the hub (not Docker or cloud)?**
MHH asked about Docker. The answer: it adds a layer of complexity for zero benefit. Google Drive already syncs files to the cloud. The Gold vault requires local filesystem access for Cryptomator. Obsidian is local by design. If the laptop dies, you clone the repo from GitHub, reinstall Python, reconnect Google Drive — back up in an hour. Docker doesn't buy portability when the data layer is already cloud-synced.

**Why Google Apps Script web app instead of a native phone app?**
Cross-platform (Android and iPhone), no app store approval, instant deployment, zero maintenance. The URL is long and unguessable so "Anyone" access is safe. The app executes as the estate Google account regardless of who opens it. A native app would require separate builds, signing, and updates.

**Why text prompts displayed (not read aloud)?**
Simpler implementation, works on all devices, doesn't require Text-to-Speech API, and lets the user read at their own pace. The prompts are guidance, not a script — users speak freely while glancing at them.

**Why continuous recording instead of per-question?**
One long recording is more natural. Users speak freely and touch on multiple topics. Gemini is smart enough to split mixed-topic transcripts into individual items. Per-question recording would feel like a form and reduce adoption.

**Why business communication rules instead of PII screening?**
Building PII detection is complex, error-prone, and creates a false sense of security. The simpler and more reliable approach: speak as if you're in a business meeting. No account numbers, no SSNs, no financial figures. This is a human discipline, not a software feature. It's foolproof because there's nothing to break.

**Why append-only flat files alongside the Google Sheet?**
The sheet is a working workspace — users edit it freely (mark done, fix categories, add notes). Flat files are the immutable safety net. Even if someone accidentally deletes sheet rows, the flat files preserve every item ever captured. Two systems, different purposes.

### People and Access Decisions

**Why separate estate email accounts (mhh.rosevale.west, hbs.rosevale.west)?**
Keeps estate activity isolated from personal Gmail. Google Drive, Sheets, and the capture app all run under the estate account. If MHH's personal Gmail gets compromised, estate data is on a separate account.

**Why a separate macOS user account for HBS instead of just a Chrome profile?**
Full isolation. A Chrome profile only separates browser data — HBS would still see her personal Desktop, Downloads, and apps. A separate macOS user gives her a clean workspace: her own Desktop, her own Google Drive mount, her own Cryptomator, her own Obsidian. When she logs in as "Estate," she's in estate mode. When she logs out, it's gone.

**Why share the entire estate Drive with HBS instead of individual folders?**
Simplifies setup dramatically. Originally we planned to share folders one by one, but that meant HBS would need to find and bookmark each shared folder separately. Sharing everything at once means she installs Google Drive for Desktop and everything appears under "Shared with me" automatically. One step instead of sixteen.

**Why Google Drive "My Drive" can't be shared as a top-level share?**
We tried. Google Drive doesn't allow sharing "My Drive" as a single item — you must select individual items within it. MHH selected all 16 items and shared them with HBS as Editor in one batch.

**Why generic family property guide instead of HJH-specific?**
OPA also manages property. LEH and HAH may in the future. A generic guide works for any family member on any property. HJH's specific property names (2312, Rental 1 TX, Mule) are in CLAUDE.md and the pipeline config, not in the user-facing guide.

### Security Decisions

**Why give Claude broad access during the build, then lock down after?**
Speed. Building the system required Claude to read config files, check folder structures, verify vault paths, deploy code to Apps Script via browser, and test integrations end-to-end. Restricting access during build would have meant MHH doing dozens of manual steps he doesn't have the technical skill for. The tradeoff: accept temporary exposure during build, then execute a comprehensive lockdown plan (Volume 1, Section 15) when the build is complete. Every credential that was exposed gets rotated. Every access path that was opened gets closed.

**Why rotate OAuth credentials instead of just revoking the token?**
The client_secret itself was visible to Claude sessions (it's in credentials.json, which Claude read to troubleshoot auth). Revoking the token only invalidates the current session — someone with the client_secret could potentially generate a new token. Rotating the entire OAuth client (deleting and recreating it in Google Cloud Console) invalidates everything.

**Why not just delete git history entirely?**
The git history contains useful information (what was built when, why decisions were made, who authored what). The SSL certs in history are the only truly sensitive item. Using `git filter-repo` to surgically remove just those files preserves the rest of the history. If that's too complex, deleting and re-creating the repo with a clean export is the simpler alternative.

### Documentation Decisions

**Why two reference manual volumes instead of one?**
Everything through the Gold vault (architecture, rules, schema, people, vaults, capture app, sheet) is built, tested, and stable. Everything after (scripts, pipelines, config, flat files) is actively being developed on the dev machine. A single manual would force future Claude sessions to guess which parts are trustworthy. Two volumes with clear trust levels prevent that: Volume 1 = gospel, Volume 2 = guide (verify against code).

**Why a separate Claude Reference Manual instead of embedding in the MHH Technical Manual?**
Two audiences, two purposes. The MHH manual is written for a human — narrative, readable, explains the "why." The Claude manual is written for a machine — structured, exhaustive, every path and key exact. Combining them would make the human manual unreadable or the machine manual incomplete.

**Why markdown for the Claude manual instead of .docx?**
Claude reads markdown natively and can parse it instantly. A .docx requires extraction before processing. The Claude manual is a technical reference that will be read by Claude at session start — markdown is the natural format.

---

## 13. WHAT NOT TO BUILD

These are off-limits. Do not develop.

- No sensitivity screening, PII detection, or content filtering in the capture pipeline
- No bifurcated routing (everything → Master Log, period)
- No Claude API calls in daily operations (Gemini handles daily ops)
- No Publish behavior development (deferred to Phase 7+)
- No direct LLM writes to Obsidian or Gold vault
- No custom database (Google Sheets IS the database)
- No custom UI beyond the Google Apps Script capture app
- No multi-step approvals or routing rules
- No automatic classification of sensitive vs. non-sensitive

---

## 14. HOW TO WORK WITH MHH

**MHH is not a developer.** These rules are non-negotiable:

- **Silent problem solving.** If you hit an error, try to fix it yourself first. Attempt at least 3 different approaches before asking. MHH has zero technical knowledge.
- **Never ask MHH technical questions.** No file paths, API keys, config values, Python versions, package names, error codes. Figure it out from config files, the environment, or by trying alternatives.
- **The only things worth stopping for:** (1) browser action needed — describe in plain English, (2) credential only he has, (3) completely stuck after 3+ attempts — ask ONE plain-English question.
- **Key milestones only.** Report when a major phase completes. Skip play-by-play.
- **Real writes: use judgment.** Dry-run for real data. Go live for low-risk steps. Never `--confirm` on the real sheet without a one-line heads-up.
- **Safe by default.** Log errors to file. Validate config. Check dependencies. Write plain-English debug summaries.
- **Plain English only.** One or two sentences max. No jargon, no stack traces unless asked.

---

## 15. SECURITY AUDIT AND LOCKDOWN PLAN

This section documents every permission Claude was given during the build, what's exposed, and exactly how to lock it down when the build is complete. Items are ranked from most impactful to least impactful.

### Current Exposure Summary (as of April 2026, during active build)

During the build, Claude (via Cowork and Claude Code) has had access to:

- **Google OAuth credentials** — client_id, client_secret, refresh_token in `behaviors/ops-ledger/credentials.json` and `token.json`. These grant read/write access to the estate Google Sheet and Google Drive.
- **Google Sheet ID** — the spreadsheet_id in config.json (18OVdgdFLHd1qBUMIP4iWoZAGSrSfrV-WLjFQ7980b-w) identifies the live MHH Master Log.
- **Gemini API key** — stored as environment variable. Grants access to Google AI.
- **SSL cert and private key** — `behaviors/desktop-capture/cert.pem` and `key.pem` for the local HTTPS capture server. These were committed to git history (commit 6ef880c), then removed from tracking (commit 4388b7a). They still exist in git history.
- **All file paths** — Obsidian vault, Gold vault mount letter, Google Drive folder structure, inbox paths. All in config.json files across multiple behaviors.
- **GitHub repo** — public or private, Claude has push access via MHH's git credentials on the dev machine.
- **Browser automation** — Cowork sessions have had Chrome access to the estate Google account (mhh.rosevale.west@gmail.com), including Google Drive, Google Sheets, and Apps Script editor.
- **Obsidian vault** — full read access via Cowork file mount.
- **Capture app deployment URL** — the full Apps Script URL is in multiple documents and config files.

### Lockdown Plan (Most Impactful → Least Impactful)

#### TIER 1: DO IMMEDIATELY WHEN BUILD COMPLETES

**1. Rotate Google OAuth credentials (CRITICAL)**
- Go to Google Cloud Console → APIs & Credentials
- Delete the current OAuth client (client_id: 1027055341664-c4206abbrq7qu8fcu667551k6l1i8qon)
- Create a NEW OAuth client
- Download new credentials.json, replace the old one
- Delete token.json (forces re-auth with new credentials)
- Run any script once to generate a new token.json
- WHY: The current client_secret and refresh_token have been visible to Claude sessions. Rotating them invalidates any cached tokens.

**2. Rotate Gemini API key (CRITICAL)**
- Go to Google AI Studio → API Keys
- Delete the current key
- Create a new one
- Update .env or environment variable
- WHY: The API key may have been visible in environment during Cowork sessions.

**3. Scrub git history of SSL certs (HIGH)**
- The cert.pem and key.pem files were committed in commit 6ef880c
- Even though they were removed from tracking in 4388b7a, they're still in git history
- Run: `git filter-branch` or `git filter-repo` to remove them from all commits
- OR: if the repo is private and small, consider deleting and re-creating it with a clean history
- After scrubbing, force-push to GitHub
- Generate new SSL certs for the desktop capture server
- WHY: Anyone with repo access can check out the old commit and extract the private key.

**4. Review GitHub repo visibility (HIGH)**
- Confirm the repo (github.com/mhaefele2312/estate-orchestrator) is PRIVATE
- If public: make it private immediately
- Review who has access (Settings → Collaborators)
- WHY: The repo contains config files with file paths, sheet IDs, and architecture details. Not secrets per se, but valuable reconnaissance for social engineering.

#### TIER 2: DO WITHIN ONE WEEK OF BUILD COMPLETION

**5. Restrict OAuth scopes (MEDIUM)**
- Current scope: `https://www.googleapis.com/auth/spreadsheets` (full read/write to ALL spreadsheets)
- Consider whether you can restrict to a more limited scope
- At minimum, the token should only be used by scripts you run yourself — never by a cloud LLM
- WHY: The current scope grants access to every spreadsheet in the estate account, not just the Master Log.

**6. Move credentials out of the repo directory (MEDIUM)**
- Move credentials.json and token.json to a location OUTSIDE the repo
- Update config.json paths to point to the new location (e.g., `C:\Users\mhhro\.estate-os\credentials.json`)
- WHY: Even with .gitignore, having secrets inside the repo directory increases the risk of accidental exposure.

**7. Revoke Cowork/Claude Code file access to Obsidian vault (MEDIUM)**
- After the build, Claude should not need access to the Obsidian vault folder
- In Cowork: don't mount the Obsidian vault folder in future sessions
- In Claude Code: remove the vault from any workspace settings
- WHY: Rule 3 says vaults are dark to LLMs. During build, Claude needed to create folders and check structure. After build, that access is no longer needed.

**8. Audit Google account sessions (MEDIUM)**
- Go to myaccount.google.com → Security → Your devices
- Review and remove any sessions you don't recognize
- Go to Security → Third-party apps → remove any apps you didn't authorize
- Do this for BOTH mhh.rosevale.west@gmail.com AND mhaefele@gmail.com
- WHY: Browser automation sessions may have left cached sessions.

#### TIER 3: DO WITHIN ONE MONTH

**9. Generate new SSL certs for desktop capture (LOW)**
- Delete the current cert.pem and key.pem in `behaviors/desktop-capture/`
- Generate fresh self-signed certs: `openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes`
- WHY: The old certs are in git history. New certs ensure no one can MITM the local capture server.

**10. Review Apps Script deployment permissions (LOW)**
- Go to script.google.com → Estate Capture → Deploy → Manage Deployments
- Confirm "Execute as: Me" and "Who has access: Anyone" are correct
- Consider whether you want to restrict access (e.g., "Anyone with Google account" vs. "Anyone")
- WHY: "Anyone" means no authentication required to open the capture URL. The URL is unguessable, but restricting access adds a layer.

**11. Add a .env.example file (LOW)**
- Create a .env.example with placeholder values (not real keys)
- Document which environment variables are needed
- WHY: Makes it clear what secrets exist without exposing actual values.

**12. Review config.json files across all behaviors (LOW)**
- Each behavior has its own config.json with paths
- Verify all paths are correct for the estate laptop (not the dev machine)
- Remove any config values that reference the dev machine
- WHY: Stale config paths could cause scripts to write to wrong locations.

### What's Already Secure (No Action Needed)

- **credentials.json and token.json** — never committed to git (.gitignore)
- **config.json (ops-ledger)** — never committed to git (.gitignore)
- **.env** — doesn't exist as a file; API key is in environment only
- **Gold vault** — Cryptomator encryption is independent of Estate OS; Claude never had the vault password
- **Gold vault backup** — encrypted ciphertext in Google Drive; useless without the password
- **Other behavior config.json files** — committed to git but contain only file paths, no secrets

### Ongoing Security Practices (After Lockdown)

- Never give Claude access to the Obsidian vault folder after build is complete
- Never paste credentials into a Claude conversation
- Run scripts locally only (never through a cloud LLM)
- Keep the GitHub repo private
- Review OAuth tokens annually (rotate if needed)
- Keep Cryptomator updated
- Never store the vault password digitally

---

## 16. CROSS-REFERENCE TO VOLUME 2

**Volume 2 location:** `CLAUDE-REFERENCE-MANUAL-V2.md` (same directory as this file)

**Volume 2 covers (ACTIVELY BEING DEVELOPED — verify against codebase):**

- All Python scripts: capture_pipeline.py, snapshot.py, weekly_sync.py, reconciliation.py, gate.py, health_check.py, backup_check.py, inbox_pickup.py, staging tools, weekly_review.py
- Batch files: run_daily.bat, run_weekly.bat, desktop_capture.bat
- Config reference: config.json keys, credentials setup, environment variables
- Flat file architecture: all 12 log files, SOT snapshots, how they interconnect
- Gemini Gems: processing prompt, query prompt
- Known issues and workarounds
- Phase roadmap and completion status
- Session continuity checklist
- Testing and validation procedures
- Troubleshooting guide

**IMPORTANT FOR FUTURE CLAUDE SESSIONS:**
Volume 2's content describes scripts and pipelines that are being actively developed on the dev machine. Before modifying any script, always:
1. Run `git log --oneline -20` to see what changed recently
2. Read the actual script file (not just Volume 2's description)
3. Run `python run_tests.py` to check current state
4. If Volume 2 says something different from the code, THE CODE IS RIGHT

---

**Document Version:** 1.0
**Last Updated:** April 1, 2026
**This volume is STABLE.** Update only when the foundation changes (new user added, schema change, vault restructure, or architectural decision).
