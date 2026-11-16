import {BOARD} from "./01_looks.js";
import {
  OUTPUTS, acrossWiring, breakOutWiring, draw, drawHeld, mono, order, outputSaid, outs, placeLamp,
  rejoinWiring, runs, wiring
} from "./03_runs.js";
import {apply, capture, slotAt, state, store} from "./04_scenes.js";
import {changeWiring, playsOf, stripLengthTail} from "./05_effects.js";
import {canEdit} from "./08_setup.js";
import {plainOrder} from "./27_readback.js";

// ---- the board, the same in every scene ------------------------------------------------
// How the board is built is the same in every scene, which outputs have an adapter
// fitted, how long each strip is, and which screen is plugged into each port. The pages
// built on this one differ only in where those are shown and when they can be changed.

// What the screens parts lend the parts every board takes, filled in by screens/ where the board
// has screens. Without them no drive file is a picture or drawing, and no panel is drawn
export var screenHooks = {mediaNamed: function () { return null; }, panelPreview: null};

// What the firmware part lends the others, filled in by firmware/ where the board has a release to
// check against. Without it, whether the latest release brings a version is unknown
export var firmwareHooks = {covers: function () { return null; }};

// Which panel is plugged into each screen port, or none. Only the panel's size is the board's
export var SCREEN_PORTS = BOARD.screens ? BOARD.screens.ports : [];
// The catalogue is the board's own, so a board that finds it has no screen ports offers none
SCREEN_PORTS = SCREEN_PORTS.filter(function (port) {
  return CATALOGUE.screen_ports.indexOf(port.id) >= 0;
});
// The sizes a panel can be, as the firmware takes them. The catalogue's hub is not a panel size
export var SCREEN_SIZES = (SCREEN_PORTS.length ? CATALOGUE.board_settings[SCREEN_PORTS[0].id] : [])
  .filter(function (inches) { return inches !== "hub"; });
export var screensFitted = {};
SCREEN_PORTS.forEach(function (port) { screensFitted[port.id] = ""; });

// Breaking an output out, or putting it back, is done to every scene in turn, each carrying
// its own looks across. A scene's steps to undo end there, since they are about lamps that
// have since moved. Putting the output back is the way to undo it
function acrossScenes(change) {
  return function (out) {
    store();
    var editing = state.at;
    var before = {wiring: JSON.stringify(wiring), order: JSON.stringify(order)};
    // Each scene is changed with the page held still, since drawing would store what is
    // being changed into the scene being edited
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

// Where a lamp sits is the build's as well. Moving one keeps every scene's looks on the
// lamps they were on, the way breaking out does, so a stretch the move takes apart
// becomes two playing the same
export var moveLampInScenes = acrossScenes(function (move) {
  acrossWiring(function () { placeLamp(move); });
});

// The wiring put back as the board comes, every output that breaks out rejoined and every lamp in
// the order the board wires them. Each scene keeps its looks on the lamps they were on, and
// neighbouring stretches left playing the same, as moves and splits leave them, become one
var rejoinOne = changeWiring(rejoinWiring, true);

export var resetWiringInScenes = acrossScenes(function () {
  breakingOutputs().forEach(rejoinOne);
  acrossWiring(function () { order = plainOrder(); });
  [outs, mono].forEach(joinAlike);
});

// Join a run's neighbouring stretches that play exactly the same
function joinAlike(run) {
  var joined = [];
  run.sections.forEach(function (section) {
    var last = joined[joined.length - 1];
    if (last && JSON.stringify(playsOf(last)) === JSON.stringify(playsOf(section))) {
      last.to = section.to;
    } else {
      joined.push(section);
    }
  });
  run.sections = joined;
  run.picked = Math.max(0, Math.min(run.picked, joined.length - 1));
}

// Whether the wiring differs from how the board comes, a lamp out of order or an output broken out
export function wiringChanged(astray) {
  return astray.length > 0 || breakingOutputs().some(function (out) { return wiring[out].broken; });
}

// Whether a lamp can be dragged to where it sits just now. Where a lamp sits is changed with
// the wiring, so only where that can be
export function lampsMovable() { return canEdit("outPanel"); }

// The colour outputs that break out, by place
export function breakingOutputs() {
  var found = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono && output.breaks) found.push(out); });
  return found;
}

// The outputs broken out, as a person would say it
export function brokenSaid() {
  var breaking = breakingOutputs();
  var broken = breaking.filter(function (out) { return wiring[out].broken; });
  if (!broken.length) {
    return breaking.length === 1 ? outputSaid(breaking[0]) + " is one colour light"
                                 : "every output is one colour light";
  }
  // Three or more in a row close up into a range, as the file writes them, so the box is
  // never much longer than it is with nothing broken out and the setup hint keeps its room
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

// ---- what the file says about the board -------------------------------------------------
// The parts below add their own steps to the board line, what each readies before it is
// written and what each makes of the line written so far, both in the order the parts come

export var boardLineSteps = {before: [], after: []};

export function boardLine() {
  boardLineSteps.before.forEach(function (step) { step(); });
  var tokens = [];
  SCREEN_PORTS.forEach(function (port) {
    if (screensFitted[port.id]) tokens.push(port.id + "=" + screensFitted[port.id]);
  });
  // A strip's length brings its connector up, so it is given only where some scene plays on it
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

// ---- what is not fitted, in a comment of the page's own ---------------------------------
// The board line names a strip or screen only where a scene plays on it, so one taken off in
// Edit board writes the same file as one fitted and left unused. Where something the board fits
// by default has been taken off, the page lists it by the name its tab or box shows in a comment
// of its own, which autofx passes over, and reads it back so a reload does not fit it again

export var NOT_FITTED = "# Not fitted: ";

// The names the file listed as not fitted, in lower case, or null where it had no such comment
export var notFittedRead = null;

// The names of what the board fits by default and has been taken off, as a step from each part
export var notFittedSteps = [];

// A strip as the board describes it, with its tab's name and whether it is fitted by default
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

// Whether the file listed a strip or screen as not fitted, by the name its tab or box shows
export function saidNotFitted(name) {
  return notFittedRead.indexOf(name.toLowerCase()) >= 0;
}
