/**
 * GeM Tender Auto-Tracker for Nikom InfraSolutions
 * Google Apps Script — runs inside the spreadsheet, no proxy needed.
 *
 * Setup:  Open sheet → Extensions → Apps Script → paste this → save.
 *         Run setupDailyTrigger() once.  Done.
 */

// ─── CONFIG ────────────────────────────────────────────────────────────────
var SHEET_NAME = "Live GeM Bids";
var DATA_START_ROW = 5; // Rows 1-3 metadata, row 4 headers, row 5 first data

var SEARCH_TERMS = [
  "precision air conditioning", "precision air conditioner",
  "chiller", "water cooled chiller", "screw chiller",
  "centrifugal chiller", "cooling system", "data centre cooling",
  "mini data centre",
  "HPC cluster", "GPU compute",
  "O&M HVAC", "AMC chiller", "AMC precision air conditioner", "CAMC HVAC",
  "VRF", "VRV", "ductable AC", "HVAC", "cleanroom HVAC",
  "online UPS", "UPS", "DG set", "diesel generator", "busduct",
  "fire detection", "fire alarm", "fire suppression",
  "smart rack", "server rack", "structured cabling"
];

// ─── CLASSIFIER (mirrors gem_classifier.py) ────────────────────────────────
var GROUP_RULES = [
  {
    label: "7 Fire detection AMC", role: "Direct bidder",
    match: [/fire\s+detect/i, /fire\s+alarm/i, /fire\s+hydrant/i,
            /fire\s+sprinkler/i, /fire\s+suppress/i, /fire\s+fight/i,
            /fire\s+extinguish/i,
            /(?:amc|cmc|camc|o\s*&?\s*m).*fire/i,
            /fire.*(?:amc|cmc|camc|o\s*&?\s*m)/i],
    exclude: []
  },
  {
    label: "3 HPC – partner only",
    role: "Site-prep / power / cooling partner to IT bidder",
    match: [/\bhpc\b/i, /high\s*performance\s*comput/i,
            /gpu\s+compute/i, /gpu\s+cluster/i, /supercomput/i],
    exclude: []
  },
  {
    label: "4 Chiller / HVAC O&M & AMC", role: "Direct bidder",
    match: [
      /\b(?:amc|cmc|camc|comprehensive\s+(?:annual\s+)?maintenance)\b.*(?:hvac|chiller|air\s*condition|precision\s+a\/?c|vrf|vrv|cooling)/i,
      /(?:hvac|chiller|air\s*condition|precision\s+a\/?c|vrf|vrv|cooling).*\b(?:amc|cmc|camc|comprehensive\s+(?:annual\s+)?maintenance)\b/i,
      /\bo\s*&\s*m\b\s+(?:of\s+)?(?:hvac|chiller|air\s*condition|cooling|precision)/i,
      /(?:hvac|chiller|air\s*condition|cooling|precision).*\bo\s*&\s*m\b/i,
      /(?:repair|overhaul|servicing).*(?:chiller|precision\s+a\/?c|hvac|air\s*condition)/i,
      /(?:chiller|precision\s+a\/?c|hvac|air\s*condition).*(?:repair|overhaul|servicing)/i,
      /\bmaintenance\b.*(?:chiller|hvac|air\s*condition|precision|cooling\s+plant)/i,
      /\boperation\b.*\bmaintenance\b.*(?:hvac|chiller|cooling)/i
    ],
    exclude: []
  },
  {
    label: "1 Best fit – cooling & power", role: "Direct bidder",
    match: [
      /precision\s+air\s*condition/i, /precision\s+a\/?c/i,
      /(?:data\s+cent(?:re|er)|server\s+room).*(?:cool|power|infra)/i,
      /(?:cool|power|infra).*(?:data\s+cent(?:re|er)|server\s+room)/i,
      /mini\s+data\s+cent/i,
      /integrated.*cooling\s+solution/i,
      /(?:chilled[\s-]*water|water[\s-]*cooled).*(?:chiller|plant|system|hvac|piping)/i,
      /chilled[\s-]*water\s+(?:hvac|plant)/i,
      /(?:screw|centrifugal|scroll)\s+chiller/i,
      /(?:100|150|200|250|300|400|500|600)\s*tr\b.*chiller/i,
      /chiller\s+(?:plant|package|system)/i,
      /cooling\s+(?:system|solution|tower|plant)/i,
      /comprehensive\s+amc.*(?:ups|online\s+ups)/i,
      /(?:comprehensive|manpower).*(?:cmc|ups|precision)/i,
      /(?:cmc|amc).*(?:ups\s+system|precision\s+air)/i
    ],
    exclude: [
      /(?:amc|cmc|camc|o\s*&?\s*m|repair|overhaul|maintenance).*(?:hvac(?!\s*plant)|(?<!precision\s)air\s*condition(?!er))/i
    ]
  },
  {
    label: "8 Racks & cabling", role: "Direct bidder",
    match: [/structured\s+cabl/i, /server\s+rack/i, /network\s+rack/i,
            /smart\s+rack.*server/i, /server.*smart\s+rack/i,
            /rack.*cable/i, /cable.*rack/i,
            /lan\s+cabl/i, /fibre?\s+cabl/i],
    exclude: []
  },
  {
    label: "2 Quick win", role: "Direct bidder",
    match: [
      /smart\s+rack/i,
      /compact.*(?:chiller|water\s+chiller)/i,
      /industrial\s+chiller/i,
      /\b(?:5|7\.?5|10|15)\s*tr\b.*(?:chiller|water\s+chiller)/i,
      /chiller\s+(?:5|7\.?5|10|15)\s*ton/i
    ],
    exclude: [/\b(?:amc|cmc|camc)\b/i, /\bo\s*&\s*m\b/i,
              /\b(?:repair|overhaul|maintenance)\b/i,
              /(?:100|150|200|250|300|400|500|600)\s*tr\b/i]
  },
  {
    label: "5 HVAC & VRF supply / install", role: "Direct bidder",
    match: [
      /(?:sitc|supply.*install|erection.*commission).*(?:hvac|vrf|vrv|ductable|ducted|air\s*condition|chiller|ahu|cleanroom)/i,
      /(?:hvac|vrf|vrv|ductable|ducted).*(?:sitc|supply.*install|erection.*commission)/i,
      /execution.*hvac\s+work/i, /hvac.*(?:works?|system)/i,
      /(?:vrf|vrv)\s+(?:systems?|units?|outdoor|indoor)/i,
      /(?:vrf|vrv)\b.*(?:compensat|copper\s+pip|install)/i,
      /ductable\s+a\/?c/i,
      /cleanroom.*(?:hvac|panel|facility)/i, /modular\s+cleanroom/i
    ],
    exclude: [/\b(?:amc|cmc|camc)\b/i, /\bo\s*&\s*m\b/i,
              /\b(?:repair|overhaul|maintenance)\b/i, /chilled[\s-]*water/i]
  },
  {
    label: "6 UPS / DG / electrical", role: "Direct bidder",
    match: [
      /\bups\b.*\d+\s*kva/i, /\d+\s*kva\b.*\bups\b/i,
      /(?:online\s+)?ups\b(?!.*(?:chiller|hvac|precision|cooling))/i,
      /\bups\s+(?:system|battery|batteries)/i,
      /(?:diesel|dg)\s+(?:gen|set)/i, /\bdg\s+set/i,
      /generator\s+set/i, /\bgenset\b/i,
      /(?:amc|cmc).*(?:dg\s+set|generator)/i,
      /(?:dg\s+set|generator).*(?:amc|cmc)/i,
      /busduct/i, /bus\s*duct/i,
      /batter(?:y|ies).*ups/i, /ups.*batter(?:y|ies)/i,
      /(?:lt|ht)\s+panel/i, /transformer/i,
      /\bkva\b.*(?:dg|generator)/i, /(?:dg|generator).*\bkva\b/i,
      /rental.*(?:dg|generator)/i
    ],
    exclude: [/comprehensive\s+amc.*ups/i,
              /(?:manpower|\bcmc\b).*(?:ups\s+system|precision)/i]
  }
];

