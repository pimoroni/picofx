import {banner, saving} from "./00_banner.js";
import {draw} from "./00_draw.js";
import {state} from "./04_scenes.js";
import {currentText} from "./07_writing.js";
import {takeAnswer} from "./18_file_preview.js";

var SAVING_TAIL_MS = 920;

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

function playsItself(text) {
  return !/\breload\s*=\s*manual\b/i.test(text);
}

var CHECKING = "The board has not loaded the file yet.";

async function markChecking() {
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

export async function driveTrouble(e, name) {
  if (e.name === "QuotaExceededError")
    return "The FX drive is full. Delete something from it and try again.";
  if (!await driveAnswers())
    return "The FX drive is not showing. Check the board is plugged in, and double-press Boot " +
           "if the drive does not appear.";
  if (e.name === "NotFoundError" && name) return nameShown(name) + " is no longer on the FX drive.";
  return e.message || e.name;
}

async function readErrors() {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    return (await (await handle.getFile()).text()).trim();
  } catch (e) {
    if (e.name !== "NotFoundError") return false;
    return (await driveAnswers()) ? null : false;
  }
}

async function waitForBoard(before, nothingYet) {
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

function sayWhatHappened(said, also) {
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

async function openDrive(fresh) {
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

export var WROTE_KEY = "fx-picker-wrote";

function overwriteQuestion() {
  return "The file on the board has changed since it was opened here. Overwrite those changes?";
}

export var connectSteps = [];

async function connect(fresh) {
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
  state.dirHandle = dir;
  document.getElementById("check").disabled = false;
  var openButton = document.getElementById("open");
  openButton.removeAttribute("data-primary");
  openButton.textContent = "Change drive";
  openButton.title = "Connected to " + (dir.name && dir.name.length > 1 ? dir.name : "the FX drive") +
                     ". Open a different one";
  openButton.onclick = openFresh;
  var saveButton = document.getElementById("save");
  saveButton.toggleAttribute("data-primary", true);
  saveButton.disabled = false;
  draw();
  for (var at = 0; at < connectSteps.length; at++) await connectSteps[at]();
}

document.getElementById("save").onclick = async function () {
  var button = this;
  var check = document.getElementById("check");
  try {
    if (!drive.fileHandle) await connect();
    button.disabled = true;
    check.disabled = true;
    var onBoard = await (await drive.fileHandle.getFile()).text();
    var lastWritten = null;
    try { lastWritten = localStorage.getItem(WROTE_KEY); } catch (e) {}
    if (onBoard !== lastWritten && onBoard.trim() !== "" && !confirm(overwriteQuestion()))
      return;
    var text = currentText();
    saving("Saving to the board...");
    var errorsBefore = playsItself(onBoard) ? await readErrors() : undefined;
    if (errorsBefore !== undefined && await markChecking()) errorsBefore = CHECKING;
    var writable = await drive.fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    var back = await (await drive.fileHandle.getFile()).text();
    if (back !== text) {
      var differs = new Error("effects.txt reads back different");
      differs.name = "NotWhatWasSaved";
      throw differs;
    }
    try { localStorage.setItem(WROTE_KEY, text); } catch (e) {}
    takeAnswer(null, text);
    await new Promise(function (settle) { setTimeout(settle, SAVING_TAIL_MS); });
    var hides = /\bdrive=manual\b/.test(text) && !/\bdrive=manual\b/.test(onBoard)
      ? " The drive will be hidden next time the board starts. Double-press Boot to show it."
      : "";
    if (/\bprogram=/.test(onBoard)) {
      banner("Saved. The board is running a program, so press Reset to play this change." + hides);
      return;
    }
    if (errorsBefore !== undefined && /\bprogram=/.test(text)) {
      banner("Saved. The board is restarting to run the program." +
             hides);
      return;
    }
    if (errorsBefore === undefined) {
      banner("Saved. " + (playsItself(text)
             ? "Eject the FX drive or press Boot once to play " +
               "it. Future saves will play automatically."
             : "Eject the FX drive to play it. Then double-press " +
               "Boot to show the drive again and press 'Check board'.") + hides);
      return;
    }
    banner("Saved. Waiting for the board to load it...", "hold");
    var was = errorsBefore === false ? null : errorsBefore;
    var said = await waitForBoard(was, function () {
      banner("Playing on the board. Checking for problems...", "hold");
    });
    sayWhatHappened(said, hides);
    if (said !== CHECKING) takeAnswer(said, text);
  } catch (e) {
    if (e.name === "AbortError") return;
    if (e.name === "QuotaExceededError") {
      banner("The FX drive is full. Delete a picture, sound or program and try again.", true);
      return;
    }
    drive.fileHandle = null;
    drive.dirHandle = null;
    if (e.name === "NotWhatWasSaved")
      banner("The file on the drive did not match what was saved. Check the FX drive is " +
             "showing, then try again.", true);
    else
      banner("The save did not reach the board (" + e.name + "). Check the FX drive " +
             "is showing, double-press Boot if it is not, then try again.", true);
  } finally {
    button.disabled = !drive.fileHandle;
    check.disabled = !drive.fileHandle;
  }
};

document.getElementById("check").onclick = async function () {
  banner("Checking...", "hold");
  await new Promise(function (settle) { setTimeout(settle, 350); });
  try {
    var about = await (await drive.fileHandle.getFile()).text();
    var said = await readErrors();
    if (said === false) throw {name: "NotReadable"};
    if (said === CHECKING) {
      banner("The board has not loaded the file yet. Eject the FX drive or press Boot once.", "hold");
      return;
    }
    if (said) banner("The board reported problems:", true, said);
    else banner("No problems reported.");
    takeAnswer(said, about);
  } catch (e) {
    banner("Could not read the drive (" + e.name + "). Is it showing?", true);
  }
};

document.getElementById("open").onclick = function () { openDrive(false); };

if (!CAN_REACH_A_DRIVE) {
  document.getElementById("open").disabled = true;
  banner("This page needs Chrome or Edge to reach the drive.");
}

export function nameShown(name) {
  return name.slice(name.lastIndexOf("/") + 1);
}

export function isHiddenName(name) {
  return name.charAt(0) === ".";
}
