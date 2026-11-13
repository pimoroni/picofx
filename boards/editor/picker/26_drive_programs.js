import {banner} from "./00_banner.js";
import {draw} from "./00_draw.js";
import {BOARD} from "./01_looks.js";
import {drive, driveTrouble, isHiddenName} from "./18_drive.js";
import {PROGRAMS, boardSet, programNamed, setPrograms} from "./19_board_settings.js";

export var EXAMPLES_ROOT = BOARD.examples ? "examples/programs/" : "";

export var OWN_FOLDER = "programs";

export var SECTIONS = [];

export var PICTURES = {};

export var programsReading = null;

export var driveHasCredentials = false;

var EXAMPLE_NEEDS = {screens: "a screen", audio: "a speaker", motors: "motors", servos: "a servo",
                     strips: "a strip"};

var PROGRAM_USES = [["outputs", "{board}\\.(outputs|monos)\\b|ColourPlayer|MonoPlayer"],
                    ["rgb", "{board}\\.rgb\\b"],
                    ["screen", "^from screens import|SPCE\\.SCREEN"],
                    ["pair", "ScreenPair"],
                    ["hub", "{board}\\.hub\\b|SPCE\\.HUB"],
                    ["strip", "{board}\\.strip_[lr]\\b"],
                    ["sound", "{board}\\.wav\\b"],
                    ["remote", "aye_arr|from sensor import IR"],
                    ["qwst", "^from (breakout_\\w+|lsm6ds3) import"],
                    ["analog", "sensor=ANALOG\\)"],
                    ["motor", "MotorDriver|SPCE\\.MOTOR"],
                    ["servo", "^from servo import|{board}\\.servo_[lr]\\b"],
                    ["wifi", "^import network|urequests|^import requests"],
                    ["button", "Press \"Boot\" (?!to exit)|press Boot|boot_taps"]];

var EITHER_SCREEN = "for port in \\({board}\\.spce_a, {board}\\.spce_b\\)";

var ARGUMENT_KINDS = {"Screen size": "size", "Rotation": "rotation"};

