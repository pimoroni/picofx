import {addStep, draw, holdDrawing} from "./draw.js";
import {targetFor} from "./lines.js";
import {BOARD, canPlay, keyOf, lookNamed} from "./looks.js";
import {OUTPUTS, order, outputSaid, placeLamp, plainOrder, setLayout, wiring} from "./outputs.js";
import {
  acrossWiring, breakOutWiring, canEdit, copyBlinks, copyExact, mono, outs, pickOutput, playsOf,
  rejoinWiring, runs, sectionAt, settle
} from "./runs.js";
import {apply, capture, carried, slotAt, state, store} from "./scenes.js";
import {stripLengthTail} from "./strips.js";

// ---- what an output's lamps play when its wiring changes ----------------------------------
// When an output is broken out into three mono lamps, or three are put back as one colour lamp,
// the wiring change gives the new lamps a stretch of their own, starting dark. changeWiring()
// fills it with what the output played, where the look can play on them

// The stretch an output's lamps played. Put back from three that differ, it is the one
// most of them played, and the first channel's where all three differ
function playedBy(out) {
  var lamps = [];
  runs.forEach(function (run) {
    run.lamps.forEach(function (lamp, at) {
      if (lamp.out === out) lamps.push({channel: lamp.channel || 0,
                                        section: run.sections[sectionAt(run, at)]});
    });
  });
  // A channel can be dragged from the other two, so sorting by channel lets the first win a tie
  lamps.sort(function (a, b) { return a.channel - b.channel; });
  var counted = [];
  lamps.forEach(function (one) {
    var seen = counted.filter(function (had) { return had.look === one.section.look; })[0];
    if (seen) seen.many++;
    else counted.push({look: one.section.look, section: one.section, many: 1});
  });
  var most = counted[0];
  counted.forEach(function (one) { if (one.many > most.many) most = one; });
  return most ? most.section : null;
}

// The nearest look for lamps a look cannot play on. Rainbow's colours travel along the
// lamps, and on mono lamps the nearest is brightness travelling
var STAND_INS = {"Rainbow": "Wave"};

// What each output was carried from, as scenes.js keeps it
function carriedFrom() { return carried; }

// The stand-in a stretch is playing, and what for, where it is one
export function standingIn(run, section) {
  var memo = null;
  run.lamps.slice(section.from, section.to + 1).forEach(function (lamp) {
    var had = carriedFrom()[lamp.out];
    if (had && had.as === section.look) memo = had;
  });
  return memo;
}

function changeWiring(change, toColour) {
  return function (out) {
    if (!!wiring[out].broken !== toColour) return;
    var played = playedBy(out);
    played = played && {look: played.look, pace: played.pace, mood: played.mood,
                        colour: played.colour, level: played.level,
                        blinks: copyBlinks(played.blinks), exact: copyExact(played.exact),
                        timings: copyExact(played.timings)};
    var memo = carriedFrom()[out];
    delete carriedFrom()[out];
    change(out);
    runs.some(function (run) {
      var mine = run.sections.filter(function (section) {
        return run.lamps.slice(section.from, section.to + 1).every(function (lamp) {
          return lamp.out === out;
        });
      })[0];
      if (!mine) return false;
      if (played) {
        var look = lookNamed(played.look);
        var target = targetFor(run, mine);
        var standIn = lookNamed(STAND_INS[played.look]);
        if (toColour && memo && played.look === memo.as) {
          // Back from a stand-in, it plays its old look at the stand-in's pace and level
          Object.assign(mine, {look: memo.look, pace: played.pace, mood: memo.mood,
                               colour: memo.colour, level: played.level});
        } else if (look && canPlay(look, target)) {
          Object.assign(mine, played);
        } else if (standIn && canPlay(standIn, target)) {
          Object.assign(mine, played, {look: keyOf(standIn)});
          carriedFrom()[out] = {as: keyOf(standIn), look: played.look, mood: played.mood,
                                colour: played.colour};
        }
      }
      return true;
    });
    settle();
    pickOutput(out);
    draw();
  };
}

// ---- the board, the same in every scene ------------------------------------------------
// How the board is built is the same in every scene, such as which outputs have an adapter
// fitted, how long each strip is and which panel is plugged into each screen port.

// What the screens parts lend the parts every board takes, filled in by screens/ where the board
// has screens. Without them no drive file is a picture or drawing, and no panel is drawn
export var screenHooks = {mediaNamed: function () { return null; }, panelPreview: null};

// What the firmware part lends the others, filled in by firmware/ where the board has a release to
// check against. Without it, whether the latest release brings a version is unknown
export var firmwareHooks = {covers: function () { return null; }};

