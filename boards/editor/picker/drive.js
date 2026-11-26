import {banner} from "./banner.js";
import {draw} from "./draw.js";
import {BOARD} from "./looks.js";
import {state} from "./scenes.js";

// ---- the drive, and what the board says back ----------------------------------------------------
// This part opens the FX drive and remembers it, and reads errors.txt and waits on the board
// after a save. Opening a drive takes its handles, and later parts read what they need from it.
// It works in Chrome and Edge only, where a page can be handed a folder to write to.

// How long a save waits after the write before it reads the board. The board holds its light for
// 500ms after the last write, then runs one pass of half-steps, which is 920ms for seven lights
export var SAVING_TAIL_MS = 920;

// How long opening a drive waits on the remembered drive at each step. The browser can leave a
// question about a drive that has gone unanswered for ever, and a click opens the dialog only
// within a few seconds of it
var REMEMBERED_WAIT_MS = 1000;

// Remember the drive for the next visit, or forget it where handle is null
function rememberDrive(handle) {
  try {
    var open = indexedDB.open("fx-pages", 1);
    open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
    open.onsuccess = function () {
      try {
        var store = open.result.transaction("handles", "readwrite").objectStore("handles");
        if (handle) store.put(handle, "drive");
        else store.delete("drive");
      } catch (e) {}
    };
  } catch (e) {}
}

// Settle as the promise does, or with null where it fails or is still waiting after ms
function withinTime(promise, ms) {
  return new Promise(function (settle) {
    var timer = setTimeout(function () { settle(null); }, ms);
    promise.then(function (value) { clearTimeout(timer); settle(value); },
                 function () { clearTimeout(timer); settle(null); });
  });
}

function rememberedDrive() {
  return new Promise(function (settle) {
    try {
      var open = indexedDB.open("fx-pages", 1);
      open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
      open.onerror = function () { settle(null); };
      open.onsuccess = function () {
        try {
          var ask = open.result.transaction("handles").objectStore("handles").get("drive");
          ask.onsuccess = function () { settle(ask.result || null); };
          ask.onerror = function () { settle(null); };
        } catch (e) { settle(null); }
      };
    } catch (e) { settle(null); }
  });
}

async function pickDrive(fresh) {
  var kept = await withinTime(rememberedDrive(), REMEMBERED_WAIT_MS);
  // Check if the page may still reach the remembered drive, as it may after a reload, so it
  // reopens without the dialog. A new browser session asks again through the dialog
  if (kept && !fresh) {
    var allowed = await withinTime(kept.queryPermission({mode: "readwrite"}), REMEMBERED_WAIT_MS);
    if (allowed === "granted" &&
        await withinTime(kept.getFileHandle("effects.txt"), REMEMBERED_WAIT_MS)) return kept;
    // Check if the drive has gone or the browser gave no answer, and forget it. A drive only
    // waiting for permission still starts the dialog
    if (allowed !== "prompt") {
      rememberDrive(null);
      kept = null;
    }
  }
  var picked;
  try {
    picked = await window.showDirectoryPicker(
        kept ? {mode: "readwrite", startIn: kept} : {mode: "readwrite"});
  } catch (e) {
    if (e.name === "AbortError") throw e;
    picked = await window.showDirectoryPicker({mode: "readwrite"});
  }
  rememberDrive(picked);
  return picked;
}

var BOARD_SETTLE_MS = 6000;

var BOARD_WAIT_MS = 15000;

var BOARD_AWAY_MS = 30000;

var BOARD_POLL_MS = 250;

// The file with each line's comment cut off, so a setting in a comment is not taken as set
export function uncommented(text) {
  return text.split("\n").map(function (line) { return line.split("#")[0]; }).join("\n");
}

export function playsItself(text) {
  return !/\breload\s*=\s*manual\b/i.test(uncommented(text));
}

// The marker a save writes into errors.txt for the board to clear. It must match the editor's, as
// either page reads the marker the other wrote
export var CHECKING = "The board has not loaded the file yet.";

export async function markChecking() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt", {create: true});
    var writable = await handle.createWritable();
    await writable.write(CHECKING + "\n");
    await writable.close();
    return true;
  } catch (e) {
    return false;
  }
}

async function driveAnswers() {
  try {
    for await (var entry of state.dirHandle.values()) return true;
    return true;
  } catch (e) {
    return false;
  }
}

// The reason a change to the drive failed, as a sentence to follow one saying what failed. The
// drive may be full or gone, such as when the board is unplugged while the page holds it. The
// file named may also be gone from a drive still showing. Any other error is in the browser's words
export async function driveTrouble(e, name) {
  if (e.name === "QuotaExceededError")
    return "The FX drive is full. Delete something from it and try again.";
  if (!await driveAnswers())
    return "The FX drive is not showing. Check the board is plugged in, and double-press Boot " +
           "if the drive does not appear.";
  if (e.name === "NotFoundError" && name) return nameShown(name) + " is no longer on the FX drive.";
  return e.message || e.name;
}

export async function readErrors() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    return (await (await handle.getFile()).text()).trim();
  } catch (e) {
    if (e.name !== "NotFoundError") return false;
    return (await driveAnswers()) ? null : false;
  }
}

