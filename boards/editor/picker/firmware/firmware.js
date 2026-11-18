import {firmwareHooks} from "../board.js";
import {h, replace} from "../dom.js";
import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps} from "../draw.js";
import {CONNECT_ORDER, connectSteps} from "../drive.js";
import {BOARD, VERSION} from "../looks.js";
import {
  FIRMWARE_RELEASES, FIRMWARE_SIGN, firmwareBehindOf, firmwareButtonLooks, firmwareOlder,
  firmwareOurs, firmwareVersion, firmwareWarnings, latestRelease
} from "./release.js";

// ---- firmware updates ----------------------------------------------------------------------------
// The Update available button beside the version in the page's header, and the sheet it opens. Once
// an FX drive is open, or the page is opened at #update, the page asks for the latest release and
// shows the button where the board's firmware is older. The sheet says what is new and how to flash the board's -with-libs
// .uf2. That image also rewrites the filesystem holding picofx and the board's libraries, so they
// match the new autofx, and it leaves the FX drive alone. build_editor.py takes this folder only for
// a board whose description has a release entry.
//
// A release whose notes have lines starting with the warning sign, or a GitHub warning alert, shows
// them first, in amber, and turns the button amber too.
//
// A board can have a wireless build that places the FX drive elsewhere, so flashing the other
// build's file empties the drive. The firmware writes catalogue.js beside the page, saying which
// build it is, and the sheet offers the file for the build the catalogue names.

// The firmware the board runs, since the drive carries the picker made with it
var FIRMWARE_SHOWN = VERSION;

// The status is idle, checking, done or failed, latest is the release as firmwareFrom() reads it,
// and open is whether the sheet is shown
var firmware = {status: "idle", latest: null, open: false};

// Whether the board's firmware is older than the latest release
function firmwareBehind(latest) {
  return !!latest && firmwareBehindOf(FIRMWARE_SHOWN, latest.version);
}

// Whether the latest release would bring the board to at least the version given, or null while the
// latest release is unknown
function firmwareCovers(version) {
  if (firmware.status !== "done" || !firmware.latest) return null;
  return firmwareBehind(firmware.latest) && !firmwareOlder(firmware.latest.version, version);
}
firmwareHooks.covers = firmwareCovers;

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
  var version = firmwareVersion(release);
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

// Find the latest release and draw the page for it, or show nothing where none can be had
async function checkFirmware() {
  if (firmware.status === "checking") return;
  firmware.status = "checking";
  // A release whose files CI has yet to upload is asked for again next time
  var release = await latestRelease(function (fetched) {
    return firmwareFrom(fetched).files.length > 0;
  });
  if (release) {
    firmwareUse(release);
  } else {
    firmware.status = "failed";
    firmware.latest = null;
  }
  draw();
  // The text editor's Update available button opens this page at #update, for the sheet
  if (firmware.status === "done" && location.hash === "#update" && firmwareBehind(firmware.latest)) {
    history.replaceState(null, "", location.pathname + location.search);
    openFirmware();
  }
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
    firmwareButton = where.appendChild(h("button", {type: "button", "aria-haspopup": "dialog",
                                                    onclick: openFirmware}, "Update available"));
  }
  var looks = firmwareButtonLooks(firmware.latest.version, firmware.latest.notes);
  firmwareButton.className = looks.className;
  firmwareButton.title = looks.title;
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
      shown.push(h("h4", {}, kind.charAt(0).toUpperCase() + kind.slice(1)));
      return;
    }
    var item = /^\s*[-*]\s+(.*)$/.exec(line);
    if (item) {
      if (!list) shown.push(list = h("ul"));
      list.appendChild(h("li", {}, firmwarePlain(item[1]) || null));
      return;
    }
    list = null;
    var heading = /^\s*#+\s+(.*)$/.exec(line);
    if (heading) shown.push(h("h4", {}, firmwarePlain(heading[1]) || null));
    else if (line.trim()) shown.push(h("p", {}, firmwarePlain(line) || null));
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
  return h("a", {href: url, target: "_blank", rel: "noopener"}, text);
}

// A file's name and size, as the sheet's foot shows it
function firmwareFileSays(file) {
  return file.name + ", " + (file.size / 1048576).toFixed(1) + " MB";
}

