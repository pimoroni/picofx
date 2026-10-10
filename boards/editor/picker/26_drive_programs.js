
// ---- the programs on the drive ------------------------------------------------------------------
// Opening the drive reads the programs it holds, every Python file at its top level and under
// EXAMPLES_ROOT, so the page offers what this drive carries and nothing it does not. A file whose
// opening string starts "Drawing:" is a drawing for a screen, not a program, so it is left out, as
// is the WiFi credentials file at the top level.
//
// Every program is read the same way. Lines in its opening string say how to show it: "Program:"
// its name, "Args:" what it takes, "Picture:" a picture beside it to show it by, "Section:" the
// program tab's section it is offered in, and "Thumbnail:" what its thumbnail draws where it has no
// picture. The first sentence of the rest says what it does. What it uses is read from its source,
// and an example's folder says what it needs attached. A picture is the one named, else name.png
// beside it, and name-2.png beside it is a second screen's. sections.txt in EXAMPLES_ROOT orders
// the sections and says what each holds.

// Where the drive keeps its examples, on a board that carries them
var EXAMPLES_ROOT = BOARD.examples ? "examples/python/" : "";

// The program tab's sections, as [name, what it holds], in sections.txt's order
var SECTIONS = [];

// Each program's pictures as object URLs, by its path: its own, and a second screen's after it
var PICTURES = {};

// How far reading the programs has got, as [read, of], while it is under way, else null
var programsReading = null;

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

// The screen size a program reads, with a default where none is given
var SIZE_ARGUMENT = /^SCREEN_SIZE = "([^"]+)" if not sys\.argv\[1:\] else sys\.argv\[1\]/m;

// The name a program gives the board, from the line that makes it, such as mighty = MightyFX()
var BOARD_MADE = /^(\w+)\s*=\s*\w*FX\(/m;

// The lines of an opening string that say how to show the program
var PROGRAM_LINE = /^\s*(Program|Args|Picture|Section|Thumbnail):\s*(.+?)\s*$/;

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

// A Python file's opening string, the first one written in triple quotes, or "" where it has none
function openingString(source) {
  var found = source.match(/("""|''')([\s\S]*?)\1/);
  return found ? found[2].trim() : "";
}

// One program as the page describes it, from its path, its folder under EXAMPLES_ROOT ("" for one
// at the top of the drive) and its source, or null for a drawing
function programFrom(path, folder, source) {
  var opening = openingString(source);
  if (/^Drawing:/.test(opening)) return null;
  var program = {path: path, folder: folder,
                 example: !!EXAMPLES_ROOT && path.indexOf(EXAMPLES_ROOT) === 0,
                 name: null, does: "", args: null, picture: null, section: null, thumbnail: null,
                 needs: EXAMPLE_NEEDS[folder.split("/")[0]] || null, uses: usesInSource(source)};
  var said = opening.split("\n").filter(function (line) {
    var told = line.match(PROGRAM_LINE);
    if (!told) return true;
    if (told[1] === "Program") program.name = told[2];
    else if (told[1] === "Args") program.args = told[2].split(",").map(function (arg) {
      return {name: arg.trim(), kind: "text"};
    });
    else if (told[1] === "Picture") program.picture = told[2];
    else if (told[1] === "Section") program.section = told[2];
    else program.thumbnail = told[2].split(/\s+/).join(":");
    return false;
  }).join(" ").split(/\s+/).join(" ").trim();
  var first = said.match(/^(.*?\.)(\s|$)/);
  program.does = first ? first[1] : said;
  // Without an Args line, what it reads: the screen size, else whatever is given where it reads
  // sys.argv at all, else nothing
  if (!program.args) {
    var size = source.match(SIZE_ARGUMENT);
    if (size) program.args = [{name: "Screen size", kind: "size", "default": size[1]}];
    else if (source.indexOf("sys.argv") < 0) program.args = [];
  }
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
  for await (var pair of dir.entries()) entries.push(pair);
  entries.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
  for (var i = 0; i < entries.length; i++) {
    var name = entries[i][0], handle = entries[i][1];
    if (handle.kind === "directory") {
      if (deep) await filesIn(handle, path + name + "/", folder ? folder + "/" + name : name,
                              deep, files, pictures);
    } else if (/\.png$/i.test(name)) {
      pictures[path + name] = handle;
    } else if (!deep && /^secrets\.py$/i.test(name)) {
      // The WiFi credentials, which programs import, are not a program
    } else if (/\.py$/i.test(name)) {
      if (!deep || folder) files.push([path + name, folder, handle]);
    } else if (name === "sections.txt" && deep && !folder) {
      try {
        SECTIONS = sectionsFrom(await (await handle.getFile()).text());
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

// Every program on the drive, the program tab counting them in as they are read
async function drivePrograms(dir) {
  var files = [], pictures = {}, found = [];
  SECTIONS = [];
  Object.keys(PICTURES).forEach(function (path) { PICTURES[path].forEach(URL.revokeObjectURL); });
  PICTURES = {};
  await filesIn(dir, "", "", false, files, pictures);
  var examples = EXAMPLES_ROOT ? await folderAt(dir, EXAMPLES_ROOT.split("/").filter(Boolean))
                               : null;
  if (examples) await filesIn(examples, EXAMPLES_ROOT, "", true, files, pictures);
  programsReading = [0, files.length];
  renderProgramView();
  for (var i = 0; i < files.length; i++) {
    try {
      var source = await (await files[i][2].getFile()).text();
      var program = programFrom(files[i][0], files[i][1], source);
      if (program) {
        found.push(program);
        var shown = await picturesOf(program, pictures);
        if (shown.length) PICTURES[program.path] = shown;
      }
    } catch (e) {
      // One that will not read is left out, as if it were not there
    }
    programsReading[0] = i + 1;
    if (i % 8 === 7) renderProgramView();
  }
  programsReading = null;
  var urls = [];
  Object.keys(PICTURES).forEach(function (path) { urls = urls.concat(PICTURES[path]); });
  loadThumbs(urls);
  return found;
}

connectSteps.push(async function () {
  PROGRAMS = await drivePrograms(drive.dirHandle);
  // A program the page had chosen that this drive does not hold is no longer there to run
  if (boardSet.program && !programNamed(boardSet.program)) boardSet.program = null;
  if (boardSet.lastProgram && !programNamed(boardSet.lastProgram)) boardSet.lastProgram = null;
  draw();
});
