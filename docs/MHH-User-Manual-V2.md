# Estate OS — MHH User Manual: Volume 2

**Last updated:** April 1, 2026
**Covers:** Everything built after the Gold Vault went live on the estate laptop
**Volume 1:** Covers the capture app, Gold vault setup, and daily ops pipeline (already live)

---

## Before You Read This

This manual assumes Volume 1 is already working on the estate laptop:

- The Capture App is deployed and all 6 family members can use it
- The pipeline processes voice memos and writes rows to the Ops Ledger Google Sheet
- The Gold vault (E:\ on the estate laptop) exists and is organized
- You use Gemini daily to query and manage the estate

Volume 2 covers everything built *after* that — the Silver vault system, the estate interview app, and the path toward local AI that can read your private documents without sending anything to the cloud.

---

## Part 1: What the System Is and Why It Exists

### The Problem It Solves

Most families don't have a system. When something happens — a medical emergency, a death, a legal dispute, a natural disaster — nobody knows where anything is. Passwords are lost. Insurance policies are buried in email. Property deeds are in a box somewhere. The person who knew where everything was is gone.

Estate OS is the answer. It's a personal and family operating system that:

1. **Captures daily activity** — what happened, what needs to happen, who you talked to, what matters
2. **Preserves institutional memory** — documents, decisions, history, relationships
3. **Survives any person** — built so that any family member (or their professional advisor) can pick up and understand the full picture
4. **Respects privacy** — the most sensitive information never leaves your control and never touches the cloud

### The Three Layers

Think of it as three concentric rings of information:

**Ring 1: The Ops Ledger (visible to AI)**
Your Google Sheet. Daily capture items, todos, notes, contacts, calendar events. Cloud AI (Gemini) can read and help you with this. Nothing sensitive goes here — you speak and write accordingly.

**Ring 2: The Obsidian Vault (your working memory)**
A local folder on the estate laptop. Markdown files organized into 12 domains. The weekly sync script pushes logs and notes here. No cloud AI ever touches this. Your working knowledge base.

**Ring 3: The Gold Vault (dark, encrypted)**
Cryptomator-encrypted drive on the estate laptop (E:\). Every important document — deeds, policies, wills, financial statements. Organized into the same 12 domains. No AI ever touches this. MHH files documents here personally.

### The 12 Domains

Every piece of information belongs to one of these:

| # | Domain | What Goes Here |
|---|--------|----------------|
| 01 | Financial | Bank accounts, investments, statements |
| 02 | Legal | Contracts, agreements, corporate records |
| 03 | Property | Real estate deeds, surveys, HOA docs |
| 04 | Insurance | Policies, claims, coverage summaries |
| 05 | Medical | Health records, medications, providers |
| 06 | Tax | Returns, correspondence, receipts |
| 07 | Estate Planning | Will, trust, POA, beneficiary forms |
| 08 | Vehicles | Titles, registration, maintenance |
| 09 | Digital | Account lists, passwords (reference only), subscriptions |
| 10 | Family | Vital records, school, family history |
| 11 | Contacts | People, relationships, professional advisors |
| 12 | Operations | Maintenance, household, recurring tasks |

---

## Part 2: The Document Flow

Here is how information moves through the system from the moment you speak into your phone to the moment it's accessible for years to come.

```
You speak into your phone
        ↓
Capture App (Google Apps Script)
 — Saves a .md transcript to your Google Drive inbox
        ↓
Laptop Pipeline (capture_pipeline.py)
 — Reads the transcript
 — Sends it to Gemini for parsing
 — Gemini returns structured data (not the raw text)
        ↓
Four simultaneous writes:
  ├── Google Sheet (the Ops Ledger) — one row per item
  ├── Flat log files — master-log.md, todos, contacts, etc.
  ├── contacts-import.csv — ready for Google Contacts
  └── contact-mentions.md — every name detected
        ↓
Weekly Sync (weekly_sync.py)
 — Pushes logs to Obsidian vault
 — Updates contact pages with new mentions
        ↓
Snapshot (snapshot.py)
 — Exports edited sheet to CSV
 — Saves to Source-of-Truth folder and Gold vault
        ↓
Gold Vault (E:\)
 — Permanent, encrypted, human-curated record
 — Survives any laptop, any cloud service going down
```

