
// ---- the drive, and what the board says back ------------------------------------------------
// Saving and the read-back of errors.txt: the banner and the saving lights, remembering the
// drive, and waiting on the board. Opening a drive takes its handles, the read-back part
// reading its effects.txt into the page. Chrome and Edge only, where a page can be handed a
// folder to write to.

var SPOT_STEP_MS = 120;

var SAVING_TAIL_MS = 920;

var spotTimer = null;

function stopSpots() {
  if (spotTimer !== null) clearInterval(spotTimer);
  spotTimer = null;
}

function saving(text) {
  banner(text, "hold");
  var row = document.createElement("span");
  row.className = "spots";
  for (var i = 0; i < 7; i++) row.appendChild(document.createElement("i"));
  document.getElementById("banner").firstChild.appendChild(row);
  var at = 0;
  spotTimer = setInterval(function () {
    for (var i = 0; i < row.children.length; i++)
      row.children[i].className = i === at ? "lit" : "";
    at = (at + 1) % row.children.length;
  }, SPOT_STEP_MS);
}

function banner(text, warn, detail) {
  stopSpots();
  var box = document.getElementById("banner");
  box.textContent = "";
  if (!text) return;
  var note = document.createElement("div");
  // warn may also be "hold", the amber of a check still running
  note.className = warn === "hold" ? "banner hold" : warn ? "banner warn" : "banner";
  note.textContent = text;
  if (detail) {
    var pre = document.createElement("pre");
    pre.textContent = detail;
    note.appendChild(pre);
  }
  box.appendChild(note);
}

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

var BOARD_AWAY_MS = 10000;

var BOARD_POLL_MS = 250;

function playsItself(text) {
  return /\breload\s*=\s*auto\b/i.test(text);
}

var CHECKING = "The board has not read the file yet.";

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
    banner("No answer from the board yet. Eject the FX drive, or press Boot " +
           "once, and it plays. If the lights already changed, this computer is " +
           "showing the page an old copy of the drive: press the board's Reset " +
           "button to see what it wrote.", true);
  else if (said)
    banner("The board wasn't happy with some of it:", true, said);
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
      banner("That folder has no effects.txt, so it does not look like an FX " +
             "drive. Pick the drive itself, the one named FX.", true);
      return;
    }
    banner("Could not open the drive: " + e.name + ". Is it showing? " +
           "A double press of Boot brings it back.", true);
  }
}

function openFresh() { openDrive(true); }

var CAN_REACH_A_DRIVE = typeof window.showDirectoryPicker === "function";


var drive = {dirHandle: null, fileHandle: null};

// The board's answer as this page shows it: what errors.txt said, and the file it was about,
// so a line is marked only while the page still writes it the same
var answered = {said: null, about: null};

// What this page last wrote or read
var WROTE_KEY = "fx-picker-wrote";

// What a save asks where the file on the board has changed since this page read it
function overwriteQuestion() {
  return "The file on the board has changed since this page read it, so saving replaces " +
         "those changes. Save over it?";
}

// What the parts below read off a drive once it is open, each awaited in the order the parts come
var connectSteps = [];

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
  // The wait on the board reads the drive through the page's state
  state.dirHandle = dir;
  document.getElementById("check").disabled = false;
  // Open, the drive button goes quiet and narrower, saying in its tip which drive is open, and
  // saving takes the colour as the next thing to do
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

// errors.txt read into the lines it names. autofx begins each problem "line N:", and anything
// after it up to the next is that problem's, such as a program's traceback
function problemsIn(said) {
  var found = {};
  var at = null;
  (said || "").split("\n").forEach(function (line) {
    var named = line.match(/^line (\d+): ?(.*)$/);
    if (named) {
      at = Number(named[1]);
      (found[at] = found[at] || []).push(named[2]);
    } else if (at !== null && line.trim()) {
      found[at].push(line.trim());
    }
  });
  return found;
}

// Takes the board's answer and the file it read, then marks the lines it named
function takeAnswer(said, about) {
  answered = {said: said || null, about: about};
  renderPreview();
}

