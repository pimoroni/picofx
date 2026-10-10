
// ---- the programs on the drive ------------------------------------------------------------------
// Opening the drive lists the programs it holds: every Python file at its top level, each described
// by its opening string as the examples are. A file whose opening string starts "Drawing:" is a
// drawing for a screen, not a program, so it is left out. A "Picture:" line names a picture on the
// drive that the program is shown by. The examples' captured frames are read from beside them.

// A Python file's opening string, the first one written in triple quotes, or "" where it has none
function openingString(source) {
  var found = source.match(/("""|''')([\s\S]*?)\1/);
  return found ? found[2].trim() : "";
}

async function drivePrograms(dir) {
  var found = [];
  for await (var pair of dir.entries()) {
    var name = pair[0], handle = pair[1];
    if (handle.kind !== "file" || !/\.py$/i.test(name)) continue;
    var said = "";
    try {
      said = openingString(await (await handle.getFile()).text());
    } catch (e) {
      said = "";
    }
    if (/^Drawing:/.test(said)) continue;
    found.push([name, said]);
  }
  return found.sort(function (a, b) { return a[0] < b[0] ? -1 : 1; });
}

// Each program's named picture, read off the drive. One that is missing or will not read leaves
// the program shown by its plain tile
async function drivePictures(dir, programs) {
  Object.keys(DRIVE_PICTURES).forEach(function (name) { URL.revokeObjectURL(DRIVE_PICTURES[name]); });
  DRIVE_PICTURES = {};
  for (var i = 0; i < programs.length; i++) {
    var picture = programSaid(programs[i][1]).picture;
    if (!picture) continue;
    try {
      var file = await (await dir.getFileHandle(picture)).getFile();
      DRIVE_PICTURES[programs[i][0]] = URL.createObjectURL(file);
    } catch (e) {
      continue;
    }
  }
  loadThumbs(Object.keys(DRIVE_PICTURES).map(function (name) { return DRIVE_PICTURES[name]; }));
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

// Each example's captured frames, read from beside it on the drive, a pair's second screen being
// name-2.png. One the drive does not hold leaves the example its drawn tile
async function exampleThumbs(dir) {
  Object.keys(THUMBS).forEach(function (name) { URL.revokeObjectURL(THUMBS[name]); });
  THUMBS = {};
  var folders = {};
  for (var i = 0; i < BOARD_EXAMPLES.length; i++) {
    var parts = BOARD_EXAMPLES[i].path.split("/");
    var file = parts.pop().replace(/\.py$/, "");
    var where = parts.join("/");
    if (!(where in folders)) folders[where] = await folderAt(dir, parts);
    if (!folders[where]) continue;
    var names = [file, file + "-2"];
    for (var n = 0; n < names.length; n++) {
      try {
        var picture = await (await folders[where].getFileHandle(names[n] + ".png")).getFile();
        THUMBS[names[n]] = URL.createObjectURL(picture);
      } catch (e) {
        continue;
      }
    }
  }
  loadThumbs(Object.keys(THUMBS).map(function (name) { return THUMBS[name]; }));
}

connectSteps.push(async function () {
  DRIVE_PROGRAMS = await drivePrograms(drive.dirHandle);
  await drivePictures(drive.dirHandle, DRIVE_PROGRAMS);
  await exampleThumbs(drive.dirHandle);
  // A program the page had chosen that this drive does not hold is no longer there to run
  if (boardSet.program && !programNamed(boardSet.program)) boardSet.program = null;
  if (boardSet.lastProgram && !programNamed(boardSet.lastProgram)) boardSet.lastProgram = null;
  draw();
});