### What Gemini Sees and Doesn't See

Gemini (the cloud AI) sees:
- Your voice transcripts (so speak accordingly — no account numbers, no SSNs)
- The Ops Ledger sheet (when you query it through Gemini Gems)
- SOT snapshot CSVs (structured, non-sensitive summaries)

Gemini never sees:
- The Obsidian vault
- The Gold vault
- The Silver vault
- Any document in any vault folder

This is by design and enforced in the code. There is no way to accidentally share vault contents with Gemini.

---

## Part 3: The Silver Vault System

The Silver vault (Y:\ on the estate laptop) is the machine-curated archive for **legacy documents** — the pile of old files that existed before this system was built.

### What Silver Is For

Think of Silver as the staging ground for history:
- Old scanned documents
- PDFs from past years
- Legacy files from old computers
- Anything you're not sure where to put yet

The machine (a local script) reads each document, scores it against the 12 domains, and files it automatically. You review the machine's work before anything is finalized.

Gold vault is going-forward — you file things there yourself as they happen.
Silver vault is the past — the machine helps you sort through it.

### Running the Silver Intake

When you have a folder of legacy documents to process:

1. **Open a terminal on the estate laptop**
2. **Navigate to the repo:** `cd C:\Users\mhhro\estate-orchestrator`
3. **Run a dry-run first:**
   ```
   python behaviors/silver-classifier/silver_classifier.py --source "path\to\documents" --vault Y:\
   ```
   This shows what it would do without actually moving anything.
4. **Run live when satisfied:**
   ```
   python behaviors/silver-classifier/silver_classifier.py --source "path\to\documents" --vault Y:\ --confirm
   ```

### What You See During Intake

For each document, the script shows:
- The filename
- Its confidence score (how sure it is about the domain)
- The suggested domain folder

