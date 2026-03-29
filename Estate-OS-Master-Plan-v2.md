# Estate OS — Master Build Plan v2

**Version:** 2.0
**Date:** 2026-03-28
**Status:** Design complete — ready for phased build
**Owner:** MHH (mhaefele@gmail.com)
**Repository:** github.com/mhaefele2312/estate-orchestrator

---

## 1. PURPOSE

This document is the complete design specification for the Estate OS — a personal and family estate operating system. It is written so that any Claude session (including Opus, Claude Code on dev machine, or any future session) can review the plan, identify gaps, and resume building without needing prior context.

**Two goals:**

1. Help one person (MHH) and his family capture, organize, and act on estate and family information with minimal friction.
2. Build toward a permanent estate operating manual that survives any one person and runs the estate automatically year over year.

**What this replaces:** This system replaces Quicken LifeHub and similar estate management SaaS products. It provides the same functionality (centralized estate records, document management, family sharing) but with local encryption, family-aware architecture, multi-layer routing, and an executor/family handoff plan that LifeHub never offered. The one gap LifeHub had that this system also addresses: a break-glass executor package for heirs.

---

## 2. DESIGN PRINCIPLES (Non-Negotiable)

1. **Zero LLM write — the supreme rule.** With the sole exception of appending parsed rows to the Ops Ledger Google Sheet, no LLM (cloud or local) ever writes to, modifies, or deletes any document in this system. Cloud LLMs can read the Ops Ledger to answer queries. Cloud LLMs process voice transcripts and output JSON. That is the full extent of LLM write access. Obsidian files: LLMs never write. Gold vault files: LLMs never read or write. Staging intake: a local LLM may later rename files, but renamed copies are always kept separate from originals, and originals are always preserved as backup — because we assume LLMs will drift if they write to documents.
2. **Business communication rules for voice capture.** The phone voice capture is treated as professional-grade content — speak as if you are in a business meeting. No sensitive data (account numbers, SSNs, financial figures) goes through the voice pipeline. Cloud LLMs see these transcripts and that is acceptable. There is no sensitive-data screening in the capture loop because the content is non-sensitive by design. This is a human discipline, not a software feature — no code screens or validates content for sensitivity.
3. **Vaults are dark.** Anything admitted into the Obsidian vault or the Gold vault is treated as sensitive by definition. Cloud LLMs can never read vault contents. Only tokenized information from the vaults, processed through a local LLM at a later stage, can be seen by cloud LLMs.
4. **Ease of use beats features.** If the wife won't use it, it doesn't exist.
5. **Fail-closed.** Every script defaults to dry-run. Real actions require `--confirm`.
6. **Append-only ops ledger.** The master log sheet is never modified by an LLM — only appended to by code. MHH can manually edit the sheets at any time in Google Drive or in Obsidian.
7. **One LLM for daily operations: Gemini.** The whole family is on Gemini. Claude builds and maintains the system, not daily operations.
8. **Minimum custom code.** Every layer uses the simplest tool that works. Google Sheets over a database. Gemini Gems over custom prompts. Off-the-shelf tools over custom behaviors.
9. **Human in the loop.** Every piece of data is reviewed by a human before it becomes permanent institutional memory.
10. **No heartbeat requirement.** The system works if you use it daily or weekly. Captures accumulate in Google Drive and wait. Nothing breaks if you skip a day or a week. The value compounds over months and years, not days.
11. **Nothing is deleted.** Raw transcripts are archived, not destroyed. Some captures have future archival value (voice recordings of family, explanation notes, verbal histories). Processed transcripts move to a Google Drive archive folder where they can be reviewed, moved to the vault, or preserved permanently.
12. **Three copies minimum.** Critical estate data exists in at least three places at all times (3-2-1 backup rule).

---

## 3. THREE-LAYER ARCHITECTURE

```
+------------------------------------------------------------+
|  LAYER 1: OPS LEDGER (non-sensitive by design, LLM-visible)|
|  Google Sheet in Estate Google Drive                        |
|  Append-only. Cloud LLMs can read and append.              |
|  Todos, reminders, calendar, contacts, action log           |
|  Business communication rules: no sensitive data spoken     |
+------------------------------------------------------------+
          |
          | Weekly one-way sync (script exports
          | sheets to Obsidian Ops-Ledger/ folder)
          v
+--------------------------------------------------+
|  LAYER 2: OBSIDIAN VAULT (dark to all LLMs)      |
|  Local markdown. Cloud LLMs never read or write.  |
|  SOPs, meeting notes, property manuals,           |
|  document summaries, institutional memory,         |
|  Ops Ledger copies, system documentation           |
+--------------------------------------------------+
          |
          | Original documents filed manually
          | to Layer 3
          v
+--------------------------------------------------+
|  LAYER 3: GOLD VAULT (encrypted, air-gapped)     |
|  Cryptomator-encrypted, Google Drive backup       |
|  Tax returns, deeds, trusts, policies,            |
|  bank statements, medical records                  |
|  LLMs NEVER access this layer                      |
+--------------------------------------------------+

NOTE: Layers 2 and 3 are populated MANUALLY by the user —
not by any automated pipeline from Layer 1. The only automated
flow is the weekly one-way sync of Ops Ledger sheets into
Obsidian for archival. Everything else (scans, web clips,
documents, emails) enters the vaults through manual filing
or through gate.py for items placed in the Obsidian Inbox.
```

### 3.1 Layer 1 — Ops Ledger

**What:** A Google Sheet in the estate Google Drive. Append-only by architecture. Every capture from every family member lands here as individual rows. This is the daily working layer — the engine of the todo list, reminders, action log, and contacts.

**Contains:** Todos, reminders, deadlines, action log entries, contact notes, calendar items, health check-ins. Plain operational information only — non-sensitive content by design. Nothing in the Ops Ledger is sensitive by design, because voice captures follow the business communication rule (no account numbers, SSNs, financial figures spoken into the phone).

**Who reads it:** Gemini reads it to answer queries ("what do I have to do today?"). Claude reads it on the laptop during weekly review. Family members each have their own sheet visible to each other. MHH can manually edit the sheets at any time in Google Drive.

**Location:** `G:\My Drive\Estate Ops\MHH-Ops-Ledger` (and later `HBS-Ops-Ledger`)

**Schema — one row per item:**

| Column | Description | Example |
|--------|-------------|---------|
| entry_date | Date captured | 2026-03-28 |
| entry_time | Time captured | 09:15 |
| capture_mode | morning_sweep / quick_note / evening_sweep | morning_sweep |
| item_type | todo / reminder / action_log / contact / calendar / note / health_log | todo |
| domain | From the 12 domains | 03_Property |
| description | The actual item, one sentence | Call insurance agent re Elm St coverage |
| responsible | Who owns this (text only) | MHH |
| due_date | When (blank if N/A) | 2026-04-01 |
| status | open / in_progress / done / deferred | open |
| notes | Additional context | Agent is Sarah Chen, 555-1234 |
| source_capture | Which .md file this came from | capture-2026-03-28-0915-MHH.md |
| captured_by | Which family member | MHH |
| given_name | Contact first name (blank for non-contacts) | Sarah |
| family_name | Contact last name (blank for non-contacts) | Chen |
| organization | Contact organization (blank for non-contacts) | First National Bank |
| title | Contact title (blank for non-contacts) | Mortgage Broker |
| phone | Contact phone (blank for non-contacts) | 555-1234 |
| email | Contact email (blank for non-contacts) | |

**Note:** `health_log` is included as an item_type for health tracking entries from voice capture check-ins ("How are you feeling?" responses). These always stay in the Ops Ledger — business communication rules apply, so nothing sensitive is spoken. Detailed medical records (diagnoses, lab results, prescriptions) are filed directly to Gold vault or Obsidian by the user — they are never spoken into the phone capture.

**Sheet tabs — views built with Google Sheets formulas, no custom code:**

The master log lives on Tab 1 (Raw Log). All other tabs are read-only views built from `=FILTER()` formulas. Zero custom code. The sheet IS the project management system.

- **Tab 1: Raw Log** — append-only master, never edited after writing
- **Tab 2: Open Todos** — `=FILTER()` where item_type=todo and status=open
- **Tab 3: This Week** — filter by due_date within next 7 days
- **Tab 4: Contacts** — filter by item_type=contact
- **Tab 5: Calendar** — filter by item_type=calendar
- **Tab 6: Action Log** — filter by item_type=action_log
- **Tab 7: Health Log** — filter by item_type=health_log

**Longevity:** After 12-24 months the sheet may have 2,000+ rows. Google Sheets handles up to 10 million cells. Quarterly archiving of completed/deferred items to an Archive tab is the mitigation plan.

### 3.1.1 Two File Types — Append-Only Logs vs. Source-of-Truth Snapshots

The Ops Layer uses TWO kinds of flat files. Understanding the difference is critical.

**TYPE 1: APPEND-ONLY LOGS (historical record, never modified)**

Python writes to these at capture time. Every item ever captured is here. No LLM ever writes to these files. They are the immutable history of the system.

| File | GTD Category | What Goes In |
|------|-------------|-------------|
| `master-log.md` | (All) | Every item ever captured — complete source of truth for history |
| `next-actions.md` | Next Actions | Specific single-step tasks with context to act on |
| `projects.md` | Projects | Multi-step efforts (see project schema below) |
| `waiting-for.md` | Waiting For | Items delegated or awaiting external response |
| `calendar.md` | Calendar | Date/time-specific events and hard deadlines |
| `someday-maybe.md` | Someday/Maybe | Ideas, aspirations, not committed |
| `reference-notes.md` | Reference | Notes, observations, context — no action required |
| `completed.md` | Done | Items marked done (appended by reconciliation script) |
| `health.md` | (Custom) | "How are you feeling?" responses |
| `contacts.md` | (Custom) | People, roles, contact info (see contacts workflow below) |

