import {BOARD} from "./01_looks.js";
import {
  CHANNEL_INKS, OUTPUTS, draw, drawSteps, lampKey, order, outputSaid, placesOf, shortName, wiring
} from "./03_runs.js";
import {astrayOf} from "./05_effects.js";
import {
  breakOutInScenes, breakingOutputs, brokenSaid, moveLampInScenes, rejoinInScenes,
  resetWiringInScenes, wiringChanged
} from "./07_board.js";
import {setupOn} from "./08_setup.js";

// ---- the wiring, while the board is set up ------------------------------------------------
// The outputs' own panel shows the wiring while the board is set up. The board's connectors run
// along the bottom, each colour output one pin and each broken-out one three. A faint line runs
// from every pin to the lamp it feeds, brought forward by pointing at the lamp or connector. A
// moved lamp slides to its new place, and a lamp out of wiring order has its number in bold.

var SLIDE_MS = 420;

// The connectors sit under both sides of the outputs, before the chosen stretch's settings
(function () {
  var row = document.createElement("div");
  row.id = "wiringRow";
  var sides = document.getElementById("sides");
  sides.parentNode.insertBefore(row, sides.nextSibling);
}());

// Every lamp in the order the board wires them, an output's own lamp or its three channels
function wiredLamps() {
  var lamps = [];
  wiring.forEach(function (one, out) { lamps = lamps.concat(placesOf(out)); });
  lamps.forEach(function (lamp) { lamp.key = lampKey(lamp); });
  return lamps;
}

// The board as the out-of-order rule reads it, a side of the same lamps
// in wired order and in build order
function wiredSide() {
  var wired = wiredLamps();
  var byKey = {};
  wired.forEach(function (lamp) { byKey[lamp.key] = lamp; });
  return {wiring: wired, order: order.map(function (place) { return byKey[lampKey(place)]; })};
}

// The lamps on show
function lampsShown() {
  return Array.prototype.slice.call(document.querySelectorAll(
    "#outBar .cardlamp[data-key], #monoBar .cardlamp[data-key]"));
}

function lampNode(key) {
  return lampsShown().filter(function (node) { return node.dataset.key === key; })[0] || null;
}

// A line, its lamp and its pin brought forward, or let go
export function bringForward(keys, on) {
  keys.forEach(function (key) {
    document.querySelectorAll("#outPanel [data-key='" + key + "']").forEach(function (node) {
      node.classList.toggle("wirehot", on);
    });
  });
}

// Lay the connectors over the chosen stretch's settings, which stand back while setting up,
// so entering and leaving Edit board moves nothing below them. The connectors cover the whole
// of the settings, and the panel only grows by what they need beyond that room
function overlapBelow(box) {
  var settings = document.getElementById("outChosen").getBoundingClientRect().bottom -
                 box.getBoundingClientRect().bottom;
  if (settings <= 0) return;
  box.style.minHeight = Math.max(box.getBoundingClientRect().height, settings) + "px";
  box.style.marginBottom = -settings + "px";
}

function renderConnectors() {
  var box = document.getElementById("wiringRow");
  box.textContent = "";
  box.style.marginBottom = "";
  box.style.minHeight = "";
  var old = document.getElementById("wiringLines");
  if (old) old.parentNode.removeChild(old);
  // A board whose outputs are its own LEDs has no wiring to show
  document.getElementById("outPanel").classList.toggle("wired", setupOn && BOARD.wiring_order);
  if (!setupOn || !BOARD.wiring_order) return;

  var row = document.createElement("div");
  row.className = "wireconnectors";
  wiring.forEach(function (one, out) {
    var block = document.createElement("div");
    block.className = "wireconnector";
    var pins = document.createElement("div");
    pins.className = "wirepins";
    var keys = [];
    // A mono output is one light on one pin, with no channel to mark
    var single = OUTPUTS[out].mono;
    placesOf(out).forEach(function (place) {
      var pin = document.createElement("span");
      var key = lampKey(place);
      pin.className = "wirepin" + (place.channel === null ? " whole" : single ? " single" : "");
      pin.dataset.key = key;
      if (place.channel !== null && !single) pin.style.background = CHANNEL_INKS[place.channel];
      pins.appendChild(pin);
      keys.push(key);
    });
    block.appendChild(pins);
    var name = document.createElement("b");
    name.textContent = shortName({out: out, colour: true});
    block.appendChild(name);
    block.title = outputSaid(out) + (one.broken && !single ? ", broken out into three" : "");
    // A pin is too small to aim at, so the connector is what is pointed at
    block.addEventListener("mouseenter", function () { bringForward(keys, true); });
    block.addEventListener("mouseleave", function () { bringForward(keys, false); });
    row.appendChild(block);
  });
  // The board's edge holds its connectors and, under them, what the wiring order says
  var board = document.createElement("div");
  board.className = "wireboard";
  board.appendChild(row);
  box.appendChild(board);

  var side = wiredSide();
  var astray = astrayOf(side);
  astray.forEach(function (lamp) {
    var node = lampNode(lamp.key);
    if (node) node.classList.add("astray");
  });
  var foot = document.createElement("div");
  foot.className = "wirefoot";
  var said = document.createElement("span");
  said.innerHTML = (astray.length
    ? "<b>" + astray.length + " of " + side.order.length + "</b> lights are out of wiring " +
      "order, numbered in bold. "
    : "All lights are in wiring order. ") + brokenSentence() +
    "Hover over a light or connector to highlight its wire.";
  foot.appendChild(said);
  // The button stays while there is nothing to reset, so the board's edge never changes height
  var reset = resetWiringButton();
  reset.disabled = !wiringChanged(astray);
  foot.appendChild(reset);
  board.appendChild(foot);
  overlapBelow(box);
  drawLines();
}

