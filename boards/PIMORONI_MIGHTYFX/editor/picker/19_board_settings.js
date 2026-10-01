
// ---- the board's own settings -----------------------------------------------------------------
// Three settings belong to the board and to no section: whether a save plays without an eject
// (reload=auto), whether the drive stays hidden at start (drive=manual), and a program run in
// place of the effects (program= and args=). They are the board's, so no scene keeps them. The
// pages built on this one each put them somewhere different, using what is here.

// Saving without an eject starts on
var boardSet = {reload: true, driveHidden: false, program: null, args: {}};

// The programs on the drive, as [name, opening string], listed once a drive is open. A program
// may say what it is in its opening string, as a drawing does: "Program:" and its name, a line on
// what it does, "Args:" naming what it takes, and "Picture:" naming a picture on the drive to show
// it by. One that says nothing is listed by its file name
var DRIVE_PROGRAMS = [];

// The examples that come with the board, read from its examples folder when the page is built:
// each one's path on the board, its folder, and the first sentence of its opening string
var BOARD_EXAMPLES = __EXAMPLES__;

// What an opening string says of a program: a name where it gives one, what it does, the
// arguments it names and the picture it is shown by, each null where it names none
function programSaid(docstring) {
  var lines = (docstring || "").split("\n").filter(function (line) { return line.trim(); });
  var said = {name: null, does: "", args: null, picture: null};
  lines.forEach(function (line) {
    var named = line.match(/^Program:\s*(.+)$/);
    var takes = line.match(/^Args:\s*(.+)$/);
    var shown = line.match(/^Picture:\s*(.+)$/);
    if (named) said.name = named[1].trim();
    else if (takes) said.args = takes[1].split(",").map(function (arg) { return arg.trim(); });
    else if (shown) said.picture = shown[1].trim();
    else if (!said.does) said.does = line.trim();
  });
  return said;
}

function programNamed(path) {
  var mine = DRIVE_PROGRAMS.filter(function (one) { return one[0] === path; })[0];
  if (mine) return Object.assign({path: path, onDrive: true}, programSaid(mine[1]));
  var example = BOARD_EXAMPLES.filter(function (one) { return one.path === path; })[0];
  return example ? {path: path, onDrive: false, name: null, does: example.does,
                    args: example.args || [], needs: example.needs}
                 : null;
}

