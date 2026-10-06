
// ---- where the board is set up ----------------------------------------------------------
// Every fact about the board stays beside what it is about: the wiring on the outputs, a
// strip's length on the strip, a screen's type on the screen. Each reads as a box in its
// section's own colour, and the whole board is set up at once in a setup mode.

// Whether the whole page is in its setup mode
var setupOn = false;

// The panels that hold a board fact, and the colour each one's box takes
var SECTIONS = {outPanel: "outs", striplPanel: "stripl", striprPanel: "stripr",
                screenaPanel: "screena", screenbPanel: "screenb"};

// Whether the board facts in this panel can be changed just now
function canEdit(panel) { return setupOn; }

// Where a lamp sits is changed with the wiring, so only where that can be
lampsMovable = function () { return canEdit("outPanel"); };

// The outputs read as a strip does, with no row above the lamps and no line under them. The
// arrows and dragging are explained beside the board's box while setting up, so the section
// is one size either way
var onePanelHead = renderPanelHead;

renderPanelHead = function () {
  onePanelHead();
  var head = document.getElementById("outHead");
  head.textContent = "";
  head.style.display = "none";
};

var oneLegend = renderLegend;

renderLegend = function () {
  oneLegend();
  var legend = document.getElementById("outLegend");
  legend.textContent = "";
  legend.style.display = "none";
};

// The steps the two sides share go on the cutting row of the side at the right, as a strip
// keeps its own on its cutting row
var oneCutting = renderCutting;

renderCutting = function (where, run) {
  oneCutting(where, run);
  if (where !== (mono.lamps.length ? "monoCut" : "outCut")) return;
  var row = document.getElementById(where);
  if (row) zoomAndSteps(row, active);
};

// A side is named only while there are two, telling the colour lamps from the mono ones.
// With every output one colour lamp, the board's box says so already
var oneSides = renderSides;

renderSides = function () {
  oneSides();
  var two = mono.lamps.length > 0;
  ["headA", "headB"].forEach(function (id) {
    var head = document.getElementById(id);
    if (head) head.style.display = two ? "" : "none";
  });
  var sides = document.getElementById("sides");
  if (sides) sides.classList.toggle("unnamed", !two);
};

// ---- selection waits while the board is set up ------------------------------------------------
// A stretch is picked to give it a look, which setup does not do, so a tap there picks
// nothing and nothing looks picked. What was picked is held by its lamp, the wiring
// being free to move it, and is picked again when setup ends; an output broken out or
// put back meanwhile is picked instead, as it would have been outside setup

var heldPick = null;
var heldOutput = null;

var onePick = pick;

pick = function (run, at) {
  if (setupOn) return;
  onePick(run, at);
};

var onePickOutput = pickOutput;

pickOutput = function (out) {
  if (setupOn) {
    heldOutput = out;
    return;
  }
  onePickOutput(out);
};

function setSetup(on) {
  if (on && !setupOn) {
    var section = active.sections[active.picked];
    heldPick = section ? lampKey(active.lamps[section.from]) : null;
    heldOutput = null;
  }
  setupOn = on;
  if (on) return;
  if (heldOutput !== null) {
    pickOutput(heldOutput);
  } else if (heldPick) {
    runs.some(function (run) {
      var at = run.lamps.map(lampKey).indexOf(heldPick);
      if (at >= 0) pick(run, sectionAt(run, at));
      return at >= 0;
    });
  }
  heldPick = null;
  heldOutput = null;
}

// Nothing looks picked while setup is on: the marks are drawn by the pages below, so they
// are taken off once drawn
function unmark() {
  document.querySelectorAll(".lamp.ringed, .sec.picked, .card.picked").forEach(function (one) {
    one.classList.remove("ringed", "picked");
  });
  document.querySelectorAll(".run svg rect.ringed").forEach(function (ring) {
    ring.parentNode.removeChild(ring);
  });
}

// A section's coloured box, the chip icon inside it with whatever the fact says
function boardBox(panel, parts) {
  var box = document.createElement("span");
  box.className = "chip boardchip " + SECTIONS[panel];
  box.title = "How the board is built, which is the same in every scene";
  box.appendChild(boardIcon());
  parts.forEach(function (part) {
    box.appendChild(typeof part === "string" ? document.createTextNode(part) : part);
  });
  return box;
}

function small(words) {
  var said = document.createElement("small");
  said.textContent = words;
  return said;
}

// The board's chip, three legs a side, set three apart as the smallest spacing that still
// reads as legs at 16px
function boardIcon() {
  var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("width", "13");
  svg.setAttribute("height", "13");
  svg.setAttribute("class", "boardicon");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = "<rect x='3' y='3' width='8' height='8' rx='1' fill='none' " +
                  "stroke='currentColor' stroke-width='1.3'/>" +
                  "<path d='M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2" +
                  "M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2' " +
                  "stroke='currentColor' stroke-width='1.3' stroke-linecap='round'/>";
  return svg;
}

// ---- the facts, in place --------------------------------------------------------------------

