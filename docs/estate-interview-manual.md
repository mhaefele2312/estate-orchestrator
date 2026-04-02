# Estate OS — Estate Interview App
## User Manual v1.2

---

## What This Is

The Estate Interview is a private desktop application for Windows. It guides you through a structured conversation to build two things at once:

1. **A Break-the-Glass Estate Plan** — the practical document your executor needs when something happens to you: who to call, where the accounts are, where the documents live, what your wishes are.

2. **A Family History Record** — your story, and the story of the generations before you, captured in your own words. This second part is entirely optional but irreplaceable. No one else can write it.

When you are done — or whenever you feel ready — the app exports a professional PDF you can print, sign, and store in a fireproof safe.

**Everything stays on your computer.** Nothing is sent anywhere. No account required.

---

## Who Can Use It

Anyone in your family. Each person gets their own independent profile. You can have one profile for yourself, one for your spouse, one for an elderly parent — all on the same computer. They never mix.

---

## Before You Start: One-Time Setup

The app needs one free piece of software installed on your computer before it will run. This takes about 10 minutes and you only ever do it once.

### Step 1 — Check if Python is already installed

1. Click the Windows **Start** button (the four-square icon at the bottom-left of your screen).
2. Type the word `cmd` into the search box.
3. Click **Command Prompt** in the results. A black window will open.
4. Type the following exactly as shown and press **Enter**:
   ```
   python --version
   ```
5. Look at what it says:
   - If you see something like `Python 3.11.4` (any number starting with 3), Python is already installed. Close the black window and skip to **Step 2 — Get the Estate OS folder** below.
   - If you see `'python' is not recognized` or nothing useful, continue to the next step.

### Step 1b — Install Python (only if Step 1 said it was missing)

1. Open a web browser (Edge, Chrome, or Safari).
2. Go to: **python.org/downloads**
3. Click the large yellow button that says **Download Python 3.x.x** (the exact version number does not matter).
4. When the download finishes, open the downloaded file. It will be named something like `python-3.x.x-amd64.exe`.
5. A setup window will open. **Before you click anything else**, look at the bottom of the window. There is a small checkbox that says **"Add python.exe to PATH"**. **Tick this box.** This is the most important step. If you miss it, the app will not work.
6. Click **Install Now**.
7. Wait for it to finish (about 2 minutes). Click **Close** when done.
8. To confirm it worked: open Command Prompt again (Start → type `cmd` → press Enter), type `python --version`, and press Enter. You should now see a version number.

### Step 2 — Get the Estate OS folder onto your computer

If you are reading this manual, you likely already have the Estate OS folder. It is the folder that contains this manual. Skip to **Step 3** below.

If you do not have it yet, ask the person who set up Estate OS to copy the folder to your computer. The whole folder can be placed anywhere you like — your Desktop, your Documents folder, or a USB drive.

### Step 3 — Run the app for the first time

1. Open the Estate OS folder.
2. Double-click the file called **`launch_estate_interview.bat`**. It is a white document icon with a small gear symbol.
3. A black window will appear briefly. It will print some lines of text while it installs a few small supporting tools. This only happens the first time and takes about 30–60 seconds. Do not close this window.
4. When it is finished, the Estate Interview app opens automatically in a new window with a dark blue background.

That is the setup complete. From now on, double-clicking `launch_estate_interview.bat` opens the app directly in a few seconds.

---

## If Something Goes Wrong During Setup

**"Windows protected your PC" warning appears:**
Click **More info**, then click **Run anyway**. This warning appears for any program that was not downloaded from the Microsoft Store. It is safe to dismiss for files you received from someone you trust.

**The black window opens and closes immediately:**
This usually means Python is installed but the "Add to PATH" step was missed during installation. To fix it:
1. Open Start → search for **Add or remove programs** → click it.
2. Find **Python 3.x.x** in the list and click it.
3. Click **Modify**, then **Next**, then tick **Add Python to environment variables**, then **Install**.
4. Try double-clicking `launch_estate_interview.bat` again.

**The black window says "pip is not recognized":**
This means Python installed without its package manager. Uninstall Python (Start → Add or remove programs → find Python → Uninstall), then reinstall it following Step 1b above, making sure to tick the PATH checkbox.

**You see a red error message you do not understand:**
Take a photo of the screen and send it to whoever set up the system for you.

