/**
 * Estate OS -- Email Intake (Phase 4)
 * =====================================
 * Watches Gmail for emails labeled "estate-intake". For each one:
 *   1. Saves all attachments to G:/My Drive/Staging-Intake/Email-[date]/
 *   2. Saves a plain-text summary of the email itself as a .txt file
 *   3. Marks the email with label "estate-processed" so it is not re-run
 *
 * SETUP (one-time):
 *   1. In Gmail, create two labels: "estate-intake" and "estate-processed"
 *   2. Create Gmail filters to auto-apply "estate-intake" to estate emails
 *      (see GMAIL FILTER SETUP section below)
 *   3. Open Google Apps Script: https://script.google.com
 *   4. Create a new project named "Estate Email Intake"
 *   5. Paste this file into Code.gs
 *   6. Run setupTrigger() once from the Run menu to install the hourly trigger
 *   7. Authorize when prompted (needs Gmail + Drive access)
 *
 * GMAIL FILTER SETUP (do this in Gmail settings > Filters):
 *   Suggested filters -- apply label "estate-intake" to emails matching:
 *     - From: your insurance companies, banks, attorneys, HOAs
 *     - Subject contains: [estate], [property], invoice, statement, renewal
 *     - To: mhh.rosevale.west@gmail.com  (catches all estate account mail)
 *   Add more filters as you identify recurring estate email senders.
 *
 * RULES:
 *   - Never deletes emails. Labels only.
 *   - Never writes to Obsidian or Gold vault directly.
 *     Attachments land in Staging-Intake for manual routing via staging_router.py
 *   - Each run is idempotent: processed emails are skipped.
 */

// ── Configuration ─────────────────────────────────────────────────────────

var INTAKE_LABEL    = "estate-intake";
var PROCESSED_LABEL = "estate-processed";
var STAGING_FOLDER  = "Staging-Intake";  // subfolder name inside My Drive
var EMAIL_SUBFOLDER = "Email-Attachments";

// ── Main function (runs on trigger) ───────────────────────────────────────

function runEmailIntake() {
  var intakeLabel    = getOrCreateLabel_(INTAKE_LABEL);
  var processedLabel = getOrCreateLabel_(PROCESSED_LABEL);
  var stagingDir     = getOrCreateFolder_(STAGING_FOLDER);

  // Find today's email subfolder
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
  var emailDir = getOrCreateSubfolder_(stagingDir, EMAIL_SUBFOLDER + "-" + today);

  var threads = GmailApp.search("label:" + INTAKE_LABEL + " -label:" + PROCESSED_LABEL);

  if (threads.length === 0) {
    Logger.log("No new estate-intake emails found.");
    return;
  }

  Logger.log("Processing " + threads.length + " thread(s).");

  var saved = 0;
  var errors = 0;

  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    try {
      var messages = thread.getMessages();
      for (var j = 0; j < messages.length; j++) {
        var msg = messages[j];
        var subject = msg.getSubject() || "(no subject)";
        var from    = msg.getFrom();
        var date    = Utilities.formatDate(msg.getDate(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm");

        // Save email summary as .txt
        var summary = "From: " + from + "\n"
                    + "Date: " + date + "\n"
                    + "Subject: " + subject + "\n"
                    + "---\n"
                    + msg.getPlainBody();
        var summaryName = sanitize_(date + " -- " + subject) + ".txt";
        emailDir.createFile(summaryName, summary, MimeType.PLAIN_TEXT);
        saved++;

        // Save each attachment
        var attachments = msg.getAttachments();
        for (var k = 0; k < attachments.length; k++) {
          var att = attachments[k];
          var attName = sanitize_(att.getName());
          emailDir.createFile(att);
          Logger.log("  Saved attachment: " + attName);
          saved++;
        }
      }

      // Mark thread as processed
      thread.addLabel(processedLabel);
      thread.removeLabel(intakeLabel);

    } catch (e) {
      Logger.log("ERROR on thread " + i + ": " + e.toString());
      errors++;
    }
  }

  Logger.log("Done. Saved: " + saved + "  Errors: " + errors);
  Logger.log("Staging folder: " + emailDir.getUrl());
}

// ── One-time setup: install hourly trigger ─────────────────────────────────

function setupTrigger() {
  // Remove any existing triggers for this function first
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "runEmailIntake") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  // Install a new hourly trigger
  ScriptApp.newTrigger("runEmailIntake")
    .timeBased()
    .everyHours(1)
    .create();

  Logger.log("Hourly trigger installed for runEmailIntake.");
}

// ── Helpers ────────────────────────────────────────────────────────────────

function getOrCreateLabel_(name) {
  var label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
    Logger.log("Created label: " + name);
  }
  return label;
}

function getOrCreateFolder_(name) {
  var folders = DriveApp.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  }
  return DriveApp.createFolder(name);
}

function getOrCreateSubfolder_(parent, name) {
  var folders = parent.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  }
  return parent.createFolder(name);
}

function sanitize_(str) {
  // Replace characters not safe for filenames with underscores
  return str.replace(/[\/\\:*?"<>|]/g, "_").substring(0, 80);
}
