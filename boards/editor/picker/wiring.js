import {
  breakOutInScenes, breakingOutputs, brokenSaid, moveLampInScenes, rejoinInScenes,
  resetWiringInScenes, wiringChanged
} from "./board.js";
import {astrayOf} from "./colours.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "./draw.js";
import {iconButton} from "./led_panels.js";
import {BOARD} from "./looks.js";
import {
  CHANNEL_INKS, MONO_FIRST, OUTPUTS, kinOf, order, outputSaid, placesOf, shortName, wiring
} from "./outputs.js";
import {
  BACK, LEFT, ON, RIGHT, canEdit, joinAll, lampKey, setupOn, stepBack, stepOn
} from "./runs.js";
import {middleOfView, toolButton, zoomOf, zoomTo} from "./stretch_bar.js";
import {GLASS_IN, GLASS_OUT, ZOOMS_OVER} from "./strips.js";

// ---- the wiring ---------------------------------------------------------------------------------
// The wiring row over the outputs and each strip's header row, with their steps back and on, and
// the wiring drawn and changed while the board is set up.

// Light an output's three channels, each at its own edge and in its own colour, so what the
// arrow would rejoin is visible before it is pressed
export function showKin(out, on) {
  (kinOf[out] || []).forEach(function (node) { node.classList.toggle("kin", on); });
}

// The one act there is, said as a direction. A colour output crosses to the mono side and
// becomes three mono lights, and those three cross back as one colour output. It shows only
// where the wiring can be changed, in the board's colour, and only on an output that breaks out
export function crossing(out, colour) {
  if (!canEdit("outPanel") || OUTPUTS[out].mono || !OUTPUTS[out].breaks) return noArrow();
  var says = colour
    ? "split " + outputSaid(out) + " into three mono lights"
    : "rejoin " + outputSaid(out) + " as one colour light";
  return h("button", {
    className: "cross boardarrow", title: says, "aria-label": says,
    html: "<svg viewBox='0 0 16 16' width='12' height='12' fill='none' " +
          "stroke='currentColor' stroke-width='1.7' stroke-linecap='round' " +
          "stroke-linejoin='round'>" + (colour === MONO_FIRST ? LEFT : RIGHT) + "</svg>",
    onclick: function (event) {
      event.stopPropagation();
      if (colour) breakOut(out); else rejoin(out);
    }
  });
}

// ---- the rows around the bar ---------------------------------------------------------------

// Add the run's controls at the right of its header row, the box naming its wiring or its strip.
// A long strip zooms first, then come the steps back and on, then Join all as a quick reset
export function headSteps(row, run) {
  var join = toolButton("&#10231;", "Join all", run.sections.length < 2, "join",
                        "merge into one stretch, keeping the selected stretch's look");
  join.onclick = function () { joinAll(run); };
  // Zooming is only any use where there are more lights than a panel can show. The
  // buttons hold the middle of the view, since a press has no place on the run to hold
  var zooms = run.strip && run.count > ZOOMS_OVER;
  row.appendChild(h("span", {className: "headsteps"},
    zooms ? [iconButton(GLASS_OUT, "Zoom out", zoomOf(run) <= 1.001, function () {
               zoomTo(run, zoomOf(run) / 1.6, middleOfView(run));
             }),
             h("span", {className: "howfar"}, Math.round(zoomOf(run) * 100) + "%"),
             iconButton(GLASS_IN, "Zoom in", zoomOf(run) >= 23.9, function () {
               zoomTo(run, zoomOf(run) * 1.6, middleOfView(run));
             })]
          : null,
    iconButton(BACK, "Undo", !(run.was && run.was.length), function () { stepBack(run); }),
    iconButton(ON, "Redo", !(run.undone && run.undone.length), function () { stepOn(run); }),
    join));
}

// ---- the wiring, while the board is set up ------------------------------------------------
// The outputs' own panel shows the wiring while the board is set up. The board's connectors run
// along the bottom, each colour output one pin and each broken-out one three. A faint line runs
// from every pin to the lamp it feeds, brought forward by pointing at the lamp or connector. A
// moved lamp slides to its new place, and a lamp out of wiring order has its number in bold.

var SLIDE_MS = 420;