Location: `G:\My Drive\Estate Ops\Logs\`

**TYPE 2: SOURCE-OF-TRUTH SNAPSHOTS (current state after user edits)**

When MHH has manually edited the Google Sheets — marked things done, added notes, cleaned up descriptions, corrected categories — and is satisfied the sheets are accurate, MHH "hits the button" to promote the current sheet state as the new source of truth. This is what Gemini reads for daily queries.

| File | What It Is |
|------|-----------|
| `sot-MHH-2026-03-28.csv` | Full export of MHH sheet as of that date |
| `sot-Family-2026-03-28.csv` | Full export of combined family sheet |
| `sot-latest-MHH.csv` | Always points to the most recent snapshot |

Location: `G:\My Drive\Estate Ops\Source-of-Truth\`

**How they work together:**

```
CAPTURE TIME (automatic):
  Gemini processes transcript → JSON
  Python simultaneously writes to:
    ├── Append-only log files (Type 1) — never modified after writing
    └── Google Sheet (via gspread append_row)

BETWEEN CAPTURES (manual):
  MHH edits Google Sheets:
    - Marks items done
    - Adds notes, corrects categories
    - Cleans up descriptions
    - Deletes duplicates
  The sheets become the user's curated version.

"HIT THE BUTTON" (when MHH is satisfied the sheets are clean):
  snapshot.py --confirm
    ├── Exports all sheets as timestamped CSVs → Source-of-Truth/ folder
    ├── Copies to Gold vault: E:\12_Operations\Source-of-Truth\
    ├── Copies to Obsidian: Ops-Ledger\Source-of-Truth\
    └── Updates sot-latest-MHH.csv pointer

  Also available as a button in Google Sheet (Apps Script custom menu).

GEMINI DAILY QUERIES:
  Gemini reads sot-latest-MHH.csv (the source-of-truth snapshot)
  NOT the append-only logs, NOT the live sheet directly.
  This ensures Gemini always works from MHH's curated, edited version.

WEEKLY SYNC TO OBSIDIAN:
  All log files + latest source-of-truth → Obsidian Ops-Ledger/ folder
  One-way push. Obsidian is the offline backup.
```

**Why two types:** The append-only logs are the safety net — if anything ever goes wrong with the sheets or the snapshots, the complete history exists in files no LLM ever touched. The source-of-truth snapshots are the working version that Gemini reads — always reflecting MHH's latest manual edits. Old snapshot versions pile up with timestamps; MHH manually deletes old ones when they want.

### 3.1.2 Project Tracking Schema

The `projects.md` append-only log tracks multi-step efforts with richer fields than simple todos:

```
## [project_name] — [domain]
- Status: active / someday / completed / on-hold
- Next action: [the very next physical thing to do]
- Responsible: [who owns the next action]
- Target date: [when the project should be done]
- Related contacts: [people involved]
- Notes: [context, history, decisions]
- Domain: [from 12 domains]
```

Example:
```
## Refinance VA House — 03_Property
- Status: active
- Next action: Call mortgage broker for rate quote
- Responsible: MHH
- Target date: 2026-06-01
- Related contacts: Sarah Chen (broker), Jim Walsh (attorney)
- Notes: Current rate 5.2%, targeting below 4.5%. Pre-approval docs in Gold vault.
- Domain: 03_Property
```

Gemini detects multi-step efforts from voice captures and outputs project-type JSON. Python appends to `projects.md`. The Google Sheet has a Projects tab using the same fields.

### 3.1.3 Contacts Workflow

Contacts have a richer flow than other item types because they feed into both Google Contacts (for phone access) and Obsidian (for relationship network).

**At capture time — when user says "new contact":**

Gemini classifies as item_type=contact and extracts: name, organization, title, phone, email, context. Python writes simultaneously to:

1. `contacts.md` (append-only log)
2. Google Sheet Contacts tab
3. `google-contacts-import.csv` — formatted with Google Contacts column headers:
   ```
   Given Name,Family Name,Organization,Title,Phone 1 - Value,Email 1 - Value,Notes
   Sarah,Chen,First National Bank,Mortgage Broker,555-1234,,Met through Jim Walsh re VA House refinance
   ```
   MHH manually imports this CSV to Google Contacts whenever convenient.

**At capture time — when any person is mentioned (not just "new contact"):**

Gemini extracts the person's name from any voice capture. Python appends a mention record to `contact-mentions.md`:
```
2026-03-28 | Sarah Chen | morning_sweep | Discussed rate options, she'll send quotes by Friday
2026-03-28 | Jim Walsh | morning_sweep | Need to ask him about trust amendment timeline
```

**Weekly sync — auto-create Obsidian contact pages:**

The weekly sync script reads `contacts.md` and `contact-mentions.md` and creates/updates a page per person in `11_Contacts/`:

```
11_Contacts/
├── Sarah-Chen.md
├── Jim-Walsh.md
├── ... (one page per person)
└── _contact-template.md
```

Each contact page follows a standard template:

```markdown
# Sarah Chen
## Contact Info
- Organization: First National Bank
- Title: Mortgage Broker
- Phone: 555-1234
- Email:
- Google Contact: imported

## Relationship
- How we met:
- Mutual contacts: Jim Walsh
- How I can help them:
- How they can help me: Mortgage rates, lending advice

