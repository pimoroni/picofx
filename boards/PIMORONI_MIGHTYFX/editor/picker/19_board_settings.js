
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

// ---- a program's arguments --------------------------------------------------------------------

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
