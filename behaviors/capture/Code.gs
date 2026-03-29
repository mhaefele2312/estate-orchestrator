/**
 * Estate OS — Capture App (Google Apps Script Backend)
 * =====================================================
 * Saves voice memo transcripts as .md files to Google Drive.
 *
 * SETUP:
 *   1. Create a new Google Apps Script project
 *   2. Paste this into Code.gs
 *   3. Paste Index.html into a new HTML file
 *   4. Deploy as web app (Execute as: Me, Access: Anyone with link)
 *   5. Add the deployed URL to Android home screen
 *
 * URL PARAMETERS:
 *   ?user=MHH  (default) — saves to MHH-Inbox folder
 *   ?user=HBS           — saves to HBS-Inbox folder (Phase 2)
 */

function doGet(e) {
  var html = HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Estate Capture')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

  // Pass user parameter to the page
  var user = (e && e.parameter && e.parameter.user) ? e.parameter.user.toUpperCase() : 'MHH';
  html.append('<script>var CAPTURE_USER = "' + user + '";</script>');

  return html;
}

function saveCapture(content, filename, user) {
  try {
    var folderName = (user || 'MHH') + '-Inbox';
    var folders = DriveApp.getFoldersByName(folderName);
    var folder;

    if (folders.hasNext()) {
      folder = folders.next();
    } else {
      folder = DriveApp.createFolder(folderName);
    }

    folder.createFile(filename, content, MimeType.PLAIN_TEXT);
    return 'saved';

  } catch(e) {
    throw new Error('Could not save to Google Drive: ' + e.message);
  }
}