function classifyBid(title, scope) {
  var text = (title + " " + (scope || "")).toLowerCase();
  for (var i = 0; i < GROUP_RULES.length; i++) {
    var rule = GROUP_RULES[i];
    var excluded = false;
    for (var e = 0; e < rule.exclude.length; e++) {
      if (rule.exclude[e].test(text)) { excluded = true; break; }
    }
    if (excluded) continue;
    for (var m = 0; m < rule.match.length; m++) {
      if (rule.match[m].test(text)) {
        var role = rule.role;
        if (rule.label === "8 Racks & cabling" && /server/i.test(text)) {
          role = "Rack portion / partner with server OEM";
        }
        return { group: rule.label, role: role };
      }
    }
  }
  return { group: "1 Best fit – cooling & power", role: "Direct bidder" };
}

var RELEVANCE_PATTERNS = [
  /ups\b/i, /precision\s+a/i, /chiller/i, /hvac/i,
  /cooling/i, /dg\s+set/i, /diesel\s+gen/i, /genset/i,
  /data\s+cent/i, /server\s+room/i, /smart\s+rack/i,
  /structured\s+cabl/i, /fire\s+detect/i, /fire\s+alarm/i,
  /fire\s+suppress/i, /fire\s+hydrant/i, /hpc\b/i,
  /gpu\s+cluster/i, /vrf\b/i, /vrv\b/i, /ductable/i,
  /air\s*condition/i, /ahu\b/i, /busduct/i, /transformer/i,
  /lt\s+panel/i, /generator/i, /cleanroom/i,
  /network\s+rack/i, /server\s+rack/i,
  /bms\b/i, /building\s+management/i
];

