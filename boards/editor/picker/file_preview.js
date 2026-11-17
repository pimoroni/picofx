import {banner, saving} from "./banner.js";
import {drawParts} from "./draw.js";
import {
  CAN_REACH_A_DRIVE, CHECKING, SAVING_TAIL_MS, WROTE_KEY, connect, drive, markChecking, openDrive,
  overwriteQuestion, playsItself, readErrors, sayWhatHappened, waitForBoard
} from "./drive.js";
import {currentText} from "./writing.js";

// ---- the file, painted -----------------------------------------------------------------------

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function paintLine(line) {
  var plain = escapeHtml(line);
  // A scene heading carries a colon, which would read as the one dividing a channel from its
  // effect, so headings are taken first
  if (line.charAt(0) === "[") return "<span class='s-scene'>" + plain + "</span>";
  if (/^\s*#/.test(line)) return "<span class='s-comment'>" + plain + "</span>";
  var at = line.indexOf(":");
  if (at < 0) return plain;
  function settings(text) {
    return (text.match(/"[^"]*"|\S+|\s+/g) || []).map(function (token) {
      var pair = token.match(/^([^=\s]+)(=)(.*)$/);
      if (!pair) return escapeHtml(token);
      return "<span class='s-name'>" + escapeHtml(pair[1]) + "</span>" +
             "<span class='s-punc'>=</span>" +
             "<span class='s-value'>" + escapeHtml(pair[3]) + "</span>";
    }).join("");
  }
  var left = line.slice(0, at), right = line.slice(at + 1);
  var selector = left.match(/^(\s*)(\S+)(.*)$/);
  var head = selector
    ? escapeHtml(selector[1]) + "<span class='s-target'>" + escapeHtml(selector[2]) +
      "</span>" + settings(selector[3])
    : escapeHtml(left);
  var effect = right.match(/^(\s*)(\S+)(.*)$/);
  var tail = effect
    ? escapeHtml(effect[1]) + "<span class='s-effect'>" + escapeHtml(effect[2]) +
      "</span>" + settings(effect[3])
    : escapeHtml(right);
  return head + "<span class='s-colon'>:</span>" + tail;
}

// The board's answer as this page shows it: what errors.txt said, and the file it was about,
// so a line is marked only while the page still writes it the same
var answered = {said: null, about: null};

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

// Show the file as the page writes it. A line the board named is marked, with the board's words
// after it, where the page still writes it as the board read it
export function renderPreview() {
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
    note.textContent = stale === 1 ? "One reported line has since changed."
                                   : stale + " reported lines have since changed.";
  }
}
drawParts.preview = renderPreview;

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
    // The marks were about the file the board had, which this one replaces
    takeAnswer(null, text);
    await new Promise(function (settle) { setTimeout(settle, SAVING_TAIL_MS); });
    // Said once, where this save is the first to hide the drive
    var hides = /\bdrive=manual\b/.test(text) && !/\bdrive=manual\b/.test(onBoard)
      ? " The drive will be hidden next time the board starts. Double-press Boot to show it."
      : "";
    // Check if the board is running a program
    if (/\bprogram=/.test(onBoard)) {
      // A program keeps the board busy, so neither an eject nor a press reaches it
      banner("Saved. The board is running a program, so press Reset to play this change." + hides);
      return;
    }
    // Check if a board that plays each save itself is given a program
    if (errorsBefore !== undefined && /\bprogram=/.test(text)) {
      // The board restarts to run the program, so there is no answer to wait for
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

// The answer and the file it is about are read together, as the board has finished with both
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
