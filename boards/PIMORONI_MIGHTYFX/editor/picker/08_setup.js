
// ---- where the board is set up ----------------------------------------------------------
// Every fact about the board stays beside what it is about: the wiring on the outputs, a
// strip's length on the strip, a screen's type on the screen. What differs is how a page
// says those are the board's and not the scene's, and when they can be changed.
//
//   page     a setup mode for the whole page, turned on in the header
//   panel    a setup band in each panel, opened from that panel's header
//   marker   always editable, every board fact wearing the same mark
//   both     the mark always, and the setup mode for changing them
//   section  each fact in a box of its section's own colour, and the setup mode for
//            the whole board entered from any section's header, where it is needed

var SETUP_WAY = "section";

var WAYS_SAID = {
  page: "Set up the board from the header; outside that, it reads as plain words",
  panel: "Each panel sets up its own part of the board",
  marker: "Board facts are changed where they sit, and marked as the board's",
  both: "Board facts are marked, and changed in a setup mode",
  section: "A coloured box is a board setting, set up from any section"
};

// Whether the whole page is in its setup mode, and which panels have their band open
var setupOn = false;
var setupOpen = {};

// The panels that hold a board fact, and the colour each one's box takes
var SECTIONS = {outPanel: "outs", striplPanel: "stripl", striprPanel: "stripr",
                screenaPanel: "screena", screenbPanel: "screenb"};

function marked() { return SETUP_WAY === "marker" || SETUP_WAY === "both"; }

// Whether a fact reads as its section's coloured box
function boxed() { return SETUP_WAY === "section"; }

// Whether the board facts in this panel can be changed just now
function canEdit(panel) {
  if (SETUP_WAY === "marker") return true;
  if (SETUP_WAY === "panel") return !!setupOpen[panel];
  return setupOn;
}

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

// The mark every board fact wears where marking is the way: a small board with pins
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

// One board fact as it reads in place: marked where that is the way, and saying so
function fact(content) {
  var chip = document.createElement("span");
  chip.className = "fact" + (marked() ? " boardfact" : "");
  if (marked()) {
    chip.appendChild(boardIcon());
    chip.title = "How the board is built, which is the same in every scene";
  }
  if (typeof content === "string") chip.appendChild(document.createTextNode(content));
  else chip.appendChild(content);
  return chip;
}

// A panel's band, where the panel way opens one: its facts under a label saying whose
function band(box, panel) {
  box.classList.toggle("setupband", SETUP_WAY === "panel" && !!setupOpen[panel]);
  if (SETUP_WAY !== "panel" || !setupOpen[panel]) return;
  var says = document.createElement("span");
  says.className = "bandsays";
  says.textContent = "Board setup, the same in every scene";
  box.appendChild(says);
}

// ---- the facts, in place --------------------------------------------------------------------

// The arrows on the lamps are how an output is broken out, so they show only where the
// wiring can be changed, and are marked as the board's where marking is the way
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
  if (marked()) made.classList.add("boardfact");
  if (boxed()) made.classList.add("boardarrow");
  return made;
};

function renderOutFacts() {
  var box = document.getElementById("outFacts");
  box.textContent = "";
  band(box, "outPanel");
  var said = brokenSaid();
  if (boxed()) {
    box.appendChild(boardBox("outPanel", ["Wiring", small(said)]));
    if (canEdit("outPanel")) {
      var hint = document.createElement("span");
      hint.className = "hint";
      hint.textContent = "Drag a light to where it sits in your build. Arrows split an " +
                         "output into three mono lights, or rejoin them.";
      hint.title = hint.textContent;
      box.appendChild(hint);
    }
    return;
  }
  box.appendChild(fact(said.charAt(0).toUpperCase() + said.slice(1) +
                       (canEdit("outPanel") ? ". The arrow on an output breaks it out, or " +
                                              "puts it back." : ".")));
}

var oneRenderLeds = renderLeds;

