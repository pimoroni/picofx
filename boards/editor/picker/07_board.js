import {BOARD} from "./01_looks.js";
import {
  OUTPUTS, acrossWiring, breakOutWiring, draw, drawHeld, order, outputSaid, placeLamp,
  rejoinWiring, runs, wiring
} from "./03_runs.js";
import {apply, capture, slotAt, state, store} from "./04_scenes.js";
import {changeWiring, stripLengthTail} from "./05_effects.js";
import {canEdit} from "./08_setup.js";

export var screenHooks = {mediaNamed: function () { return null; }, panelPreview: null};

export var SCREEN_PORTS = BOARD.screens ? BOARD.screens.ports : [];
SCREEN_PORTS = SCREEN_PORTS.filter(function (port) {
  return CATALOGUE.screen_ports.indexOf(port.id) >= 0;
});
export var SCREEN_SIZES = (SCREEN_PORTS.length ? CATALOGUE.board_settings[SCREEN_PORTS[0].id] : [])
  .filter(function (inches) { return inches !== "hub"; });
export var screensFitted = {};
SCREEN_PORTS.forEach(function (port) { screensFitted[port.id] = ""; });

function acrossScenes(change) {
  return function (out) {
    store();
    var editing = state.at;
    var before = {wiring: JSON.stringify(wiring), order: JSON.stringify(order)};
    drawHeld = true;
    try {
      [state.always].concat(state.scenes).forEach(function (slot) {
        wiring = JSON.parse(before.wiring);
        order = JSON.parse(before.order);
        apply(slot.body);
        change(out);
        runs.forEach(function (run) {
          run.was = [];
          run.undone = [];
        });
        slot.body = capture();
      });
    } finally {
      drawHeld = false;
    }
    state.at = editing;
    apply(slotAt(editing).body);
    draw();
  };
}

export var breakOutInScenes = acrossScenes(changeWiring(breakOutWiring, false));
export var rejoinInScenes = acrossScenes(changeWiring(rejoinWiring, true));

export var moveLampInScenes = acrossScenes(function (move) {
  acrossWiring(function () { placeLamp(move); });
});

export function lampsMovable() { return canEdit("outPanel"); }

export function breakingOutputs() {
  var found = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono && output.breaks) found.push(out); });
  return found;
}

export function brokenSaid() {
  var breaking = breakingOutputs();
  var broken = breaking.filter(function (out) { return wiring[out].broken; });
  if (!broken.length) {
    return breaking.length === 1 ? outputSaid(breaking[0]) + " is one colour light"
                                 : "every output is one colour light";
  }
  var numbers = broken.filter(function (out) { return OUTPUTS[out].number !== null; })
    .map(function (out) { return OUTPUTS[out].number; });
  var parts = [];
  for (var at = 0; at < numbers.length;) {
    var end = at;
    while (end + 1 < numbers.length && numbers[end + 1] === numbers[end] + 1) end++;
    if (end - at >= 2) parts.push(numbers[at] + "-" + numbers[end]);
    else for (var one = at; one <= end; one++) parts.push(String(numbers[one]));
    at = end + 1;
  }
  var said = parts.length ? [(numbers.length === 1 ? "output " : "outputs ") + parts.join(", ")]
                          : [];
  broken.forEach(function (out) { if (OUTPUTS[out].number === null) said.push(outputSaid(out)); });
  return said.join(" and ") + (broken.length === 1 ? " is" : " are") + " broken out";
}

export var boardLineSteps = {before: [], after: []};

export function boardLine() {
  boardLineSteps.before.forEach(function (step) { step(); });
  var tokens = [];
  SCREEN_PORTS.forEach(function (port) {
    if (screensFitted[port.id]) tokens.push(port.id + "=" + screensFitted[port.id]);
  });
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    var used = bodies.some(function (body) {
      var held = body && body.runs && body.runs[run.name];
      return held && held.sections.some(function (section) { return section.look; });
    });
    if (used) tokens.push(run.name + "=" + run.leds + stripLengthTail(run));
  });
  var line = tokens.length ? "board: " + tokens.join(" ") : "";
  boardLineSteps.after.forEach(function (step) { line = step(line); });
  return line;
}

export var NOT_FITTED = "# Not fitted: ";

export var notFittedRead = null;

export var notFittedSteps = [];

export function stripDescribed(run) {
  return BOARD.strips.filter(function (strip) { return strip.name === run.name; })[0];
}

notFittedSteps.push(function () {
  return runs.filter(function (run) {
    return run.strip && !run.there && stripDescribed(run).fitted;
  }).map(function (run) { return stripDescribed(run).tab; });
});

export function notFittedLine() {
  var names = [];
  notFittedSteps.forEach(function (step) { names = names.concat(step()); });
  return names.length ? NOT_FITTED + names.join(", ") : null;
}

export function saidNotFitted(name) {
  return notFittedRead.indexOf(name.toLowerCase()) >= 0;
}
