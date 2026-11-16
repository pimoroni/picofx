import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps} from "../00_draw.js";
import {BOARD, VERSION} from "../01_looks.js";
import {firmwareHooks} from "../07_board.js";
import {CONNECT_ORDER, connectSteps} from "../18_drive.js";

// ---- firmware updates ----------------------------------------------------------------------------
// The Update available button beside the version in the page's header, and the sheet it opens. Once
// an FX drive is open, the page asks GitHub for the latest release and shows the button where the
// board's firmware is older. The sheet says what is new and how to flash the board's -with-libs
// .uf2. That image also rewrites the filesystem holding picofx and the board's libraries, so they
// match the new autofx, and it leaves the FX drive alone. build_editor.py takes this folder only for
// a board whose description has a release entry.
//
// A release whose notes have lines starting with the warning sign, or a GitHub warning alert, shows
// them first, in amber, and turns the button amber too.
//
// Tiny FX and Tiny FX W share this page, and their builds place the FX drive differently, so the
// wrong one empties it. The firmware writes catalogue.js beside the page, the wireless build's own
// version saying so, and the sheet offers the file for the build the catalogue names.

// Where the latest release is fetched from
var FIRMWARE_LATEST = "https://api.github.com/repos/pimoroni/picofx/releases/latest";

// The start every address the sheet links to must have. What localStorage holds can be written by
// any page opened from this computer, so nothing else is linked to
var FIRMWARE_HOME = "https://github.com/pimoroni/picofx/";

// The releases page, linked to where a release's own page address is missing or elsewhere
var FIRMWARE_RELEASES = FIRMWARE_HOME + "releases";

// The localStorage key that holds GitHub's answer and when it came. Every picker opened from a
// drive shares this browser's storage, so it holds the release as GitHub gave it, and each board
// finds its own files in that
var FIRMWARE_STORE = "fx-picker-firmware-release";

// How long a stored answer is used before GitHub is asked again
var FIRMWARE_FRESH_MS = 24 * 60 * 60 * 1000;

// The firmware the board runs, since the drive carries the picker made with it. A preview build is
// older than the release of its own number
var FIRMWARE_SHOWN = VERSION;
var FIRMWARE_RUNNING = FIRMWARE_SHOWN.split(" ")[0];
var FIRMWARE_PREVIEW = / preview$/.test(FIRMWARE_SHOWN);

// The warning sign, with the selector that asks for its colour form
var FIRMWARE_SIGN = "\u26a0\ufe0f";

// The status is idle, checking, done or failed, latest is the release as firmwareFrom() reads it,
// and open is whether the sheet is shown
var firmware = {status: "idle", latest: null, open: false};

// Whether version a is older than version b, each as dotted numbers
function firmwareOlder(a, b) {
  var x = a.split("."), y = b.split(".");
  for (var at = 0; at < Math.max(x.length, y.length); at++) {
    var difference = (parseInt(x[at], 10) || 0) - (parseInt(y[at], 10) || 0);
    if (difference) return difference < 0;
  }
  return false;
}

// Whether the board's firmware is older than the latest release
function firmwareBehind(latest) {
  if (!latest) return false;
  if (firmwareOlder(FIRMWARE_RUNNING, latest.version)) return true;
  return FIRMWARE_PREVIEW && !firmwareOlder(latest.version, FIRMWARE_RUNNING);
}

// Whether the latest release would bring the board to at least the version given, or null while the
// latest release is unknown
function firmwareCovers(version) {
  if (firmware.status !== "done" || !firmware.latest) return null;
  return firmwareBehind(firmware.latest) && !firmwareOlder(firmware.latest.version, version);
}
firmwareHooks.covers = firmwareCovers;

// What localStorage holds under FIRMWARE_STORE, or an empty object where it cannot be read
function firmwareStored() {
  try {
    return JSON.parse(localStorage.getItem(FIRMWARE_STORE)) || {};
  } catch (e) {
    return {};
  }
}

// Store GitHub's answer with the time it came. A browser that refuses is asked again next time
function firmwareStore(release) {
  try {
    localStorage.setItem(FIRMWARE_STORE, JSON.stringify({at: Date.now(), release: release}));
  } catch (e) {
  }
}

// The parts of GitHub's answer the page uses, which are all it stores
function firmwareTrimmed(release) {
  var assets = Array.isArray(release.assets) ? release.assets : [];
  return {tag_name: release.tag_name, body: release.body, html_url: release.html_url,
          assets: assets.map(function (asset) {
            return {name: asset.name, size: asset.size, browser_download_url: asset.browser_download_url};
          })};
}

// Whether an address is one of picofx's own pages on GitHub
function firmwareOurs(url) {
  return typeof url === "string" && url.indexOf(FIRMWARE_HOME) === 0;
}

