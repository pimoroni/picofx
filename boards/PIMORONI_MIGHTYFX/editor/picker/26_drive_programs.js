
// ---- the programs on the drive ------------------------------------------------------------------
// Opening the drive lists the programs it holds: every Python file at its top level, each described
// by its opening string as the examples are. A file whose opening string starts "Drawing:" is a
// drawing for a screen, not a program, so it is left out. A "Picture:" line names a picture on the
// drive that the program is shown by.

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

var oneProgramsConnect = connect;

connect = async function (fresh) {
  await oneProgramsConnect(fresh);
  DRIVE_PROGRAMS = await drivePrograms(drive.dirHandle);
  await drivePictures(drive.dirHandle, DRIVE_PROGRAMS);
  // A program the page had chosen that this drive does not hold is no longer there to run
  if (boardSet.program && !programNamed(boardSet.program)) boardSet.program = null;
  if (boardSet.lastProgram && !programNamed(boardSet.lastProgram)) boardSet.lastProgram = null;
  draw();
};