function isNikomRelevant(title, scope) {
  var text = (title + " " + (scope || "")).toLowerCase();
  for (var i = 0; i < RELEVANCE_PATTERNS.length; i++) {
    if (RELEVANCE_PATTERNS[i].test(text)) return true;
  }
  return false;
}

// ─── GeM API ───────────────────────────────────────────────────────────────

function getCsrfToken_() {
  var res = UrlFetchApp.fetch("https://bidplus.gem.gov.in/all-bids", {
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
  });
  var headers = res.getAllHeaders();
  var cookies = headers["Set-Cookie"] || headers["set-cookie"] || [];
  if (typeof cookies === "string") cookies = [cookies];
  for (var i = 0; i < cookies.length; i++) {
    var match = cookies[i].match(/csrf_gem_cookie=([^;]+)/);
    if (match) return match[1];
  }
  // Fallback: try to extract from response body
  var body = res.getContentText();
  var metaMatch = body.match(/name="csrf_bd_gem_nk"[^>]*value="([^"]+)"/);
  if (metaMatch) return metaMatch[1];
  return "";
}

function fetchGemBids_(term, csrf, page) {
  var payload = {
    "csrf_bd_gem_nk": csrf,
    "payload": JSON.stringify({
      page: page || 1,
      param: { searchBid: term },
      filter: { bidStatusType: "ongoing_bids", sort: "Bid-Start-Date-Latest" }
    })
  };

  try {
    var res = UrlFetchApp.fetch("https://bidplus.gem.gov.in/all-bids-data", {
      method: "post",
      payload: payload,
      muteHttpExceptions: true,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://bidplus.gem.gov.in/all-bids",
        "Cookie": "csrf_gem_cookie=" + csrf
      }
    });
    var data = JSON.parse(res.getContentText());
    return (data.response && data.response.response && data.response.response.docs) || [];
  } catch (e) {
    Logger.log("GeM fetch error for '" + term + "': " + e.message);
    return [];
  }
}

