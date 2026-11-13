import {SCREEN_SIZES, boardWords} from "./board.js";
import {h, replace} from "./dom.js";
import {draw} from "./draw.js";
import {renderPreview} from "./file_preview.js";
import {state} from "./scenes.js";
import {boardIcon} from "./setup.js";

export var boardSet = {reload: true, driveHidden: false, program: null, args: {}};

export var PROGRAMS = [];

export function setPrograms(list) {
  PROGRAMS = list;
}

export var programsElsewhere = [];

export function programNamed(path) {
  var found = PROGRAMS.filter(function (one) { return one.path === path; })[0];
  for (var at = 0; !found && at < programsElsewhere.length; at++) found = programsElsewhere[at](path);
  return found || null;
}

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

export function driveMeansSomething() { return !boardSet.program; }

boardWords.program = function () {
  var tokens = [];
  if (boardSet.program) {
    tokens.push("program=" + boardSet.program);
    var args = argsWritten(boardSet.program);
    if (args) tokens.push("args=" + args);
  }
  if (boardSet.driveHidden) tokens.push("drive=manual");
  if (!boardSet.reload) tokens.push("reload=manual");
  return tokens;
};

function sizeOffered(argument) {
  var screen = state.screens && state.screens.A;
  return screen && screen.there && screen.size ? screen.size : argument.default;
}

var ARGUMENT_CHOICES = {
  size: function () {
    return SCREEN_SIZES.map(function (inches) { return [inches, inches + "\""]; });
  },
  rotation: function (argument) {
    return (argument.choices || ["0", "90", "180", "270"]).map(function (turn) {
      return [turn, turn + "\u00b0"];
    });
  }
};

export function programArguments(path, locked) {
  var program = programNamed(path);
  var given = boardSet.args[path] || (boardSet.args[path] = []);
  var named = !!program.args;
  var taken = program.args || given.map(function (arg, at) {
    return {name: "Argument " + (at + 1), kind: "text"};
  });
  return h("fieldset", {class: "programargs", disabled: !!locked},
    h("legend", {}, "Arguments"),
    taken.map(function (argument, at) {
      return ARGUMENT_CHOICES[argument.kind] ? chosenArgument(argument, given, at)
                                              : typedArgument(argument, given, at, !named);
    }),
    named ? null : h("button", {type: "button", title: "Passed to the program in sys.argv",
                                onclick: function () {
                                  given.push("");
                                  draw();
                                }}, "+ an argument"));
}

function chosenArgument(argument, given, at) {
  var choices = ARGUMENT_CHOICES[argument.kind](argument);
  if (given[at] === undefined) {
    given[at] = argument.kind === "size" ? sizeOffered(argument) : argument.default || choices[0][0];
  }
  return h("div", {},
    h("label", {}, argument.name,
      h("select", {onchange: function (event) {
                     given[at] = event.currentTarget.value;
                     draw();
                   }},
        choices.map(function (offered) {
          return h("option", {value: offered[0], selected: given[at] === offered[0]}, offered[1]);
        }))));
}

function typedArgument(argument, given, at, removable) {
  if (given[at] === undefined && "default" in argument) given[at] = argument.default;
  return h("div", {},
    h("label", {}, argument.name,
      h("input", {value: given[at] || "",
                  oninput: function (event) {
                    given[at] = event.currentTarget.value;
                    renderPreview();
                  },
                  onchange: function () { draw(); }})),
    removable ? h("button", {type: "button", title: "Remove this argument",
                             "aria-label": "Remove " + argument.name,
                             onclick: function () {
                               given.splice(at, 1);
                               draw();
                             }}, "\u00d7") : null);
}

export function programNote(said, ...after) {
  return h("p", {class: "programnote"}, boardIcon(), h("span", {}, said), after);
}

function effectsNote() {
  var note = document.getElementById("programNote");
  if (!note) {
    note = h("div", {id: "programNote"});
    var looks = document.getElementById("looksStack") || document.getElementById("looks");
    looks.parentNode.insertBefore(note, looks);
  }
  note.hidden = !boardSet.program;
  if (!boardSet.program) return;
  var program = programNamed(boardSet.program);
  replace(note, programNote(
    "The board runs " + (program && program.name ? program.name + " (" + boardSet.program + ")"
                                                 : boardSet.program) +
    " instead of the effects. The effects are kept, and play if the " +
    "program is missing or stops, with the reason in errors.txt."));
}

export function drawBoardSettings() {
  document.body.toggleAttribute("data-programmed", !!boardSet.program);
  effectsNote();
}

export var onProgramPage = false;

export function setProgramPage(on) {
  onProgramPage = on;
}