// Whether the board's description has a wireless build apart from its plain one
function firmwareHasTwoBuilds() {
  return !!BOARD.release.wireless_files;
}

// The release file names this build is updated from, each by its CI name stem with its label. A
// board with two builds takes the set its catalogue names, and none where the catalogue does not
// say, since the other build's file empties the FX drive
function firmwareStems() {
  if (!firmwareHasTwoBuilds()) return BOARD.release.files;
  var wireless = typeof CATALOGUE === "object" && CATALOGUE.board ? CATALOGUE.board.wireless : null;
  if (wireless === true) return BOARD.release.wireless_files;
  if (wireless === false) return BOARD.release.files;
  return {};
}

// A release as the sheet shows it. Its files are this build's -with-libs images, as CI names them
function firmwareFrom(release) {
  var version = String(release.tag_name || "").replace(/^v/, "");
  var assets = Array.isArray(release.assets) ? release.assets : [];
  var stems = firmwareStems();
  var files = Object.keys(stems).map(function (stem) {
    var name = stem + "-v" + version + "-pimoroni-micropython-with-libs.uf2";
    var asset = assets.filter(function (one) { return one.name === name; })[0];
    if (!asset || !firmwareOurs(asset.browser_download_url)) return null;
    return {label: stems[stem], name: name, url: asset.browser_download_url,
            size: Number(asset.size) || 0};
  }).filter(Boolean);
  return {version: version, notes: String(release.body || ""), files: files,
          known: Object.keys(stems).length > 0,
          url: firmwareOurs(release.html_url) ? release.html_url : FIRMWARE_RELEASES};
}

// Take a release as the latest
function firmwareUse(release) {
  firmware.latest = firmwareFrom(release);
  firmware.status = "done";
}

// Fetch the latest release, or use the stored one while it is fresh. A failed fetch falls back on any
// stored release, however old, and otherwise shows nothing
async function checkFirmware() {
  if (firmware.status === "checking") return;
  var stored = firmwareStored();
  // Check if the stored answer is fresh enough to use without asking GitHub
  if (stored.release && Date.now() - stored.at < FIRMWARE_FRESH_MS) {
    firmwareUse(stored.release);
    draw();
    return;
  }
  firmware.status = "checking";
  try {
    var answer = await fetch(FIRMWARE_LATEST, {cache: "no-store"});
    if (!answer.ok) throw new Error(String(answer.status));
    var release = firmwareTrimmed(await answer.json());
    firmwareUse(release);
    // A release whose files CI has yet to upload is asked for again next time
    if (firmware.latest.files.length) firmwareStore(release);
  } catch (e) {
    if (stored.release) {
      firmwareUse(stored.release);
    } else {
      firmware.status = "failed";
      firmware.latest = null;
    }
  }
  draw();
}

// The warning marks a line of the notes can start or end with, as GitHub shows the sign or its
// :warning: code
var FIRMWARE_MARKS = "(?:[" + FIRMWARE_SIGN + "]|:warning:)";

// A line starting with the marks, after any list bullet or heading marks
var FIRMWARE_MARKED = new RegExp("^\\s*(?:[-*]\\s+|#+\\s+)?" + FIRMWARE_MARKS + "[\\s" + FIRMWARE_SIGN + "]*");

// The marks at the end of a line, which some warnings close with
var FIRMWARE_MARKS_AFTER = new RegExp("(?:\\s*" + FIRMWARE_MARKS + ")+\\s*$");

// The first line of a GitHub alert, whose quoted lines below it are its text. A warning or caution
// alert is a warning, and any other kind, such as a note, stays in the notes
var FIRMWARE_ALERT = /^\s*>\s*\[!(\w+)\]\s*$/;
var FIRMWARE_ALERT_WARNS = /^(?:warning|caution)$/i;

// A release's notes split into its warnings and the rest. A warning is a line that starts with the
// warning sign, or a GitHub warning alert, which a release keeps for a change a picker user must act
// on, such as one that empties the FX drive. Each warning loses its marks
function firmwareWarnings(notes) {
  var warnings = [], rest = [];
  // The lines of the alert being read, or null outside one
  var alert = null;
  function warn(text) {
    text = text.replace(FIRMWARE_MARKS_AFTER, "").trim();
    if (text) warnings.push(text);
  }
  function endAlert() {
    if (alert) warn(alert.join(" "));
    alert = null;
  }
  notes.replace(/\r\n/g, "\n").split("\n").forEach(function (line) {
    // Check if the line opens an alert, which ends any alert before it, or carries on a warning one
    var opens = FIRMWARE_ALERT.exec(line);
    if (opens) {
      endAlert();
      if (FIRMWARE_ALERT_WARNS.test(opens[1])) alert = [];
      else rest.push(line);
      return;
    }
    if (alert && /^\s*>/.test(line)) {
      alert.push(line.replace(/^\s*>\s?/, "").trim());
      return;
    }
    endAlert();
    var marked = FIRMWARE_MARKED.exec(line);
    if (marked) warn(line.slice(marked[0].length));
    else rest.push(line);
  });
  endAlert();
  return {warnings: warnings, rest: rest.join("\n")};
}

