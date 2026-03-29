# Session Notes — 2026-03-28

## Where we left off

The core pipeline is fully built:

1. **Capture** — Google Apps Script voice form (9 questions, Android home screen button) saves a structured `.md` file to Google Drive `MHH-Inbox/`
2. **Inbox Pickup** — moves files from Google Drive → Obsidian Vault `Inbox/`
3. **Gate** — operator reviews each file, stamps provenance frontmatter, moves to `Accepted/`
4. **Publish** — checks provenance + PII scan, sanitizes financial figures, moves to `Published/`

All behaviors follow dry-run-first discipline. Test data is in `tests/`. Vault paths point to `C:\Users\mhhro\Documents\Obsidian Vault\`.

---

## The open design problem: split and route

The voice capture app produces **one monolithic file per session**. A single capture can contain items spanning multiple topics — taxes, property, tasks, contacts, family scheduling — all mixed together under the 9 question headers.

Currently nothing splits these. The Gate assigns one `classification` to the whole file, which is too coarse.

---

## What we plan to work on next

Design and build a **split/route behavior** that sits between Inbox Pickup and Gate (or as part of Gate), and:

1. Parses a voice capture into individual atomic items
2. Assigns each item a classification (taxes, property, legal, medical, general, task, contact, etc.)
3. Routes each item to the right place — either as separate inbox files, or directly into typed destination notes

### Key design questions to resolve first

- **When does splitting happen?** Before Gate (pre-processor creates multiple inbox files), inside Gate (operator splits during review), or after Gate (separate behavior on accepted captures)?
- **How much is automated vs. operator-confirmed?** Does Claude propose splits and the operator approves, or does the operator split manually?
- **What are the destination types?** Does every item land in `Published/` generically, or do property items go to a Properties note, tasks to a task list, contacts to a contacts note?
- **What about captures that are already atomic?** A quick one-thing voice note should pass through without being split.
- **Per-item classification vs. per-file?** Classification needs to move to the item level, not the file level, if we're splitting.

### Starting point for next session

Begin by agreeing on the split/route architecture — specifically the "when" question — before writing any code.