// ─── DATE HELPERS ──────────────────────────────────────────────────────────

function formatGemDate_(raw) {
  if (!raw) return "";
  try {
    var d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var dd = ("0" + d.getDate()).slice(-2);
    var hh = ("0" + d.getHours()).slice(-2);
    var mm = ("0" + d.getMinutes()).slice(-2);
    return dd + "-" + months[d.getMonth()] + "-" + d.getFullYear() + " " + hh + ":" + mm;
  } catch (e) {
    return raw;
  }
}

function daysLeft_(closingDateStr) {
  if (!closingDateStr) return "";
  try {
    var months = {Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};
    var parts = closingDateStr.split(/[\s-:]+/);
    if (parts.length < 4) return "";
    var d = new Date(parseInt(parts[2]), months[parts[1]], parseInt(parts[0]),
                     parseInt(parts[3]), parseInt(parts[4]) || 0);
    if (isNaN(d.getTime())) return "";
    var diff = Math.ceil((d - new Date()) / 86400000);
    return diff;
  } catch (e) { return ""; }
}

// ─── MAIN SYNC ─────────────────────────────────────────────────────────────

function syncGemTenders() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    Logger.log("ERROR: Sheet '" + SHEET_NAME + "' not found");
    return;
  }

  // Read existing bid numbers for dedup (column B)
  var lastRow = sheet.getLastRow();
  var existingBids = {};
  if (lastRow >= DATA_START_ROW) {
    var bidCol = sheet.getRange(DATA_START_ROW, 2, lastRow - DATA_START_ROW + 1, 1).getValues();
    for (var i = 0; i < bidCol.length; i++) {
      if (bidCol[i][0]) existingBids[bidCol[i][0].toString().trim()] = true;
    }
  }
  Logger.log("Existing bids in sheet: " + Object.keys(existingBids).length);

  // Get CSRF token
  var csrf = getCsrfToken_();
  if (!csrf) {
    Logger.log("ERROR: Could not get CSRF token from GeM");
    return;
  }
  Logger.log("Got CSRF token");

  // Discover bids across all search terms
  var allDocs = {};
  for (var t = 0; t < SEARCH_TERMS.length; t++) {
    var term = SEARCH_TERMS[t];
    for (var p = 1; p <= 3; p++) {
      var docs = fetchGemBids_(term, csrf, p);
      for (var d = 0; d < docs.length; d++) {
        var doc = docs[d];
        var bidNumArr = doc.b_bid_number || [];
        var bidNum = bidNumArr[0] || "";
        if (bidNum && !allDocs[bidNum]) {
          allDocs[bidNum] = doc;
        }
      }
      if (docs.length < 10) break; // no more pages
      Utilities.sleep(200); // rate limit
    }
  }

  var totalFound = Object.keys(allDocs).length;
  Logger.log("Total unique bids from GeM: " + totalFound);

  // Filter, classify, and build rows
  var newRows = [];
  var bidNums = Object.keys(allDocs);
  for (var b = 0; b < bidNums.length; b++) {
    var bidNum = bidNums[b];
    if (existingBids[bidNum]) continue; // already in sheet

    var doc = allDocs[bidNum];
    var catArr = doc.bd_category_name || doc.b_category_name || [];
    var title = catArr[0] || ("GeM Bid " + bidNum);

    if (!isNikomRelevant(title, "")) continue;

    var cls = classifyBid(title, "");

    var minArr = doc.ba_official_details_minName || [];
    var deptArr = doc.ba_official_details_deptName || [];
    var buyer = (minArr[0] && minArr[0] !== "NA") ? minArr[0] :
                (deptArr[0] && deptArr[0] !== "NA") ? deptArr[0] : "Government of India";

    var endArr = doc.final_end_date_sort || [];
    var closingRaw = endArr[0] || "";
    var closingFormatted = formatGemDate_(closingRaw);

    var bIdArr = doc.b_id || [];
    var numericId = bIdArr[0] || doc.id || "";
    var docLink = numericId ? "https://bidplus.gem.gov.in/showbidDocument/" + numericId : "";

    var days = daysLeft_(closingFormatted);
    if (typeof days === "number" && days < 0) continue; // already expired

    var today = new Date();
    var dd = ("0" + today.getDate()).slice(-2);
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var dateStr = dd + "-" + months[today.getMonth()] + "-" + today.getFullYear();

    // Row: #, Bid number, Scope, Closing date, Doc link, Days left,
    //       Buyer, Group, Nikom role, Eligibility, Est value, EMD,
    //       Experience, Min turnover, Remarks
    newRows.push([
      "",             // # (auto-number later)
      bidNum,         // GeM bid number
      title,          // Scope of work
      closingFormatted, // Closing date & time
      docLink,        // Bid document link
      days,           // Days left
      buyer,          // Buyer (Ministry / Dept)
      cls.group,      // Group
      cls.role,       // Nikom role
      "Not started",  // Eligibility
      "",             // Est. value
      "",             // EMD
      "",             // Past experience
      "",             // Min. turnover
      "Auto-discovered " + dateStr  // Remarks
    ]);
  }

  Logger.log("New Nikom-relevant bids to add: " + newRows.length);

  if (newRows.length > 0) {
    // Auto-number
    var startNum = lastRow - DATA_START_ROW + 2; // next serial number
    for (var r = 0; r < newRows.length; r++) {
      newRows[r][0] = startNum + r;
    }

    // Append
    sheet.getRange(lastRow + 1, 1, newRows.length, 15).setValues(newRows);
    Logger.log("Appended " + newRows.length + " new bids");

    // Make doc links clickable
    for (var r = 0; r < newRows.length; r++) {
      if (newRows[r][4]) {
        var cell = sheet.getRange(lastRow + 1 + r, 5);
        cell.setFormula('=HYPERLINK("' + newRows[r][4] + '","View doc")');
      }
    }
  }

  // Update "Days left" for ALL rows
  updateDaysLeft_(sheet);

  Logger.log("SYNC COMPLETE — Found: " + totalFound + ", New: " + newRows.length);
}

