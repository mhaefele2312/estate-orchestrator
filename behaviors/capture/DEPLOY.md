# Estate Capture App — Deploy Instructions

One-time setup. Takes about 10 minutes.
After setup: one tap on your phone opens a voice capture form.

---

## What This Does

You tap a button on your phone home screen.
A form opens with text prompts based on time of day:
- **Morning Sweep** (before 11am) — 9 prompts, includes health check-in
- **Quick Note** (11am-5pm) — 5 rapid-fire prompts (who/what/where/when/why)
- **Evening Sweep** (after 5pm) — 6 prompts, includes health check-in

You tap the mic button and speak freely while reading the prompts.
Recording is continuous — one long recording, not per-question.
When done, review and edit the transcript, then save.
The .md file goes to your Google Drive inbox folder.
The capture pipeline processes it automatically.

---

## Step 1 — Open Google Apps Script

On your laptop, go to:
  https://script.google.com

Sign in with your ESTATE Google account (mhh.rosevale.west@gmail.com).
Click "New Project" in the top left.

---

## Step 2 — Name the Project

Click "Untitled project" at the top.
Rename it to: Estate Capture

---

## Step 3 — Paste the Backend Code

You will see a file called "Code.gs" already open.
Delete everything in it.
Open this file on your laptop:
  estate-orchestrator/behaviors/capture/Code.gs
Copy the entire contents and paste into Code.gs in Apps Script.

---

## Step 4 — Add the HTML File

In Apps Script, click the + button next to "Files" in the left sidebar.
Choose "HTML".
Name it exactly: Index
(No .html extension — Apps Script adds it automatically.)

Delete everything in the new Index.html file.
Open this file on your laptop:
  estate-orchestrator/behaviors/capture/Index.html
Copy the entire contents and paste into Index.html in Apps Script.

---

## Step 5 — Save and Deploy

Press Ctrl+S to save.

Click the blue "Deploy" button in the top right.
Choose "New deployment".

In the dialog:
  - Type: Web app
  - Description: Estate Capture v2
  - Execute as: Me (your estate Google account)
  - Who has access: Only myself

Click "Deploy".

Google will ask you to authorize the app.
Click "Authorize access" > Choose your estate account > Click "Allow".

---

## Step 6 — Copy Your App URL

After deploying, Google shows you a Web app URL like:
  https://script.google.com/macros/s/LONG_ID_HERE/exec

Copy this URL. This is your capture button.

---

## Step 7 — Add to Your Android Home Screen

On your Android phone, open Chrome.
Go to the URL you just copied.
Tap the three-dot menu (top right).
Choose "Add to Home screen".
Name it: Estate Capture
Tap Add.

---

## What Happens When You Tap

1. App opens in Chrome
2. Auto-detects capture mode based on time of day
3. Shows the prompts as a text list on screen (not read aloud)
4. Tap the red mic button to start recording
5. Speak freely — recording is continuous
6. Tap "Next Prompt" to move through the list as you go
7. Tap "Done" when finished
8. Review screen lets you edit the transcript
9. Tap "Save" — file goes to MHH-Inbox in Google Drive
10. Capture pipeline processes it into the sheet + flat logs

---

## For HBS (Phase 2)

When HBS is added, she uses the same app with a URL parameter:
  https://script.google.com/macros/s/LONG_ID_HERE/exec?user=HBS

This saves to HBS-Inbox instead of MHH-Inbox.

---

## If Voice Does Not Work

Chrome on Android supports voice capture.
If it asks for microphone permission, tap Allow.
If voice still does not work, the transcript box becomes editable
so you can type instead.

---

## Troubleshooting

Save failed error:
  The app auto-creates the inbox folder if missing.
  If it still fails, check that Google Drive has space.

App asks to re-authorize:
  This happens if you redeploy. Just click Allow again.

URL stopped working:
  Go to script.google.com, open Estate Capture,
  click Deploy > Manage deployments, and check status.