// Show the sheet
function openFirmware() {
  firmware.open = true;
  draw();
}

// Hide the sheet
function closeFirmware() {
  firmware.open = false;
  draw();
}

// A new element of the tag, with the class and text where they are given
function firmwareElement(tag, className, text) {
  var made = document.createElement(tag);
  if (className) made.className = className;
  if (text) made.textContent = text;
  return made;
}

// The button beside the version, made on its first showing and changed in place after, so the sheet
// gives focus back to it on closing
var firmwareButton = null;

// Draw the button beside the version, shown only where the board's firmware is older. It is drawn
// before the rest of the page, which measures the header to see if it fits on one line
function renderFirmwareButton() {
  var where = document.getElementById("firmware");
  var behind = firmware.status === "done" && firmwareBehind(firmware.latest);
  where.hidden = !behind;
  if (!behind) return;
  if (!firmwareButton) {
    firmwareButton = firmwareElement("button", "", "Update available");
    firmwareButton.type = "button";
    firmwareButton.setAttribute("aria-haspopup", "dialog");
    firmwareButton.onclick = openFirmware;
    where.appendChild(firmwareButton);
  }
  var version = firmware.latest.version;
  var heed = firmwareWarnings(firmware.latest.notes).warnings.length > 0;
  firmwareButton.className = heed ? "firmwarebutton hold" : "firmwarebutton";
  firmwareButton.title = heed ? "See the warning for firmware " + version + " and how to update."
                              : "See what's new in firmware " + version + " and how to update.";
}

// The elements that show a release's notes as text, never as HTML. A line starting - or * is a list
// item and one starting # a heading. A quoted line loses its quote mark, and an alert's first line,
// such as [!NOTE], becomes a heading of its kind
function firmwareNotes(text) {
  var shown = [];
  var list = null;
  text.replace(/\r\n/g, "\n").split("\n").forEach(function (line) {
    line = line.replace(/^\s*>\s?/, "");
    var alert = /^\s*\[!(\w+)\]\s*$/.exec(line);
    if (alert) {
      list = null;
      var kind = alert[1].toLowerCase();
      shown.push(firmwareElement("h4", "", kind.charAt(0).toUpperCase() + kind.slice(1)));
      return;
    }
    var item = /^\s*[-*]\s+(.*)$/.exec(line);
    if (item) {
      if (!list) shown.push(list = firmwareElement("ul"));
      list.appendChild(firmwareElement("li", "", firmwarePlain(item[1])));
      return;
    }
    list = null;
    var heading = /^\s*#+\s+(.*)$/.exec(line);
    if (heading) shown.push(firmwareElement("h4", "", firmwarePlain(heading[1])));
    else if (line.trim()) shown.push(firmwareElement("p", "", firmwarePlain(line)));
  });
  return shown;
}