// A program's arguments as the file takes them, each one quoted where a space or a colon would
// otherwise divide it, and an empty one left out. A pipe divides them, so none can carry one. An
// example given only what it would take anyway is given nothing, so its line stays as short
function argsWritten(path) {
  var program = programNamed(path);
  if (program && !program.onDrive && program.args.every(function (argument, at) {
    var value = (boardSet.args[path] || [])[at];
    return value === undefined || value === argument.default;
  })) return "";
  var given = (boardSet.args[path] || []).map(function (arg) {
    return arg.replace(/[|"]/g, "").trim();
  }).filter(Boolean);
  return given.map(function (arg) { return /[\s:]/.test(arg) ? '"' + arg + '"' : arg; })
              .join("|");
}

// Whether each of the others means anything, a program keeping the board busy while it runs
function savingMeansSomething() { return !boardSet.program; }
function driveMeansSomething() { return !boardSet.program; }

var oneSettingsBoardLine = boardLine;

boardLine = function () {
  var line = oneSettingsBoardLine();
  var tokens = [];
  if (boardSet.program) {
    tokens.push("program=" + boardSet.program);
    var args = argsWritten(boardSet.program);
    if (args) tokens.push("args=" + args);
  }
  if (boardSet.driveHidden) tokens.push("drive=manual");
  if (boardSet.reload) tokens.push("reload=auto");
  if (!tokens.length) return line;
  var rest = line.replace(/^board: ?/, "");
  return "board: " + tokens.join(" ") + (rest ? " " + rest : "");
};

// ---- the settings, drawn ----------------------------------------------------------------------

// A setting's row: its name, its choice, and a line under it where there is something to say
function boardRow(name, choice, hint) {
  var row = document.createElement("div");
  row.className = "boardrow";
  var label = document.createElement("span");
  label.className = "boardrowname";
  label.textContent = name;
  row.appendChild(label);
  row.appendChild(choice);
  if (hint) {
    var under = document.createElement("small");
    under.textContent = hint;
    row.appendChild(under);
  }
  return row;
}

// Whether the settings carry what the board runs, which a page choosing between an effects page
// and a program page does not
var boardRowsRun = true;

// The three settings, locked where the page only lets the board change while editing it
function boardRows(locked) {
  var rows = document.createElement("div");
  rows.className = "boardrows";
  var runs = segment([["effects", "the effects", locked], ["program", "a program", locked]],
                     boardSet.program ? "program" : "effects", function (value) {
                       if (value === "effects") {
                         boardSet.program = null;
                       } else if (!boardSet.program) {
                         boardSet.program = boardSet.lastProgram || DRIVE_PROGRAMS[0][0];
                       }
                     });
  if (boardRowsRun) rows.appendChild(boardRow("Runs", runs));

  var busy = !savingMeansSomething();
  var saving = segment([["auto", "plays without an eject", locked || busy],
                        ["manual", "waits for an eject", locked || busy]],
                       boardSet.reload ? "auto" : "manual",
                       function (value) { boardSet.reload = value === "auto"; });
  rows.appendChild(boardRow("Saving", saving,
    busy ? "a program keeps the board busy, so press its Reset button to play a change"
         : boardSet.reload ? "the board has to be running a file that says so, so the save " +
                             "that first turns this on still needs an eject"
                           : "eject the drive, or press Boot once, to play a save"));

  var shown = !driveMeansSomething();
  var driveChoice = segment([["shown", "shown at start", locked || shown],
                             ["hidden", "hidden until asked", locked || shown]],
                            boardSet.driveHidden ? "hidden" : "shown",
                            function (value) { boardSet.driveHidden = value === "hidden"; });
  rows.appendChild(boardRow("The drive", driveChoice,
    shown ? "shown anyway while a program runs, so it can always be changed back"
          : boardSet.driveHidden ? "double-press Boot to bring it back" : ""));
  if (boardSet.program && boardRowsRun) rows.appendChild(programChooser(locked));
  return rows;
}

// Where a program comes from and what it does, in a line
function programRow(path, locked) {
  var program = programNamed(path);
  var row = document.createElement("button");
  row.type = "button";
  row.className = "progrow" + (boardSet.program === path ? " on" : "");
  row.disabled = !!locked;
  var file = path.split("/").pop();
  row.innerHTML = "<b>" + escapeHtml(program.name || file) + "</b>" +
                  (program.name ? "<em>" + escapeHtml(file) + "</em>" : "") +
                  (program.needs ? "<em>needs " + escapeHtml(program.needs) + "</em>" : "") +
                  "<small>" + escapeHtml(program.does || "says nothing about itself") + "</small>";
  row.onclick = function () {
    boardSet.program = path;
    boardSet.lastProgram = path;
    draw();
  };
  return row;
}

// The screen size a program is first given: the size set for screen A, else the program's own
function sizeOffered(argument) {
  var screen = state.screens && state.screens.A;
  return screen && screen.there && screen.size ? screen.size : argument.default;
}

// The picked program's arguments. An example takes only what it reads, a screen size chosen from
// those the firmware knows. A program on the drive gets a box for each its opening string names,
// or plain ones to add and take away
function argsFor(path, locked) {
  var program = programNamed(path);
  var given = boardSet.args[path] || (boardSet.args[path] = []);
  var box = document.createElement("div");
  box.className = "progargs";
  if (!program.onDrive) {
    program.args.forEach(function (argument, at) {
      if (given[at] === undefined) given[at] = sizeOffered(argument);
      var label = document.createElement("label");
      label.textContent = argument.name;
      var choice = document.createElement("select");
      choice.disabled = !!locked;
      SCREEN_SIZES.forEach(function (inches) {
        var option = document.createElement("option");
        option.value = inches;
        option.textContent = inches + "\"";
        option.selected = given[at] === inches;
        choice.appendChild(option);
      });
      choice.onchange = function () {
        given[at] = choice.value;
        draw();
      };
      label.appendChild(choice);
      box.appendChild(label);
    });
    return box;
  }
  var named = !!program.args;
  var names = program.args || given.map(function (arg, at) { return "Argument " + (at + 1); });
  names.forEach(function (name, at) {
    var label = document.createElement("label");
    label.textContent = name;
    var field = document.createElement("input");
    field.value = given[at] || "";
    field.disabled = !!locked;
    field.oninput = function () {
      given[at] = field.value;
      renderPreview();
    };
    field.onchange = function () { draw(); };
    label.appendChild(field);
    // An argument added by hand can be taken away again, the rest moving up
    if (!named) {
      var gone = document.createElement("button");
      gone.type = "button";
      gone.className = "progless";
      gone.innerHTML = "&times;";
      gone.title = "Take this argument away";
      gone.disabled = !!locked;
      gone.onclick = function () {
        given.splice(at, 1);
        draw();
      };
      label.appendChild(gone);
    }
    box.appendChild(label);
  });
  if (!named) {
    var more = document.createElement("button");
    more.type = "button";
    more.className = "progmore";
    more.textContent = "+ an argument";
    more.disabled = !!locked;
    more.title = "Something to pass the program, which it reads from sys.argv";
    more.onclick = function () {
      given.push("");
      draw();
    };
    box.appendChild(more);
  }
  return box;
}

// Programs on the drive first, then the examples that come with the board by folder, the
// picked one's arguments under it. A drawing is a screen's picture, so it is not listed
function programChooser(locked) {
  var box = document.createElement("div");
  box.className = "chooser";
  function heading(words) {
    var said = document.createElement("div");
    said.className = "progheading";
    said.textContent = words;
    box.appendChild(said);
  }
  function listed(path, into) {
    into.appendChild(programRow(path, locked));
    if (boardSet.program === path) into.appendChild(argsFor(path, locked));
  }
  heading("On the drive");
  DRIVE_PROGRAMS.forEach(function (one) { listed(one[0], box); });
  heading("Come with the board");
  // A folder of folders, such as screens, opens onto its own, so the list starts short
  function fold(name, within, into) {
    var mine = BOARD_EXAMPLES.filter(function (one) {
      return one.folder === within || one.folder.indexOf(within + "/") === 0;
    });
    var node = document.createElement("details");
    node.className = "progfolder";
    node.open = mine.some(function (one) { return one.path === boardSet.program; }) ||
                !!openFolders[within];
    node.addEventListener("toggle", function () { openFolders[within] = node.open; });
    var summary = document.createElement("summary");
    summary.innerHTML = escapeHtml(name) + " <small>" + mine.length +
                        (mine.length === 1 ? " program" : " programs") + "</small>";
    node.appendChild(summary);
    mine.filter(function (one) { return one.folder === within; })
        .forEach(function (one) { listed(one.path, node); });
    foldersIn(within).forEach(function (inner) {
      fold(inner.split("/").pop(), inner, node);
    });
    into.appendChild(node);
  }
  foldersIn("").forEach(function (top) { fold(top, top, box); });
  return box;
}

// The folders directly inside one, the examples' own top folders for none
function foldersIn(within) {
  var found = [];
  BOARD_EXAMPLES.forEach(function (one) {
    var rest = within ? one.folder.slice(within.length + 1) : one.folder;
    if (within && one.folder.indexOf(within + "/") !== 0) return;
    var next = rest.split("/")[0];
    var path = within ? within + "/" + next : next;
    if (next && found.indexOf(path) < 0) found.push(path);
  });
  return found;
}

var openFolders = {};

// ---- the effects, while a program runs --------------------------------------------------------
// The board runs a program in their place, so they stand back with a note saying what runs
// instead. They are kept, and run again if the program is missing or stops

function programNote() {
  var note = document.getElementById("programNote");
  if (!note) {
    note = document.createElement("div");
    note.id = "programNote";
    note.className = "programnote";
    // Above the gallery, or above what a page has stacked it in
    var looks = document.getElementById("looksStack") || document.getElementById("looks");
    looks.parentNode.insertBefore(note, looks);
  }
  note.hidden = !boardSet.program;
  if (!boardSet.program) return;
  var program = programNamed(boardSet.program);
  note.textContent = "";
  note.appendChild(boardIcon());
  note.appendChild(document.createTextNode(
    "The board runs " + (program && program.name ? program.name + " (" + boardSet.program + ")"
                                                 : boardSet.program) +
    " in place of the effects. They are kept, and play if it is missing or stops, when " +
    "errors.txt says why."));
}

var oneSettingsDraw = draw;

draw = function () {
  oneSettingsDraw();
  document.body.classList.toggle("programmed", !!boardSet.program);
  programNote();
};