renderLeds = function (where, run) {
  var box = document.getElementById(where);
  var panel = run.id + "Panel";
  if (boxed()) {
    // The strip's own count box is already the board's, so the icon goes inside it and
    // it takes the strip's colour
    if (canEdit(panel)) {
      oneRenderLeds(where, run);
      var says = box.querySelector(".says");
      if (says) box.removeChild(says);
      var chip = box.querySelector(".chip");
      chip.className = "chip boardchip " + SECTIONS[panel];
      chip.title = "How the board is built, which is the same in every scene";
      chip.insertBefore(boardIcon(), chip.firstChild);
    } else {
      box.textContent = "";
      box.appendChild(boardBox(panel, ["Strip", small(run.leds + " LEDs")]));
    }
    return;
  }
  if (canEdit(panel)) {
    oneRenderLeds(where, run);
    var chip = box.querySelector(".chip");
    var says = box.querySelector(".says");
    if (says) box.removeChild(says);
    box.removeChild(chip);
    band(box, panel);
    box.appendChild(fact(chip));
  } else {
    box.textContent = "";
    band(box, panel);
    box.appendChild(fact(run.leds + " LEDs"));
  }
};

function renderScreenFacts(port) {
  var box = document.getElementById(port.id + "Facts");
  var panel = port.id + "Panel";
  box.textContent = "";
  band(box, panel);
  if (boxed()) {
    var size = screensFitted[port.id];
    box.appendChild(boardBox(panel, [port.label, canEdit(panel)
      ? screenSize(port)
      : small(size ? size + " inch" : "no panel fitted")]));
    return;
  }
  if (canEdit(panel)) {
    var label = document.createElement("label");
    label.appendChild(document.createTextNode("Panel fitted "));
    label.appendChild(screenSize(port));
    box.appendChild(fact(label));
  } else {
    var fitted = screensFitted[port.id];
    box.appendChild(fact(fitted ? fitted + " inch panel fitted" : "No panel fitted"));
  }
}

// Once there are scenes the mark has to be read against them, so the frame says what it is
function renderMarkNote() {
  var box = document.getElementById("markNote");
  box.textContent = "";
  if (!marked() || !state.scenes.length) return;
  box.appendChild(boardIcon());
  box.appendChild(document.createTextNode(
    "marks how the board is built, which is the same in every scene"));
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

function renderSetupButtons() {
  if (SETUP_WAY === "page" || SETUP_WAY === "both") {
    var header = document.getElementById("setupHead");
    header.textContent = "";
    header.appendChild(setupButton(setupOn ? "Done setting up" : "Set up the board", setupOn,
                                   function () {
                                     setSetup(!setupOn);
                                     draw();
                                   }));
    document.body.classList.toggle("setup", setupOn);
    var banner = document.getElementById("setupBanner");
    banner.hidden = !setupOn;
    banner.textContent = setupOn
      ? "Setting up the board. What is changed here is the same in every scene, so the " +
        "scenes and looks wait until you are done."
      : "";
  }
  if (SETUP_WAY === "section") {
    // The whole board is set up at once, from whichever section it was wanted in, and
    // any section's Done ends it. What is not the board stands back meanwhile
    document.body.classList.toggle("setupall", setupOn);
    Object.keys(SECTIONS).forEach(function (panel) {
      sectionButton(panel, setupOn ? "Done" : "Set up", setupOn,
                    function () { setSetup(!setupOn); });
    });
  }
  if (SETUP_WAY === "panel") {
    Object.keys(SECTIONS).forEach(function (panel) {
      sectionButton(panel, setupOpen[panel] ? "Done" : "Set up", setupOpen[panel],
                    function () { setupOpen[panel] = !setupOpen[panel]; });
    });
  }
}

// A section's own setup button, in the header of its panel
function sectionButton(panel, label, on, toggle) {
  var summary = document.querySelector("#" + panel + " > summary");
  var box = summary.querySelector(".setupslot");
  if (!box) {
    box = document.createElement("span");
    box.className = "setupslot";
    summary.appendChild(box);
  }
  box.textContent = "";
  // Every section grows or shrinks as setup opens and closes, so the one pressed is
  // held where it was on the screen
  box.appendChild(setupButton(label, on, function () {
    var was = summary.getBoundingClientRect().top;
    toggle();
    draw();
    window.scrollBy(0, summary.getBoundingClientRect().top - was);
  }));
}

var oneSetupDraw = draw;

draw = function () {
  oneSetupDraw();
  renderOutFacts();
  SCREEN_PORTS.forEach(renderScreenFacts);
  renderMarkNote();
  renderSetupButtons();
  if (setupOn) unmark();
  document.getElementById("setupWay").textContent = WAYS_SAID[SETUP_WAY];
  paintAll();
};

state.always.body = capture();
draw();
