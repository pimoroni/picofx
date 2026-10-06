
// ---- the wiring, while the board is set up ------------------------------------------------
// In the outputs' own panel and only while the board is set up, the board's seven connectors along the bottom, each colour output one pin and
// each broken-out one three, a faint line from every pin to the lamp it feeds, brought
// forward by pointing at the lamp or the connector, a moved lamp sliding to its new place,
// and the lamps out of the order they are wired in with their numbers in bold.

var SLIDE_MS = 420;

// The connectors sit under both sides of the outputs, before their tools and settings
(function () {
  var row = document.createElement("div");
  row.id = "wiringRow";
  var sides = document.getElementById("sides");
  sides.parentNode.insertBefore(row, sides.nextSibling);
}());

// Every lamp in the order the board wires them: an output's own lamp, or its three channels
function wiredLamps() {
  var lamps = [];
  wiring.forEach(function (one, out) {
    if (one.broken) {
      [0, 1, 2].forEach(function (channel) { lamps.push({out: out, channel: channel}); });
    } else {
      lamps.push({out: out, channel: null});
    }
  });
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
    "#outRun .lamp[data-key], #monoRun .lamp[data-key]"));
}

function lampNode(key) {
  return lampsShown().filter(function (node) { return node.dataset.key === key; })[0] || null;
}

// Every lamp can be found by what it is, which is what the lines and the slide go by
var oneWiredTakesPlace = takesPlace;

takesPlace = function (node, lamp) {
  oneWiredTakesPlace(node, lamp);
  var key = lampKey({out: lamp.out, channel: lamp.colour ? null : lamp.channel});
  node.dataset.key = key;
  node.addEventListener("mouseenter", function () { bringForward([key], true); });
  node.addEventListener("mouseleave", function () { bringForward([key], false); });
};

// A line, its lamp and its pin brought forward, or let go
function bringForward(keys, on) {
  keys.forEach(function (key) {
    document.querySelectorAll("#outPanel [data-key='" + key + "']").forEach(function (node) {
      node.classList.toggle("wirehot", on);
    });
  });
}

// How far the sides and what follows them run outside setup, the cutting and the bar
// included, so the connectors can take up the same room while setting up
var unwiredSpan = null;

function sidesSpan() {
  return document.getElementById("outTools").getBoundingClientRect().top -
         document.getElementById("sides").getBoundingClientRect().top;
}

function renderConnectors() {
  var box = document.getElementById("wiringRow");
  box.textContent = "";
  var old = document.getElementById("wiringLines");
  if (old) old.parentNode.removeChild(old);
  document.getElementById("outPanel").classList.toggle("wired", setupOn);
  if (!setupOn) {
    unwiredSpan = sidesSpan();
    return;
  }

  var row = document.createElement("div");
  row.className = "wireconnectors";
  wiring.forEach(function (one, out) {
    var block = document.createElement("div");
    block.className = "wireconnector";
    var pins = document.createElement("div");
    pins.className = "wirepins";
    var keys = [];
    (one.broken ? [0, 1, 2] : [null]).forEach(function (channel) {
      var pin = document.createElement("span");
      var key = lampKey({out: out, channel: channel});
      pin.className = "wirepin" + (channel === null ? " whole" : "");
      pin.dataset.key = key;
      if (channel !== null) pin.style.background = CHANNEL_INKS[channel];
      pins.appendChild(pin);
      keys.push(key);
    });
    block.appendChild(pins);
    var name = document.createElement("b");
    name.textContent = String(out + 1);
    block.appendChild(name);
    block.title = "output " + (out + 1) + (one.broken ? ", broken out into three" : "");
    // A pin is too small to aim at, so the connector is what is pointed at
    block.addEventListener("mouseenter", function () { bringForward(keys, true); });
    block.addEventListener("mouseleave", function () { bringForward(keys, false); });
    row.appendChild(block);
  });
  box.appendChild(row);

  var side = wiredSide();
  var astray = astrayOf(side);
  astray.forEach(function (lamp) {
    var node = lampNode(lamp.key);
    if (node) node.classList.add("astray");
  });
  var said = document.createElement("p");
  said.className = "wiresay";
  said.innerHTML = astray.length
    ? "<b>" + astray.length + " of " + side.order.length + "</b> lights are out of the order " +
      "they are wired in, their numbers in bold. Hover over a light or a connector to " +
      "highlight its wire."
    : "Every light is in the order it is wired. Hover over a light or a connector to " +
      "highlight its wire.";
  box.appendChild(said);
  // The connectors sit lower by whatever the cutting and the bar took beyond them, the
  // lines running on down, so setting up leaves the section its size
  row.style.marginTop = "";
  var short = unwiredSpan === null ? 0 : unwiredSpan - sidesSpan();
  if (short > 0) row.style.marginTop = (parseFloat(getComputedStyle(row).marginTop) + short) + "px";
  drawLines();
}

// Faint lines, never none: with no line at all, the lamps over a connector read as the ones
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
    path.style.stroke = lamp.channel === null ? "var(--boardOuts)" : CHANNEL_INKS[lamp.channel];
    lines.appendChild(path);
  });
  panel.appendChild(lines);
}

// ---- the move shown ------------------------------------------------------------------------
// Every lamp measured before a move and played back from its old place to its new one, the
// one carried lifted above the rest. The drag ending draws the page again straight after
// the drop, which would replace the lamps mid-slide, so every draw until the page is next
// idle plays the slide from the same starting places

var oneWiredMove = moveLamp;
var sliding = null;

moveLamp = function (move) {
  slideFrom(lampKey(move.from));
  oneWiredMove(move);
};

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
// from there to its own place; putting one back, the lamp it becomes closes in from the
// middle of the three. The other lamps make way as they do for a move
var oneWiredBreakOut = breakOut;
var oneWiredRejoin = rejoin;

breakOut = function (out) {
  slideFrom(null);
  var whole = sliding.was[lampKey({out: out, channel: null})];
  if (whole) {
    [0, 1, 2].forEach(function (channel) {
      sliding.was[lampKey({out: out, channel: channel})] = whole;
    });
  }
  oneWiredBreakOut(out);
};

rejoin = function (out) {
  slideFrom(null);
  var three = [0, 1, 2].map(function (channel) {
    return sliding.was[lampKey({out: out, channel: channel})];
  }).filter(Boolean);
  if (three.length) {
    sliding.was[lampKey({out: out, channel: null})] = {
      left: three.reduce(function (sum, one) { return sum + one.left; }, 0) / three.length,
      top: three.reduce(function (sum, one) { return sum + one.top; }, 0) / three.length
    };
  }
  oneWiredRejoin(out);
};

drawSteps.after.push(function () {
  renderConnectors();
  playSlide();
});

// The lines run between things the page has laid out, so they follow the layout
window.addEventListener("resize", function () { if (setupOn) draw(); });
