import {banner} from "./00_banner.js";
import {draw} from "./00_draw.js";
import {BOARD} from "./01_looks.js";
import {apply, driveParts, slotAt, state, store} from "./04_scenes.js";
import {screenHooks} from "./07_board.js";
import {CAN_REACH_A_DRIVE, connectSteps, drive, driveTrouble} from "./18_drive.js";
import {OWN_FOLDER, folderAt, removePictures, sectionsFrom} from "./26_drive_programs.js";

state.fileHandle = null;
state.scanned = false;

var scanBusy = false;

var MEDIA_FOLDERS = {pictures: /\.(gif|png|jpe?g)$/i, drawings: /\.py$/i, sounds: /\.wav$/i};

export function isHiddenName(name) {
  return name.charAt(0) === ".";
}

var EXAMPLE_FOLDERS = BOARD.examples ? ["drawings", "pictures", "sounds"] : [];

export var exampleSections = {};

export var mediaHome = {};

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

export function isExampleMedia(name) {
  return name.indexOf("examples/") === 0;
}

export var OTHER_EXAMPLES = {drawings: "Example drawings", pictures: "Example pictures",
                      sounds: "Example sounds"};

export var groupsOpen = {};

export function groupOpen(group) {
  return group[0] in groupsOpen ? groupsOpen[group[0]] : !group[3];
}

export function exampleGroups(kind, files) {
  var root = "examples/" + kind + "/";
  var left = files.filter(function (one) { return one.name.indexOf(root) === 0; });
  var sections = (exampleSections[kind] || []).slice();
  left.forEach(function (one) {
    var named = one.drawing && one.drawing.section;
    if (named && !sections.some(function (section) { return section[0] === named; }))
      sections.push([named, "", [], false]);
  });
  var groups = sections.map(function (section) {
    var held = left.filter(function (one) { return sectionHolds(section, one); });
    left = left.filter(function (one) { return held.indexOf(one) < 0; });
    return [section[0], section[1], held, section[3]];
  });
  groups.push([OTHER_EXAMPLES[kind], "", left, kind !== "drawings"]);
  return groups;
}

function sectionHolds(section, media) {
  if (media.drawing) return media.drawing.section === section[0];
  var folder = media.name.slice(0, media.name.lastIndexOf("/") + 1);
  return section[2].some(function (member) {
    return member === media.name || member === folder + "*";
  });
}

function mediaFolderFor(name) {
  return Object.keys(MEDIA_FOLDERS).filter(function (folder) {
    return MEDIA_FOLDERS[folder].test(name);
  })[0] || null;
}

