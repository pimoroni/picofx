import {BOARD_LINE_AFTER, SCREEN_SIZES, boardLineSteps} from "./board.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "./draw.js";
import {renderPreview} from "./file_preview.js";
import {state} from "./scenes.js";
import {BOARD_SETTING_SAYS, boardIcon} from "./setup.js";

// ---- the board's own settings -----------------------------------------------------------------
// Three settings belong to the board and to no section. They are whether a save plays without an
// eject, which reload=manual turns off, whether the drive stays hidden at start (drive=manual),
// and a program run in place of the effects (program= and args=). They are the board's, so no
// scene keeps them. The pages built on this one each place them differently, using what is here.

// Saving without an eject starts on
export var boardSet = {reload: true, driveHidden: false, program: null, args: {}};

// The programs on the drive, read once a drive is open, its own and the examples alike. Each holds
// its path, name, what it does, the arguments it takes, its section and thumbnail, and what it
// uses. drivePrograms() in drive_programs.js reads them
export var PROGRAMS = [];

// Set the programs on the drive
export function setPrograms(list) {
  PROGRAMS = list;
}

// Lookups for programs the page shows that the drive does not hold, each given a path and
// returning its program or null
export var programsElsewhere = [];

// The program at a path, or null where neither the drive nor a lookup holds one there
export function programNamed(path) {
  var found = PROGRAMS.filter(function (one) { return one.path === path; })[0];
  for (var at = 0; !found && at < programsElsewhere.length; at++) found = programsElsewhere[at](path);
  return found || null;
}

// A program's arguments as the file takes them, each one quoted where a space or a colon would
// otherwise divide it, and an empty one left out. A pipe divides them, so none can carry one. A
// program given only what it would take anyway is given nothing, so its line stays short
export function argsWritten(path) {
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

// Whether keeping the drive hidden means anything, as a program has it shown while it runs
export function driveMeansSomething() { return !boardSet.program; }

addStep(boardLineSteps.after, BOARD_LINE_AFTER, "boardSettings", function (line) {
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

// The screen size a program is first given, which is the size set for screen A, else its own
function sizeOffered(argument) {
  var screen = state.screens && state.screens.A;
  return screen && screen.there && screen.size ? screen.size : argument.default;
}

// The choices an argument of each offered kind gives, as [value, how it is shown]. A rotation
// offers the four, or those its Args line names
var ARGUMENT_CHOICES = {
  size: function () {
    return SCREEN_SIZES.map(function (inches) { return [inches, inches + "\""]; });
  },
  rotation: function (argument) {
    return (argument.choices || ["0", "90", "180", "270"]).map(function (turn) {
      return [turn, turn + "&deg;"];
    });
  }
};

// The picked program's arguments, as a box for each it names. A screen size is chosen from those
// the firmware knows and a rotation from the four. A program that names none but reads sys.argv
// gets plain boxes to add and take away
export function argsFor(path, locked) {
  var program = programNamed(path);
  var given = boardSet.args[path] || (boardSet.args[path] = []);
  var named = !!program.args;
  var taken = program.args || given.map(function (arg, at) {
    return {name: "Argument " + (at + 1), kind: "text"};
  });
  return h("div", {className: "progargs"}, taken.map(function (argument, at) {
    if (ARGUMENT_CHOICES[argument.kind]) {
      var choices = ARGUMENT_CHOICES[argument.kind](argument);
      if (given[at] === undefined) {
        given[at] = argument.kind === "size" ? sizeOffered(argument)
                                             : argument.default || choices[0][0];
      }
      var choice = h("select", {
        disabled: !!locked,
        onchange: function () {
          given[at] = choice.value;
          draw();
        }
      }, choices.map(function (offered) {
        return h("option", {value: offered[0], selected: given[at] === offered[0],
                            html: offered[1]});
      }));
      return h("label", {}, argument.name, choice);
    }
    if (given[at] === undefined && "default" in argument) given[at] = argument.default;
    var field = h("input", {
      value: given[at] || "", disabled: !!locked,
      oninput: function () {
        given[at] = field.value;
        renderPreview();
      },
      onchange: function () { draw(); }
    });
    // Check if the argument was added by hand, so it can be taken away again and the rest move up
    return h("label", {}, argument.name, field, named ? null : h("button", {
      type: "button", className: "progless", title: "Remove this argument", disabled: !!locked,
      onclick: function () {
        given.splice(at, 1);
        draw();
      }
    }, "×"));
  }), named ? null : h("button", {
    type: "button", className: "progmore", disabled: !!locked,
    title: "Passed to the program in sys.argv",
    onclick: function () {
      given.push("");
      draw();
    }
  }, "+ an argument"));
}

// ---- the effects, while a program runs --------------------------------------------------------
// The board runs a program in their place, so they stand back with a note saying what runs
// instead. They are kept, and run again if the program is missing or stops

function programNote() {
  var note = document.getElementById("programNote");
  if (!note) {
    note = h("div", {id: "programNote", className: "programnote"});
    // Above the gallery, or above what a page has stacked it in
    (document.getElementById("looksStack") || document.getElementById("looks")).before(note);
  }
  note.hidden = !boardSet.program;
  if (!boardSet.program) return;
  var program = programNamed(boardSet.program);
  note.title = BOARD_SETTING_SAYS;
  replace(note, boardIcon(),
          "The board runs " + (program && program.name ? program.name + " (" + boardSet.program + ")"
                                                       : boardSet.program) +
          " instead of the effects. The effects are kept, and play if the " +
          "program is missing or stops, with the reason in errors.txt.");
}

addStep(drawSteps.after, DRAW_AFTER, "boardSettings", function () {
  document.body.classList.toggle("programmed", !!boardSet.program);
  programNote();
});

// Whether the program tab is open. A program is chosen only by picking one, so the tab can be open
// with none chosen, and the file says program= only once one is
export var onProgramPage = false;

// Open or close the program tab
export function setProgramPage(on) {
  onProgramPage = on;
}

// The steps run while the programs are read, so the program tab can count them in
export var programsReadingSteps = [];

// The steps run once the programs are read, before the page is drawn
export var programsReadSteps = [];
