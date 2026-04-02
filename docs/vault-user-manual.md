# Estate OS — Vault User Manual

**Version:** 1.2
**Last updated:** 2026-03-31
**Audience:** MHH and authorized family members

---

## What Is a Vault?

A vault is an encrypted folder on your computer. Files inside look like scrambled nonsense to anyone without the password. Cryptomator is the app that locks and unlocks your vaults — it turns a vault into a normal folder you can browse while it is open, and scrambles everything back when you close it.

You have three vaults. Each one has a specific purpose and set of rules.

---

## The Three Vaults at a Glance

| Vault | Drive | What It Holds | Who Files It |
|-------|-------|---------------|--------------|
| **Gold** | `X:\` | Your permanent records, going forward | You, manually |
| **Silver** | `Y:\` | Legacy files sorted by machine | The AI pipeline |
| **Bronze** | USB drive | Silver overflow when laptop fills up | You, manually redirect the pipeline |

---

## Gold Vault (`X:\`)

### What it is

The Gold vault is your permanent estate record. It holds every important document from today forward — tax returns, deeds, insurance policies, trust documents, bank statements, medical records, contracts.

Everything in Gold was put there by you, named by you, and filed by you. No machine ever touches this vault. It is your single source of truth for the estate going forward.

### When to use it

- You receive a new tax document → save it to `X:\06_Tax\`
- You sign a legal agreement → save it to `X:\02_Legal\`
- You get an insurance renewal → save it to `X:\04_Insurance\`
- You scan a property document → save it to `X:\03_Property\`

### Rules

- **You file everything here manually.** No script, no AI, no automation ever writes to Gold.
- **Name files yourself** before saving. Use clear, dated names: `2025-home-insurance-renewal.pdf` not `scan_047.pdf`.
- **Never put sensitive data in voice captures.** Account numbers, SSNs, and financial figures go directly into Gold — never spoken into the phone app.

### Folder structure

```
X:\  (Gold Vault — unlock in Cryptomator first)
├── 01_Financial/      Bank statements, investment accounts, loan documents
├── 02_Legal/          Contracts, agreements, court documents, attorney correspondence
├── 03_Property/       Deeds, titles, surveys, HOA documents, property tax notices
├── 04_Insurance/      All policies and renewals — home, auto, life, umbrella
├── 05_Medical/        Medical records, lab results, prescriptions, EOBs
├── 06_Tax/            Tax returns, W-2s, 1099s, IRS correspondence
├── 07_Estate-Planning/ Trust documents, wills, power of attorney, beneficiary forms
├── 08_Vehicles/       Titles, registration, service records
├── 09_Digital/        Password records, account inventory, digital asset notes
├── 10_Family/         Family records, school documents, personal history
├── 11_Contacts/       Key contact reference documents, professional relationships
└── 12_Operations/     System configs, API credentials, backup keys (do not modify manually)
```

### Backup

Gold automatically backs up to Google Drive as encrypted ciphertext. Even if Google can see the files, they are scrambled — Google cannot read them. The backup runs automatically in the background via Google Drive for Desktop.

---

## Silver Vault (`Y:\`)

### What it is

The Silver vault holds legacy files — documents from old drives, scanned archives, and historical records that have been sorted and named by the AI pipeline (not by you). The machine does its best, but some classifications may be wrong.

Silver is not a lower-security vault. It is just as encrypted as Gold. The distinction is **who did the organizing**: Gold was organized by you; Silver was organized by a machine.

### When to use it

Silver is populated automatically by the Silver Classifier when you process old drives. You do not file things into Silver manually — the pipeline does it.

You do interact with Silver when:
- Reviewing machine classifications to correct mistakes
- Promoting a file from Silver to Gold after you have personally verified it

### Rules

- **Never file anything into Silver manually.** That defeats the purpose — Silver means machine-curated.
- **Do not mix Silver with Gold.** If a file from Silver has been reviewed and you trust it, promote it to Gold. Don't leave reviewed files in Silver as if they were still machine-classified.
- **The `_provenance/` folder is read-only for you.** It is the machine's log of what it did. Do not edit or delete files in `_provenance/`.
- **Low-confidence files land in `00_Unsorted/`.** Review these manually.

### Folder structure

```
Y:\  (Silver Vault — unlock in Cryptomator first)
├── 00_Unsorted/       Machine confidence too low to classify — review these manually
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
└── _provenance/
    ├── ingestion-log.jsonl     What the machine processed, when, and how confident it was
    ├── review-queue.jsonl      Files flagged for your review
    └── corrections-log.jsonl   Your corrections to machine decisions (written by review tool)