export async function scanMedia(dir) {
  if (scanBusy) return;
  scanBusy = true;
  driveParts.forEach(function (part) { if (part.begin) part.begin(); });
  var homes = Object.create(null);
  var kept = Object.keys(MEDIA_FOLDERS).concat([OWN_FOLDER, "examples",
                                                "System Volume Information"]);
  var sections = {};
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
      if (isHiddenName(name)) continue;
      if (name in homes || (top && handle.kind !== "file" && kept.indexOf(name) >= 0)) continue;
      if (await taken(name, handle)) homes[name] = folder;
    }
  }
  async function offerExamples(folder, path, split) {
    for await (var pair of folder.entries()) {
      var named = path + pair[0], handle = pair[1];
      if (isHiddenName(pair[0])) continue;
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

export function adderTile(label, kinds, what, takes) {
  var tile = document.createElement("button");
  tile.className = "adder";
  tile.innerHTML = "<svg width='13' height='13' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" + label;
  tile.title = "Copy files from this computer onto the FX drive";
  tile.onclick = function () { addFiles(kinds, what, takes); };
  return tile;
}

export function binButton(name, kind) {
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
    if (e.name !== "AbortError")
      banner("The browser could not open those files. Copy them to another folder, such as " +
             "Downloads, and try again.", true);
    return;
  }
  var landed = 0;
  var arrived = [];
  var refused = [];
  var trouble = null;
  for (var i = 0; i < picked.length; i++) {
    var file;
    try {
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
      trouble = trouble || e;
      if (e.name === "QuotaExceededError") {
        refused = refused.concat(picked.slice(i + 1).map(function (p) { return p.name; }));
        banner("The FX drive filled up: " + landed + " " + what + " copied, no room for " +
               refused.join(", ") + ". Delete something from it and try again.", true);
        break;
      }
    }
  }
  try { await scanMedia(state.dirHandle); } catch (e) {}
  var unoffered = arrived.filter(function (name) {
    return /\.py$/i.test(name) && !screenHooks.mediaNamed(name);
  });
  var reason = trouble ? ". " + await driveTrouble(trouble) : "";
  if (refused.length && landed)
    banner(landed + " copied. These could not be copied: " + refused.join(", ") + reason, true);
  else if (refused.length)
    banner("Nothing copied: " + refused.join(", ") + reason, true);
  else if (unoffered.length)
    banner(unoffered.join(", ") + " copied, but only drawings appear here. " +
           "A drawing's opening string has a Drawing: line with its name.", true);
  else if (landed)
    banner(landed + " " + what + " copied to the drive.");
  draw();
}

async function removeFromDrive(name, kind) {
  var media = kind === "drawing" ? screenHooks.mediaNamed(name) : null;
  var thumbs = [];
  if (media && media.thumbHandle) {
    var stem = name.replace(/\.py$/i, "");
    thumbs.push(stem + ".png");
    Object.keys(media.styleThumbs || {}).forEach(function (style) {
      thumbs.push(stem + "-" + style + ".png");
    });
  }
  var said = kind === "folder"
    ? "Delete the folder " + name + " and every picture in it from the FX drive?"
    : "Delete " + name + " from the FX drive?";
  if (!confirm(said)) return;
  try {
    var home = mediaHome[name] || state.dirHandle;
    await home.removeEntry(name, {recursive: kind === "folder"});
    await removePictures(home, thumbs);
  } catch (e) {
    banner("Could not delete " + name + ". " + await driveTrouble(e, name), true);
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

(function () {
  var file = document.getElementById("preview").closest("details");
  if (file) file.open = false;
}());

async function entryIn(folder, name) {
  try {
    return await folder.getFileHandle(name);
  } catch (e) {
    try {
      return await folder.getDirectoryHandle(name);
    } catch (e2) {
      return null;
    }
  }
}

async function scanNamed(dir, text) {
  var names = [];
  var named = /\b(?:file|folder)=(?:"([^"]+)"|(\S+))/g;
  for (var found = named.exec(text); found; found = named.exec(text)) {
    names.push(found[1] || found[2]);
  }
  if (!names.length || scanBusy) return;
  driveParts.forEach(function (part) { if (part.begin) part.begin(); });
  var homes = Object.create(null);
  async function offerIn(folder, file, name) {
    var handle = await entryIn(folder, file);
    if (!handle) return false;
    for (var at = 0; at < driveParts.length; at++) {
      var take = handle.kind === "file" ? driveParts[at].file : driveParts[at].folder;
      if (take && await take(name, handle)) {
        homes[name] = folder;
        return true;
      }
    }
    return false;
  }
  for (var name of names) {
    var parts = name.split("/");
    var file = parts.pop();
    var places = parts.length ? [parts] : [[mediaFolderFor(file) || "pictures"], []];
    for (var place of places) {
      var folder = await folderAt(dir, place);
      if (!folder || !await offerIn(folder, file, name)) continue;
      if (/\.py$/i.test(file)) {
        await offerIn(folder, file.replace(/\.py$/i, ".png"), name.replace(/\.py$/i, ".png"));
      }
      break;
    }
  }
  mediaHome = homes;
  driveParts.forEach(function (part) { if (part.land) part.land(); });
}

connectSteps.push(async function () {
  state.fileHandle = drive.fileHandle;
  draw();
  try {
    await scanNamed(drive.dirHandle, await (await drive.fileHandle.getFile()).text());
  } catch (e) {
  }
  draw();
  scanMedia(drive.dirHandle).then(draw, function () {});
});

setInterval(rescanMedia, 5000);