// A line of the notes without its bold and code marks, and with each link's text alone. Underscores
// are left, since a name such as __init__ is written with them
function firmwarePlain(text) {
  return text.replace(/\*\*|`/g, "").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
}

// A link that opens in a new tab
function firmwareLink(text, url) {
  var link = firmwareElement("a", "", text);
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener";
  return link;
}

// A file's name and size, as the foot and a download's tip show it
function firmwareFileSays(file) {
  return file.name + ", " + (file.size / 1048576).toFixed(1) + " MB";
}

// The sheet's foot, which names the file beside its download, or says there is none to offer
function firmwareFoot(latest) {
  var foot = firmwareElement("div", "firmwaresheetfoot");
  var says = firmwareElement("div", "firmwarefootsays");
  foot.appendChild(says);
  var file = latest.files[0];
  if (!file) {
    says.append(latest.known ? "This release has no file for " + BOARD.name + " yet. "
                             : "This page could not tell which " + BOARD.name + " this is. ",
                firmwareLink("See the release", latest.url));
    return foot;
  }
  says.textContent = firmwareFileSays(file);
  // A new tab takes the download, so the page keeps its open drive
  var link = firmwareLink("Download for " + file.label, file.url);
  link.className = "firmwareget primary";
  foot.appendChild(link);
  return foot;
}

// The sheet, made on its first opening
var firmwareDialog = null;

// What the sheet was last filled with, so a draw that changes nothing leaves its scroll and focus
var firmwareFilled = null;

// Fill the sheet with the release's warnings, notes, steps and downloads
function fillFirmwareDialog(latest) {
  var bootloader = BOARD.release.bootloader_drive;

  var head = firmwareElement("div", "firmwaresheethead");
  var back = firmwareElement("button", "", "\u2039 Back");
  back.type = "button";
  back.onclick = closeFirmware;
  var title = firmwareElement("h2", "", "Firmware " + latest.version + " is available");
  title.id = "firmwareTitle";
  head.append(back, title);

  var body = firmwareElement("div", "firmwarescroll");
  body.appendChild(firmwareElement("p", "", "This " + BOARD.name + " runs " + FIRMWARE_SHOWN + "."));
  var split = firmwareWarnings(latest.notes);
  // Check if the release has warnings, which come first in amber, each behind the warning sign
  if (split.warnings.length) {
    var warned = firmwareElement("section", "firmwarewarnings");
    split.warnings.forEach(function (warning) {
      warned.appendChild(firmwareElement("p", "", FIRMWARE_SIGN + " " + firmwarePlain(warning)));
    });
    body.appendChild(warned);
  }
  var news = firmwareNotes(split.rest);
  if (news.length) {
    body.appendChild(firmwareElement("h3", "", "What's new"));
    news.forEach(function (one) { body.appendChild(one); });
  }
  body.appendChild(firmwareLink("Read the full release notes", latest.url));
  body.appendChild(firmwareElement("h3", "", "How to update"));
  var steps = firmwareElement("ol");
  ["Save to board, so your scenes are on the FX drive.",
   "Download the firmware below.",
   "Hold Boot, press " + BOARD.release.reset_button + ", then let go of Boot.",
   "Drag the .uf2 file onto the " + bootloader + " drive that appears.",
   "Once the board restarts, open PICKER.html from the FX drive again."
  ].forEach(function (step) { steps.appendChild(firmwareElement("li", "", step)); });
  body.appendChild(steps);
  // The board restarts as the copy ends, which a computer can report as a failed copy, and a copy
  // that really is cut short leaves the bootloader's drive showing
  body.appendChild(firmwareElement("p", "firmwarenote",
    "If your computer reports an error as the board restarts, check whether the " + bootloader +
    " drive is still showing. If it is, drag the file onto it again."));
  // A release with a warning may empty the FX drive, so it does not promise to keep it
  var warnings = split.warnings.length;
  body.appendChild(firmwareElement("p", "firmwarenote", warnings
    ? "Read the " + (warnings > 1 ? "warnings" : "warning") + " at the top before you start."
    : "Your FX drive and the files on it are kept."));

  firmwareDialog.replaceChildren(head, body, firmwareFoot(latest));
}

// Draw the sheet, or close it where it should not be shown
function renderFirmwareDialog() {
  if (!firmware.open || !firmware.latest) {
    if (firmwareDialog && firmwareDialog.open) firmwareDialog.close();
    return;
  }
  if (!firmwareDialog) {
    firmwareDialog = firmwareElement("dialog", "firmwaresheet");
    firmwareDialog.setAttribute("aria-labelledby", "firmwareTitle");
    // Focusable, so the sheet takes focus itself on opening. The browser would focus the Back
    // button, which shows its focus outline
    firmwareDialog.tabIndex = -1;
    // Escape closes the dialog itself, so the page's state follows it
    firmwareDialog.onclose = function () { if (firmware.open) closeFirmware(); };
    // A click on the backdrop lands on the dialog, and one inside it lands on its contents
    firmwareDialog.onclick = function (event) {
      if (event.target === firmwareDialog) closeFirmware();
    };
    document.body.appendChild(firmwareDialog);
  }
  var filling = JSON.stringify(firmware.latest);
  if (filling !== firmwareFilled) {
    var scroll = firmwareDialog.querySelector(".firmwarescroll");
    var scrolled = scroll ? scroll.scrollTop : 0;
    fillFirmwareDialog(firmware.latest);
    firmwareDialog.querySelector(".firmwarescroll").scrollTop = scrolled;
    firmwareFilled = filling;
  }
  if (!firmwareDialog.open) {
    firmwareDialog.querySelector(".firmwarescroll").scrollTop = 0;
    firmwareDialog.showModal();
    firmwareDialog.focus();
  }
}

addStep(drawSteps.before, DRAW_BEFORE, "firmware", renderFirmwareButton);
addStep(drawSteps.after, DRAW_AFTER, "firmware", renderFirmwareDialog);

// Check once a drive is open, since only then is the page known to be the one the board carries.
// The fetch is not awaited, so a slow network holds up no step after it
addStep(connectSteps, CONNECT_ORDER, "firmware", async function () {
  checkFirmware();
});