// The screen ports the board describes
export var SCREEN_PORTS = BOARD.screens ? BOARD.screens.ports : [];
// Keep only the ports the catalogue lists, so a board whose catalogue has none offers none
SCREEN_PORTS = SCREEN_PORTS.filter(function (port) {
  return CATALOGUE.screen_ports.indexOf(port.id) >= 0;
});
// The sizes a panel can be, as the firmware takes them. The catalogue's hub is not a panel size
export var SCREEN_SIZES = (SCREEN_PORTS.length ? CATALOGUE.board_settings[SCREEN_PORTS[0].id] : [])
  .filter(function (inches) { return inches !== "hub"; });
// The panel size plugged into each screen port, by port id, or "" for none
export var screensFitted = {};
SCREEN_PORTS.forEach(function (port) { screensFitted[port.id] = ""; });

// Make a wiring change to every scene in turn, and carry each scene's looks across to the new
// lamps. Every scene's undo steps are cleared, since they are about lamps that have since moved
function acrossScenes(change) {
  return function (out) {
    store();
    var editing = state.at;
    var before = {wiring: JSON.stringify(wiring), order: JSON.stringify(order)};
    // Each scene is changed with the page held still, since drawing would store what is
    // being changed into the scene being edited
    holdDrawing(true);
    try {
      [state.always].concat(state.scenes).forEach(function (slot) {
        setLayout(JSON.parse(before.wiring), JSON.parse(before.order));
        apply(slot.body);
        change(out);
        runs.forEach(function (run) {
          run.was = [];
          run.undone = [];
        });
        slot.body = capture();
      });
    } finally {
      holdDrawing(false);
    }
    state.at = editing;
    apply(slotAt(editing).body);
    draw();
  };
}

export var breakOutInScenes = acrossScenes(changeWiring(breakOutWiring, false));
export var rejoinInScenes = acrossScenes(changeWiring(rejoinWiring, true));

// Where a lamp sits is the same in every scene too. Moving one keeps every scene's looks on the
// lamps they were on, so a stretch the move takes apart becomes two playing the same
export var moveLampInScenes = acrossScenes(function (move) {
  acrossWiring(function () { placeLamp(move); });
});

var rejoinOne = changeWiring(rejoinWiring, true);

// Put the wiring back as the board comes, with every output rejoined and every lamp in the order
// the board wires them. Each scene keeps its looks on the lamps they were on, and neighbouring
// stretches that moves and splits left playing the same become one
export var resetWiringInScenes = acrossScenes(function () {
  breakingOutputs().forEach(rejoinOne);
  acrossWiring(function () { setLayout(wiring, plainOrder()); });
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

// Whether a lamp can be moved just now, which is only while the wiring view is open
export function lampsMovable() { return canEdit("outPanel"); }

// The colour outputs that break out, by place
export function breakingOutputs() {
  var found = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono && output.breaks) found.push(out); });
  return found;
}

// Whether the outputs are one light that does not break out, which leaves no wiring to set
export var ONE_LIGHT = OUTPUTS.length === 1 && !breakingOutputs().length;

// The outputs broken out, as a person would say it
export function brokenSaid() {
  var breaking = breakingOutputs();
  var broken = breaking.filter(function (out) { return wiring[out].broken; });
  if (!broken.length) {
    return breaking.length === 1 ? outputSaid(breaking[0]) + " is one colour light"
                                 : "every output is one colour light";
  }
  // Three or more in a row close up into a range, as the file writes them, to keep the words short
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
// Later parts add their own steps to the board line, what each readies before it is written and
// what each makes of the line written so far. The after steps go in the order BOARD_LINE_AFTER
// states, which is the order their words are written in

export var boardLineSteps = {before: [], after: []};
export var BOARD_LINE_AFTER = ["sensor", "hub", "boardSettings", "readback"];

export function boardLine() {
  boardLineSteps.before.forEach(function (step) { step(); });
  var tokens = [];
  SCREEN_PORTS.forEach(function (port) {
    if (screensFitted[port.id]) tokens.push(port.id + "=" + screensFitted[port.id]);
  });
  // A strip's length has the board set up its connector, so it goes only where a scene plays on it
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
// The board line names a strip or screen only where a scene plays on it, so one removed writes
// the same file as one fitted and left unused. The page lists what the board fits by default but
// has been taken off in a comment of its own, by the name its tab or box shows. autofx passes over
// the comment, and the page reads it back so a reload does not fit it again

export var NOT_FITTED = "# Not fitted: ";

// The names the file listed as not fitted, in lower case, or null where it had no such comment
export var notFittedRead = null;

// Set the names the file listed as not fitted
export function setNotFittedRead(names) {
  notFittedRead = names;
}

// The names of what the board fits by default and has been taken off, as a step from each part
export var notFittedSteps = [];
export var NOT_FITTED_ORDER = ["board", "screens"];

// A strip as the board describes it, with its tab's name and whether it is fitted by default
export function stripDescribed(run) {
  return BOARD.strips.filter(function (strip) { return strip.name === run.name; })[0];
}

addStep(notFittedSteps, NOT_FITTED_ORDER, "board", function () {
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