---

## Starting the App Each Time

Double-click **`launch_estate_interview.bat`** in the Estate OS folder.

A small black window will flash briefly, then the Estate Interview opens. You do not need to look at the black window.

---

## First Time: Creating Your Profile

When the app opens for the first time, you will see a welcome screen with a text box asking for your name.

1. Click inside the text box and type your name. You can use any name — "Dad", "Margaret", or your full name. It only matters that you will recognise it when you return.
2. Click **Begin My Estate Plan**.

The interview starts immediately.

---

## Returning: Picking Up Where You Left Off

If you have used the app before, it will show a list of profiles when it opens. Each entry shows:

- The person's name
- How far along they are (e.g. "43% complete")
- When they last updated it

Click **Continue** next to your name. The app takes you back to exactly the question you were on when you last closed it.

---

## The Interview

### Two Parts

The interview is divided into 11 chapters, organised in two parts:

**Part One — Your Estate Plan** (Chapters 1–9)

These are the practical questions your executor will need answered. Work through them in order, or jump to any chapter using the sidebar.

| Chapter | What It Covers |
|---------|---------------|
| 1. About You | Full legal name, date of birth, national insurance / SSN, address |
| 2. Your Family | Spouse or partner, children, dependants |
| 3. Key People | Your executor, backup executor, attorney, financial advisor |
| 4. Your Documents | Where your will is, trust documents, advance directive, power of attorney |
| 5. Your Finances | Bank accounts, investment accounts, pension, insurance policies |
| 6. Your Property | Home and any other property you own or rent |
| 7. Digital Life | Email, Apple/Google account, passwords manager, social media wishes |
| 8. Your Wishes | Burial or cremation, memorial preferences, organ donation |
| 9. Messages | A personal message to your executor, your spouse, your children |

**Part One Extended — Complex Estates & Operations** (Chapters 10–13)

These chapters go deeper. Chapter 10 is for estates with business entities, trusts, or complex investment structures. Chapters 11–13 document how your home, vehicles, and digital world work so any family member can take over. Skip any chapter that does not apply to you.

| Chapter | What It Covers |
|---------|---------------|
| 10. Advanced Estate Planning | LLCs, trusts, buy-sell agreements, life insurance schedule, retirement account beneficiary designations, private equity, cryptocurrency, charitable vehicles, gift history, estate tax planning |
| 11. Your Main Home | HVAC, thermostat, alarm system, electrical panel, water and gas shutoffs, water heater, internet, smart home, appliances, sump pump, generator, irrigation, HOA, utilities, all service providers, maintenance schedule |
| 12. Vehicles & Other Property | Each vehicle (title, insurance, maintenance, keys), roadside assistance, garage door operation, boats/RVs/motorcycles, storage units |
| 13. Digital Accounts & Media Systems | Password manager emergency access, account inventory, cloud storage, photo library, all subscriptions to cancel, cryptocurrency executor instructions, loyalty programs, social media legacy instructions, how to operate the main TV and switch inputs, streaming service setup, sound system operation, AV receiver, gaming consoles, physical media collections |

---

**Part Two — Your History** (Chapters 14–15)

These chapters are different. There are no right answers. Write as much or as little as you like. You can come back and add to them any time.

| Chapter | What It Covers |
|---------|---------------|
| 14. Your Life Story | Your childhood, parents, education, career, marriage, hardest times, proudest moments, what you want to be remembered for |
| 15. Family History & Lore | Where your family came from, immigration stories, grandparents, family traditions, heirlooms, values, what you want future generations to know |

These two chapters are an extraordinary gift to your family. Once you are gone, this information cannot be recovered from anywhere else.

---

### Navigating the Interview

**Left sidebar:** Shows all 11 chapters with a status indicator next to each:
- **✓ (green)** — all questions in this chapter answered
- **● (gold)** — chapter started but not finished
- **○ (grey)** — not yet started

Click any chapter title to jump straight to it. You do not have to go in order.

The progress bar at the bottom of the sidebar shows your overall completion percentage.

**Main area:** Shows one question at a time. Above each question you can see which chapter you are in and how far through it you are (e.g. "Chapter 3 · Question 2 of 8").

**Navigation buttons** at the bottom of the screen:
- **← Previous** — go back one question
- **Save & Continue →** — save your answer and move to the next question
- **Skip →** — leave this question blank for now and come back later