```

### Backup

Silver backs up to Google Drive as encrypted ciphertext, same as Gold, via `G:\My Drive\Silver-Backup\`.

---

## Bronze Vault (USB Drive)

### What it is

Bronze is the overflow vault for Silver. When the Silver vault on the estate laptop gets large enough that you want to move content off the laptop, you redirect the pipeline to write new machine-processed legacy content to Bronze instead.

Bronze is on an external USB drive (or later, a NAS). It has exactly the same folder structure as Silver.

### When to use it

- The estate laptop is running low on storage and Silver is large
- You are processing a very large legacy drive and want to keep it separate
- You want a physical, offline copy of machine-processed legacy content

### Rules

- **Bronze is not always connected.** Scripts that need Bronze will stop clearly if the drive is not plugged in. This is intentional — no silent failures.
- **You redirect to Bronze manually.** Open `config/vault_config.json`, set `bronze_vault` to the USB drive path, and run the pipeline with `--vault bronze`. The pipeline does not switch automatically.
- **Bronze has the same encryption standard as Silver.** If using Cryptomator for Bronze, the vault container lives on the USB drive.
- **Provenance records travel with the vault.** The `_provenance/` folder on Bronze contains the records for everything stored there.

### Setting up Bronze for the first time

1. Connect the USB drive to the estate laptop
2. Note what drive letter Windows assigned to it (check in Windows Explorer — it will appear as a new drive, e.g. `Z:\`)
3. Open `config/vault_config.json` in the estate-orchestrator folder
4. Change `"bronze_vault": ""` to `"bronze_vault": "Z:\\"` (use your actual drive letter)
5. Save the file
6. Run vault setup for Bronze:
   ```
   python behaviors/vault-setup/vault_setup.py --vault bronze
   ```
   *(dry-run — review the output)*
   ```
   python behaviors/vault-setup/vault_setup.py --vault bronze --confirm
   ```
   *(creates all folders on the USB drive)*

### When the USB drive is not connected

Scripts will report: *"Bronze vault drive is not accessible"* with instructions to reconnect and configure. Nothing will write to a wrong location. Nothing will silently fail.

---

## How the Three Vaults Work Together

```
OLD DRIVES / LEGACY FILES
         |
         v
  Silver Classifier (sorts, names, and files each document)
         |
         v
  Silver Vault (Y:\)   -- machine files it here
         |
    Space running low?
         |
         v
    Bronze Vault (USB)   -- redirect pipeline here manually

    You review Silver/Bronze content periodically
         |
    File verified? --> promote to Gold (X:\)

  Gold Vault (X:\)   -- your permanent, human-curated record