<!-- mentions-start — everything below this line is auto-populated by weekly_sync.py -->
## Mentions (auto-populated from voice captures)
- 2026-03-28: Discussed rate options, she'll send quotes by Friday
- 2026-03-25: Jim Walsh recommended her for VA House refinance
```

The **Contact Info** section is populated automatically from capture data. The **Relationship** section has blank fields the user fills in manually over time. The **Mentions** section below the `<!-- mentions-start -->` marker is auto-populated by the weekly sync script from `contact-mentions.md`. The sync script replaces everything below the marker each week — manual edits above the marker are always preserved. Over time, each contact page builds into a complete relationship history.

**Gemini query support:** User asks "What do I know about Sarah Chen?" Gemini reads `contact-mentions.md` (focused file, all mentions across all captures) and the source-of-truth contacts tab to synthesize an answer. No new code — just Gemini reading existing files.

### 3.1.4 Human-Readable Outputs from the Ops Ledger

The data in the system needs to be viewable in multiple ways:

**Built-in (zero code):** Google Sheets filter tabs automatically display Open Todos, This Week, Contacts, Calendar, Projects, Health Log. MHH views and edits these directly.

**Gemini queries (zero code):** Gemini reads the latest source-of-truth snapshot and answers conversational questions: "What do I need to do today?" "What's overdue?" "What projects are active?"

**Script-generated summaries (Phase 4):** A Python script reads the source-of-truth snapshots and produces formatted outputs:

- **Weekly summary .md** — what got done, what's overdue, what's coming up
- **Project tracker** — grouped by domain, showing status of multi-step efforts
- **Todo list export** — formatted for printing or for Google Keep (future)
- **Family roll-up** — combined view across all family members
- **Contact network** — who was mentioned this week, relationship updates

These scripts read from snapshots — they never touch the live sheet or the append-only logs.

**Family sharing — individual sheets + combined family sheet:**

Four family members, added in phases:

| Member | Sheet | Phase |
|--------|-------|-------|
| MHH | MHH-Ops-Ledger | 1 |
| HBS | HBS-Ops-Ledger | 2 |
| LEH | LEH-Ops-Ledger | Later |
| HAH | HAH-Ops-Ledger | Later |
| Combined | Family-Ops-Ledger | 2 (created as soon as HBS is added) |

```
G:\My Drive\Estate Ops\
├── MHH-Ops-Ledger         (MHH's personal sheet)
├── HBS-Ops-Ledger         (HBS's personal sheet — Phase 2)
├── LEH-Ops-Ledger         (LEH's personal sheet — later)
├── HAH-Ops-Ledger         (HAH's personal sheet — later)
└── Family-Ops-Ledger      (combined family sheet — Phase 2)
```

All sheets are visible to all family members. The combined Family-Ops-Ledger aggregates open items from all individual sheets. MHH can manually edit any sheet at any time in Google Drive.

**Ops Ledger → Obsidian sync (weekly, one-way):**

A script runs weekly and exports all sheets (individual + combined) as files into the Obsidian vault's `Ops-Ledger/` folder. This is a one-way push — Obsidian gets a copy for archival and offline reference. Changes in Obsidian do NOT flow back to Google Sheets.

```
Obsidian Vault/
└── Ops-Ledger/
    ├── MHH-Ops-Ledger-2026-03-28.csv
    ├── Family-Ops-Ledger-2026-03-28.csv
    └── ... (timestamped weekly snapshots)
```

Ops Ledger content goes into this folder as-is. It does NOT get categorized into the domain folders (01_Financial, 03_Property, etc.). Voice captures deal with multiple subjects and don't fit easy categorization. The domain folders in Obsidian are for manually-filed documents, SOPs, and property manuals — not for Ops Ledger data.

**Prior art:** Todoist launched "Ramble" in January 2026 — voice to structured tasks using Gemini. 76,000 users in 3 weeks. Their architecture validates the voice-to-structured-data approach. Their product is not suitable here because it is proprietary SaaS, sends audio to Doist's cloud servers, stores data in Todoist's format only, and does not support the multi-layer architecture.

---

### 3.2 Layer 2 — Obsidian Vault

**What:** Local Obsidian vault at `C:\Users\mhhro\Documents\Obsidian Vault\`. The institutional memory of the estate. SOPs, operational notes, substantive captures with sensitive content, document summaries, property operating manuals.

**Contains:** Everything that needs to be remembered long-term but is not a raw document. Meeting notes with legal detail. Property history. Health records summaries. Estate planning decisions. Home operating manuals. Explanation notes.

**Does NOT contain:** Raw financial documents, legal originals, tax returns, SSNs, account numbers. Those go to Layer 3.

**LLM access:** None. LLMs never read or write to the Obsidian vault directly. They produce staged content that humans review and manually move in.

**Version control:** Weekly git snapshot of the vault contents (local repo only, never pushed to GitHub since vault contains private data). Adds ~2 minutes to weekly routine. Provides full version history of every note.

**Folder structure (20 folders):**

```
C:\Users\mhhro\Documents\Obsidian Vault\
├── Inbox/              ← incoming items waiting for gate review (scans, web clips, manual drops)
├── Accepted/           ← gate-approved, ready for filing
├── Published/          ← sanitized, cleared for sharing (future use — deferred)
├── Ops-Ledger/         ← weekly one-way sync of Ops Ledger sheets (auto-populated)
├── 01_Financial/
├── 02_Legal/
├── 03_Property/        ← home operating manual lives here (see section 8)
│   ├── _property-template/    ← standard template (copied for each property)
│   ├── Property-Index.md      ← master list of all properties with links
│   ├── [Property-Name-1]/
│   ├── [Property-Name-2]/
│   └── ... (7+ properties)
├── 04_Insurance/
├── 05_Medical/
├── 06_Tax/
├── 07_Estate-Planning/
├── 08_Vehicles/
├── 09_Digital/
├── 10_Family/
├── 11_Contacts/
├── 12_Operations/      ← system documentation, build logs, Estate OS config notes
├── _prompts/
├── _archive/
└── _views/
```

**Note on Inbox:** The Inbox is for manually-placed items only (scans, web clips, documents dropped there). Voice captures do NOT route through the Inbox — they go directly to the Ops Ledger via the capture pipeline. Gate.py processes Inbox items with provenance frontmatter.

---

### 3.3 Layer 3 — Gold Vault

**What:** Cryptomator-encrypted vault mounted at `E:\` on the estate laptop. Backed up to `G:\My Drive\Gold-Backup\` on estate Google Drive as encrypted ciphertext only.

**Contains:** Tax returns, trust documents, deeds, insurance policies, financial statements, legal originals, medical records. Raw documents only.

**Folder structure (12 folders):**

```
E:\ (Cryptomator mount)
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
└── 12_Operations/      ← encrypted system configs, API credentials, backup keys
```

**LLM access:** Never. Absolute boundary. No exceptions.

**Backup:** Encrypted ciphertext syncs automatically to `G:\My Drive\Gold-Backup\` via Google Drive for Desktop. The encryption key exists only on the estate laptop and in the executor package (see section 10).

---

## 4. ROUTING DECISION FRAMEWORK

### Voice Captures (Phone) — Always Ops Ledger

Everything from the phone voice capture goes to the Ops Ledger. Period. No routing decision needed. Business communication rules apply — content is non-sensitive by design.

The only exception: if the user says "take a special note to be filed under [topic]" during a capture, that note can be manually routed from Google Drive to the appropriate Obsidian folder. This is a manual step, not an automated pipeline.

### Everything Else (Scans, Emails, Documents, Web Clips) — Manual Routing

For content that enters the system through channels other than voice capture, one question determines where it goes:

> **"Could this expose my accounts, identity, or financial position to someone unauthorized?"**

**If YES → Gold Vault (Layer 3)**
**If NO → Obsidian Vault (Layer 2)**

### Always Gold (Layer 3):

- Dollar amounts attached to accounts or positions
- Account numbers, routing numbers, policy numbers, EINs, SSNs
- Original signed legal documents (contracts, deeds, wills, trusts)
- Tax returns and supporting schedules
- Insurance policies (originals)
- Medical records with diagnoses, medications, test results
- Brokerage/bank statements
- User manuals and original documents for property systems

### Always Obsidian (Layer 2):

- Notes written from scratch (project notes, travel logs, observations)
- Summaries or interpretations of Gold documents (summary in Obsidian, original in Gold)
- Web clippings, article excerpts, research notes
- SOPs and procedures
- Contact notes (name, role, context — NOT account numbers or policy numbers)
- Meeting notes that reference but don't reproduce sensitive figures
- Project plans without budget line items
- Property operating manuals and explanation notes
- Ops Ledger weekly snapshots (auto-synced to Ops-Ledger/ folder)

### Multi-Layer Pattern:

Most real-world items produce entries at multiple layers:

> "An email saying you owe a vendor $4,200 generates:
> - **Ops Ledger:** (via voice capture at next morning sweep) 'Pay vendor invoice, due April 15, responsible: MHH'
> - **Gold Vault:** the PDF invoice itself (manually filed)
> - **Obsidian:** nothing (unless you want a note about the vendor relationship)"

### Future: Email Tags for Fast Filing

In a later phase, emails sent to the estate email account with tags (e.g., subject line contains `[property]` or `[legal]`) could be automatically routed to the correct Obsidian domain folder. This is a Phase 4+ automation.

---

## 5. THE CAPTURE SYSTEM

### 5.1 Three Capture Modes

**Morning Sweep** (auto-detected before 11am)
Text prompts shown on screen — not read aloud:

1. How are you feeling?
2. What's on your mind right now that you haven't written down?
3. What did you promise someone yesterday?
4. Who's waiting on something from you?
5. What's the one thing that would make today a win?
6. What are you avoiding?
7. What's worrying you that you haven't dealt with?
8. Anything coming up this week you haven't planned for?
9. What longer-term projects do you need to start on?

**Quick Note** (auto-detected 11am–5pm)
Five rapid-fire prompts:

1. Who?
2. What?
3. Where?
4. When?
5. Why?

**Evening Sweep** (auto-detected after 5pm)

1. How are you feeling?
2. What did you actually do today?
3. What did you say you'd do that you didn't?
4. Who did you talk to and what did you commit to?
5. What came up today that isn't captured yet — a name, a number, a decision, a problem?
6. What's nagging at you that you need to put somewhere so you can sleep?

### 5.2 Capture Flow

```
[User taps home screen button on Android phone]
        |
        v
[Google Apps Script web app opens in Chrome]
        |
        v
[Time-of-day auto-selects mode — no user choice required]
        |
        v
[Text prompts appear as lightweight guide]
[Voice recording is active — user speaks freely (business communication rules)]
        |
        v
[User taps Submit]
        |
        v
[Raw transcript saved as timestamped .md file to Google Drive]
[File name: capture-YYYY-MM-DD-HHMM-MHH.md]
        |
        v
========= PHASE 1: LAPTOP PROCESSING =========
(migrates to Apps Script processing in Phase 1b)
        |
        v
[Python script on laptop picks up new .md files]
        |
        v
STAGE 1 — TRANSCRIPT (no LLM)
  Raw .md file read from Google Drive sync folder
        |
        v
STAGE 2 — PARSING (Gemini only, outputs JSON)
  Gemini API receives ONLY the raw transcript
  Gemini never sees the sheet
  Output: JSON array of row objects
  NO sensitive screening — content is non-sensitive by design
        |
        v
STAGE 3 — APPENDING (no LLM, code only)
  Python + gspread library
  ALL rows appended via sheet.append_row() → Ops Ledger
  No routing, no bifurcation — everything goes to the sheet
        |
        v
[Raw transcript .md file MOVED to Capture-Archive in Google Drive]
[Transcripts preserved — some have future archival value]
```

**No sensitive screening in this pipeline.** Voice captures follow business communication rules. Nothing spoken into the phone contains sensitive data. There is no sensitive-flagging step, no bifurcated routing, and no staging files. Every parsed row goes to the Ops Ledger. Period.

**Migration to Phase 1b (all in Apps Script):** Once the laptop-based pipeline is tested and trusted, Stages 2 and 3 move into Google Apps Script. The phone handles everything automatically — no laptop needed for daily captures. This requires storing a Google AI API key in Apps Script project properties (Google-to-Google, relatively safe). The laptop pipeline remains available as a fallback.

### 5.3 Drift Prevention (Critical)

Drift prevention is architectural, not instructional. The LLM is physically isolated from all persistent storage:

- Stage 2 (Gemini) receives only the raw transcript. It never sees the sheet or any flat file.
- Stage 2 outputs only JSON. It writes to nothing.
- Stage 3 (Python) receives only the JSON. It writes to four places simultaneously:
  - Google Sheet via `append_row()` (cannot modify existing rows)
  - Append-only flat log files (master-log.md + GTD topic files by item_type)
  - Google Contacts import CSV (for contact-type items)
  - Contact mentions log — `contact-mentions.md` (for any person name detected)
- The append-only log files are flat files in Google Drive. Gemini has no API to write to flat files.
- Gemini reads source-of-truth snapshots for daily queries — these are CSVs that only the snapshot script writes.
- **The LLM has no write path to any persistent document except appending rows to the Google Sheet.**

**This is not "we told the LLM not to modify documents." This is "the LLM has no path to modify documents."**

**This is not "we told the LLM not to modify the sheet." This is "the LLM has no path to the sheet."**

**Why gspread:** Mature, widely-used open-source Python library (github.com/burnash/gspread). The `append_row()` method adds rows to the bottom and has no ability to read or modify existing data. LLM drift on the sheet is architecturally impossible.

---

## 6. THE GEMINI OPS GEM

A saved Gemini Gem (custom prompt) used for two purposes:

### Purpose 1 — Processing Captures

Called after each voice capture. Receives the raw transcript. Outputs structured rows in JSON format. No sensitive screening — business communication rules mean content is non-sensitive by design.

Key behaviors:

- Split mixed-topic transcripts into individual items (voice captures often cover multiple subjects)
- Assign item_type (todo / reminder / action_log / contact / calendar / note / health_log)
- Assign domain from the 12 domains (best guess — multi-topic captures may span domains)
- Identify responsible person if mentioned
- Assign due date if mentioned or implied
- Output ONLY a JSON array of new rows — nothing else
- Never reference or modify existing data
- **No sensitive screening** — voice captures follow business communication rules, content is non-sensitive by design

**Example output:**

```json
[
  {
    "item_type": "todo",
    "domain": "03_Property",
    "description": "Call insurance agent re Elm St coverage",
    "responsible": "MHH",
    "due_date": "2026-04-01",
    "notes": "Agent is Sarah Chen",
    "given_name": "",
    "family_name": "",
    "organization": "",
    "title": "",
    "phone": "",
    "email": ""
  },
  {
    "item_type": "contact",
    "domain": "11_Contacts",
    "description": "New contact: Sarah Chen, mortgage broker",
    "responsible": "MHH",
    "due_date": "",
    "notes": "Met through Jim Walsh re VA House refinance",
    "given_name": "Sarah",
    "family_name": "Chen",
    "organization": "First National Bank",
    "title": "Mortgage Broker",
    "phone": "555-1234",
    "email": ""
  },
  {
    "item_type": "health_log",
    "domain": "05_Medical",
    "description": "Feeling tired, slight headache",
    "responsible": "MHH",
    "due_date": "",
    "notes": "Morning check-in",
    "given_name": "",
    "family_name": "",
    "organization": "",
    "title": "",
    "phone": "",
    "email": ""
  }
]
```

### Purpose 2 — Querying

User asks Gemini verbally or by text: "What do I have to do today?" "What's overdue?" "What did I capture this week about the property?"

Gemini reads the Ops Ledger sheet via Google Workspace integration and answers conversationally.

---

## 7. INFLOW TYPES AND TOOLS

Every type of information that enters the system, and what handles it:

| Inflow Type | Tool | Destination | Phase |
|-------------|------|-------------|-------|
| Voice capture (phone) | Google Apps Script web app | Ops Ledger (via pipeline) | 1 |
| Explanation notes (micro recorder) | Upload .m4a/.mp3 → local Whisper transcription | Obsidian Inbox → gate review | 5 |
| Web articles / research | Obsidian Web Clipper (browser extension) | Obsidian vault directly | 1 |
| Scanned documents (phone) | Microsoft Lens app → Google Drive | MHH-Inbox → inbox-pickup → gate | 1 |
| Email attachments | Manual save during weekly review (Gmail filters + Apps Script later) | Gold vault or Obsidian depending on content | 1 (manual) / 4 (automated) |
| Downloads from internet | Manual save to appropriate folder | Gold if sensitive, Obsidian if reference | 1 |
| Spreadsheets / project plans | Google Drive estate folder | Link from Obsidian; budget figures → Gold | 1 |
| Legacy documents (old drives) | Staging intake pipeline (see section 9) | Sorted to Gold, Obsidian, or archive | 3 |
| Photos (family/estate) | Microsoft Lens or manual | Obsidian or staging depending on type | 3 |

**Off-the-shelf tools to install:**

1. **Obsidian Web Clipper** — free browser extension, saves web content directly to Obsidian vault
2. **Microsoft Lens** — free phone app, scans documents to Google Drive as searchable PDFs
3. **Obsidian Templates plugin** — built-in, provides consistent note structure for properties, contacts, projects

---

## 8. HOME OPERATING MANUAL

The home operating manual lives inside `03_Property/` in the Obsidian vault. With 7+ properties, every property gets a subfolder using a standard template.

### Property Index

`03_Property/Property-Index.md` — master list linking to every property with address, key contacts, and status.

### Standard Property Template

Every property folder follows this structure. Blank folders are fine — the template serves as a menu of what to document, not a requirement to fill everything. For large houses, every room or building gets its own subfolder.

```
03_Property/[Property-Name]/
├── overview.md              ← address, purchase date, key contacts, utilities, layout description
│
├── systems/                 ← whole-house systems
│   ├── hvac.md              ← thermostat operation, filter schedule, contractor
│   ├── plumbing.md          ← main shutoff location, hot water heater, quirks
│   ├── electrical.md        ← panel location, generator, breaker map
│   ├── security.md          ← alarm codes, cameras, who has keys
│   ├── internet.md          ← ISP, router location, wifi password, mesh nodes
│   ├── irrigation.md        ← zones, schedule, winterization
│   ├── audio.md             ← whole-house audio, speaker setup, streaming
│   ├── visual.md            ← TVs, projectors, cable/streaming setup
│   └── tech.md              ← smart home devices, hubs, automations
│
├── rooms/                   ← room-by-room documentation
│   ├── kitchen.md
│   ├── dining-room.md
│   ├── living-room.md
│   ├── family-room.md
│   ├── master-bedroom.md
│   ├── master-bathroom.md
│   ├── bedroom-2.md         ← (name as needed per property)
│   ├── bedroom-3.md
│   ├── guest-room.md
│   ├── laundry.md
│   ├── basement.md
│   └── ... (add rooms as needed)
│
├── exterior/                ← outdoor and outbuildings
│   ├── garden.md            ← plantings, layout, maintenance schedule
│   ├── garage.md            ← parking, tools, storage layout
│   ├── storage.md           ← sheds, storage units, what's where
│   ├── pool.md              ← (if applicable)
│   └── ... (add structures as needed)
│
├── assets/                  ← valuable items and equipment at this property
│   ├── vehicles.md          ← cars, boats, equipment kept at this property
│   ├── bikes.md             ← bicycles, e-bikes
│   ├── gear.md              ← sports equipment, tools, outdoor gear
│   ├── valuables.md         ← art, collectibles, high-value items
│   ├── safes.md             ← safe locations, types, what's stored
│   └── kitchen-equipment.md ← major appliances, special equipment
│
├── contacts/
│   ├── contractors.md       ← plumber, electrician, handyman, etc.
│   └── neighbors.md         ← key neighbor contacts, HOA
│
├── maintenance-log.md       ← chronological record of repairs and upgrades
├── seasonal-checklist.md    ← spring/fall tasks specific to this property
│
└── documents/               ← links (not copies) to Gold vault originals
    └── README.md            ← "Originals in Gold vault at E:\03_Property\..."
```

**Note:** Not every property needs every folder. A small apartment might have 5 files. A large multi-building estate might have 40+. The template is a menu, not a mandate.

### Explanation Notes Workflow

Recording how things work in each property:

1. Record explanation verbally (phone voice capture or micro recorder)
2. Transcript lands in Obsidian Inbox (via capture pipeline or manual upload)
3. During gate review, file into the correct property subfolder
4. Link to user manuals stored in Gold vault using Obsidian `[[filename]]` links

**This structure solves the inheritance problem.** When children eventually take over, they open the property folder and everything is there — how every system works, who to call, what the seasonal tasks are, and where the original documents live.

---

## 9. STAGING INTAKE AREA (Legacy Documents)

**What it is:** A temporary processing area for sorting old external drive contents. NOT a permanent vault. The "loading dock" metaphor — everything that arrives here has a destination elsewhere.

**What it handles:** Full digital life archives from old external drives — documents (PDFs, Word), photos, videos, and miscellaneous files. Multi-type triage pipeline.

**Why it exists:** You have old external drives with unsorted estate-relevant documents mixed with personal files. These need security scanning, type classification, and routing to the correct layer.

### Processing Pipeline

```
[Plug in old external drive]
        |
        v
[Security scan — antivirus/malware check]
        |
        v
[Copy contents to staging folder on Google Drive]
G:\My Drive\Staging-Intake\[drive-name-date]\
        |
        v
[Sort by file type — automated script]
├── documents/     (PDF, DOCX, TXT)
├── photos/        (JPG, PNG, HEIC)
├── video/         (MP4, MOV)
├── spreadsheets/  (XLSX, CSV)
└── other/         (everything else)
        |
        v
[For documents: OCR if scanned images (local Tesseract or Ollama)]
        |
        v
[Local LLM classification — what is this document?]
  - Invoice? → route to Gold vault under appropriate domain
  - Family photo? → route to Obsidian 10_Family/ or photo archive
  - Tax document? → route to Gold vault 06_Tax/
  - Personal note? → route to Obsidian under appropriate domain
  - Junk/duplicate? → flag for deletion review
        |
        v
[Human reviews LLM suggestions before any routing happens]
        |
        v
[Items routed to final destination]
[Staging folder emptied — nothing stays permanently]
```

### Storage Planning

- Gold vault: well under 1TB (PDFs, financial statements, legal docs). Fits comfortably in encrypted Google Drive.
- Staging intake: varies. Estate business documents fit in Google Drive. Large personal archives (photos, videos) may overflow to external drive or Synology NAS (future purchase).
- Migration path: when staging data exceeds Google Drive capacity, move to external storage backed up on Synology NAS.

### Phase Placement

Staging intake is Phase 3. It requires the local LLM stack (Ollama) for classification, which is Phase 5. However, Phase 3 can use manual classification with LLM assistance added later. The security scan and type-sorting steps work without LLM.

---

## 10. EXECUTOR PACKAGE ("What to Do If We Die")

**Status:** Requirements defined, detailed design deferred until MHH and spouse discuss.

### What It Is

A break-glass document package that gives executors/trustees/family members everything they need to manage the estate if MHH and/or spouse are incapacitated or deceased.

### Requirements

- **Format:** Encrypted document on a passcode-protected USB drive
- **Copies:** One in safe deposit box at bank, one in home safe or trusted location
- **Updates:** Reviewed and updated annually during estate review
- **Recipients:** Named executor(s), spouse, and eventually children (staged access)

### Must Contain (at minimum)

- Where everything is (all three layers, how to access each)
- Cryptomator vault password and how to open it
- Google account credentials or recovery path
- List of all financial accounts with institution names (no account numbers — those are in Gold vault)
- Insurance policies summary (carrier, policy number location, agent contact)
- Attorney and accountant contact information
- Location of physical documents (safe deposit box key, filing cabinet, etc.)
- How the Estate OS works (brief user guide)
- List of recurring obligations (mortgage, insurance, subscriptions, property tax)
- Digital accounts and how to access or close them
- Instructions for the Obsidian vault and what's in each folder

### Staged Family Involvement

Children are 15-18. Staged access plan:

- **Now:** No access to financial systems. Can see property documentation and family notes.
- **18-21:** Read access to selected Obsidian sections. Introduction to the system structure.
- **21-25:** Read access to Ops Ledger. Begin participating in property management tasks.
- **25+:** Gradual financial responsibility handoff. Access to Gold vault under supervision.
- **Full handoff:** All access, executor role, system administration.

### Research Needed Before Building

- Best practices for digital estate planning (research task)
- Legal requirements for executor access in relevant jurisdictions
- Optimal encryption for USB drives (VeraCrypt vs. hardware-encrypted drives)
- How to handle two-factor authentication accounts after death

---

## 11. LOCAL LLM AND RAG STACK (Future)

### Purpose

Enable querying all estate data (Obsidian + Gold) through a cloud LLM safely by tokenizing sensitive information first. The local LLM processes raw data, replaces PII with tokens, and stores tokenized versions. A RAG layer on top allows natural language queries against the full estate dataset.

### Architecture

```
[Obsidian Vault] ──→ [Local LLM: Ollama] ──→ [PII Tokenization: Presidio]
[Gold Vault]     ──→ [Local LLM: Ollama] ──→ [PII Tokenization: Presidio]
                                                      |
                                                      v
                                           [Tokenized Data Store]
                                                      |
                                                      v
                                      [Vector DB: ChromaDB + LlamaIndex]
                                                      |
                                                      v
                              [Cloud LLM (Gemini) queries tokenized data safely]
```

### Components

| Component | Purpose | Status |
|-----------|---------|--------|
| Ollama | Local LLM runtime | Watchlist — Phase 5 |
| ChromaDB | Vector database for embeddings | Watchlist — Phase 5 |
| LlamaIndex | RAG orchestration library | Watchlist — Phase 5 |
| Microsoft Presidio | PII tokenization before RAG | Watchlist — Phase 5 |
| Whisper (via Ollama) | Local transcription for micro recorder uploads | Phase 5 |

### Reor (Watchlist Alternative)

Reor (github.com/reorproject/reor) is an open-source desktop app: Obsidian + built-in local RAG. Same markdown format, runs Ollama locally, automatically links related notes, Obsidian-compatible. If mature enough by Phase 5, it could replace the manual Ollama + ChromaDB + LlamaIndex stack.

### Query Use Cases

From the laptop only:

- "How much did I spend on property tax last year?"
- "What maintenance has been done on the VA house heating system?"
- "What did the attorney say about the trust amendment in March?"
- "Where are we spending too much money?"

### Mini PC Network Access (Unresolved)

The local LLM may run on an always-on mini PC rather than the estate laptop. How this machine accesses the vault data is an open design question. Options under consideration:

**Option A: Syncthing (encrypted sync)** — Open-source tool syncs vault folders between machines over encrypted connection. Both machines have a copy. Most resilient, works when either machine is off, but two copies to manage.

**Option B: Shared network folder** — Estate laptop shares Documents folder on home network. Mini PC reads from there. Simple, but requires both machines on same network and laptop running.

**Option C: Manual USB transfer** — Periodically copy vault data to mini PC via USB. Air-gapped, most secure, but manual and data gets stale between transfers.

**Recommendation (not yet decided):** Option A (Syncthing) is likely the best fit. Encrypted, automatic, works without both machines being on simultaneously. But this decision depends on the mini PC purchase and home network setup.

---

## 12. HARDWARE AND SOFTWARE

### Hardware (Current)

| Component | Status | Purpose |
|-----------|--------|---------|
| Estate laptop (Windows 11) | Live | Primary estate machine. Obsidian vault, Cryptomator, Google Drive sync |
| Android phone (MHH) | Live | Voice capture via Apps Script web app |
| iOS device (HBS) | Live | Voice capture (Phase 2 — needs iOS compatibility testing) |
| 1TB external SSD | Arriving tomorrow | Laptop backup (Veeam image + File History) |
| Mini computer (backup mirror) | Arriving in weeks | Air-gapped mirror of estate laptop, updated periodically |

### Hardware (Planned)

| Component | Purpose | Phase |
|-----------|---------|-------|
| Always-on mini PC | Shared family LLM server (Ollama + RAG) | 5 |
| Mac mini (Claude Code) | Dedicated Claude Code machine with own email + Signal. Completely separate from estate data. | 5 |
| Synology NAS (optional) | Overflow storage for large legacy archives (photos, video) | 6+ |

### Software (Current / Phase 1)

| Software | Purpose | Status |
|----------|---------|--------|
| Obsidian | Vault management (Layer 2) | Installed |
| Cryptomator | Gold vault encryption (Layer 3) | Installed |
| Google Drive for Desktop | Cloud sync for Gold backup + Google Drive inboxes | Installed |
| Git | Version control for orchestrator code + vault snapshots | Installed |
| Python 3 | Orchestrator behaviors, gspread pipeline | Installed |
| Node.js (v24) | Claude Code on dev machine | Installed on dev machine |
| Google Apps Script | Capture web app | Built, not yet deployed |
| gspread (Python) | Append-only writes to Google Sheet | To install |
| Obsidian Web Clipper | Web clipping to vault | To install |
| Microsoft Lens | Phone document scanning | To install |
| Veeam Agent Free | System image backup | To install (when SSD arrives) |

### Software (Future Phases)

| Software | Purpose | Phase |
|----------|---------|-------|
| Ollama | Local LLM runtime | 5 |
| ChromaDB | Vector database | 5 |
| LlamaIndex | RAG orchestration | 5 |
| Microsoft Presidio | PII tokenization | 5 |
| Whisper (via Ollama) | Local audio transcription | 5 |
| n8n or Apps Script | Email intake automation | 4 |
| Reor (watchlist) | Possible Obsidian + RAG replacement | 5 |

---

## 13. LAPTOP BACKUP

**Full plan in separate document:** `Laptop-Backup-Plan.md` (same folder as this file).

**Summary:**

- **Layer 1:** Full system image via Veeam Agent Free → 1TB SSD (weekly)
- **Layer 2:** Continuous file backup via Windows File History → 1TB SSD (hourly when connected)
- **Layer 3:** Git push orchestrator code to GitHub (weekly)
- **Layer 4:** Gold vault encrypted ciphertext syncs to Google Drive automatically

**3-2-1 rule coverage:**

| Copy | Location |
|------|----------|
| 1 | Laptop C: drive |
| 2 | 1TB external SSD |
| 3 | Google Drive (Gold) + GitHub (code) |

**Mini computer mirror:** A separate mini computer (arriving in weeks) will be an air-gapped backup. Updated periodically via USB/direct transfer. Stored in a secure location (vault or safe). Not a daily-use machine — a recovery-of-last-resort machine.

---

## 14. WHAT IS ALREADY BUILT

All core orchestrator behaviors are built, tested, and committed to git at `github.com/mhaefele2312/estate-orchestrator`:

| Behavior | File | What It Does | Status |
|----------|------|-------------|--------|
| Gate | gate.py | Scans Obsidian Inbox, prompts for provenance frontmatter, moves to Accepted/ | Tested live |
| Publish | publish.py | Scans Accepted/, PII scan, sanitizes, copies to Published/ | Tested live — **deferred (see note)** |
| Health Check | health_check.py | Checks vault structure, stale items, conflicts, Gold boundary, log currency | Tested live |
| Backup Check | backup_check.py | Checks Gold-Backup on Google Drive, reports file count and last modified | Tested live |
| Inbox Pickup | inbox_pickup.py | Moves .md/.txt from Google Drive inboxes to Obsidian Inbox | Tested (test mode) |
| Capture App | Code.gs + Index.html | Google Apps Script voice capture, saves to Google Drive | Built, not deployed |
| Test Runner | run_tests.py | Runs all behaviors in test mode | All passing |

**Note on Publish behavior:** Publish is premature and deferred to Phase 7+. It assumes Obsidian content is ready to go public, but: the vault still needs security hardening, the tokenization layer isn't built, and publishing logic (what gets published, where, to whom) hasn't been defined. The behavior exists in the codebase but should not be used or developed further until the foundational layers are stable.

**Known bug:** Gate silently defaults to MHH on invalid visibility input instead of re-prompting. Fix in Phase 1.

---

## 15. 12 DOMAINS

Used across all three layers for consistent categorization:

| # | Domain | Examples |
|---|--------|----------|
| 01 | Financial | Bank accounts, investments, budgets |
| 02 | Legal | Contracts, agreements, legal correspondence |
| 03 | Property | Real estate, home systems, maintenance, room-by-room docs |
| 04 | Insurance | Policies, claims, coverage |
| 05 | Medical | Health records, prescriptions, appointments |
| 06 | Tax | Returns, receipts, filings |
| 07 | Estate-Planning | Wills, trusts, succession plans |
| 08 | Vehicles | Registration, maintenance, insurance |
| 09 | Digital | Accounts, passwords, subscriptions |
| 10 | Family | Personal notes, traditions, family history |
| 11 | Contacts | People, professionals, relationships |
| 12 | Operations | Estate OS system docs, configs, build logs, API credentials (Gold) |

---

## 16. PHASED BUILD PLAN

### Phase 0 — Laptop Backup (Day 1 — when SSD arrives)

**Estimated time:** 90 minutes

- Format 1TB SSD (NTFS)
- Install Veeam Agent for Windows Free
- Run first full system image
- Enable Windows File History
- Create Veeam Recovery Media USB
- Set up weekly git snapshot for Obsidian vault (local repo)

**Deliverable:** Laptop fully backed up with automated weekly schedule.

### Phase 1 — Core Ops Ledger (Week 1-2)

**Estimated time:** 8-12 hours of build time

1. **Create MHH-Ops-Ledger Google Sheet** with schema from section 3.1. Add all 7 tabs with FILTER formulas.
2. **Install gspread** on estate laptop. Set up Google Sheets API credentials (OAuth).
3. **Build Stage 2-3 pipeline** (Python on laptop):
   - Script reads new .md captures from Google Drive sync folder
   - Calls Gemini API with processing prompt
   - Parses JSON response
   - Appends ALL rows via gspread (no sensitive routing — business communication rules)
   - Writes simultaneously to flat log files and contacts CSV
   - Moves raw transcript to Capture-Archive/ after successful processing
4. **Draft Gemini Processing Gem** prompt (for capture parsing)
5. **Draft Gemini Query Gem** prompt (for conversational queries)
6. **Update capture app** (Code.gs + Index.html):
   - Time-based mode detection
   - Text prompts (not audio)
   - Voice recording throughout
   - Save raw transcript to MHH-Inbox in Google Drive
7. **Deploy capture app** to Google Apps Script, get URL, add to Android home screen
8. **Install Obsidian Web Clipper** and Microsoft Lens
9. **Fix gate.py** visibility input bug
10. **Create property template** in Obsidian (03_Property/_property-template/)
11. **Create Property-Index.md** with links to all 7+ property folders
12. **Test end-to-end:** Voice capture → transcript → Gemini parse → sheet append → query

**Deliverable:** Working voice-to-structured-data pipeline. One button on phone, data in sheet, queryable by Gemini.

### Phase 1b — Pipeline Migration (Week 3-4, after Phase 1 is stable)

**Estimated time:** 4-6 hours

- Move Stages 2-3 into Google Apps Script
- Store Gemini API key in Apps Script project properties
- Phone handles everything automatically — no laptop needed
- Laptop pipeline remains as fallback
- Test on both Android (MHH) and iOS (HBS device compatibility check)

**Deliverable:** Fully phone-based capture pipeline.

### Phase 2 — HBS Capture (Week 4-6)

**Estimated time:** 2-3 hours

- Same capture app, different URL parameter (`?user=HBS`)
- Create HBS-Ops-Ledger Google Sheet (same schema)
- Share MHH sheet with HBS (read access) and vice versa
- HBS gets her own home screen button
- Test on iOS (Safari/Chrome — Web Speech API compatibility)

**Deliverable:** Both family members capturing independently with mutual visibility.

### Phase 3 — Staging Intake (Months 2-3)

**Estimated time:** 6-10 hours

- Build file-type sorting script (Python — sorts by extension)
- Set up staging folder in Google Drive: `G:\My Drive\Staging-Intake\`
- Build security scan step (Windows Defender CLI or ClamAV)
- Manual classification workflow (human sorts with LLM assistance later)
- Process first old external drive
- Route estate documents to Gold/Obsidian
- Route photos to appropriate archive

**Deliverable:** Repeatable process for ingesting legacy drives.

### Phase 4 — Email Intake + Weekly Review Automation (Months 3-4)

**Estimated time:** 4-6 hours

- Set up Gmail filters to auto-label estate-related emails
- Build Apps Script time-based trigger to watch labeled emails (or defer to n8n when mini PC arrives)
- Stage attachments for routing during weekly review
- Build Claude behavior for weekly vault review:
  - Reads Ops Ledger for past week
  - Identifies vault-bound items
  - Produces formatted .md drafts
  - Human reviews and approves

**Deliverable:** Semi-automated email intake and weekly review workflow.

### Phase 5 — Local LLM + RAG (Months 4-8)

**Estimated time:** 20-40 hours (significant project)

- Purchase and set up always-on mini PC
- Install Ollama + local model
- Install Whisper for audio transcription
- Install Microsoft Presidio for PII tokenization
- Process vault data through tokenization pipeline
- Install ChromaDB + LlamaIndex (or evaluate Reor as alternative)
- Build RAG query interface
- Test queries against tokenized estate data
- Integrate micro recorder upload workflow (audio → Whisper → Obsidian Inbox)

**Deliverable:** Queryable estate knowledge base with PII protection.

### Phase 6 — Claude Code Machine + Estate Operating Manual (Months 6-10)

**Estimated time:** 10-20 hours

- Set up dedicated Mac mini for Claude Code (separate email, Signal)
- Clone estate-orchestrator repo
- Build annual operating manual generation:
  - Claude reads full year of Ops Ledger
  - Identifies recurring tasks, decisions, patterns
  - Produces draft chapters for estate operating manual
  - Human reviews and promotes to Obsidian vault
- Begin documenting all 7+ properties systematically (explanation notes workflow)
- Begin documenting intention, purpose, values, personality of MHH and spouse

**Deliverable:** First draft of estate operating manual. All properties documented.

### Phase 7 — Executor Package + Digital Legacy (Months 8-12)

**Estimated time:** 8-12 hours

- Research best practices for digital estate planning
- Design executor package contents (see section 10)
- Build the break-glass document
- Encrypt on passcode-protected USB drive
- Create safe deposit box copy
- Get spouse to do their version
- Get father to do his version
- Design and implement staged family access (children 15-18 → young adults)
- Begin "guru circle" — teaching children the system

**Deliverable:** Complete executor package. Family access tiers implemented.

### Phase 8 — Publish + Sharing (Months 12+)

- Revisit publish behavior with clear requirements
- Define what gets published, where, to whom
- Build tokenization-based sharing (safe extracts of vault data)
- n8n on mini PC for advanced automation (if not done in Phase 4)

### Future / Watchlist

- Synology NAS for overflow storage (large legacy archives)
- Reor as Obsidian + RAG replacement
- Android native app for capture (if Apps Script web app proves unreliable)
- Obsidian Sync for multi-device vault access (evaluate security implications)

---

## 17. DOCUMENT FLOW SUMMARY

How information moves through the entire system. There are two completely separate flows:

### Flow A: Voice Captures (phone → Ops Ledger)

```
[Phone voice capture — business communication rules, no sensitive data]
        |
        v
[Raw transcript .md saved to Google Drive]
        |
        v
[Capture pipeline: Gemini parses → JSON → gspread appends to sheet]
        |
        v
[Ops Ledger Google Sheet — ALL rows appended, no routing]
        |
        v
[Raw transcript archived to Capture-Archive/ in Google Drive]
        |
        v
[Weekly: script exports sheets to Obsidian Ops-Ledger/ folder]
        (one-way sync, no categorization)
```

This flow is fully automated. No human review needed. No gate. No categorization.

### Flow B: Everything Else (manual → vaults)

```
SCANS (Microsoft Lens → Google Drive)
WEB CLIPS (Obsidian Web Clipper → Obsidian Inbox)
EMAILS (manual save or future email-tag automation)
DOCUMENTS (manual download/save)
        |
        v
+-- Is it sensitive/original? --+
|  YES                           |  NO
|  v                             |  v
|  Gold Vault (E:\)              |  Obsidian Inbox
|  Filed under matching          |        |
|  domain folder manually        |        v
|                                |  gate.py (human reviews,
|                                |  adds provenance frontmatter)
|                                |        |
|                                |  +-----+-----+
|                                |  |           |
|                                |  Approved  Rejected
|                                |  |           |
|                                |  v           v
|                                |  Accepted/  _archive/
|                                |  |
|                                |  v
|                                |  Human files to correct
|                                |  domain folder in vault
+--------------------------------+
```

This flow is manual. The user decides where things go. Gate.py adds provenance metadata to items entering Obsidian through the Inbox. Gold vault items are filed directly — no gate needed.

### Key Simplification

Voice captures NEVER route to Obsidian domain folders or Gold vault. They go to the Ops Ledger only, and a weekly snapshot lands in Obsidian's Ops-Ledger/ folder for archival. All vault filing (Obsidian domain folders and Gold) is manual and deliberate.

---

## 18. PHYSICAL INFRASTRUCTURE

| Component | Location | Status |
|-----------|----------|--------|
| Obsidian vault | `C:\Users\mhhro\Documents\Obsidian Vault\` | Live — 17 folders |
| Gold vault | `E:\` (Cryptomator) | Live — 11 folders |
| Gold backup | `G:\My Drive\Gold-Backup\` | Live — syncing |
| Estate Ops folder | `G:\My Drive\Estate Ops\` | To be created (Phase 1) |
| MHH-Inbox | `G:\My Drive\MHH-Inbox\` | To be created |
| HBS-Inbox | `G:\My Drive\HBS-Inbox\` | Created, not yet used |
| Staging-Intake | `G:\My Drive\Staging-Intake\` | To be created (Phase 3) |
| Capture-Archive | `G:\My Drive\Capture-Archive\` | To be created (Phase 1) — processed transcripts preserved here |
| Git repo | `github.com/mhaefele2312/estate-orchestrator` | Live — pushed |
| Laptop backup | 1TB SSD (arriving) | Phase 0 |

---

## 19. OPEN QUESTIONS

These are design decisions not yet resolved:

1. **iOS Web Speech API compatibility** — Does the capture web app work reliably on iOS Safari/Chrome for HBS? Needs testing in Phase 2.

2. **Mini PC → vault data access** — How the always-on LLM server accesses vault data from the estate laptop. Syncthing is the leading option. Decision deferred until hardware purchase.

3. **Executor package encryption** — VeraCrypt vs. hardware-encrypted USB for the break-glass document. Research needed.

4. **Reor vs. custom RAG** — Whether Reor is mature enough to replace the Ollama + ChromaDB + LlamaIndex stack. Evaluate in Phase 5.

5. **Capture app API key security** — When migrating to Apps Script (Phase 1b), the Gemini API key lives in Apps Script project properties. This is Google-to-Google and relatively safe, but it's a credential in the cloud. Acceptable tradeoff for phone-based automation.

6. **Quarterly archiving strategy** — Exact process for moving completed/deferred rows to an Archive tab in the Ops Ledger. Design when the sheet approaches 1,000+ rows.

7. **n8n vs. Apps Script for email** — If no mini PC for n8n hosting, Apps Script with time-based triggers can watch Gmail labels. Simpler, no extra hosting, but less powerful than n8n. Decision depends on whether the mini PC arrives before Phase 4.

---

## 20. CONTEXT ON THE BUILDER

MHH describes himself as a zero-knowledge user. He understands the concepts clearly but needs explicit, step-by-step instructions for any terminal or code work. Cursor tickets (instructions pasted into Cursor Agent) and Cowork are his primary build tools. Claude Code CLI is installed on a separate dev computer only — not on the estate machine where sensitive data lives.

The estate machine runs Windows 11. The dev computer is being set up separately.

MHH has intentionally disconnected most web connections on the estate laptop for security. The laptop is primarily an offline estate management machine with Google Drive sync for backup.

---

## 21. KEY DECISIONS ALREADY MADE (Not Up for Revision)

- Gold vault never in Obsidian Sync or any unencrypted cloud
- LLMs never read or write Gold
- Cryptomator on estate laptop only
- Obsidian vault is local (not in Google Drive)
- Git as the safety net for all orchestrator code
- Fail-closed: every behavior defaults to dry-run
- Gemini for daily operations, Claude for building/maintaining
- Append-only Ops Ledger (gspread, not custom sheet-writing code)
- Three-stage pipeline (transcript → JSON → append) with LLM isolated to Stage 2

---

## 22. SESSION HISTORY

This plan was developed over multiple extended Claude Cowork sessions. The original build design document (Estate-OS-Build-Design.docx) is in the same folder and contains the initial architectural rationale, boundary model, and risk register.

This v2 document supersedes the original Estate-OS-Master-Plan.md and incorporates all design decisions from the extended discussion including: routing decision framework, staging intake area, home operating manual, executor package, laptop backup plan, local LLM/RAG stack, hardware planning, health tracking, inflow types, and off-the-shelf tools catalog.

---

## APPENDIX A: MACHINE-READABLE BUILD SPECIFICATION

This section is designed for Claude Code or any automated build system to parse and execute.

```yaml
project:
  name: estate-orchestrator
  repo: github.com/mhaefele2312/estate-orchestrator
  language: python
  runtime: python3
  secondary: google-apps-script

paths:
  obsidian_vault: "C:\\Users\\mhhro\\Documents\\Obsidian Vault"
  gold_vault: "E:\\"
  gold_backup: "G:\\My Drive\\Gold-Backup"
  estate_ops: "G:\\My Drive\\Estate Ops"
  mhh_inbox: "G:\\My Drive\\MHH-Inbox"
  hbs_inbox: "G:\\My Drive\\HBS-Inbox"
  staging_intake: "G:\\My Drive\\Staging-Intake"
  orchestrator_root: "[dev-machine-path]/estate-orchestrator"

google_sheets:
  sheets:
    - name: "MHH-Ops-Ledger"
      owner: MHH
      phase: 1
    - name: "HBS-Ops-Ledger"
      owner: HBS
      phase: 2
    - name: "LEH-Ops-Ledger"
      owner: LEH
      phase: later
    - name: "HAH-Ops-Ledger"
      owner: HAH
      phase: later
    - name: "Family-Ops-Ledger"
      owner: combined
      phase: 2
      notes: "Created as soon as HBS is added. Aggregates open items from all individual sheets."
  sheet_template:
    location: "G:\\My Drive\\Estate Ops\\"
    tabs:
      - name: "Raw Log"
        type: append_only
        columns: [entry_date, entry_time, capture_mode, item_type, domain,
                  description, responsible, due_date, status, notes,
                  source_capture, captured_by,
                  given_name, family_name, organization, title, phone, email]
      - name: "Open Todos"
        type: filter_view
        formula: "=FILTER(RawLog, item_type='todo', status='open')"
      - name: "This Week"
        type: filter_view
        formula: "=FILTER(RawLog, due_date within 7 days)"
      - name: "Contacts"
        type: filter_view
        formula: "=FILTER(RawLog, item_type='contact')"
      - name: "Calendar"
        type: filter_view
        formula: "=FILTER(RawLog, item_type='calendar')"
      - name: "Action Log"
        type: filter_view
        formula: "=FILTER(RawLog, item_type='action_log')"
      - name: "Health Log"
        type: filter_view
        formula: "=FILTER(RawLog, item_type='health_log')"
    user_editable: true
    notes: "MHH can manually edit sheets at any time in Google Drive"

behaviors:
  existing:
    - name: gate
      file: behaviors/gate/gate.py
      config: behaviors/gate/config.json
      status: tested_live
      known_bugs:
        - "Silently defaults to MHH on invalid visibility input"
    - name: publish
      file: behaviors/publish/publish.py
      config: behaviors/publish/config.json
      status: deferred_phase_7
    - name: health_check
      file: behaviors/health-check/health_check.py
      config: behaviors/health-check/config.json
      status: tested_live
    - name: backup_check
      file: behaviors/backup-check/backup_check.py
      config: behaviors/backup-check/config.json
      status: tested_live
    - name: inbox_pickup
      file: behaviors/inbox-pickup/inbox_pickup.py
      config: behaviors/inbox-pickup/config.json
      status: tested_test_mode
    - name: capture_app
      files:
        - behaviors/capture/Code.gs
        - behaviors/capture/Index.html
        - behaviors/capture/DEPLOY.md
      status: built_not_deployed
      needs_update: true
      update_notes: "Rebuild for text prompts, time-based mode, direct pipeline"

  to_build:
    - name: capture_pipeline
      description: "Stage 2-3 processor: reads .md transcripts, calls Gemini, appends to Google Sheet AND flat log files AND contacts CSV simultaneously (no sensitive screening)"
      phase: 1
      language: python
      dependencies: [gspread, google-auth, google-generativeai]
      writes_to:
        - google_sheet: "via gspread append_row"
        - flat_files: "append-only log files (master-log.md, topic files by GTD category)"
        - contacts_csv: "google-contacts-import.csv (when item_type=contact)"
        - mentions_log: "contact-mentions.md (person name + context from any capture)"
    - name: snapshot_script
      description: "Source-of-truth promotion: exports edited sheets to Gold vault + Obsidian + SOT folder"
      phase: 1
      language: python
      trigger: "manual (python snapshot.py --confirm) or Google Sheet custom menu button"
      writes_to:
        - sot_folder: "G:\\My Drive\\Estate Ops\\Source-of-Truth\\"
        - gold_vault: "E:\\12_Operations\\Source-of-Truth\\"
        - obsidian: "Obsidian Vault\\Ops-Ledger\\Source-of-Truth\\"
    - name: weekly_sync
      description: "Weekly one-way push: log files + latest SOT + contact pages to Obsidian"
      phase: 1
      language: python
      dependencies: [gspread, google-auth]
      creates:
        - "Obsidian Ops-Ledger/ copies of all flat files"
        - "Obsidian 11_Contacts/ individual pages per person (auto-created from contacts.md + contact-mentions.md)"
      contact_page_merge:
        strategy: "marker comment <!-- mentions-start -->"
        above_marker: "manual — Contact Info + Relationship sections, never overwritten"
        below_marker: "auto-replaced — Mentions section rebuilt from contact-mentions.md each week"
        new_contacts: "created from template with blank Relationship fields"
    - name: reconciliation_script
      description: "Reads sheet status changes (items marked done), appends completion entries to flat log files"
      phase: 1
      language: python
      trigger: "weekly, before snapshot"
    - name: weekly_review
      description: "Reads SOT snapshots, produces human-readable summaries (todo lists, project trackers)"
      phase: 4
      language: python
    - name: staging_sorter
      description: "Sorts files from old drives by type for classification"
      phase: 3
      language: python

  flat_file_architecture:
    type_1_append_only_logs:
      location: "G:\\My Drive\\Estate Ops\\Logs\\"
      files:
        - master-log.md
        - next-actions.md
        - projects.md
        - waiting-for.md
        - calendar.md
        - someday-maybe.md
        - reference-notes.md
        - completed.md
        - health.md
        - contacts.md
        - contact-mentions.md
        - google-contacts-import.csv
      write_access: "Python only (capture_pipeline + reconciliation_script)"
      llm_access: "read only — Gemini can read but has no write API for flat files"
    type_2_source_of_truth:
      location: "G:\\My Drive\\Estate Ops\\Source-of-Truth\\"
      files:
        - "sot-[MEMBER]-[DATE].csv (timestamped snapshots)"
        - "sot-latest-[MEMBER].csv (pointer to most recent)"
      write_access: "snapshot_script only (triggered manually by user)"
      llm_access: "read only — this is what Gemini uses for daily queries"
      copies_to:
        - "E:\\12_Operations\\Source-of-Truth\\ (Gold vault, encrypted)"
        - "Obsidian Vault\\Ops-Ledger\\Source-of-Truth\\ (offline backup)"

  contacts_workflow:
    trigger: "user says 'new contact' in voice capture"
    json_shape: "flat — contact fields (given_name, family_name, organization, title, phone, email) are top-level on every item, blank for non-contacts"
    python_writes_to:
      - "contacts.md (append-only log)"
      - "Google Sheet Raw Log tab (same flat row as all other items)"
      - "google-contacts-import.csv (Google Contacts CSV format for manual import)"
    mention_tracking:
      trigger: "any person name detected in any voice capture"
      writes_to: "contact-mentions.md (date, name, capture_mode, context)"
    obsidian_pages:
      location: "11_Contacts/[Person-Name].md"
      created_by: "weekly_sync script"
      template: "Contact Info + Relationship (manual, above marker) + Mentions (auto-populated, below <!-- mentions-start --> marker)"
      merge_strategy: "replace everything below marker, preserve everything above"
      gemini_query: "Gemini reads contact-mentions.md to answer 'what do I know about [person]?'"

obsidian_vault_structure:
  folders:
    - Inbox
    - Accepted
    - Published
    - Ops-Ledger
    - 01_Financial
    - 02_Legal
    - 03_Property
    - 04_Insurance
    - 05_Medical
    - 06_Tax
    - 07_Estate-Planning
    - 08_Vehicles
    - 09_Digital
    - 10_Family
    - 11_Contacts
    - 12_Operations
    - _prompts
    - _archive
    - _views
  property_template:
    path: "03_Property/_property-template"
    files:
      - overview.md
      - systems/hvac.md
      - systems/plumbing.md
      - systems/electrical.md
      - systems/security.md
      - systems/internet.md
      - systems/irrigation.md
      - contacts/contractors.md
      - contacts/neighbors.md
      - maintenance-log.md
      - seasonal-checklist.md
      - documents/README.md

domains:
  - {id: "01", name: "Financial"}
  - {id: "02", name: "Legal"}
  - {id: "03", name: "Property"}
  - {id: "04", name: "Insurance"}
  - {id: "05", name: "Medical"}
  - {id: "06", name: "Tax"}
  - {id: "07", name: "Estate-Planning"}
  - {id: "08", name: "Vehicles"}
  - {id: "09", name: "Digital"}
  - {id: "10", name: "Family"}
  - {id: "11", name: "Contacts"}
  - {id: "12", name: "Operations"}

capture_modes:
  morning_sweep:
    trigger: "before 11am"
    questions: 9
    includes_health_checkin: true
  quick_note:
    trigger: "11am-5pm"
    questions: 5
  evening_sweep:
    trigger: "after 5pm"
    questions: 6
    includes_health_checkin: true

family_members:
  - {id: MHH, phase: 1}
  - {id: HBS, phase: 2}
  - {id: LEH, phase: later}
  - {id: HAH, phase: later}

ops_to_obsidian_sync:
  direction: one_way
  frequency: weekly
  destination: "Obsidian Vault\\Ops-Ledger\\"
  format: csv
  categorization: none
  notes: "Sheets exported as-is to Ops-Ledger folder. No categorization into domain folders."

pipeline:
  stage_1:
    name: transcript
    llm: false
    input: voice_recording
    output: timestamped_md_file
    location: google_drive_inbox
  stage_2:
    name: parsing
    llm: gemini
    input: raw_transcript_md
    output: json_array
    isolation: "Gemini sees ONLY transcript, never the sheet"
    sensitive_screening: "none — human discipline only, no software checks"
    notes: "Business communication rules — voice captures contain no sensitive data by design"
  stage_3:
    name: appending
    llm: false
    input: json_array
    output: sheet_rows
    library: gspread
    method: append_row
    routing: "ALL rows go to Ops Ledger sheet — no bifurcation"
    post_processing: "move raw transcript to G:\\My Drive\\Capture-Archive\\ after successful append"

phase_1_build_order:
  1: "Create MHH-Ops-Ledger Google Sheet with schema and tabs (Raw Log, Open Todos, This Week, Contacts, Calendar, Projects, Health Log)"
  2: "Install gspread + set up Google Sheets API OAuth credentials"
  3: "Build capture_pipeline.py — writes to sheet + flat log files + contacts CSV simultaneously"
  4: "Build snapshot.py — source-of-truth promotion to Gold vault + Obsidian + SOT folder"
  5: "Build weekly_sync.py — push logs + SOT + contact pages to Obsidian"
  6: "Build reconciliation.py — reads sheet status changes, appends completions to flat files"
  7: "Create Logs/ and Source-of-Truth/ folders in G:\\My Drive\\Estate Ops\\"
  8: "Create Ops-Ledger/ and 12_Operations/ folders in Obsidian + Gold vault"
  9: "Draft Gemini Processing Gem prompt (business communication rules, GTD categories, contact extraction)"
  10: "Draft Gemini Query Gem prompt (reads SOT snapshots for daily answers)"
  11: "Update capture app (Code.gs + Index.html) for new design"
  12: "Deploy capture app + Android home screen shortcut"
  13: "Add snapshot button to Google Sheet (Apps Script custom menu)"
  14: "Install Obsidian Web Clipper + Microsoft Lens"
  15: "Fix gate.py visibility input bug"
  16: "Create property template + Property-Index.md + contact template"
  17: "End-to-end test: voice → parse → sheet + logs → edit sheet → snapshot → query SOT → weekly sync to Obsidian"
```

---

## APPENDIX B: CUSTOM SOFTWARE AUDIT

This section identifies every piece of custom code in the system and evaluates whether it could be replaced with an off-the-shelf tool. See discussion notes following this table.

| Custom Code | What It Does | Could Replace With | Tradeoff |
|-------------|-------------|-------------------|----------|
| **gate.py** | Scans Inbox, prompts for provenance frontmatter, moves to Accepted/ | Obsidian Templates plugin + manual filing | Loses automated provenance check and consistent frontmatter. Manual is slower but zero code. |
| **publish.py** | PII scan, sanitizes, copies to Published/ | **Already deferred.** No replacement needed until Phase 7+. | N/A |
| **health_check.py** | Checks vault structure, stale items, boundary violations | Manual checklist (printed or in Obsidian) | Loses automated detection of problems. Manual works but requires discipline. |
| **backup_check.py** | Checks Gold-Backup status on Google Drive | Manual: open Google Drive, look at Gold-Backup folder | Loses automated reporting. Manual takes 30 seconds. |
| **inbox_pickup.py** | Moves files from Google Drive inboxes to Obsidian Inbox | Robocopy/xcopy scheduled task, or manual drag-and-drop | Robocopy is off-the-shelf (built into Windows). Could replace custom Python. Loses frontmatter prepending for .txt files. |
| **capture_pipeline.py** (to build) | Reads transcripts, calls Gemini, appends via gspread | No off-the-shelf alternative. This is the core custom code. | **Cannot be removed.** This is the drift-proof pipeline. |
| **capture app (Apps Script)** | Voice capture web app on phone | Todoist Ramble, Google Keep voice notes, or standard note app | Loses structured prompts, time-based modes, and direct pipeline integration. Off-the-shelf alternatives don't support the three-layer architecture. |
| **staging_sorter.py** (to build) | Sorts legacy files by type | Manual sorting into folders, or a file manager with sort-by-type | Manual works for one-time use. Script is faster for large drives. |
| **weekly_review.py** (to build) | Reads Ops Ledger, identifies vault-bound items, produces .md drafts | Manual: read the sheet, write notes by hand | Loses automation but the process is clear enough to do manually. |
| **vault_git_snapshot** (to build) | Weekly git commit of vault contents | Windows File History (already in backup plan) | File History provides version recovery. Git adds commit messages and explicit snapshots. Git is marginally better but File History may be sufficient. |

### Audit Summary

**Cannot remove (core to architecture):**
- capture_pipeline.py — the drift-proof pipeline IS the system
- capture app (Apps Script) — the phone button IS the user interface

**Could remove with minimal loss:**
- backup_check.py → manual 30-second check
- vault_git_snapshot → File History already covers this
- staging_sorter.py → manual sorting (especially for one-time use)

**Could remove but loses real value:**
- gate.py → provenance frontmatter is valuable for institutional memory
- health_check.py → automated problem detection catches things humans miss
- inbox_pickup.py → robocopy could replace the file-moving, but loses frontmatter handling

**Already removed:**
- publish.py → deferred to Phase 7+

### Recommendation

Keep gate.py, health_check.py, and inbox_pickup.py. They're small, tested, and provide real value. The provenance check in gate.py is particularly important — it ensures every document entering the vault has metadata about where it came from and who reviewed it. This is the kind of institutional discipline that compounds over years.

Consider replacing vault_git_snapshot with just File History (already set up in backup plan). If you later want explicit version history with commit messages, git is easy to add back.

For staging_sorter.py: build a minimal version for Phase 3 since you'll be processing multiple old drives. If you only had one drive, manual would be fine. Multiple drives justify the automation.
