
// ---- the board's own settings -----------------------------------------------------------------
// Three settings belong to the board and to no section: whether a save plays without an eject,
// which reload=manual turns off, whether the drive stays hidden at start (drive=manual), and a
// program run in place of the effects (program= and args=). They are the board's, so no scene
// keeps them. The pages built on this one each put them somewhere different, using what is here.

// Saving without an eject starts on
var boardSet = {reload: true, driveHidden: false, program: null, args: {}};

// The programs on the drive, read once a drive is open, its own and the examples alike: each one's
// path, name, what it does, the arguments it takes, its section and thumbnail, and what it uses and
// needs. 26_drive_programs.js reads them
var PROGRAMS = [];

// The program at a path, or null where the drive holds none there
function programNamed(path) {
  return PROGRAMS.filter(function (one) { return one.path === path; })[0] || null;
}

// A program's arguments as the file takes them, each one quoted where a space or a colon would
// otherwise divide it, and an empty one left out. A pipe divides them, so none can carry one. A
// program given only what it would take anyway is given nothing, so its line stays as short
function argsWritten(path) {
  var program = programNamed(path);
  if (program && program.args && program.args.length && program.args.every(function (argument, at) {
    var value = (boardSet.args[path] || [])[at];
    return "default" in argument && (value === undefined || value === argument.default);
  })) return "";
  var given = (boardSet.args[path] || []).map(function (arg) {
    return arg.replace(/[|"]/g, "").trim();
  }).filter(Boolean);
  return given.map(function (arg) { return /[\s:]/.test(arg) ? '"' + arg + '"' : arg; })
              .join("|");
}

// Whether keeping the drive hidden means anything, a program having it shown while it runs
function driveMeansSomething() { return !boardSet.program; }

boardLineSteps.after.push(function (line) {
  var tokens = [];
  if (boardSet.program) {
    tokens.push("program=" + boardSet.program);
    var args = argsWritten(boardSet.program);
    if (args) tokens.push("args=" + args);
  }
  if (boardSet.driveHidden) tokens.push("drive=manual");
  if (!boardSet.reload) tokens.push("reload=manual");
  if (!tokens.length) return line;
  var rest = line.replace(/^board: ?/, "");
  return "board: " + tokens.join(" ") + (rest ? " " + rest : "");
});

// ---- a program's arguments --------------------------------------------------------------------

// The screen size a program is first given: the size set for screen A, else the program's own
function sizeOffered(argument) {
  var screen = state.screens && state.screens.A;
  return screen && screen.there && screen.size ? screen.size : argument.default;
}

// The picked program's arguments: a box for each it names, a screen size chosen from those the
// firmware knows, or where it names none but reads sys.argv, plain boxes to add and take away
function argsFor(path, locked) {
  var program = programNamed(path);
  var given = boardSet.args[path] || (boardSet.args[path] = []);
  var box = document.createElement("div");
  box.className = "progargs";
  var named = !!program.args;
  var taken = program.args || given.map(function (arg, at) {
    return {name: "Argument " + (at + 1), kind: "text"};
  });
  taken.forEach(function (argument, at) {
    var label = document.createElement("label");
    label.textContent = argument.name;
    if (argument.kind === "size") {
      if (given[at] === undefined) given[at] = sizeOffered(argument);
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
      return;
    }
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

drawSteps.after.push(function () {
  document.body.classList.toggle("programmed", !!boardSet.program);
  programNote();
});