You choose:
- **Enter** — accept the suggestion and file it
- **1-12** — override with a specific domain number
- **r** — rename the file first, then file it
- **s** — skip this file (process it later)
- **d** — mark for delete review (doesn't delete — flags it)
- **q** — quit and save progress

### Reviewing Machine Classifications

After intake, use the Silver Review script to audit what was filed:

```
python behaviors/silver-review/silver_review.py --vault Y:\
```

For each file, you can:
- **Enter** or **a** — accept as-is
- **r** — rename the file
- **m** — move to a different domain folder
- **g** — promote to Gold vault (copies to E:\, removes from Silver)
- **s** — skip
- **q** — quit

**Promoting to Gold** is the key action. When a legacy document is important enough to be part of the permanent record, promote it. It moves from the machine-curated Silver vault to the human-curated Gold vault.

### The Provenance Log

Every Silver vault action is logged to `Silver\_provenance\`. This is a permanent record of:
- What the machine classified and why
- What you accepted or overrode
- What was promoted to Gold and when

This log exists so that years from now, if you wonder "how did this file end up here?", you can find out.

---

## Part 4: Tokenization — Making Documents Safe for AI

This part is about the future, but you should understand what it does.

The Tokenizer (`vault_tokenizer.py`) scans vault documents and replaces sensitive values with stable placeholder tokens:

- `123-45-6789` (a Social Security Number) becomes `[SSN_0001]`
- `Account 987654321` becomes `[ACCT_0001]`
- `Jane Smith` (a name) becomes `[PERSON_0001]`

The original documents are never changed. The script creates **sanitized copies** in a Token Store folder. A registry file maps every token back to the real value — but the registry stays locked, never accessible to any AI.

**Why this matters:** When the local AI (Ollama, Phase 5) comes online, it will read from the Token Store — not the actual vaults. It can answer questions like "do I have flood insurance on the Mule property?" without ever seeing your actual policy numbers, names, or SSNs.

### Running the Tokenizer

```
python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold --confirm
python behaviors/vault-tokenizer/vault_tokenizer.py --vault silver --confirm
```

Always run without `--confirm` first to see what it would do. The tokenizer is smart enough to re-run safely — it only re-processes files that have changed since the last run (SHA-256 file tracking).

---

## Part 5: The Estate Interview App

The Estate Interview app is a desktop application that helps you build your estate plan through guided conversation.

### What It Is

A Windows app that walks you through everything that belongs in a complete estate plan:
- Personal information and family tree
- Real estate and property inventory
- Financial accounts and investments
- Insurance policies
- Legal documents (will, trust, POA, healthcare directives)
- Business interests
- Digital assets
- Final wishes and family instructions

You answer questions at your own pace, in your own voice, over multiple sessions. When you're done, you export a complete draft document.

### Opening the App

Double-click the **Estate OS** shortcut on the estate laptop desktop.

### Your First Session

1. **Welcome screen** — explains what the app is trying to accomplish
2. **Enter your name** — creates your profile
3. **Choose a chapter** — click any chapter in the left sidebar to start there
4. **Choose your time** — how much time do you have? (5 / 10 / 15 / 20 / 30 minutes, or No Limit)
5. **Choose your mode** — Voice (speak your answers) or Text (type your answers)
6. **Begin**

### The Layout

```
┌─────────────────┬──────────────────────────────────────────┐
│   LEFT SIDEBAR  │           MAIN CONTENT AREA              │
│                 │                                          │
│ Chapter List:   │  Chapter title + timer + mode toggle     │
│ ✓ Personal Info │                                          │
│ ◑ Real Estate   │  Current question                        │
│ ○ Finances      │                                          │
│ — Insurance     │  Your answer (text box or voice)         │
│   [Skip]        │                                          │
│                 │  ← Previous | Save & Continue → | Skip → │
│ ✔ Done Today    │                                          │
│ Export PDF      │                                          │
└─────────────────┴──────────────────────────────────────────┘
```

**Left sidebar:** All chapters. Click any chapter to jump to it. Green checkmark = complete. Half circle = started. Circle = not started. Dash = included but not started.

**Include/Skip toggle:** Each chapter has a Skip or Include button. If a chapter doesn't apply to your situation (e.g., no business interests), skip it. Skipped chapters show a dash and don't appear in your final document.

**Done for Today button:** Always visible at the bottom of the sidebar. Click this when you need to stop — your progress is saved and you're taken to the review screen.

### Voice Mode

When you choose Voice mode:
- A microphone button appears
- Click it to start recording
- Speak your answer naturally — you don't have to be formal
- When you stop talking, it transcribes automatically
- You can edit the transcription before saving

Voice mode uses Windows' built-in speech recognition — no microphone app needed, no internet required.

### Finishing for Today

Click **Done for Today** in the sidebar. This takes you to the **Draft Review** screen.

### The Draft Review Screen

Shows everything you've answered, organized by chapter, in a readable draft format. Every answer is editable — click on any text to revise it.

The draft review is where you refine voice transcriptions, fix awkward phrasing, and fill in details you couldn't articulate in the moment.

**Export to PDF/Word:** The Export button at the top creates a formatted document. If you have Microsoft Word, it opens directly. If not, the app will offer to download LibreOffice (free, compatible).

### Coming Back to Continue

Next time you open the app, you'll see your existing profile. Click it to resume where you left off. Your previous answers are all there.

---

## Part 6: Running the System — Daily and Weekly

### Daily

**MHH or any family member:**
1. Open the Capture App on your phone
2. Speak your morning sweep / quick note / evening sweep
3. Done. The pipeline picks it up the next time it runs.

**On the estate laptop (you or a scheduled task):**
```
python behaviors/capture-pipeline/capture_pipeline.py --inbox --confirm
```
This processes all 6 family inboxes, writes to the sheet and logs, and archives processed transcripts.

### Weekly

**Snapshot** — export the current sheet state:
```
python behaviors/snapshot/snapshot.py --confirm
```
Creates a timestamped CSV and updates the SOT (Source-of-Truth) folder and Gold vault copy.

**Weekly Sync** — push logs to Obsidian:
```
python behaviors/weekly-sync/weekly_sync.py --confirm
```
Pushes all flat log files to the Obsidian vault, updates contact pages.

### Quarterly or As Needed

**Silver intake** — process a batch of legacy documents (see Part 3)
**Silver review** — audit machine classifications (see Part 3)
**Tokenizer** — update the token store after adding files to vaults (see Part 4)
**Estate interview** — work through your estate plan chapters (see Part 5)

---

## Part 7: System Health Checks

### Quick Health Check

```
python behaviors/health-check/health_check.py
```

Shows: Google Sheets connection, drive connectivity, config values, dependencies.

### Backup Check

```
python behaviors/backup-check/backup_check.py
```

Verifies the Gold backup (G:\My Drive\Gold-Backup) matches E:\ (Gold vault).

### Vault Setup Verification

If you're not sure the Silver vault folder structure is correct:
```
python behaviors/vault-setup/vault_setup.py --vault silver --test
```
Test mode shows what it would create without creating anything.

### Setup Check

```
python setup_check.py
```
Verifies Python, all dependencies, and config files are correct. Run this after any migration or fresh setup.

---

## Part 8: Configuration

Everything the scripts know about your system — where files live, which Google Sheets to use, which inboxes to scan — lives in two config files.

### `config/config.json` (Ops Ledger config)

Key values:
- `sheet_id` — your Google Sheet ID (from the URL)
- `inbox_dir` — MHH's Google Drive inbox path
- `[family]_inbox_dir` — each family member's inbox
- `gemini_api_key` — or set as GEMINI_API_KEY environment variable

### `config/vault_config.json` (Vault config)

Key values:
- `gold_vault` — E:\ on estate laptop
- `silver_vault` — Y:\ on estate laptop
- `token_store` — where sanitized token copies are stored
- `gold_backup` — G:\My Drive\Gold-Backup

**Never change paths in the code itself.** Always change them in config files. This is what makes migration safe.

---

## Part 9: What's Coming — Phase 5 (Ollama)

Phase 5 is the local AI layer. This is where the system becomes fully intelligent about your private documents.

### What Ollama Is

Ollama runs an AI model directly on the estate laptop — no internet required, no cloud involved. Your sensitive documents stay local. The AI can read them.

### What It Will Enable

Once Ollama is running:
- You'll be able to ask "Where is my flood insurance policy for the Mule property?" and get a direct answer
- You'll be able to ask "What were the major financial events of 2024?" and get a summary from your own records
- The AI will have context about your entire estate without any of that information leaving your laptop

### How It Will Work (Without Exposing Private Data)

The tokenizer (Part 4) is the bridge. It creates sanitized versions of your vault documents with placeholder tokens. Ollama reads the sanitized versions. A lookup layer (the "RAG" system) translates token references back to real values at display time — only after confirming you're looking at your own screen, on your own laptop.

No sensitive information ever travels over a network, even your home network.

### The Plan

1. Install Ollama on the estate laptop
2. Pull a capable model (Mistral or Llama 3 — ~4GB download)
3. Build the RAG layer (local document index using LanceDB)
4. Connect it to the token store
5. Build a query interface — either command-line or a simple desktop window

This is built on the dev machine first, then migrated. The estate laptop is strong enough to run it (may be slow, but functional).

---

## Part 10: Troubleshooting

### "The pipeline ran but nothing appeared in the sheet"

1. Check that the transcript file exists in the inbox
2. Check `G:\My Drive\Estate Ops\Logs\pipeline-errors.log` for error messages
3. Verify Gemini API key is set: `echo %GEMINI_API_KEY%` in terminal
4. Run with `--inbox` flag (not just `--confirm`)

### "Silver classifier isn't finding my files"

1. Make sure the source path is correct and uses actual Windows paths
2. The source folder must exist and contain files
3. Dry-run first (without `--confirm`) to see what it detects

### "Voice isn't working in the estate interview app"

1. Check that Windows Microphone access is enabled for the app
2. Try typing instead — text mode always works
3. If speech recognition was never set up, Windows may need the feature enabled:
   Settings → Time & Language → Speech → add a microphone

### "I can't find a document I filed in Silver"

1. Check the provenance log: `Y:\_provenance\`
2. Each intake session creates a log file with every decision
3. Search by date or filename

### "Cryptomator vault won't mount"

1. Open Cryptomator application
2. Click the vault → Unlock
3. Enter the vault password
4. The drive letter (E:\ or Y:\) should appear in Windows Explorer
5. If the drive letter changed: update `vault_config.json` to match

### "Export PDF isn't working from the estate interview app"

1. If you have Microsoft Word, it should open automatically
2. If not, download LibreOffice from https://www.libreoffice.org (free)
3. The app shows a link to download it if Word isn't detected

---

## Part 11: Security Rules (What Not to Do)

These are built into the system and documented here so you understand why.

1. **Never speak sensitive data into the capture app.** Account numbers, SSNs, full policy numbers, passwords — none of this belongs in a voice memo. Gemini parses your transcripts. Say "my Chase account" not the account number.

2. **Never leave the vault unlocked unattended.** Cryptomator auto-locks after a set timeout. If it doesn't, lock it yourself when stepping away from the laptop.

3. **Never install scripts or tools into the vault.** The vault is documents only. Scripts live in the repo.

4. **Never share the config files.** `config.json` and `vault_config.json` contain path information. Don't email them or put them in cloud storage.

5. **Always run dry-run first.** Every script supports running without `--confirm`. Before running anything that touches real data, run without `--confirm` to see exactly what it will do.

6. **Never delete from logs.** The flat log files and the Ops Ledger are append-only. If something was entered wrong, add a correction entry — never edit or delete the original.

---

## Appendix A: File Structure Reference

```
Estate Laptop:
├── C:\Users\mhhro\estate-orchestrator\   ← Repo (scripts, config)
├── C:\Users\mhhro\Documents\Obsidian Vault\  ← Working knowledge base
├── E:\                                   ← Gold vault (Cryptomator)
│   ├── 01_Financial\
│   ├── 02_Legal\
│   ├── ... (12 domain folders)
│   └── _archive\
├── Y:\                                   ← Silver vault (Cryptomator)
│   ├── 00_Unsorted\
│   ├── 01_Financial\
│   ├── ... (12 domain folders)
│   └── _provenance\
└── G:\My Drive\                          ← Google Drive
    ├── MHH-Inbox\                        ← Capture transcripts (MHH)
    ├── HBS-Inbox\                        ← Capture transcripts (HBS)
    ├── HJH-Inbox\                        ← etc.
    ├── Staging-Intake\
    ├── Capture-Archive\
    └── Estate Ops\
        ├── Logs\                         ← All flat log files
        └── Source-of-Truth\              ← Sheet export snapshots
```

---

## Appendix B: The Family

| Person | Role | Device | Notes |
|--------|------|--------|-------|
| MHH | Owner/Builder | iPhone + Laptop | Primary user, manages system |
| HBS | Owner | iPhone + Mac | Keep it simple — she won't use complex tools |
| HJH | Family | Android | Manages 3 properties (2312, Rental TX, Mule) |
| LEH | Family | TBD | Child, can be promoted to Owner tier |
| HAH | Family | TBD | Child, can be promoted to Owner tier |
| OPA | Family | Android | Similar setup to HJH |

---

## Appendix C: What Volume 1 Covers

This volume starts where Volume 1 ends. Volume 1 covers:
- How to set up the Capture App on a new phone
- How to use the Capture App for morning/evening sweep and quick notes
- The Google Sheet structure and how to query it with Gemini
- How to use the Gemini Query Gem for daily questions
- The Gold vault filing system and how to add documents manually
- How to set up a new family member

If you need to do any of those things, refer to the MHH Technical Manual (on the estate laptop) and the Family Setup Guides (one per family member).

---

*Estate OS — built to last longer than any single app, cloud service, or computer.*
