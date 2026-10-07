
// ---- the board, the same in every scene ------------------------------------------------
// How the board is built is the same in every scene: which outputs have an adapter
// fitted, how long each strip is, and which screen is plugged into each port. The pages
// built on this one differ only in where those are shown and when they can be changed.

// Which panel is plugged into each screen port, or none. Only the size is the board's:
// which way up it is mounted is left for when screens are settled
var SCREEN_PORTS = BOARD.screens ? BOARD.screens.ports : [];
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

// The outputs broken out, as a person would say it
function brokenSaid() {
  var broken = wiring.map(function (one, at) { return one.broken ? at + 1 : 0; })
    .filter(function (at) { return at; });
  if (!broken.length) return "every output is one colour light";
  // Three or more in a row close up into a range, as the file writes them, so the box is
  // never much longer than it is with nothing broken out and the setup hint keeps its room
  var parts = [];
  for (var at = 0; at < broken.length;) {
    var end = at;
    while (end + 1 < broken.length && broken[end + 1] === broken[end] + 1) end++;
    if (end - at >= 2) parts.push(broken[at] + "-" + broken[end]);
    else for (var one = at; one <= end; one++) parts.push(String(broken[one]));
    at = end + 1;
  }
  return (broken.length === 1 ? "output " : "outputs ") + parts.join(", ") +
         (broken.length === 1 ? " is" : " are") + " broken out";
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
    if (used) tokens.push(run.name + "=" + run.leds + (run.order ? "|" + run.order : ""));
  });
  var line = tokens.length ? "board: " + tokens.join(" ") : "";
  boardLineSteps.after.forEach(function (step) { line = step(line); });
  return line;
}