// The connectors sit under both sides of the outputs, before the chosen stretch's settings
document.getElementById("sides").after(h("div", {id: "wiringRow"}));

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
  replace(box);
  box.style.marginBottom = "";
  box.style.minHeight = "";
  var old = document.getElementById("wiringLines");
  if (old) old.remove();
  // A board whose outputs are its own LEDs has no wiring to show
  document.getElementById("outPanel").classList.toggle("wired", setupOn && BOARD.wiring_order);
  if (!setupOn || !BOARD.wiring_order) return;

  var side = wiredSide();
  var astray = astrayOf(side);
  astray.forEach(function (lamp) {
    var node = lampNode(lamp.key);
    if (node) node.classList.add("astray");
  });
  // The button stays while there is nothing to reset, so the board's edge never changes height
  var reset = resetWiringButton();
  reset.disabled = !wiringChanged(astray);
  // The board's edge holds its connectors and, under them, what the wiring order says
  var tail = brokenSentence() + "Hover over a light or connector to highlight its wire.";
  box.appendChild(h("div", {className: "wireboard"},
    h("div", {className: "wireconnectors"}, wiring.map(connector)),
    h("div", {className: "wirefoot"},
      h("span", {}, astray.length
        ? [h("b", {}, astray.length + " of " + side.order.length),
           " lights are out of wiring order, numbered in bold. " + tail]
        : "All lights are in wiring order. " + tail),
      reset)));
  overlapBelow(box);
  drawLines();
}

// An output's connector on the board's edge, a pin for each light it feeds, named under them
function connector(one, out) {
  // A mono output is one light on one pin, with no channel to mark
  var single = OUTPUTS[out].mono;
  var keys = [];
  var pins = placesOf(out).map(function (place) {
    var key = lampKey(place);
    keys.push(key);
    return h("span", {
      className: "wirepin" + (place.channel === null ? " whole" : single ? " single" : ""),
      "data-key": key,
      style: {background: place.channel !== null && !single ? CHANNEL_INKS[place.channel] : null}
    });
  });
  // A pin is too small to aim at, so the connector is what is pointed at
  return h("div", {
    className: "wireconnector",
    title: outputSaid(out) + (one.broken && !single ? ", broken out into three" : ""),
    onmouseenter: function () { bringForward(keys, true); },
    onmouseleave: function () { bringForward(keys, false); }
  }, h("div", {className: "wirepins"}, pins), h("b", {}, shortName({out: out, colour: true})));
}

// Faint lines, never none. With no line at all, the lamps over a connector read as the ones
// it feeds, which a rearranged build is not
function drawLines() {
  var panel = document.getElementById("outPanel");
  var from = panel.getBoundingClientRect();
  panel.appendChild(h("svg:svg", {id: "wiringLines", class: "wirelines"},
    wiredLamps().map(function (lamp) {
      var node = lampNode(lamp.key);
      var pin = panel.querySelector(".wirepin[data-key='" + lamp.key + "']");
      if (!node || !pin) return null;
      var top = node.getBoundingClientRect();
      var bottom = pin.getBoundingClientRect();
      var start = {x: bottom.left + bottom.width / 2 - from.left, y: bottom.top - from.top};
      var end = {x: top.left + top.width / 2 - from.left, y: top.bottom - from.top};
      var rise = (start.y - end.y) / 2;
      return h("svg:path", {
        d: "M" + start.x + " " + start.y + " C" + start.x + " " + (start.y - rise) + " " +
           end.x + " " + (end.y + rise) + " " + end.x + " " + end.y,
        "data-key": lamp.key,
        style: {stroke: lamp.channel === null || OUTPUTS[lamp.out].mono
                          ? "var(--boardOuts)" : CHANNEL_INKS[lamp.channel]}
      });
    })));
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
  return h("button", {
    type: "button", className: "wirereset",
    title: "Rejoin every broken-out output and put every light back in wiring order",
    onclick: function () {
      slideFrom(null);
      breakingOutputs().forEach(function (out) {
        if (wiring[out].broken) gatherFromThree(out);
      });
      resetWiringInScenes();
    }
  }, "Reset wiring");
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
function breakOut(out) {
  slideFrom(null);
  var whole = sliding.was[lampKey({out: out, channel: null})];
  if (whole) {
    [0, 1, 2].forEach(function (channel) {
      sliding.was[lampKey({out: out, channel: channel})] = whole;
    });
  }
  breakOutInScenes(out);
}

function rejoin(out) {
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

addStep(drawSteps.after, DRAW_AFTER, "wiring", function () {
  renderConnectors();
  playSlide();
});

// The lines run between things the page has laid out, so they follow the layout
window.addEventListener("resize", function () { if (setupOn) draw(); });

// ---- the facts, in place --------------------------------------------------------------------

// Where the wiring cannot be changed an output's arrow is left out. What stands in its place
// takes no room, as the arrow does, or each output's lamps would sit further apart outside setup
function noArrow() {
  return h("span", {style: {position: "absolute"}});
}
