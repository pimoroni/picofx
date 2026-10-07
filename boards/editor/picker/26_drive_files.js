
// ---- the drive's files ---------------------------------------------------------------------------
// The files on the FX drive: a walk of the drive that each part's own files are found in, adding
// files to it from this computer and deleting them from it.

state.fileHandle = null;
state.scanned = false;

var scanBusy = false;

async function scanMedia(dir) {
  // One walk at a time, built aside and landed whole, so a redraw mid-scan never sees half a
  // drive and two walks can never lace their findings together
  if (scanBusy) return;
  scanBusy = true;
  driveParts.forEach(function (part) { if (part.begin) part.begin(); });
  try {
    for await (var pair of dir.entries()) {
      var name = pair[0], handle = pair[1];
      if (handle.kind !== "file" && name === "System Volume Information") continue;
      for (var at = 0; at < driveParts.length; at++) {
        var part = driveParts[at];
        var take = handle.kind === "file" ? part.file : part.folder;
        if (take && await take(name, handle)) break;
      }
    }
  } finally {
    scanBusy = false;
  }
  driveParts.forEach(function (part) { if (part.land) part.land(); });
  state.scanned = true;
}

function driveSaid() {
  return JSON.stringify(driveParts.map(function (part) { return part.said ? part.said() : ""; }));
}

async function rescanMedia() {
  if (!state.dirHandle || scanBusy) return;
  var was = driveSaid();
  try {
    await scanMedia(state.dirHandle);
  } catch (e) {
    return;
  }
  if (driveSaid() !== was) draw();
}

function adderTile(label, kinds, what, takes) {
  var tile = document.createElement("button");
  tile.className = "adder";
  tile.innerHTML = "<svg width='13' height='13' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" + label;
  tile.title = "Copy files from this computer onto the FX drive";
  tile.onclick = function () { addFiles(kinds, what, takes); };
  return tile;
}

function binButton(name, kind) {
  if (!CAN_REACH_A_DRIVE) return document.createTextNode("");
  var bin = document.createElement("span");
  bin.className = "bin";
  bin.textContent = "\u00d7";
  bin.title = "Delete " + name + " from the FX drive";
  bin.onclick = function (e) {
    e.stopPropagation();
    removeFromDrive(name, kind);
  };
  return bin;
}

async function addFiles(kinds, what, takes) {
  var picked;
  try {
    picked = await window.showOpenFilePicker({multiple: true, types: [kinds],
                                              excludeAcceptAllOption: true});
  } catch (e) {
    // A dismissed dialog says nothing. Anything else is the browser refusing the files
    if (e.name !== "AbortError")
      banner("The browser would not open those files (" + e.message + "). Copy them to " +
             "another folder, such as Downloads, and add them from there.", true);
    return;
  }
  var landed = 0;
  var arrived = [];
  var refused = [];
  for (var i = 0; i < picked.length; i++) {
    var file;
    try {
      // The dialog filters, and this holds where a platform's does not: a kind
      // the board cannot play never reaches the drive
      if (!takes.test(picked[i].name)) {
        refused.push(picked[i].name + " (not a kind the board plays)");
        continue;
      }
      file = await picked[i].getFile();
      var existing = null;
      try { existing = await state.dirHandle.getFileHandle(file.name); } catch (e) {}
      if (existing && !confirm(file.name + " is already on the drive. Replace it?"))
        continue;
      var handle = await state.dirHandle.getFileHandle(file.name, {create: true});
      var writable = await handle.createWritable();
      await writable.write(file);
      await writable.close();
      landed++;
      arrived.push(file.name);
    } catch (e) {
      refused.push(file ? file.name : "a file");
      if (e.name === "QuotaExceededError") {
        refused = refused.concat(picked.slice(i + 1).map(function (p) { return p.name; }));
        banner("The FX drive filled up: " + landed + " " + what + " copied, no room for " +
               refused.join(", ") + ". Delete something from it and try again.", true);
        break;
      }
    }
  }
  try { await scanMedia(state.dirHandle); } catch (e) {}
  // A Python file is offered only where its opening string makes it a drawing
  var unoffered = arrived.filter(function (name) {
    return /\.py$/i.test(name) && !mediaNamed(name);
  });
  if (refused.length && landed)
    banner(landed + " copied; these did not arrive: " + refused.join(", "), true);
  else if (refused.length)
    banner("Nothing arrived: " + refused.join(", "), true);
  else if (unoffered.length)
    banner(unoffered.join(", ") + " copied, but only a drawing is offered here, and a " +
           "drawing's opening string starts with Drawing: and its name.", true);
  else if (landed)
    banner(landed + " " + what + " copied to the drive.");
  draw();
}

async function removeFromDrive(name, kind) {
  var said = kind === "folder"
    ? "Delete the folder " + name + " and every picture in it from the FX drive?"
    : "Delete " + name + " from the FX drive?";
  if (!confirm(said)) return;
  try {
    await state.dirHandle.removeEntry(name, {recursive: kind === "folder"});
  } catch (e) {
    banner("Could not delete " + name + ": " + e.name + ". Is the drive showing?", true);
    return;
  }
  store();
  driveParts.forEach(function (part) {
    if (!part.forget) return;
    part.forget(name);
    apply(slotAt(state.at).body);
  });
  try { await scanMedia(state.dirHandle); } catch (e) {}
  draw();
  driveParts.forEach(function (part) { if (part.gone) part.gone(name); });
}

// The file starts folded, there for anyone who opens it
(function () {
  var file = document.getElementById("preview").closest("details");
  if (file) file.open = false;
}());

connectSteps.push(async function () {
  state.fileHandle = drive.fileHandle;
  draw();
  await scanMedia(drive.dirHandle);
  draw();
});

setInterval(rescanMedia, 5000);
