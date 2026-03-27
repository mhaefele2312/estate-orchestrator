# Estate Orchestrator — Start Here

This is the new, clean build of the Estate Operating System orchestrator.
The old sandbox (EstateDevTest_Sandbox) is reference material only. Do not run it.

---

## What is in this folder

| Folder / File | What it is |
|---|---|
| `behaviors/gate/` | The gate script (moves Inbox → Accepted with your approval) |
| `behaviors/publish/` | The publish script (moves Accepted → Published after leak check) |
| `behaviors/health-check/` | The health check script (daily system status report) |
| `behaviors/backup-check/` | The backup check script (is Gold backed up?) |
| `behaviors/digest-generate/` | The digest script (weekly summary email for HBS) |
| `tests/` | Fake test files — scripts run here first, never against real vault |
| `logs/` | Every run is logged here automatically |
| `.cursorrules` | Rules that Cursor's AI follows — do not delete |

---

## The one rule you must always follow

**Never run any script without --dry-run first.**

Every script has two modes:
- `python script.py --dry-run` → shows you what WOULD happen, changes nothing
- `python script.py --confirm` → actually does it

Always run dry-run first. Read the output. If it says what you expect, then run with --confirm.

---

## How to set up git (do this once, right now)

Git is your undo button. Every time something works, you save a snapshot.
If anything ever breaks, you can go back to the last snapshot.

**Step 1.** In Cursor, open the Terminal.
- Go to the top menu: Terminal → New Terminal
- A black panel will appear at the bottom of Cursor

**Step 2.** Type this exactly and press Enter:
```
git init
```
You should see: `Initialized empty Git repository`

**Step 3.** Type this exactly and press Enter:
```
git add .
```
No output is normal.

**Step 4.** Type this exactly and press Enter:
```
git commit -m "initial structure"
```
You should see something about files committed.

That's it. Git is set up. You won't need to touch it again until I tell you to.

---

## How to run a behavior (once scripts exist)

1. Open Cursor Terminal (Terminal → New Terminal)
2. Type: `cd behaviors/gate` and press Enter
3. Type: `python gate.py --dry-run` and press Enter
4. Read the output carefully
5. If output looks correct, type: `python gate.py --confirm` and press Enter

---

## Who builds the scripts

Claude (Cowork) builds every script and tells you exactly where to put it.
Cursor's AI helps you make small changes after the initial build.
You never write code from scratch.

---

## Current status

- [x] Folder structure created
- [x] Cursor rules set up
- [ ] Behavior audit complete (Claude is doing this now)
- [ ] Gate behavior built
- [ ] Publish behavior built
- [ ] Health check built
- [ ] Backup check built
- [ ] Git initialized (you do this — see instructions above)
