import {banner} from "./00_banner.js";
import {draw} from "./00_draw.js";
import {state} from "./04_scenes.js";

// ---- the drive, and what the board says back ----------------------------------------------------
// Saving to the drive and reading back errors.txt, remembering the drive and waiting on the
// board. Opening a drive takes its handles, and the read-back part reads its effects.txt into the
// page. It works in Chrome and Edge only, where a page can be handed a folder to write to.

export var SAVING_TAIL_MS = 920;

function rememberDrive(handle) {
  try {
    var open = indexedDB.open("fx-pages", 1);
    open.onupgradeneeded = function () { open.result.createObjectStore("handles"); };
    open.onsuccess = function () {
      try {
        open.result.transaction("handles", "readwrite")
            .objectStore("handles").put(handle, "drive");
      } catch (e) {}
    };
  } catch (e) {}
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
  var kept = await rememberedDrive();
  if (kept && !fresh) {
    try {
      if (await kept.requestPermission({mode: "readwrite"}) === "granted") {
        await kept.getFileHandle("effects.txt");
        return kept;
      }
    } catch (e) {}
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

export function playsItself(text) {
  return !/\breload\s*=\s*manual\b/i.test(text);
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

export function sayWhatHappened(said, also) {
  if (said === CHECKING)
    banner("No response from the board yet. Eject the FX drive or press Boot " +
           "once to play the save. If the lights have already changed, the " +
           "board has played it but this computer is showing an old copy of the " +
           "drive. Press Reset on the board so the computer sees what it wrote.", true);
  else if (said)
    banner("The board reported problems:", true, said);
  else
    banner("Playing on the board. No problems reported." + (also || ""));
}

export async function openDrive(fresh) {
  try {
    await connect(fresh);
    banner("");
  } catch (e) {
    if (e.name === "AbortError") return;
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


export var drive = {dirHandle: null, fileHandle: null};

// The localStorage key holding the file this page last wrote or read
export var WROTE_KEY = "fx-picker-wrote";

// What a save asks where the file on the board has changed since this page read it
export function overwriteQuestion() {
  return "The file on the board has changed since it was opened here. Overwrite those changes?";
}

// What the parts below read off a drive once it is open, each awaited in the order stated
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
  // Once a drive is open, the drive button goes quiet and narrower and its tip names the drive.
  // The save button takes the colour as the next thing to do
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
