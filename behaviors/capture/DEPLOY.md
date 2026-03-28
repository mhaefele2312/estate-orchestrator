# Estate Capture App — Deploy Instructions

One-time setup. Takes about 10 minutes.
After setup: one tap on your phone opens a voice-guided capture form.

---

## What This Does

You tap a button on your phone home screen.
A form opens. It reads each question aloud.
You speak your answers.
When done, it saves a formatted note directly to your Google Drive MHH-Inbox.
Your laptop picks it up and moves it to Obsidian Inbox for gate review.

---

## Step 1 — Open Google Apps Script

On your laptop, go to:
  https://script.google.com

Sign in with your ESTATE Google account (not personal).
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

## Step 5 — Save the Project

Press Ctrl+S to save.

---

## Step 6 — Deploy as Web App

Click the blue "Deploy" button in the top right.
Choose "New deployment".

In the dialog:
  - Type: Web app (should already be selected)
  - Description: Estate Capture v1
  - Execute as: Me (your estate Google account)
  - Who has access: Only myself

Click "Deploy".

Google will ask you to authorize the app.
Click "Authorize access".
Choose your estate Google account.
Click "Allow".

---

## Step 7 — Copy Your App URL

After deploying, Google shows you a Web app URL.
It looks like:
  https://script.google.com/macros/s/LONG_ID_HERE/exec

Copy this URL. This is your capture button.

---

## Step 8 — Add to Your Android Home Screen

On your Android phone, open Chrome.
Go to the URL you just copied.
Tap the three-dot menu (top right).
Choose "Add to Home screen".
Name it: Estate Capture
Tap Add.

A button now appears on your home screen.
Tap it once to test.

---

## What Happens When You Tap

1. App opens in Chrome
2. Tap the red Start button
3. App reads question 1 aloud and starts recording
4. Speak your answer
5. App auto-advances to question 2
6. Continue through all 9 questions (skip any you want)
7. Review screen shows all your answers
8. Tap Save — file goes directly to MHH-Inbox in Google Drive
9. Your laptop pickup script moves it to Obsidian Inbox

---

## The 9 Questions

1. What's on your mind right now that you haven't captured yet?
2. What did you work on or commit to yesterday that needs follow-up?
3. Who needs something from you today?
4. Who do you need to reach out to — and what for?
5. How can they help you? How can you help them?
6. What are your top priorities today?
7. Anything happening with the house, cars, finances, legal, or family?
8. Any documents, bills, appointments, or deadlines coming up?
9. What else is floating in your head that belongs in the system?

---

## If Voice Does Not Work

Chrome on Android supports voice capture.
If it asks for microphone permission, tap Allow.
If voice still does not work, a text box appears so you can type instead.

---

## Troubleshooting

Save failed error:
  Make sure MHH-Inbox folder exists in your estate Google Drive.
  The app will create it automatically if missing.

App asks to re-authorize:
  This happens if you redeploy. Just click Allow again.

URL stopped working:
  You may need to redeploy. Go to script.google.com,
  open Estate Capture, click Deploy, choose Manage deployments,
  and check the status.
