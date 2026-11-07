
// ---- the drive's files ---------------------------------------------------------------------------
// The files on the FX drive: a walk of the drive that each part's own files are found in, adding
// files to it from this computer and deleting them from it.

state.fileHandle = null;
state.scanned = false;

var scanBusy = false;

// The folders a picture, a drawing and a sound are kept in, each added file going into its own.
// The top of the drive is read too, so a file dropped there still plays
var MEDIA_FOLDERS = {pictures: /\.(gif|png|jpe?g)$/i, drawings: /\.py$/i, sounds: /\.wav$/i};

// The folders of examples the walk reads, under examples/ on a board that carries them, in the
// order the gallery shows their sections. Each file is offered by its path from the top of the
// drive, which is how an effects line names it
var EXAMPLE_FOLDERS = BOARD.examples ? ["drawings", "pictures"] : [];

// Each example folder's sections, as [name, what it holds, members, whether it starts folded], in
// its sections.txt's order. A drawing joins a section with a Section: line, as a program does, and
// a drawing section starts folded where sections.txt marks it so. A picture is a member by path, a
// file or a slideshow's folder, or folder/* for each file in that folder on its own, and a picture
// section starts folded
var exampleSections = {};

// The folder each file or slideshow the walk found sits in, so it is deleted from there
var mediaHome = {};

// The sections an example folder's sections.txt lists, a line each as its name, a | and what it
// holds, then after another | "folded" for drawings, or the members split by commas for pictures
function exampleSectionsFrom(text, root, kind) {
  return sectionsFrom(text).map(function (section) {
    var parts = section[1].split("|");
    var third = (parts[1] || "").trim();
    if (kind === "drawings") return [section[0], parts[0].trim(), [], third === "folded"];
    var members = third ? third.split(",") : [];
    return [section[0], parts[0].trim(), members.map(function (member) {
      return member.trim();
    }).filter(Boolean).map(function (member) { return root + member; }), true];
  });
}

// Whether a file or folder is one of the drive's examples
function isExampleMedia(name) {
  return name.indexOf("examples/") === 0;
}

// Whether a section holds a drawing that names it, or a picture its members name, itself or as
// one of a folder's files
function sectionHolds(section, media) {
  if (media.drawing) return media.drawing.section === section[0];
  var folder = media.name.slice(0, media.name.lastIndexOf("/") + 1);
  return section[2].some(function (member) {
    return member === media.name || member === folder + "*";
  });
}

// The folder a file of this name is added to, or null for the top of the drive
function mediaFolderFor(name) {
  return Object.keys(MEDIA_FOLDERS).filter(function (folder) {
    return MEDIA_FOLDERS[folder].test(name);
  })[0] || null;
}

async function scanMedia(dir) {
  // One walk at a time, built aside and landed whole, so a redraw mid-scan never sees half a
  // drive and two walks can never lace their findings together
  if (scanBusy) return;
  scanBusy = true;
  driveParts.forEach(function (part) { if (part.begin) part.begin(); });
  var homes = Object.create(null);
  // The drive's own folders, which are never a slideshow
  var kept = Object.keys(MEDIA_FOLDERS).concat([OWN_FOLDER, "examples",
                                                "System Volume Information"]);
  var sections = {};
  // Whether a part takes the entry, the first that does keeping it
  async function taken(name, handle) {
    for (var at = 0; at < driveParts.length; at++) {
      var part = driveParts[at];
      var take = handle.kind === "file" ? part.file : part.folder;
      if (take && await take(name, handle)) return true;
    }
    return false;
  }
  async function offer(folder, top) {
    for await (var pair of folder.entries()) {
      var name = pair[0], handle = pair[1];
      // A name in a media folder and at the top is the folder's, read first
      if (name in homes || (top && handle.kind !== "file" && kept.indexOf(name) >= 0)) continue;
      if (await taken(name, handle)) homes[name] = folder;
    }
  }
  // A folder no part takes is walked into, as is one its sections split into files
  async function offerExamples(folder, path, split) {
    for await (var pair of folder.entries()) {
      var named = path + pair[0], handle = pair[1];
      if (handle.kind !== "file" && split.indexOf(named + "/*") >= 0)
        await offerExamples(handle, named + "/", split);
      else if (!await taken(named, handle) && handle.kind !== "file")
        await offerExamples(handle, named + "/", split);
    }
  }
  try {
    for (var named of Object.keys(MEDIA_FOLDERS)) {
      var folder = null;
      try {
        folder = await dir.getDirectoryHandle(named);
      } catch (e) {
        // A drive without that folder keeps nothing of that kind in one
      }
      if (folder) await offer(folder, false);
    }
    await offer(dir, true);
    for (var kind of EXAMPLE_FOLDERS) {
      var examples = await folderAt(dir, ["examples", kind]);
      if (!examples) continue;
      var root = "examples/" + kind + "/";
      sections[kind] = [];
      try {
        var listed = await (await examples.getFileHandle("sections.txt")).getFile();
        sections[kind] = exampleSectionsFrom(await listed.text(), root, kind);
      } catch (e) {
        // Without sections.txt every example is in one group of its own
      }
      var split = [].concat.apply([], sections[kind].map(function (section) {
        return section[2];
      }));
      await offerExamples(examples, root, split);
    }
  } finally {
    scanBusy = false;
  }
  mediaHome = homes;
  exampleSections = sections;
  driveParts.forEach(function (part) { if (part.land) part.land(); });
  state.scanned = true;
}

function driveSaid() {
  return JSON.stringify([exampleSections].concat(driveParts.map(function (part) {
    return part.said ? part.said() : "";
  })));
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
      banner("The browser could not open those files (" + e.message + "). " +
             "Copy them to another folder, such as Downloads, and try again.", true);
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
      var into = mediaFolderFor(file.name);
      var home = into ? await state.dirHandle.getDirectoryHandle(into, {create: true})
                      : state.dirHandle;
      var existing = null;
      try { existing = await home.getFileHandle(file.name); } catch (e) {}
      if (existing && !confirm(file.name + " is already on the drive. Replace it?"))
        continue;
      var handle = await home.getFileHandle(file.name, {create: true});
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
    banner(landed + " copied. These could not be copied: " + refused.join(", "), true);
  else if (refused.length)
    banner("Nothing copied: " + refused.join(", "), true);
  else if (unoffered.length)
    banner(unoffered.join(", ") + " copied, but only drawings appear here. " +
           "A drawing's opening string starts with Drawing: and its name.", true);
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
    await (mediaHome[name] || state.dirHandle).removeEntry(name, {recursive: kind === "folder"});
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