function updateDaysLeft_(sheet) {
  var lastRow = sheet.getLastRow();
  if (lastRow < DATA_START_ROW) return;

  // Column D = closing date, Column F = days left
  var numRows = lastRow - DATA_START_ROW + 1;
  var closingDates = sheet.getRange(DATA_START_ROW, 4, numRows, 1).getValues();
  var daysCol = [];
  for (var i = 0; i < closingDates.length; i++) {
    var val = closingDates[i][0] ? closingDates[i][0].toString() : "";
    daysCol.push([daysLeft_(val)]);
  }
  sheet.getRange(DATA_START_ROW, 6, daysCol.length, 1).setValues(daysCol);
  Logger.log("Updated Days left for " + daysCol.length + " rows");
}

// ─── TRIGGER SETUP ─────────────────────────────────────────────────────────

function setupDailyTrigger() {
  // Delete existing triggers for this function
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "syncGemTenders") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  // Create new daily trigger at 9:00 AM IST (timezone set in project)
  ScriptApp.newTrigger("syncGemTenders")
    .timeBased()
    .atHour(9)
    .everyDays(1)
    .inTimezone("Asia/Kolkata")
    .create();
  Logger.log("Daily trigger set for 9:00 AM IST");
}

// ─── MENU ──────────────────────────────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Nikom Tender Bot")
    .addItem("Sync now", "syncGemTenders")
    .addItem("Update Days Left only", "updateDaysLeftManual")
    .addItem("Setup daily 9 AM trigger", "setupDailyTrigger")
    .addToUi();
}

function updateDaysLeftManual() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (sheet) updateDaysLeft_(sheet);
}
