/*
This code receives web requests from the coinbot and populates a 'ledger' sheet
of balance and arithmetic return info over time.

Sheet headers:

Date,	Cash flow,	Cummulative contributions,	Balance,	Arithmetic return,	AR + 1,	Total Return

Sheet formulas:

Cumm. Cont. '=sum(B$2:B3)'  (starting 3rd row)
AR '=if(D4<>0,((D4-B4-D3)/D3),"")'  (starting 4th row)
AR + 1 '=E3 + 1' (starting 3rd row)
Total Return '=PRODUCT(F$3:F3) - 1' (starting 3rd row)

This code adapted from https://medium.com/@dmccoy/how-to-submit-an-html-form-to-google-sheets-without-google-forms-b833952cc175

Check it out for deployment instructions
*/

function doGet(e) {
  return handleResponse(e);
}

var SHEET_NAME = "ledger";
var SCRIPT_PROP = PropertiesService.getScriptProperties();
var DATE_INDEX = 1;
var CASHFLOW_INDEX = 2;
var BALANCE_INDEX = 4;
var SECRET = "put something here and in your config.yaml";

function handleResponse(e) {
  // we want a public lock, one that locks for all invocations
  var lock = LockService.getPublicLock();
  lock.waitLock(30000);  // wait 30 seconds before conceding defeat.

  try {
    var got_secret = e.parameter['secret'];
    if (got_secret !== SECRET) {
      throw new Error("not authorized: '" + JSON.stringify(e.parameter) + "'");
    }

    // next set where we write the data - you could write to multiple/alternate destinations
    var doc = SpreadsheetApp.openById(SCRIPT_PROP.getProperty("key"));
    var sheet = doc.getSheetByName(SHEET_NAME);

    // we'll assume header is in row 1 but you can override with header_row in GET/POST data
    var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    // loop until we find the first row with an empty date
    for (var nextRow = 1; sheet.getRange(nextRow, 1).getValue(); nextRow++) {
    }

    var balance = e.parameter['balance'];
    if (isNaN(balance)) {
      throw new Error("invalid balance of: " + balance);
    }
    sheet.getRange(nextRow, BALANCE_INDEX).setValue(balance);
    sheet.getRange(nextRow, DATE_INDEX).setValue(new Date());
    sheet.getRange(nextRow, CASHFLOW_INDEX).setValue(0);

    // return jsonp success results
    return ContentService
        .createTextOutput(JSON.stringify({"result":"success", "row": nextRow}))
        .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    // if error return this
    return ContentService
          .createTextOutput(JSON.stringify({"result":"error", "error": error}))
          .setMimeType(ContentService.MimeType.JSON);
  } finally { //release lock
    lock.releaseLock();
  }
}

function setup() {
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  SCRIPT_PROP.setProperty("key", doc.getId());
}
