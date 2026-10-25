// ---- the latest firmware release ----------------------------------------------------------------
// The latest picofx release on GitHub, kept in this browser for a day, and whether the firmware a
// page was made with is older. It imports nothing, so it can run in any page a drive serves.

// Where the latest release is fetched from
var FIRMWARE_LATEST = "https://api.github.com/repos/pimoroni/picofx/releases/latest";

// The start every address the sheet links to must have. What localStorage holds can be written by
// any page opened from this computer, so nothing else is linked to
var FIRMWARE_HOME ="https://github.com/pimoroni/picofx/";

// The releases page, linked to where a release's own page address is missing or elsewhere
export var FIRMWARE_RELEASES = FIRMWARE_HOME + "releases";

// The localStorage key that holds GitHub's answer and when it came. Every page opened from a drive
// shares this browser's storage, so it holds the release as firmwareTrimmed() leaves it, and each
// board picks its own files from that
var FIRMWARE_STORE = "fx-picker-firmware-release";

// How long a stored answer is used before GitHub is asked again
var FIRMWARE_FRESH_MS = 24 * 60 * 60 * 1000;

// The warning sign, with the variation selector that asks for its emoji form
export var FIRMWARE_SIGN = "⚠️";

// Whether version a is older than version b, each as dotted numbers
export function firmwareOlder(a, b) {
  var x = a.split("."), y = b.split(".");
  for (var at = 0; at < Math.max(x.length, y.length); at++) {
    var difference = (parseInt(x[at], 10) || 0) - (parseInt(y[at], 10) || 0);
    if (difference) return difference < 0;
  }
  return false;
}

// Whether firmware whose version a page shows as shown=, such as "1.29.0 preview", is older than
// the release version=. A preview build is older than the release of its own number
export function firmwareBehindOf(shown, version) {
  var running = shown.split(" ")[0];
  if (firmwareOlder(running, version)) return true;
  return / preview$/.test(shown) && !firmwareOlder(version, running);
}

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

// The parts of GitHub's answer the pages use, which are all they store
function firmwareTrimmed(release) {
  var assets = Array.isArray(release.assets) ? release.assets : [];
  return {tag_name: release.tag_name, body: release.body, html_url: release.html_url,
          assets: assets.map(function (asset) {
            return {name: asset.name, size: asset.size, browser_download_url: asset.browser_download_url};
          })};
}

// A release's version, its tag without the v
export function firmwareVersion(release) {
  return String(release.tag_name || "").replace(/^v/, "");
}

// The Update available button's class and tooltip for a release of version= with notes=. It is
// amber where the notes have a warning
export function firmwareButtonLooks(version, notes) {
  var heed = firmwareWarnings(notes).warnings.length > 0;
  return {className: heed ? "firmwarebutton hold" : "firmwarebutton",
          title: heed ? "See the warning for firmware " + version + " and how to update."
                      : "See what's new in firmware " + version + " and how to update."};
}

// Whether an address is one of picofx's own pages on GitHub
export function firmwareOurs(url) {
  return typeof url === "string" && url.indexOf(FIRMWARE_HOME) === 0;
}

// Find the latest release, as firmwareTrimmed() leaves it, or null where none can be had. A stored
// answer is used while it is fresh. A failed fetch falls back on any stored answer, however old.
// keep(release) says whether a fetched answer is stored
export async function latestRelease(keep) {
  var stored = firmwareStored();
  // Check if the stored answer is fresh enough to use without asking GitHub
  if (stored.release && Date.now() - stored.at < FIRMWARE_FRESH_MS) return stored.release;
  try {
    var answer = await fetch(FIRMWARE_LATEST, {cache: "no-store"});
    if (!answer.ok) throw new Error(String(answer.status));
    var release = firmwareTrimmed(await answer.json());
    if (keep(release)) firmwareStore(release);
    return release;
  } catch (e) {
    return stored.release || null;
  }
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
export function firmwareWarnings(notes) {
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