```

---

## Daily Workflow

**Adding a new document (Gold):**
1. Open Cryptomator → unlock Gold vault (mounts as `X:\`)
2. Save the document to the correct folder (e.g. `X:\04_Insurance\`)
3. Name it clearly before saving (e.g. `2026-auto-insurance-renewal.pdf`)
4. Lock Gold when done (close in Cryptomator)

**Processing a legacy drive (Silver):**
1. Connect the legacy drive
2. Copy files to the staging folder
3. Run the Silver Classifier (instructions below)
4. Review `Y:\_provenance\review-queue.jsonl` for items flagged for attention
5. Correct any misclassifications

**Redirecting to Bronze (when Silver is large):**
1. Connect USB Bronze drive
2. Update `bronze_vault` path in `config/vault_config.json`
3. Run pipeline with `--vault bronze` flag
4. Disconnect USB when done; update `bronze_vault` back to `""` in config

---

## Cryptomator Quick Reference

| Action | Steps |
|--------|-------|
| Open a vault | Open Cryptomator → click the vault name → click Unlock → enter password |
| Close a vault | Open Cryptomator → click the vault name → click Lock |
| Check which drive letter a vault uses | Open Cryptomator → select the vault → drive letter is shown in the vault details |
| Change a vault's drive letter | Open Cryptomator → vault preferences → set a custom drive letter |

**Gold vault is set to always mount as `X:\`.**
**Silver vault is set to always mount as `Y:\`.**
Set these once in Cryptomator vault preferences so they never change.

---

## Security Rules (Non-Negotiable)

1. **Cloud AI never reads the vaults.** Gemini, Claude, and any other cloud AI never see vault contents. Only local AI (on the mini PC, Phase 5) may read vaults, and only for tokenization — replacing sensitive values before any query system touches them.

2. **Gold is human-only.** No script, no AI, no automation writes to `X:\`. Ever.

3. **Vaults are always locked when not in use.** Open Cryptomator and lock the vault when you finish. Do not leave vaults unlocked overnight.

4. **The `12_Operations/` folder in Gold is managed by the system.** Do not manually add, rename, or delete files in `X:\12_Operations\`. It holds encrypted system configs and credentials used by scripts.

5. **If you are unsure where something goes, it goes to Gold.** Silver is for legacy content processed by machine. Anything new and anything you are personally filing belongs in Gold.

6. **Bronze is offline by default.** The USB drive should not be permanently connected. Connect it to run the pipeline, then disconnect.

---

## Vault Setup Checklist (One-Time, Estate Laptop)

- [ ] Gold vault (`X:\`) — already live
- [ ] Create Silver Cryptomator vault (new vault, store container on E: or C:, set drive letter to `Y:\`)
- [ ] Run: `python behaviors/vault-setup/vault_setup.py --vault silver --confirm`
- [ ] Confirm `Y:\` shows 14 folders including `_provenance/`
- [x] Connect USB drive for Bronze — completed 2026-03-31, drive label `BronzeVault`
- [x] Update `config/vault_config.json` → set `bronze_vault` to `D:\\`
- [x] Run: `python behaviors/vault-setup/vault_setup.py --vault bronze --confirm` — 17 folders created
- [x] Confirmed Bronze shows 14 domain folders + `_provenance/` with 3 empty log files
- [x] Reset `bronze_vault` back to `""` in `vault_config.json`
- [ ] Label USB drive `BronzeVault` in Windows Explorer (right-click drive → Rename)
- [ ] When reconnecting Bronze: set `bronze_vault` to drive letter, run pipeline, reset to `""` when done

---

## The Token Store and Tokenization

### What tokenization is

When the vault tokenizer runs, it reads every document in your Gold or Silver vault and replaces sensitive values with code labels before passing anything to a local AI. The real values never leave the vault. The AI only ever sees the labels.

For example, a tax return that contains:

```
Taxpayer: Martin Haefele
SSN: 214-77-3901
Routing number: 021000021
```

becomes:

```
Taxpayer: [NAME_MHH]
SSN: [SSN_0001]
Routing number: [ROUTING_0001]
```

The tokenized copies live in the Token Store. The master list mapping every label back to the real value is the Token Registry.

### What the tokenizer handles automatically

The tokenizer detects and replaces the following without any configuration:

| Type | Examples |
|------|---------|
| Names | `Martin Haefele`, `Helen Haefele` |
| Social Security Numbers | `214-77-3901` |
| Routing numbers | `021000021` (9-digit ABA routing numbers) |
| Bank account numbers | `4402817733` (8–17 digit account numbers with context) |
| Phone numbers | `(978) 555-0100` |
| Email addresses | `mhaefele@gmail.com` |
| Dates | `March 15, 2026`, `2026-03-15` |
| Dollar amounts | `$12,450.00`, `$1,200/month` |
| Credit card numbers | `4111 1111 1111 1111` |
| Addresses | `47 Ridgecrest Lane, Westford MA 01886` |

For anything the automatic detection misses — short names, unusual account numbers, property addresses — use the Custom Token List (see below).

### PDF support

The tokenizer handles PDF files automatically. It tries two methods in order:

1. **Text extraction** — if the PDF has a text layer (most bank statements, tax returns, and documents saved from software), the text is read directly. Fast and accurate.
2. **OCR** — if the PDF is a scan (a photo of a paper document), the tokenizer reads it using optical character recognition. Slower but handles scanned documents.

No action is required on your part. The tokenizer detects which method to use for each file.

### Where the Token Store lives

```
C:\Users\mhhro\Documents\Estate-Token-Store\
├── gold\          Tokenized copies of Gold vault documents
├── silver\        Tokenized copies of Silver vault documents
└── _registry\
    ├── token_registry.json    Master list: every token --> original value  [SENSITIVE]
    ├── file_hashes.json       Tracks which files have already been processed
    └── custom_tokens.json     Your list of values to always tokenize  <- you maintain this
