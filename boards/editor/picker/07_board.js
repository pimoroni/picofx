
// ---- the board, the same in every scene ------------------------------------------------
// How the board is built is the same in every scene: which outputs have an adapter
// fitted, how long each strip is, and which screen is plugged into each port. The pages
// built on this one differ only in where those are shown and when they can be changed.

// Which panel is plugged into each screen port, or none. Only the size is the board's:
// which way up it is mounted is left for when screens are settled
var SCREEN_PORTS = BOARD.screens ? BOARD.screens.ports : [];
// The catalogue is the board's own, so a board that finds it has no screen ports offers none
SCREEN_PORTS = SCREEN_PORTS.filter(function (port) {
  return CATALOGUE.screen_ports.indexOf(port.id) >= 0;
});
// The sizes a panel can be, as the firmware takes them, the catalogue's hub being no panel size
var SCREEN_SIZES = (SCREEN_PORTS.length ? CATALOGUE.board_settings[SCREEN_PORTS[0].id] : [])
  .filter(function (inches) { return inches !== "hub"; });
var screensFitted = {};
SCREEN_PORTS.forEach(function (port) { screensFitted[port.id] = ""; });

// Breaking an output out, or putting it back, is done to every scene in turn, each carrying
// its own looks across. A scene's steps to undo end there, being about
// lamps that have since moved: putting the output back is the way to undo it
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

var breakOutInScenes = acrossScenes(changeWiring(breakOutWiring, false));
var rejoinInScenes = acrossScenes(changeWiring(rejoinWiring, true));

// Where a lamp sits is the build's as well. Moving one keeps every scene's looks on the
// lamps they were on, the way breaking out does, so a stretch the move takes apart
// becomes two playing the same
var moveLampInScenes = acrossScenes(function (move) {
  acrossWiring(function () { placeLamp(move); });
});

// Whether a lamp can be dragged to where it sits just now. Where a lamp sits is changed with
// the wiring, so only where that can be
function lampsMovable() { return canEdit("outPanel"); }

// The colour outputs that break out, by place
function breakingOutputs() {
  var found = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono && output.breaks) found.push(out); });
  return found;
}

// The outputs broken out, as a person would say it
function brokenSaid() {
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
// The parts below add their own steps to the board line: what each readies before it is
// written, and what each makes of the line written so far, both in the order the parts come

var boardLineSteps = {before: [], after: []};

function boardLine() {
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