// The file as the page writes it. A line the board named is marked where the page still writes
// it as the board read it, the board's words after it
function renderPreview() {
  var problems = problemsIn(answered.said);
  var lines = currentText().split("\n");
  var read = (answered.about || "").split("\n");
  var stale = 0;
  var painted = lines.map(function (line, at) {
    var said = problems[at + 1];
    if (!said) return paintLine(line);
    if (read[at] !== line) {
      stale++;
      return paintLine(line);
    }
    return "<span class='s-problem'>" + paintLine(line) + "</span>" +
           "<span class='s-said'>  " + escapeHtml(said.join(" ")) + "</span>";
  });
  Object.keys(problems).forEach(function (at) {
    if (Number(at) > lines.length) stale++;
  });
  document.getElementById("preview").innerHTML = painted.join("\n");
  var note = document.getElementById("previewNote");
  if (note) {
    note.hidden = !stale;
    note.textContent = stale === 1 ? "One line the board named has changed since it was read."
                                   : stale + " lines the board named have changed since.";
  }
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
    if (back !== text) throw new Error("the file read back differently");
    try { localStorage.setItem(WROTE_KEY, text); } catch (e) {}
    // The marks were about the file the board had, which this one replaces
    takeAnswer(null, text);
    await new Promise(function (settle) { setTimeout(settle, SAVING_TAIL_MS); });
    // Said once, where this save is the first to hide the drive
    var hides = /\bdrive=manual\b/.test(text) && !/\bdrive=manual\b/.test(onBoard)
      ? " The drive stays hidden the next time the board starts: double-press Boot " +
        "to bring it back."
      : "";
    // A program running keeps the board busy, so neither an eject nor a press reaches it
    if (/\bprogram=/.test(onBoard)) {
      banner("On its way. The board is running a program, so press its Reset button to play " +
             "this one." + hides);
      return;
    }
    // A board saving on its own that is given a program restarts to run it, so there is no
    // answer to wait for
    if (errorsBefore !== undefined && /\bprogram=/.test(text)) {
      banner("On its way. The board restarts to run the program, which takes a few seconds." +
             hides);
      return;
    }
    if (errorsBefore === undefined) {
      banner("On its way. " + (playsItself(text)
             ? "Eject the FX drive, or press Boot once, to play this one. " +
               "From now on a save plays on its own."
             : "Eject the FX drive on this computer, and the board plays it. Double-press " +
               "Boot to bring the drive back, then press 'Check board'.") + hides);
      return;
    }
    banner("Saved. Waiting for the board to pick it up...", "hold");
    var was = errorsBefore === false ? null : errorsBefore;
    var said = await waitForBoard(was, function () {
      banner("Playing on the board. Checking for problems...", "hold");
    });
    sayWhatHappened(said, hides);
    if (said !== CHECKING) takeAnswer(said, text);
  } catch (e) {
    if (e.name === "AbortError") return;
    if (e.name === "QuotaExceededError") {
      banner("The FX drive is full, so there was no room to save. Delete a " +
             "picture or sound from it and try again.", true);
      return;
    }
    drive.fileHandle = null;
    drive.dirHandle = null;
    banner("That didn't reach the board: " + e.name + ". Is the FX drive showing? " +
           "A double press of Boot brings it back; then try again.", true);
  } finally {
    button.disabled = !drive.fileHandle;
    check.disabled = !drive.fileHandle;
  }
};

// The answer and the file it is about are read together, the board having finished with both
document.getElementById("check").onclick = async function () {
  banner("Asking the board...", "hold");
  await new Promise(function (settle) { setTimeout(settle, 350); });
  try {
    var about = await (await drive.fileHandle.getFile()).text();
    var said = await readErrors();
    if (said === false) throw {name: "NotReadable"};
    if (said === CHECKING) {
      banner("The board has not read the file yet. Eject the FX drive, or press " +
             "Boot once.", "hold");
      return;
    }
    if (said) banner("The board wasn't happy with some of it:", true, said);
    else banner("All good. The board read the file and found nothing wrong.");
    takeAnswer(said, about);
  } catch (e) {
    banner("Couldn't look: " + e.name + ". Is the drive showing?", true);
  }
};

document.getElementById("open").onclick = function () { openDrive(false); };

if (!CAN_REACH_A_DRIVE) {
  document.getElementById("open").disabled = true;
  banner("This page reaches the drive only in Chrome or Edge.");
}