export async function waitForBoard(before, nothingYet) {
  var deadline = Date.now() + BOARD_WAIT_MS;
  var settled = Date.now() + BOARD_SETTLE_MS;
  var wentAway = false;
  var told = false;
  while (Date.now() < deadline) {
    await new Promise(function (settle) { setTimeout(settle, BOARD_POLL_MS); });
    var now = await readErrors();
    if (now === false) {
      if (!wentAway) deadline = Math.max(deadline, Date.now() + BOARD_AWAY_MS);
      wentAway = true;
      continue;
    }
    if (now !== before) return now;
    if (wentAway) return now;
    if (!told && Date.now() > settled) {
      nothingYet();
      told = true;
    }
  }
  return before;
}

// Wait for the drive to go and come back, as it does while the board restarts, and return
// whether it came back. The wait for it to go is the one a save gives the board, and once gone it
// has as long to return as waitForBoard() gives it
export async function waitForReturn() {
  var deadline = Date.now() + BOARD_WAIT_MS;
  var wentAway = false;
  while (Date.now() < deadline) {
    await new Promise(function (settle) { setTimeout(settle, BOARD_POLL_MS); });
    if (await driveAnswers()) {
      if (wentAway) return true;
    } else if (!wentAway) {
      wentAway = true;
      deadline = Math.max(deadline, Date.now() + BOARD_AWAY_MS);
    }
  }
  return false;
}

// Say in the banner what the board reported after a save. also= follows the words where nothing
// went wrong, and nothing= says the save plays nothing, as a file with no entries does
export function sayWhatHappened(said, also, nothing) {
  if (said === CHECKING)
    banner("No response from the board yet. Eject the FX drive or press Boot " +
           "once to play the save. If the lights have already changed, the " +
           "board has played it but this computer is showing an old copy of the " +
           "drive. Press " + BOARD.release.reset_button + " on the board so the computer sees " +
           "what it wrote.", true);
  else if (said)
    banner("The board reported problems:", true, said);
  else
    banner((nothing ? "Nothing is playing on the board." : "Playing on the board.") +
           " No problems reported." + (also || ""));
}

export async function openDrive(fresh) {
  try {
    await connect(fresh);
    banner("");
  } catch (e) {
    // Check if the dialog, or the browser's question about editing files, was cancelled or closed
    if (e.name === "AbortError") {
      banner("No drive was opened.");
      return;
    }
    if (e.name === "NotAnFxDrive") {
      banner("That folder has no effects.txt, so it is " +
             "not an FX drive. Choose the drive named FX.", true);
      return;
    }
    banner("Could not open the drive (" + e.name + "). Check the FX " +
           "drive is showing on this computer, and double-press Boot if " +
           "it is not. If the browser asked for permission, choose Allow.", true);
  }
}

function openFresh() { openDrive(true); }

export var CAN_REACH_A_DRIVE = typeof window.showDirectoryPicker === "function";

// Whether the computer runs Linux, not counting Android or ChromeOS. Linux writes a save's contents
// at once, but the directory entry naming them waits long past this page's wait for the board,
// unless the drive is ejected first
export var ON_LINUX = /Linux/.test(navigator.platform) && !/Android|CrOS/.test(navigator.userAgent);


// The drive's handles, and the page's text as it was last read from or saved to the drive, which
// says whether the page holds changes not yet saved
export var drive = {dirHandle: null, fileHandle: null, text: null};

// The localStorage key holding the file this page last wrote or read
export var WROTE_KEY = "fx-picker-wrote";

// What a save asks where the file on the board has changed since this page read it
export function overwriteQuestion() {
  return "The file on the board has changed since it was opened here. Overwrite those changes?";
}

// What later parts read off a drive once it is open, each awaited in the order CONNECT_ORDER states
export var connectSteps = [];
export var CONNECT_ORDER = ["driveFiles", "drivePrograms", "readback", "firmware"];

export async function connect(fresh) {
  var dir = await pickDrive(fresh);
  var file;
  try {
    file = await dir.getFileHandle("effects.txt");
  } catch (e) {
    if (e.name === "NotFoundError") {
      var refused = new Error("no effects.txt");
      refused.name = "NotAnFxDrive";
      throw refused;
    }
    throw e;
  }
  drive.dirHandle = dir;
  drive.fileHandle = file;
  // The wait on the board reads the drive through the page's state
  state.dirHandle = dir;
  document.getElementById("check").disabled = false;
  // Once a drive is open, the drive button loses its colour and narrows, and its tip names the
  // drive. The save button takes the colour as the next thing to do
  var openButton = document.getElementById("open");
  openButton.className = "";
  openButton.textContent = "Change drive";
  openButton.title = "Connected to " + (dir.name && dir.name.length > 1 ? dir.name : "the FX drive") +
                     ". Open a different one";
  openButton.onclick = openFresh;
  var saveButton = document.getElementById("save");
  saveButton.className = "primary";
  saveButton.disabled = false;
  // The header's buttons have changed width, which decides whether it keeps one line
  draw();
  for (var at = 0; at < connectSteps.length; at++) await connectSteps[at]();
}

// Whether a name on the drive is hidden, such as the ._ file macOS writes beside each file it
// copies, or its .Trashes and .fseventsd. A walk of the drive passes these by
export function isHiddenName(name) {
  return name.charAt(0) === ".";
}

// A file's name as the page shows it, without the folders it sits in
export function nameShown(name) {
  return name.slice(name.lastIndexOf("/") + 1);
}