// The arrows on the lamps are how an output is broken out, so they show only where the
// wiring can be changed
var oneCrossing = crossing;

// Where the wiring cannot be changed the arrow is left out. What stands in its place takes
// no room, as the arrow does, or each output's lamps would sit further apart outside setup
function noArrow() {
  var none = document.createElement("span");
  none.style.position = "absolute";
  return none;
}

crossing = function (out, colour) {
  if (!canEdit("outPanel")) return noArrow();
  var made = oneCrossing(out, colour);
  made.classList.add("boardarrow");
  return made;
};

function renderOutFacts() {
  var box = document.getElementById("outFacts");
  box.textContent = "";
  box.appendChild(boardBox("outPanel", ["Wiring", small(brokenSaid())]));
  if (canEdit("outPanel")) {
    var hint = document.createElement("span");
    hint.className = "hint";
    hint.textContent = "Drag a light to where it sits in your build. Arrows split an " +
                       "output into three mono lights, or rejoin them.";
    hint.title = hint.textContent;
    box.appendChild(hint);
  }
}

var oneRenderLeds = renderLeds;

// What a strip is built as, its length and the order it takes its colours in
function stripBuilt(run) {
  return run.leds + " LEDs, " + (run.order || "grb").toUpperCase();
}

// Whether a strip is there, on the run and on the entry a fresh run is made from
function stripThere(run, there) {
  STRIPS.filter(function (one) { return one.id === run.id; })[0].there = there;
  run.there = there;
}

// Taking a strip out clears what it plays in every scene, which leaves its length unwritten
// and its connector off
function dropStrip(run) {
  store();
  allBodies().forEach(function (held) {
    var kept = held.runs[run.name];
    if (!kept) return;
    kept.sections = [blank(0, run.leds - 1, run)];
    kept.picked = 0;
    kept.was = [];
    kept.undone = [];
  });
  stripThere(run, false);
  apply(slotAt(state.at).body);
  draw();
}

// The cross on a strip's chip while the board is edited, as a screen has on its own
function stripDrop(run) {
  var drop = document.createElement("button");
  drop.type = "button";
  drop.className = "drop";
  drop.textContent = "\u00d7";
  drop.title = "Take this strip out of every scene";
  drop.onclick = function () { dropStrip(run); };
  return drop;
}

// A strip not fitted offers to be added, which only editing the board can take up
function renderStripOut(box, run, panel) {
  box.textContent = "";
  box.appendChild(boardBox(panel, ["Strip", small("not fitted")]));
  var add = document.createElement("button");
  add.type = "button";
  add.className = "addstrip";
  add.textContent = "add this strip";
  add.disabled = !canEdit(panel);
  add.onclick = function () {
    stripThere(run, true);
    workOn(panel);
    draw();
  };
  box.appendChild(add);
}

// A strip not fitted takes no look
var oneSetupLandLook = landLook;

landLook = function (run, at, name) {
  if (run.strip && !run.there) return;
  oneSetupLandLook(run, at, name);
};

renderLeds = function (where, run) {
  var box = document.getElementById(where);
  var panel = run.id + "Panel";
  document.getElementById(panel).classList.toggle("stripout", !run.there);
  if (!run.there) {
    renderStripOut(box, run, panel);
    return;
  }
  // The strip's own count box is already the board's, so the icon goes inside it and it
  // takes the strip's colour
  if (canEdit(panel)) {
    oneRenderLeds(where, run);
    var says = box.querySelector(".says");
    if (says) box.removeChild(says);
    var chip = box.querySelector(".chip");
    chip.className = "chip boardchip " + SECTIONS[panel];
    chip.title = "How the board is built, which is the same in every scene";
    chip.insertBefore(boardIcon(), chip.firstChild);
    chip.appendChild(stripDrop(run));
  } else {
    box.textContent = "";
    box.appendChild(boardBox(panel, ["Strip", small(stripBuilt(run))]));
  }
};

function renderScreenFacts(port) {
  var box = document.getElementById(port.id + "Facts");
  var panel = port.id + "Panel";
  box.textContent = "";
  var size = screensFitted[port.id];
  box.appendChild(boardBox(panel, [port.label, canEdit(panel)
    ? screenSize(port)
    : small(size ? size + " inch" : "no panel fitted")]));
}

// ---- turning setup on ------------------------------------------------------------------------

function setupButton(label, on, act) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "setupbutton" + (on ? " on" : "");
  // The board's chip, as every board setting wears it, since this is where they open
  button.appendChild(boardIcon());
  button.appendChild(document.createTextNode(label));
  button.addEventListener("click", act);
  return button;
}

var oneSetupDraw = draw;

draw = function () {
  oneSetupDraw();
  renderOutFacts();
  SCREEN_PORTS.forEach(renderScreenFacts);
  // What is not the board stands back while it is set up
  document.body.classList.toggle("setupall", setupOn);
  if (setupOn) unmark();
  paintAll();
};

state.always.body = capture();
draw();
