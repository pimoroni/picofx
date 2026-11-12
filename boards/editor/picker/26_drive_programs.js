
// ---- the programs on the drive ------------------------------------------------------------------
// Opening the drive reads the programs it holds, every Python file at its top level, in OWN_FOLDER
// and under EXAMPLES_ROOT, so the page offers what this drive carries and nothing it does not. A
// file whose opening string has a "Drawing:" line is a drawing for a screen, not a program, so it
// is left out, as is the WiFi credentials file at the top level.
//
// Every program is read the same way. Lines in its opening string say how to show it: "Program:"
// its name, "Args:" what it takes, "Picture:" a picture beside it to show it by, "Section:" the
// program tab's section it is offered in, "Thumbnail:" what its thumbnail draws where it has no
// picture, and "Firmware:" the lowest firmware it runs on. The first sentence of the rest says what
// it does. What it uses is read from its source,
// and an example's folder says what it needs attached. A picture is the one named, else name.png
// beside it, and name-2.png beside it is a second screen's. sections.txt in EXAMPLES_ROOT orders
// the sections and says what each holds.

// Where the drive keeps its examples, on a board that carries them
var EXAMPLES_ROOT = BOARD.examples ? "examples/programs/" : "";

// The folder at the top of the drive for the user's own programs, where a customised example goes
var OWN_FOLDER = "programs";

// The program tab's sections, as [name, what it holds, whether it starts folded], in sections.txt's
// order
var SECTIONS = [];

// Each program's pictures as object URLs, by its path: its own, and a second screen's after it
var PICTURES = {};

// How far reading the programs has got, as [read, of], while it is under way, else null
var programsReading = null;

// Whether the drive holds the WiFi credentials, which a board with a wireless module keeps at its
// top level, so the programs that go online are offered
var driveHasCredentials = false;

// What each examples folder needs attached, as the manual says
var EXAMPLE_NEEDS = {screens: "a screen", audio: "a speaker", motors: "motors", servos: "a servo",
                     strips: "a strip"};

// What a program uses beyond the board, read from its source, {board} standing for the name the
// program gives the board. Every example exits on Boot, so Boot counts only where its opening
// string gives the button another job
var PROGRAM_USES = [["outputs", "{board}\\.(outputs|monos)\\b|ColourPlayer|MonoPlayer"],
                    ["rgb", "{board}\\.rgb\\b"],
                    ["screen", "^from screens import|SPCE\\.SCREEN"],
                    ["pair", "ScreenPair"],
                    ["hub", "{board}\\.hub\\b|SPCE\\.HUB"],
                    ["strip", "{board}\\.strip_[lr]\\b"],
                    ["sound", "{board}\\.wav\\b"],
                    ["remote", "aye_arr|from sensor import IR"],
                    ["qwst", "^from (breakout_\\w+|lsm6ds3) import"],
                    // Only where one is needed, an optional one being written "ANALOG if"
                    ["analog", "sensor=ANALOG\\)"],
                    ["motor", "MotorDriver|SPCE\\.MOTOR"],
                    ["servo", "^from servo import|{board}\\.servo_[lr]\\b"],
                    ["wifi", "^import network|urequests|^import requests"],
                    ["button", "Press \"Boot\" (?!to exit)|press Boot|boot_taps"]];

// A program that looks for a screen on each port runs on one or on two
var EITHER_SCREEN = "for port in \\({board}\\.spce_a, {board}\\.spce_b\\)";

// The arguments an Args line names that are offered as a choice, by name. Any other is typed
var ARGUMENT_KINDS = {"Screen size": "size", "Rotation": "rotation"};

// The name a program gives the board, from the line that makes it, such as mighty = MightyFX()
var BOARD_MADE = /^(\w+)\s*=\s*\w*FX\(/m;

// The lines of an opening string that say how to show the program
var PROGRAM_LINE = /^\s*(Program|Args|Picture|Section|Thumbnail|Firmware):\s*(.+?)\s*$/;

// A pattern with the program's name for the board put in place of {board}, one matching nothing
// where the program makes no board
function programPattern(pattern, board) {
  var name = board ? board.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : "\\b\\B";
  return new RegExp(pattern.split("{board}").join(name), "m");
}

// What a program's source says it uses, in PROGRAM_USES order
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
  // Two screens or a hub are more than one screen, so they say it for it
  if (found.some(function (name) { return ["pair", "hub", "either"].indexOf(name) >= 0; }))
    found = found.filter(function (name) { return name !== "screen"; });
  return found;
}