// Faint lines, never none. With no line at all, the lamps over a connector read as the ones
// it feeds, which a rearranged build is not
function drawLines() {
  var panel = document.getElementById("outPanel");
  var from = panel.getBoundingClientRect();
  var lines = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  lines.id = "wiringLines";
  lines.setAttribute("class", "wirelines");
  wiredLamps().forEach(function (lamp) {
    var node = lampNode(lamp.key);
    var pin = panel.querySelector(".wirepin[data-key='" + lamp.key + "']");
    if (!node || !pin) return;
    var top = node.getBoundingClientRect();
    var bottom = pin.getBoundingClientRect();
    var start = {x: bottom.left + bottom.width / 2 - from.left, y: bottom.top - from.top};
    var end = {x: top.left + top.width / 2 - from.left, y: top.bottom - from.top};
    var rise = (start.y - end.y) / 2;
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M" + start.x + " " + start.y + " C" + start.x + " " +
                      (start.y - rise) + " " + end.x + " " + (end.y + rise) + " " + end.x +
                      " " + end.y);
    path.dataset.key = lamp.key;
    path.style.stroke = lamp.channel === null || OUTPUTS[lamp.out].mono ? "var(--boardOuts)"
                                                                        : CHANNEL_INKS[lamp.channel];
    lines.appendChild(path);
  });
  panel.appendChild(lines);
}

// ---- the move shown ------------------------------------------------------------------------
// Every lamp measured before a move and played back from its old place to its new one, the
// one carried lifted above the rest. The drag ending draws the page again straight after
// the drop, which would replace the lamps mid-slide, so every draw until the page is next
// idle plays the slide from the same starting places

var sliding = null;

export function moveLamp(move) {
  slideFrom(lampKey(move.from));
  moveLampInScenes(move);
}

// The outputs broken out, said as a sentence for the board's edge, or nothing where none are
function brokenSentence() {
  var broken = breakingOutputs().some(function (out) { return wiring[out].broken; });
  if (!broken) return "";
  var said = brokenSaid();
  return said.charAt(0).toUpperCase() + said.slice(1) + ". ";
}

// The button that puts the wiring back as the board comes, each lamp sliding to its place and a
// rejoined output's lamp gathering from the middle of its three
function resetWiringButton() {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "wirereset";
  button.textContent = "Reset wiring";
  button.title = "Rejoin every broken-out output and put every light back in wiring order";
  button.onclick = function () {
    slideFrom(null);
    breakingOutputs().forEach(function (out) {
      if (wiring[out].broken) gatherFromThree(out);
    });
    resetWiringInScenes();
  };
  return button;
}

// Where a lamp is within the outputs' panel. The page may scroll straight after a draw to
// hold a section still, and a place measured within the panel moves with it
function placeInPanel(node) {
  var box = node.getBoundingClientRect();
  var panel = document.getElementById("outPanel").getBoundingClientRect();
  return {left: box.left - panel.left, top: box.top - panel.top};
}

// Every lamp's place now, for the next draw to slide each from, the one carried lifted
function slideFrom(carried) {
  var was = {};
  lampsShown().forEach(function (node) { was[node.dataset.key] = placeInPanel(node); });
  sliding = {was: was, carried: carried};
  window.setTimeout(function () { sliding = null; }, 0);
}

function playSlide() {
  if (!sliding) return;
  var was = sliding.was;
  var carried = sliding.carried;
  lampsShown().forEach(function (node) {
    var from = was[node.dataset.key];
    if (!from) return;
    var to = placeInPanel(node);
    var dx = from.left - to.left;
    var dy = from.top - to.top;
    if (!dx && !dy) return;
    if (node.dataset.key === carried) node.classList.add("moving");
    node.style.transition = "none";
    node.style.transform = "translate(" + dx + "px," + dy + "px)";
    node.getBoundingClientRect();
    node.style.transition = "transform " + SLIDE_MS + "ms cubic-bezier(.2,.7,.2,1)";
    node.style.transform = "";
    window.setTimeout(function () {
      node.classList.remove("moving");
      node.style.transition = "";
    }, SLIDE_MS + 40);
  });
}

// Breaking an output out, its three lamps open out of where its one stood, each sliding
// from there to its own place. Putting one back, the lamp it becomes closes in from the
// middle of the three. The other lamps make way as they do for a move
export function breakOut(out) {
  slideFrom(null);
  var whole = sliding.was[lampKey({out: out, channel: null})];
  if (whole) {
    [0, 1, 2].forEach(function (channel) {
      sliding.was[lampKey({out: out, channel: channel})] = whole;
    });
  }
  breakOutInScenes(out);
}

export function rejoin(out) {
  slideFrom(null);
  gatherFromThree(out);
  rejoinInScenes(out);
}

// Start a rejoined output's lamp in the slide from the middle of its three channels
function gatherFromThree(out) {
  var three = [0, 1, 2].map(function (channel) {
    return sliding.was[lampKey({out: out, channel: channel})];
  }).filter(Boolean);
  if (three.length) {
    sliding.was[lampKey({out: out, channel: null})] = {
      left: three.reduce(function (sum, one) { return sum + one.left; }, 0) / three.length,
      top: three.reduce(function (sum, one) { return sum + one.top; }, 0) / three.length
    };
  }
}

drawSteps.after.push(function () {
  renderConnectors();
  playSlide();
});

// The lines run between things the page has laid out, so they follow the layout
window.addEventListener("resize", function () { if (setupOn) draw(); });