// The sheet's foot, which names the file beside its download, or says there is none to offer
function firmwareFoot(latest) {
  var file = latest.files[0];
  if (!file) {
    return h("div", {className: "firmwaresheetfoot"},
             h("div", {className: "firmwarefootsays"},
               latest.known ? "This release has no file for " + BOARD.name + " yet. "
                            : "This page could not tell which " + BOARD.name + " this is. ",
               firmwareLink("See the release", latest.url)));
  }
  // A new tab takes the download, so the page keeps its open drive
  var link = firmwareLink("Download for " + file.label, file.url);
  link.className = "firmwareget primary";
  return h("div", {className: "firmwaresheetfoot"},
           h("div", {className: "firmwarefootsays"}, firmwareFileSays(file)), link);
}

// The sheet, made on its first opening
var firmwareDialog = null;

// What the sheet was last filled with, so a draw that changes nothing leaves its scroll and focus
var firmwareFilled = null;

// Fill the sheet with the release's warnings, notes, steps and downloads
function fillFirmwareDialog(latest) {
  var bootloader = BOARD.release.bootloader_drive;

  var split = firmwareWarnings(latest.notes);
  var news = firmwareNotes(split.rest);
  var warnings = split.warnings.length;
  replace(firmwareDialog,
    h("div", {className: "firmwaresheethead"},
      h("button", {type: "button", onclick: closeFirmware}, "\u2039 Back"),
      h("h2", {id: "firmwareTitle"}, "Firmware " + latest.version + " is available")),
    h("div", {className: "firmwarescroll"},
      h("p", {}, "This " + BOARD.name + " runs " + FIRMWARE_SHOWN + "."),
      // Check if the release has warnings, which come first in amber, each behind the warning sign
      warnings ? h("section", {className: "firmwarewarnings"}, split.warnings.map(function (warning) {
        return h("p", {}, FIRMWARE_SIGN + " " + firmwarePlain(warning));
      })) : null,
      news.length ? [h("h3", {}, "What's new"), news] : null,
      firmwareLink("Read the full release notes", latest.url),
      h("h3", {}, "How to update"),
      h("ol", {}, ["Save to board, so your scenes are on the FX drive.",
                   "Download the firmware below.",
                   "Hold Boot, press " + BOARD.release.reset_button + ", then let go of Boot.",
                   "Drag the .uf2 file onto the " + bootloader + " drive that appears.",
                   "Once the board restarts, open PICKER.html from the FX drive again."
                  ].map(function (step) { return h("li", {}, step); })),
      // The board restarts as the copy ends, which a computer can report as a failed copy, and a
      // copy that really is cut short leaves the bootloader's drive showing
      h("p", {className: "firmwarenote"},
        "If your computer reports an error as the board restarts, check whether the " +
        bootloader + " drive is still showing. If it is, drag the file onto it again."),
      // A release with a warning may empty the FX drive, so it does not promise to keep it
      h("p", {className: "firmwarenote"}, warnings
        ? "Read the " + (warnings > 1 ? "warnings" : "warning") + " at the top before you start."
        : "Your FX drive and the files on it are kept.")),
    firmwareFoot(latest));
}

// Draw the sheet, or close it where it should not be shown
function renderFirmwareDialog() {
  if (!firmware.open || !firmware.latest) {
    if (firmwareDialog && firmwareDialog.open) firmwareDialog.close();
    return;
  }
  if (!firmwareDialog) {
    firmwareDialog = document.body.appendChild(h("dialog", {
      className: "firmwaresheet", "aria-labelledby": "firmwareTitle",
      // Focusable, so the sheet takes focus itself on opening. The browser would focus the Back
      // button, which shows its focus outline
      tabIndex: -1,
      // Escape closes the dialog itself, so the page's state follows it
      onclose: function () { if (firmware.open) closeFirmware(); },
      // A click on the backdrop lands on the dialog, and one inside it lands on its contents
      onclick: function (event) {
        if (event.target === firmwareDialog) closeFirmware();
      }
    }));
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

// Check at once where the page is opened at #update, as the text editor on the drive opens it
if (location.hash === "#update") checkFirmware();
