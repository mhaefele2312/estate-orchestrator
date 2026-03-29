/**
 * Estate OS — Snapshot Button for Google Sheet (Phase 1, Item 12)
 * ================================================================
 * Adds a custom menu to the MHH-Ops-Ledger Google Sheet with a
 * "Take Snapshot" option. When clicked, it exports all tabs as CSVs
 * to the Source-of-Truth folder in Google Drive.
 *
 * SETUP:
 *   1. Open the MHH-Ops-Ledger Google Sheet
 *   2. Extensions > Apps Script
 *   3. Paste this code into Code.gs
 *   4. Save and reload the sheet
 *   5. A new "Estate OS" menu will appear in the menu bar
 *
 * NOTE: This is the Google Apps Script version of snapshot.py.
 * It only writes to Google Drive (no Gold vault or Obsidian copies).
 * Run snapshot.py on the laptop for the full three-destination export.
 */

// ── Menu setup ─────────────────────────────────────────────────────────────

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Estate OS')
    .addItem('Take Snapshot (SOT)', 'takeSnapshot')
    .addSeparator()
    .addItem('About Estate OS', 'showAbout')
    .addToUi();
}

// ── Snapshot function ──────────────────────────────────────────────────────

function takeSnapshot() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

  // Find or create the Source-of-Truth folder
  var sotFolder = getOrCreateFolder('Estate Ops/Source-of-Truth');

  var exported = [];

  for (var i = 0; i < sheets.length; i++) {
    var sheet = sheets[i];
    var safeName = sheet.getName().replace(/\s+/g, '-').replace(/\//g, '-').toLowerCase();
    var filename = 'sot-MHH-' + today + '-' + safeName + '.csv';

    var csvContent = sheetToCsv(sheet);
    sotFolder.createFile(filename, csvContent, MimeType.CSV);
    exported.push(filename);

    // Update sot-latest-MHH.csv for the Raw Log tab
    if (sheet.getName().toLowerCase().replace(/\s/g, '') === 'rawlog') {
      var latestFiles = sotFolder.getFilesByName('sot-latest-MHH.csv');
      while (latestFiles.hasNext()) {
        latestFiles.next().setTrashed(true);
      }
      sotFolder.createFile('sot-latest-MHH.csv', csvContent, MimeType.CSV);
    }
  }

  // Show confirmation
  var ui = SpreadsheetApp.getUi();
  ui.alert(
    'Snapshot Complete',
    'Exported ' + exported.length + ' tab(s) to Source-of-Truth folder:\n\n' +
    exported.join('\n') +
    '\n\nDate: ' + today +
    '\n\nNote: For Gold vault + Obsidian copies, run snapshot.py on the laptop.',
    ui.ButtonSet.OK
  );
}

// ── Helper: convert sheet to CSV string ────────────────────────────────────

function sheetToCsv(sheet) {
  var data = sheet.getDataRange().getValues();
  var csv = '';

  for (var i = 0; i < data.length; i++) {
    var row = [];
    for (var j = 0; j < data[i].length; j++) {
      var cell = data[i][j] === null ? '' : String(data[i][j]);
      // Escape quotes and wrap in quotes if contains comma, quote, or newline
      if (cell.indexOf(',') > -1 || cell.indexOf('"') > -1 || cell.indexOf('\n') > -1) {
        cell = '"' + cell.replace(/"/g, '""') + '"';
      }
      row.push(cell);
    }
    csv += row.join(',') + '\n';
  }

  return csv;
}

// ── Helper: get or create nested folder path ───────────────────────────────

function getOrCreateFolder(path) {
  var parts = path.split('/');
  var folder = DriveApp.getRootFolder();

  for (var i = 0; i < parts.length; i++) {
    var name = parts[i].trim();
    var folders = folder.getFoldersByName(name);
    if (folders.hasNext()) {
      folder = folders.next();
    } else {
      folder = folder.createFolder(name);
    }
  }

  return folder;
}

// ── About dialog ───────────────────────────────────────────────────────────

function showAbout() {
  var ui = SpreadsheetApp.getUi();
  ui.alert(
    'Estate OS',
    'Estate Operating System — MHH Ops Ledger\n\n' +
    'This sheet is the operational layer of Estate OS.\n' +
    'Voice captures are parsed and appended here.\n' +
    'Edit items freely, then take a snapshot when satisfied.\n\n' +
    'Snapshots go to: Google Drive > Estate Ops > Source-of-Truth\n' +
    'Run snapshot.py on laptop for Gold vault + Obsidian copies.',
    ui.ButtonSet.OK
  );
}