You can also press **Enter** to submit a single-line answer.

---

### Answering Questions

Most questions have a single-line text box. Type your answer and press **Save & Continue** or press the **Enter** key on your keyboard.

Some questions — particularly in the Messages and History chapters — have a larger text area for longer answers. Click anywhere inside it and type freely. These are designed for narrative answers. Take as much space as you need.

Questions marked **Required** should be answered before you export your PDF. The app will still let you skip them, but your executor will need this information.

Questions marked **Sensitive** contain private information (such as account numbers). They are saved in the same local file as all other answers and never sent anywhere.

---

### Voice Input

Next to the answer box there is a microphone button. Click it, speak your answer, and the app will type it for you. You can then edit what it wrote before saving.

Voice input requires a working microphone and an internet connection for best results.

**To mute the app's voice** (the British female voice that reads questions aloud), click the speaker icon in the top-right corner of the screen. The icon will show a line through it when muted. Your preference is remembered until you change it.

---

### Chapter Complete

When you answer the last question in a chapter, the app shows a completion screen with a tick, a brief message, and your updated progress. Click **Continue to Next Chapter** to move on, or **Close** if you need to stop for the day.

---

## Saving Your Progress

The app saves automatically every time you click **Save & Continue**. You do not need to press Ctrl+S or do anything else.

If you close the app in the middle of a question, your last saved answer is preserved. The next time you open the app and choose your profile, you will return to exactly where you left off.

---

## Exporting Your Estate Plan as a PDF

When you are ready to produce a printed document, click **Export PDF** in the lower-left corner of the sidebar.

A window will open asking where to save the file. Choose a location you will remember — your Desktop is fine for now — type a filename if you want to change it, and click **Save**.

The PDF is created in a few seconds. It contains:
- A cover page with your name, completion percentage, and the date exported
- Page 2: emergency contacts — executor, backup executor, spouse, attorney, advisor, doctor — filled in from your answers
- One section per chapter with each question and your answer
- Questions you have not answered yet shown as *[Not yet answered]* so your executor knows what is still missing
- A confidentiality notice and your name on every page

**What to do with the PDF:**

Print two copies. Store one in a fireproof safe or lockbox. Give the second copy to your executor in a sealed envelope. Write on the envelope: *Open only if I am incapacitated or deceased.*

Each time you make significant changes — a new will, a new account, a property sale — export a fresh PDF and replace the old copies.

---

## Switching Between Family Members

To switch to a different person's profile, click **Switch Profile** in the lower-left sidebar. This returns you to the profile list without closing the app.

---

## Approaching the Advanced Chapters (10–13)

### Chapter 10 — Advanced Estate Planning

This chapter is for people with business ownership, trusts, multiple investment accounts, or other complexity. If your estate is straightforward — a will, a bank account, a house — you can skip most of it.

If you have complexity, this is the chapter that will save your family the most money and stress. A few things to know:

- **Beneficiary designations override your will.** Who you named on your IRA and life insurance years ago is who gets the money — regardless of what your will says. If those were set up before a divorce, a death, or the birth of a child, they may be wrong. This chapter asks you to document what is currently on file and when you last reviewed it.
- **Trust funding is commonly missed.** Many people have a living trust but their house, bank accounts, or investment accounts were never retitled into it. An unfunded trust does not control those assets. Document here whether funding has been completed.
- **Seed phrases for cryptocurrency should never be written in this document.** Only write *where* the seed phrase is physically stored. The seed phrase itself should be on paper or engraved steel in a fireproof safe or safety deposit box — never photographed, emailed, or stored digitally.
- **If you have a buy-sell agreement for a business**, note both the agreement document and the life insurance policy that funds it. If the policy has lapsed, the agreement may be unenforceable.

Work through this chapter with your estate attorney's last memo in front of you if you have one.

### Chapter 11 — Your Main Home

This chapter turns your home into a documented system rather than tribal knowledge. The goal: anyone who needs to look after your home — your spouse, a child, a property manager, an executor — can do so without guessing or calling around.

Work through it room by room and system by system. Most answers you already know; you just have never written them down. A few tips:

- For the HVAC filter: the size is printed on the edge of the filter that is currently installed. Write it down now.
- For the alarm: do not write the code in the app — write "see fireproof safe" and put the code document there.
- For service providers: if you have not needed a plumber in years, ask your neighbours who they use or check your records. Having someone on file before an emergency is worth more than finding one during one.
- For the maintenance schedule: think about what you do each spring, each fall, and monthly. Write those tasks down — not for yourself, but for whoever is managing the house if you cannot.

### Chapter 12 — Vehicles & Other Property

Document each vehicle as if you were handing it to someone who has never driven it and does not know where any of the paperwork is. The most commonly missing items are:

- Where the title is (especially if there is a lender — the title is at the bank, not in your glove compartment)
- How to open the garage door manually during a power failure
- Where the roadside assistance card is and what it covers

For boats and RVs: note the storage facility contact and contract, seasonal winterization requirements, and whether the trailer has its own registration.

### Chapter 13 — Digital Accounts & Media Systems

**Password manager emergency access** is the single most important action you can take for your digital estate. Set it up before completing this chapter:

- **1Password**: Share → Emergency Kit → give to executor, or set up Emergency Access in account settings.
- **Bitwarden**: Emergency Access under Settings — designate a trusted contact with a time delay.
- **LastPass**: Emergency Access feature under Account Settings.
- **No password manager**: Write account credentials on paper, seal in an envelope, store in your fireproof safe. Rebuild with a password manager when you can.

For the media and audio-visual sections: walk through the living room and write down exactly what each remote does, what order you turn things on, and which HDMI input is which device. This is often the most frustrating thing for a family member who needs to use a system they have never touched.

---

## Approaching the History Chapters (14–15)

The life story and family history chapters are different from the estate plan. A few suggestions:

- **There is no wrong answer.** Write the way you would speak. No formal language needed.
- **Short is fine.** One sentence about your grandparents is better than nothing at all.
- **Come back to it.** These chapters are designed to be filled in over many sessions — a few minutes here, half an hour there, over months or even years. Start with whatever you remember most easily.
- **Think about who will read this.** Your great-grandchildren will one day read these words. Include things that feel obvious to you — what your parents were like, what the neighbourhood felt like growing up, what your work was.
- **Uncertainty is fine to write down.** If you are not sure of a fact, write what you think you know and note that you are uncertain. That is still valuable. You can also note who in the family might know more.

---

## Backing Up Your Answers

Your answers are saved in a file inside the Estate OS folder, in a subfolder called `profiles`. The file is named after you — for example, `Margaret.json`.

To back it up:
1. Open the Estate OS folder.
2. Open the `behaviors` folder inside it.
3. Open `estate-interview` inside that.
4. Open `profiles` inside that.
5. Copy the file with your name to a USB drive, or drag it into your Google Drive or OneDrive folder.

To restore it on another computer, copy the file into the same `profiles` folder location on the new machine.

---

## Frequently Asked Questions

**Can I use this without speaking at all?**
Yes. The microphone button is entirely optional. Type your answers normally. The app's own voice can be muted with the speaker button in the top-right corner.

**What if I make a mistake in an answer?**
Click the chapter in the left sidebar, or use the **← Previous** button, to go back to that question. Type over your previous answer and click **Save & Continue**. Your new answer replaces the old one.

**Can two people use this on the same computer?**
Yes, but not at the same time. Each person has their own profile and their answers are completely separate. One person finishes and closes the app, then the next person opens it and selects their own name from the list.

**Is my information private?**
Yes. Your answers are saved only on this computer. Nothing is sent to the internet. The file is as secure as your computer is. If you want extra protection, keep the Estate OS folder inside an encrypted storage vault.

**What if I forget to fill something in?**
The PDF marks every unanswered question as *[Not yet answered]*. Your executor will know what is missing. Re-open the app, go to that chapter, fill in the answer, and export a new PDF.

**Do I have to finish in one sitting?**
No — that is the whole point. Most people take several sessions across days or weeks. Some fill in the estate plan chapters over a weekend and return to the life story chapters over months. Stop any time. The app saves everything automatically and will be exactly where you left it.

**The app opened but looks very small / very large on my screen.**
Right-click the `launch_estate_interview.bat` file, choose **Properties**, click the **Compatibility** tab, then click **Change high DPI settings**. Tick **Override high DPI scaling behaviour** and choose **Application** from the dropdown. Click OK, then try opening the app again.

---

*Estate OS — Private | Local | Secure*