var BOARD_MADE = /^(\w+)\s*=\s*\w*FX\(/m;

var PROGRAM_LINE = /^\s*(Program|Args|Picture|Section|Thumbnail|Firmware):\s*(.+?)\s*$/;

function programPattern(pattern, board) {
  var name = board ? board.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : "\\b\\B";
  return new RegExp(pattern.split("{board}").join(name), "m");
}

function usesInSource(source) {
  var made = source.match(BOARD_MADE);
  var board = made ? made[1] : null;
  var found = PROGRAM_USES.filter(function (use) {
    return programPattern(use[1], board).test(source);
  }).map(function (use) { return use[0]; });
  if (programPattern(EITHER_SCREEN, board).test(source)) {
    found = found.map(function (name) { return name === "pair" ? "either" : name; });
    if (found.indexOf("either") < 0) found.push("either");
  } else if (/spce_b=SPCE\.SCREEN/.test(source) && found.indexOf("pair") < 0) {
    found.push("pair");
  }
  if (found.some(function (name) { return ["pair", "hub", "either"].indexOf(name) >= 0; }))
    found = found.filter(function (name) { return name !== "screen"; });
  return found;
}

export function argumentFrom(text) {
  var split = text.indexOf("=");
  var name = (split < 0 ? text : text.slice(0, split)).trim();
  var argument = {name: name, kind: ARGUMENT_KINDS[name] || "text"};
  if (split >= 0) {
    var choices = text.slice(split + 1).trim().split(/\s+or\s+/);
    argument["default"] = choices[0];
    if (choices.length > 1) argument.choices = choices;
  }
  return argument;
}

export function openingString(source) {
  var found = source.match(/("""|''')([\s\S]*?)\1/);
  return found ? found[2].trim() : "";
}

export function programFrom(path, folder, source) {
  var opening = openingString(source);
  if (/^\s*Drawing:/m.test(opening)) return null;
  var program = {path: path, folder: folder,
                 example: isExample(path),
                 name: null, does: "", args: null, picture: null, section: null, thumbnail: null,
                 needs: EXAMPLE_NEEDS[folder.split("/")[0]] || null, uses: usesInSource(source)};
  var said = opening.split("\n").filter(function (line) {
    var told = line.match(PROGRAM_LINE);
    if (!told) return true;
    if (told[1] === "Program") program.name = told[2];
    else if (told[1] === "Args") program.args = told[2].split(",").map(argumentFrom);
    else if (told[1] === "Picture") program.picture = told[2];
    else if (told[1] === "Section") program.section = told[2];
    else if (told[1] === "Firmware") program.firmware = told[2];
    else program.thumbnail = told[2].split(/\s+/).join(":");
    return false;
  }).join(" ").split(/\s+/).join(" ").trim();
  var first = said.match(/^(.*?\.)(\s|$)/);
  program.does = first ? first[1] : said;
  if (!program.args && source.indexOf("sys.argv") < 0) program.args = [];
  return program;
}

export function sectionsFrom(text) {
  return text.split("\n").map(function (line) { return line.trim(); }).filter(function (line) {
    return line && line.charAt(0) !== "#";
  }).map(function (line) {
    var at = line.indexOf("|");
    return at < 0 ? [line, ""] : [line.slice(0, at).trim(), line.slice(at + 1).trim()];
  });
}

export async function folderAt(dir, parts) {
  for (var i = 0; i < parts.length; i++) {
    try {
      dir = await dir.getDirectoryHandle(parts[i]);
    } catch (e) {
      return null;
    }
  }
  return dir;
}

async function filesIn(dir, path, folder, deep, files, pictures) {
  var entries = [];
  for await (var pair of dir.entries()) {
    if (!isHiddenName(pair[0])) entries.push(pair);
  }
  entries.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  for (var i = 0; i < entries.length; i++) {
    var name = entries[i][0], handle = entries[i][1];
    if (handle.kind === "directory") {
      if (deep) await filesIn(handle, path + name + "/", folder ? folder + "/" + name : name,
                              deep, files, pictures);
    } else if (/\.png$/i.test(name)) {
      pictures[path + name] = handle;
    } else if (!path && /^secrets\.py$/i.test(name)) {
      driveHasCredentials = true;
    } else if (/\.py$/i.test(name)) {
      if (!deep || folder) files.push([path + name, folder, handle]);
    } else if (name === "sections.txt" && deep && !folder) {
      try {
        SECTIONS = sectionsFrom(await (await handle.getFile()).text()).map(function (section) {
          var parts = section[1].split("|");
          return [section[0], parts[0].trim(), (parts[1] || "").trim() === "folded"];
        });
      } catch (e) {
        SECTIONS = [];
      }
    }
  }
}

async function picturesOf(program, pictures) {
  var stem = program.path.replace(/\.py$/i, "");
  var beside = stem.slice(0, stem.lastIndexOf("/") + 1);
  var names = [program.picture ? beside + program.picture : stem + ".png", stem + "-2.png"];
  var found = [];
  for (var i = 0; i < names.length; i++) {
    if (!pictures[names[i]]) break;
    try {
      found.push(URL.createObjectURL(await pictures[names[i]].getFile()));
    } catch (e) {
      break;
    }
  }
  return found;
}

function isExample(path) {
  return !!EXAMPLES_ROOT && path.indexOf(EXAMPLES_ROOT) === 0;
}

export async function drivePrograms(dir, ownOnly) {
  var files = [], pictures = {}, found = [];
  driveHasCredentials = false;
  var read = {};
  if (ownOnly) {
    Object.keys(PICTURES).forEach(function (path) {
      if (isExample(path)) read[path] = PICTURES[path];
    });
  }
  await filesIn(dir, "", "", false, files, pictures);
  var own = await folderAt(dir, [OWN_FOLDER]);
  if (own) await filesIn(own, OWN_FOLDER + "/", "", false, files, pictures);
  if (ownOnly) {
    found = PROGRAMS.filter(function (program) { return program.example; });
  } else {
    SECTIONS = [];
    var examples = EXAMPLES_ROOT ? await folderAt(dir, EXAMPLES_ROOT.split("/").filter(Boolean))
                                 : null;
    if (examples) await filesIn(examples, EXAMPLES_ROOT, "", true, files, pictures);
    programsReading = [0, files.length];
    draw();
  }
  for (var i = 0; i < files.length; i++) {
    try {
      var source = await (await files[i][2].getFile()).text();
      var program = programFrom(files[i][0], files[i][1], source);
      if (program) {
        found.push(program);
        var shown = await picturesOf(program, pictures);
        if (shown.length) read[program.path] = shown;
      }
    } catch (e) {
    }
    if (programsReading) {
      programsReading[0] = i + 1;
      if (i % 8 === 7) draw();
    }
  }
  if (!ownOnly) programsReading = null;
  Object.keys(PICTURES).forEach(function (path) {
    if (read[path] !== PICTURES[path]) PICTURES[path].forEach(URL.revokeObjectURL);
  });
  PICTURES = read;
  var urls = [];
  Object.keys(PICTURES).forEach(function (path) { urls = urls.concat(PICTURES[path]); });
  loadThumbs(urls);
  ownSeen = await ownState(dir);
  return found;
}

var ownSeen = "";

async function ownState(dir) {
  var seen = [];
  async function note(folder, path) {
    for await (var pair of folder.entries()) {
      if (pair[1].kind !== "file" || isHiddenName(pair[0]) || !/\.(py|png)$/i.test(pair[0]))
        continue;
      var file = await pair[1].getFile();
      seen.push(path + pair[0] + " " + file.size + " " + file.lastModified);
    }
  }
  await note(dir, "");
  var own = await folderAt(dir, [OWN_FOLDER]);
  if (own) await note(own, OWN_FOLDER + "/");
  return seen.sort().join("\n");
}

export function forgetMissingPrograms() {
  if (boardSet.program && !programNamed(boardSet.program)) boardSet.program = null;
}

var programsBusy = false;
async function rescanPrograms() {
  if (!drive.dirHandle || programsBusy || !programsKnown) return;
  programsBusy = true;
  try {
    if (await ownState(drive.dirHandle) !== ownSeen) {
      setPrograms(await drivePrograms(drive.dirHandle, true));
      forgetMissingPrograms();
      draw();
    }
  } catch (e) {
  }
  programsBusy = false;
}

setInterval(rescanPrograms, 5000);

export async function copyToOwn(from, name, into, own, suffixes) {
  var stem = name.replace(/\.py$/i, "");
  var base = own ? stem.replace(/_\d+$/, "") : stem;
  var source = await (await (await from.getFileHandle(name)).getFile()).text();
  var taken = {};
  for await (var entry of into.keys()) taken[entry.toLowerCase()] = true;
  if (own) taken[base.toLowerCase() + ".py"] = true;
  var copy = base;
  for (var count = 2; taken[copy.toLowerCase() + ".py"]; count++) copy = base + "_" + count;
  var written = [[copy + ".py", source.replace(/^[ \t]*Section:.*\r?\n/m, "")]];
  for (var suffix of suffixes) {
    try {
      written.push([copy + suffix, await (await from.getFileHandle(stem + suffix)).getFile()]);
    } catch (e) {
    }
  }
  for (var i = 0; i < written.length; i++) {
    var writable = await (await into.getFileHandle(written[i][0], {create: true})).createWritable();
    await writable.write(written[i][1]);
    await writable.close();
  }
  return copy + ".py";
}

export async function copyProgram(path) {
  var parts = path.split("/");
  var name = parts.pop();
  var from = await folderAt(drive.dirHandle, parts);
  var into = await drive.dirHandle.getDirectoryHandle(OWN_FOLDER, {create: true});
  var own = !(programNamed(path) || {}).example;
  return OWN_FOLDER + "/" + await copyToOwn(from, name, into, own, [".png", "-2.png"]);
}

export async function removePictures(dir, names) {
  for (var picture of names) {
    try {
      await dir.removeEntry(picture);
    } catch (e) {
    }
  }
}

export async function removeProgram(path) {
  var parts = path.split("/");
  var name = parts.pop();
  if (!confirm("Delete " + name + " from the FX drive?")) return;
  try {
    var dir = await folderAt(drive.dirHandle, parts);
    await dir.removeEntry(name);
    if (parts.join("/") === OWN_FOLDER) {
      var stem = name.replace(/\.py$/i, "");
      await removePictures(dir, [stem + ".png", stem + "-2.png"]);
    }
  } catch (e) {
    banner("Could not delete " + name + ". " + await driveTrouble(e, name), true);
    return;
  }
  setPrograms(await drivePrograms(drive.dirHandle, true));
  forgetMissingPrograms();
  draw();
}

export var programsKnown = false;

export var programsReadSteps = [];

export async function openDrivePrograms() {
  programsKnown = false;
  await readNamedProgram();
  readDrivePrograms();
}

async function readNamedProgram() {
  try {
    var text = await (await drive.fileHandle.getFile()).text();
    var named = text.match(/^\s*board\s*:.*?\bprogram=("[^"]+"|\S+)/im);
    if (!named) return;
    var path = named[1].replace(/^"|"$/g, "");
    var parts = path.split("/");
    var name = parts.pop();
    var folder = await folderAt(drive.dirHandle, parts);
    var source = await (await (await folder.getFileHandle(name)).getFile()).text();
    var below = isExample(path) ? path.slice(EXAMPLES_ROOT.length) : "";
    var program = programFrom(path, below.slice(0, Math.max(below.lastIndexOf("/"), 0)), source);
    if (!program) return;
    setPrograms([program]);
    var beside = parts.length ? parts.join("/") + "/" : "";
    var stem = name.replace(/\.py$/i, "");
    var pictures = {};
    for (var picture of [program.picture || stem + ".png", stem + "-2.png"]) {
      try {
        pictures[beside + picture] = await folder.getFileHandle(picture);
      } catch (e) {
      }
    }
    var shown = await picturesOf(program, pictures);
    if (shown.length) {
      PICTURES[path] = shown;
      loadThumbs(shown);
    }
  } catch (e) {
  }
}

async function readDrivePrograms() {
  setPrograms(await drivePrograms(drive.dirHandle));
  programsKnown = true;
  forgetMissingPrograms();
  programsReadSteps.forEach(function (step) { step(); });
  draw();
}

export var thumbImages = {};

export function loadThumbs(sources) {
  var waiting = 0;
  sources.forEach(function (src) {
    if (thumbImages[src]) return;
    var image = thumbImages[src] = new Image();
    waiting++;
    image.onload = image.onerror = function () {
      waiting--;
      if (!waiting) draw();
    };
    image.src = src;
  });
}