```

The Token Store never leaves the estate laptop. The `token_registry.json` is sensitive — it contains the real values. The tokenized documents in `gold\` and `silver\` are safe for a local AI to read.

### Running the tokenizer

```
python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold
```
Dry-run — shows what would be found, nothing written.

```
python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold --confirm
```
Live run — writes tokenized copies to the Token Store and updates the registry.

Re-running is always safe. Files that have not changed since the last run are skipped automatically.

---

## Your Custom Token List

The tokenizer uses AI (Microsoft Presidio) to detect sensitive values automatically. But Presidio does not catch everything — it can miss addresses, short names, and values that do not look like standard formats.

The custom token list lets you guarantee that specific values are always replaced, in every document, every time.

### Where it lives

```
C:\Users\mhhro\Documents\Estate-Token-Store\_registry\custom_tokens.json
```

You create this file once and add to it over time. It is a plain text file you can open and edit in any text editor.

### Format

```json
[
  {
    "original": "47 Ridgecrest Lane, Westford MA 01886",
    "type":     "ADDR",
    "token":    "[ADDR_HOME]",
    "note":     "Primary residence"
  },
  {
    "original": "Martin Haefele",
    "type":     "NAME",
    "token":    "[NAME_MHH]",
    "note":     "MHH full name"
  },
  {
    "original": "001-447-23918",
    "type":     "ACCT",
    "note":     "Checking account -- token assigned automatically if omitted"
  }
]
```

Each entry has:

| Field | Required | What it does |
|-------|----------|--------------|
| `original` | Yes | The exact text to find and replace. Case-insensitive. |
| `type` | Yes | What kind of data it is: `NAME`, `ADDR`, `ACCT`, `SSN`, `PHONE`, `AMOUNT`, `EMAIL` |
| `token` | No | The label it becomes in every document, e.g. `[ADDR_HOME]`. If you leave this out, the system assigns a number automatically. |
| `note` | No | A reminder for yourself. Ignored by the code. |

### What to put in your custom list

Add anything you know is sensitive that you want guaranteed coverage on:

- **Your home address** — Presidio often misses full street addresses
- **Family member names** — short names like "Helen" are easily missed
- **Account numbers** — any account number Presidio might not recognize by format
- **Property addresses** — rental properties, investment properties
- **Business names** — any entity names that are sensitive
- **Short towns or zip codes** — too short for Presidio to catch reliably

### Rules

- **The file is yours to maintain.** Add entries any time. The tokenizer picks them up automatically on the next run.
- **Entries are cumulative.** Adding a new entry does not affect existing tokenized files until you re-run the tokenizer on those files. Delete `file_hashes.json` from the `_registry` folder to force a full re-run.
- **Token labels you choose are permanent.** Once `[ADDR_HOME]` is in the registry, that label sticks to that address forever across all documents. Do not reuse a label for a different value.
- **Back up this file.** `custom_tokens.json` is part of your estate configuration. Keep a copy in Gold vault: `X:\12_Operations\custom_tokens.json`.

---

## Silver Classifier — Organizing Legacy Files

### What it does

The Silver Classifier is the tool that takes a folder of old, unorganized files and files them into the Silver vault with proper names and domain folders. You run it interactively — it shows you each file, tells you where it thinks the file belongs, and asks you to confirm or correct before anything is moved.

Nothing is moved without your approval. Every filing decision is logged.

### What it handles

- `.md` and `.txt` files (already text)
- `.pdf` files — both text-layer PDFs and scanned documents (via OCR)

### How it classifies files

For each file it:

1. Reads the content
2. Scores it against 12 domain keyword lists to find the best match
3. If the best score is too low (below the confidence threshold), routes the file to `00_Unsorted/` for manual review
4. Suggests a filename using the format below
5. Asks you to confirm

### Filename format

All files filed by the Silver Classifier are renamed using this format:

```
YYYY_MM_DD_Institution_Type of Statement_account.ext
```

For financial documents:

| Part | Example | What it is |
|------|---------|------------|
| `YYYY_MM_DD` | `2023_12_31` | End of period date (last day of the statement period) |
| `Institution` | `Vanguard` | Name of the bank, brokerage, or insurer |
| `Type of Statement` | `Year End Statement` | What kind of document it is |
| `account` | `IRA-7823` | Account number or last 4 digits |

Full example: `2023_12_31_Vanguard_Year End Statement_IRA-7823.pdf`

For non-financial documents, the classifier uses the document date and a descriptive name from the content.

### Statement types recognized

The classifier recognizes these statement types automatically from document content:

- Year End Statement (December 31 period end)
- Quarterly Statement (March 31, June 30, September 30, December 31 period end)
- Monthly Statement
- 1099-INT, 1099-DIV, 1099-B, 1099-R, 1099-MISC, 1099-NEC
- W-2

### Running the classifier

```
python behaviors/silver-classifier/silver_classifier.py --staging G:\My Drive\Staging-Intake --vault silver
```

Dry-run — shows what would be done, nothing moved.

```
python behaviors/silver-classifier/silver_classifier.py --staging G:\My Drive\Staging-Intake --vault silver --confirm
```

Live run — processes files interactively, one at a time.

### Interactive commands

When the classifier shows you a file, you respond with one of these:

| Key | Action |
|-----|--------|
| Enter | Accept the suggested domain and filename — file it |
| `1`–`12` | Override the domain (use the domain number) |
| `r` | Rename — type a different filename before filing |
| `s` | Skip this file — leave it in staging, decide later |
| `d` | Delete — remove the file from staging without filing it |
| `q` | Quit — stop the session; progress so far is saved |

### Provenance

Every file the classifier moves gets a provenance record written to `_provenance/ingestion-log.jsonl`. The record includes the original filename, the domain, the confidence score, the filing date, and the classifier version. This log is never deleted.

---

## Estate OS Document Search

### What it is

Estate OS Document Search is a private search tool for your vault. It runs on your estate laptop and looks like a chat interface — you type a question, it finds the matching passages in your documents and shows them to you with the real values restored.

**There is no AI.** No language model reads your documents. No cloud service is involved. It is a keyword search engine running entirely on your machine.

### What it does

- Searches all tokenized vault documents for your keywords
- Shows you the matching passages from each document with real account numbers, routing numbers, SSNs, and other values restored (from the Token Registry)
- Shows you which vault and domain folder each result came from
- Keeps no log of your searches

### What it does NOT do

- It does not generate answers or summaries — it finds and shows passages
- It does not connect to the internet
- It does not send anything to a cloud service
- It does not write to any file

### Launching from the desktop shortcut

Double-click **Estate OS** on the estate laptop desktop. A black terminal window will open (keep it open — it is the engine running in the background) and the app will open in your browser automatically.

Close the terminal window when you are done to shut everything down.

### Launching from the command line

```
launch_estate_assistant.bat
```

Or manually:

```
python -m streamlit run behaviors/estate-assistant/estate_assistant.py --server.headless true
```

### Using the search

Type your question or keywords in the box at the bottom. Examples:

- *What is my routing number at First National Bank?*
- *Show me my 2022 tax return*
- *What life insurance policies do I have?*
- *What is my Vanguard account number?*

The search finds documents that contain your keywords and shows the most relevant passage from each matching document. Up to three results are shown.

### Before searching

The Token Store must be up to date. If you have added new documents to your vault recently, run the tokenizer first:

```
python behaviors/vault-tokenizer/vault_tokenizer.py --vault gold --confirm
```

The search engine reads from the Token Store — it does not read the vault directly.

---

## Where These Files Live

| Document or Tool | Location |
|------------------|----------|
| This manual | `docs/vault-user-manual.md` in estate-orchestrator repo |
| Vault path config | `config/vault_config.json` in estate-orchestrator repo |
| Vault setup script | `behaviors/vault-setup/vault_setup.py` |
| Tokenizer script | `behaviors/vault-tokenizer/vault_tokenizer.py` |
| Silver Classifier | `behaviors/silver-classifier/silver_classifier.py` |
| Estate OS search UI | `behaviors/estate-assistant/estate_assistant.py` |
| Estate OS desktop launcher | `launch_estate_assistant.bat` (estate-orchestrator root) |
| Token Store | `C:\Users\mhhro\Documents\Estate-Token-Store\` |
| Token Registry (master list) | `C:\Users\mhhro\Documents\Estate-Token-Store\_registry\token_registry.json` |
| Custom token list | `C:\Users\mhhro\Documents\Estate-Token-Store\_registry\custom_tokens.json` |
| Full system design | `Estate-OS-Master-Plan-v2.md` in estate-orchestrator repo |
| Document flow map | `docs/document-flow-map.md` in estate-orchestrator repo |
