// Estate Capture — Google Apps Script Backend
// Paste this into Code.gs in your Google Apps Script project

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Estate Capture')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function saveCapture(content, filename) {
  try {
    // Look for MHH-Inbox folder in Google Drive
    var folders = DriveApp.getFoldersByName('MHH-Inbox');
    var folder;

    if (folders.hasNext()) {
      folder = folders.next();
    } else {
      // Create it if it doesn't exist yet
      folder = DriveApp.createFolder('MHH-Inbox');
    }

    // Save the .md file
    folder.createFile(filename, content, MimeType.PLAIN_TEXT);
    return 'saved';

  } catch(e) {
    throw new Error('Could not save to Google Drive: ' + e.message);
  }
}