// One argument an Args line names, "Name", "Name = default" or "Name = default or other", the
// default given unless it is told, and the choices where it names more than one
function argumentFrom(text) {
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

// A Python file's opening string, the first one written in triple quotes, or "" where it has none
function openingString(source) {
  var found = source.match(/("""|''')([\s\S]*?)\1/);
  return found ? found[2].trim() : "";
}

// One program as the page describes it, from its path, its folder under EXAMPLES_ROOT ("" for one
// at the top of the drive) and its source, or null for a drawing
function programFrom(path, folder, source) {
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
  // Without an Args line, one reading sys.argv takes whatever it is given, and any other nothing
  if (!program.args && source.indexOf("sys.argv") < 0) program.args = [];
  return program;
}

// The sections sections.txt lists, a line each as its name, a |, and what it holds
function sectionsFrom(text) {
  return text.split("\n").map(function (line) { return line.trim(); }).filter(function (line) {
    return line && line.charAt(0) !== "#";
  }).map(function (line) {
    var at = line.indexOf("|");
    return at < 0 ? [line, ""] : [line.slice(0, at).trim(), line.slice(at + 1).trim()];
  });
}

// The folder a path's parts lead to on the drive, or null where one of them is not there
async function folderAt(dir, parts) {
  for (var i = 0; i < parts.length; i++) {
    try {
      dir = await dir.getDirectoryHandle(parts[i]);
    } catch (e) {
      return null;
    }
  }
  return dir;
}

// The Python files and pictures in a folder of the drive, by path, and those of the folders inside
// it where deep, walked in name order
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
      // The WiFi credentials, which programs import, are not a program
      driveHasCredentials = true;
    } else if (/\.py$/i.test(name)) {
      if (!deep || folder) files.push([path + name, folder, handle]);
    } else if (name === "sections.txt" && deep && !folder) {
      try {
        // A third column of "folded" starts the section folded
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

// A program's pictures: the one it names or name.png beside it, and name-2.png beside it
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

// Whether a path is one of the drive's examples
function isExample(path) {
  return !!EXAMPLES_ROOT && path.indexOf(EXAMPLES_ROOT) === 0;
}

// Every program on the drive, the program tab counting them in as they are read. With ownOnly
// only the user's own are read again and the examples kept as they were
async function drivePrograms(dir, ownOnly) {
  var files = [], pictures = {}, found = [];
  driveHasCredentials = false;
  // The pictures read now, landed whole at the end, so those showing stay until replaced
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
    renderProgramView();
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
      // One that will not read is left out, as if it were not there
    }
    if (programsReading) {
      programsReading[0] = i + 1;
      if (i % 8 === 7) renderProgramView();
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

// The user's own programs and pictures as last read, by name, size and time saved
var ownSeen = "";

// The user's own programs and pictures as they are now, by name, size and time saved, cheap to
// take as no file is read
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

// Forget a chosen program the drive no longer holds, as it is no longer there to run
function forgetMissingPrograms() {
  if (boardSet.program && !programNamed(boardSet.program)) boardSet.program = null;
}

// Read the user's own programs again where they have changed on the drive, as the effects' media
// are, so a program saved from an editor shows without opening the drive again
var programsBusy = false;
async function rescanPrograms() {
  // Not until every program has been read once, as the examples are kept from that read
  if (!drive.dirHandle || programsBusy || !programsKnown) return;
  programsBusy = true;
  try {
    if (await ownState(drive.dirHandle) !== ownSeen) {
      PROGRAMS = await drivePrograms(drive.dirHandle, true);
      forgetMissingPrograms();
      draw();
    }
  } catch (e) {
    // A drive that went away is read again when it is opened
  }
  programsBusy = false;
}

setInterval(rescanPrograms, 5000);

// Copy a Python file from one folder into the user's own, with the pictures named after it renamed
// to match, for the user to change. An example keeps its name where it is free, and the user's own
// always takes a new one, its number counted on, so name_2 duplicates as the first of name_3,
// name_4 and on that is free. Its Section line is dropped so the copy is listed as the user's own.
// Returns the copy's file name
async function copyToOwn(from, name, into, own, suffixes) {
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
      // A file without that picture has none to copy
    }
  }
  for (var i = 0; i < written.length; i++) {
    var writable = await (await into.getFileHandle(written[i][0], {create: true})).createWritable();
    await writable.write(written[i][1]);
    await writable.close();
  }
  return copy + ".py";
}

// Copy a program into OWN_FOLDER for the user to change, its pictures with it. Returns the copy's
// path
async function copyProgram(path) {
  var parts = path.split("/");
  var name = parts.pop();
  var from = await folderAt(drive.dirHandle, parts);
  var into = await drive.dirHandle.getDirectoryHandle(OWN_FOLDER, {create: true});
  var own = !(programNamed(path) || {}).example;
  return OWN_FOLDER + "/" + await copyToOwn(from, name, into, own, [".png", "-2.png"]);
}

// Delete the pictures beside a file, skipping any it does not have
async function removePictures(dir, names) {
  for (var picture of names) {
    try {
      await dir.removeEntry(picture);
    } catch (e) {
      // One without that picture has none to delete
    }
  }
}

// Delete one of the user's own programs from the drive, once asked. In OWN_FOLDER its pictures go
// with it, while at the top of the drive they are left, as the effects may show them too
async function removeProgram(path) {
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
  PROGRAMS = await drivePrograms(drive.dirHandle, true);
  forgetMissingPrograms();
  draw();
}

// Whether the open drive's programs have been read, which takes a while as each file is read whole
var programsKnown = false;

// The program effects.txt names is read first, so the file is read back with it known, and the rest
// without holding up the steps after
connectSteps.push(async function () {
  programsKnown = false;
  await readNamedProgram();
  readDrivePrograms();
});

// The program effects.txt's board line names, read on its own as the list of programs to begin with
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
    // An example's folder below EXAMPLES_ROOT, as the walk records it
    var below = isExample(path) ? path.slice(EXAMPLES_ROOT.length) : "";
    var program = programFrom(path, below.slice(0, Math.max(below.lastIndexOf("/"), 0)), source);
    if (!program) return;
    PROGRAMS = [program];
    // Its pictures with it, found beside it as the walk would find them
    var beside = parts.length ? parts.join("/") + "/" : "";
    var stem = name.replace(/\.py$/i, "");
    var pictures = {};
    for (var picture of [program.picture || stem + ".png", stem + "-2.png"]) {
      try {
        pictures[beside + picture] = await folder.getFileHandle(picture);
      } catch (e) {
        // One it has not got
      }
    }
    var shown = await picturesOf(program, pictures);
    if (shown.length) {
      PICTURES[path] = shown;
      loadThumbs(shown);
    }
  } catch (e) {
    // Found with the rest, or not at all
  }
}

async function readDrivePrograms() {
  PROGRAMS = await drivePrograms(drive.dirHandle);
  programsKnown = true;
  forgetMissingPrograms();
  readWaitingProgram();
  draw();
}
