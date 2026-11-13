import {h, replace} from "./00_dom.js";
import {draw, drawSteps} from "./00_draw.js";
import {astrayOf} from "./01_colours.js";
import {BOARD, lookNamed} from "./01_looks.js";
import {painters} from "./02_preview.js";
import {
  CHANNELS, CHANNEL_INKS, MONO_FIRST, OUTPUTS, isChannel, order, outputSaid, placesOf, sameLamp,
  selectorFor, shortName, wiring
} from "./03_outputs.js";
import {canEdit, inkAt, lampKey, sectionAt, setupOn} from "./03_runs.js";
import {underSaid} from "./04_scenes.js";
import {breakOutInScenes, lampsMovable, moveLampInScenes, rejoinInScenes} from "./07_board.js";

var SLIDE_MS = 420;
var RIGHT = "<path d='M3 8 H12'/><path d='M8.5 4.5 L12 8 L8.5 11.5'/>";
var LEFT = "<path d='M13 8 H4'/><path d='M7.5 4.5 L4 8 L7.5 11.5'/>";

var carrying = null;
var sliding = null;
var unwiredSpan = null;

(function () {
  var sides = document.getElementById("sides");
  sides.parentNode.insertBefore(h("div", {id: "wiringRow"}), sides.nextSibling);
}());

export function renderWiringRun(where, run) {
  var box = document.getElementById(where);
  var faces = [];
  var groups = [];
  run.lamps.forEach(function (lamp, at) {
    var last = groups[groups.length - 1];
    if (!last || last.out !== lamp.out) {
      last = {out: lamp.out, whole: lamp.colour, lamps: []};
      groups.push(last);
    }
    last.lamps.push({lamp: lamp, at: at});
  });
  replace(box, h("ol", {}, groups.map(function (group) {
    return h("li", {"data-out": group.out, "data-whole": group.whole},
      crossing(group.out, group.whole),
      h("ol", {}, group.lamps.map(function (one) {
        var face = h("i");
        faces.push(face);
        return wiringLamp(run, one.lamp, one.at, face);
      })));
  })));
  painters.push({run: run, paint: function (all) {
    faces.forEach(function (face, at) { paintWiringFace(face, all[at]); });
  }});
}

function wiringLamp(run, lamp, at, face) {
  var place = {out: lamp.out, channel: lamp.colour ? null : lamp.channel};
  var key = lampKey(place);
  var section = run.sections[sectionAt(run, at)];
  var playing = lookNamed(section.look);
  var channel = !lamp.colour && isChannel(lamp);
  var node = h("li", {"data-key": key, draggable: lampsMovable(),
                      "data-channel": channel ? CHANNELS[lamp.channel] : null,
                      "data-single": !lamp.colour && !channel,
                      style: {"--chan": channel ? CHANNEL_INKS[lamp.channel] : null},
                      title: selectorFor(lamp) + (playing ? ", playing " + playing.name : underSaid(run, at)),
                      onmouseenter: function () {
                        bringForward([key], true);
                        if (channel) showKin(lamp.out, true);
                      },
                      onmouseleave: function () {
                        bringForward([key], false);
                        if (channel) showKin(lamp.out, false);
                      },
                      ondragstart: function (event) {
                        carrying = place;
                        event.dataTransfer.effectAllowed = "move";
                        event.dataTransfer.setData("text/plain", shortName(lamp));
                        node.dataset.carried = "";
                      },
                      ondragend: function () {
                        carrying = null;
                        draw();
                      },
                      ondragover: function (event) {
                        if (!carrying || sameLamp(carrying, place)) return;
                        event.preventDefault();
                        node.dataset.landing = after(event) ? "after" : "before";
                      },
                      ondragleave: function () { delete node.dataset.landing; },
                      ondrop: function (event) {
                        event.preventDefault();
                        delete node.dataset.landing;
                        if (!carrying || sameLamp(carrying, place)) return;
                        var carried = carrying;
                        carrying = null;
                        moveLamp({from: carried, to: place, after: after(event)});
                      }},
    face, h("small", {}, shortName(lamp)));

  function after(event) {
    var box = node.getBoundingClientRect();
    return event.clientX > box.left + box.width / 2;
  }
  return node;
}

function paintWiringFace(face, lit) {
  var one = lit || {level: 0, ink: "#e4e0d9"};
  face.style.background = one.nothing ? "#2a2d30" : inkAt(one);
  face.parentNode.toggleAttribute("data-unset", !!one.unset);
  face.style.boxShadow = one.level > 0.05
    ? "inset 0 0 0 1px rgba(0,0,0,.2), 0 0 " + (3 + one.level * 8).toFixed(1) +
      "px rgba(255,217,160," + (one.level * 0.5).toFixed(2) + ")"
    : "inset 0 0 0 1px rgba(0,0,0,.2)";
}

function showKin(out, on) {
  document.querySelectorAll("#sides [id$=Run] > ol > li[data-out='" + out + "']").forEach(function (group) {
    group.toggleAttribute("data-kin", on);
  });
}

function crossing(out, whole) {
  if (!canEdit("outPanel") || OUTPUTS[out].mono || !OUTPUTS[out].breaks) return null;
  var says = whole ? "split " + outputSaid(out) + " into three mono lights"
                   : "rejoin " + outputSaid(out) + " as one colour light";
  return h("button", {type: "button", title: says, "aria-label": says,
                      onclick: function (event) {
                        event.stopPropagation();
                        if (whole) breakOut(out); else rejoin(out);
                      }},
    h("svg:svg", {viewBox: "0 0 16 16", width: 12, height: 12, fill: "none", stroke: "currentColor",
                  "stroke-width": 1.7, "stroke-linecap": "round", "stroke-linejoin": "round",
                  html: whole === MONO_FIRST ? LEFT : RIGHT}));
}

function wiredLamps() {
  var lamps = [];
  wiring.forEach(function (one, out) { lamps = lamps.concat(placesOf(out)); });
  lamps.forEach(function (lamp) { lamp.key = lampKey(lamp); });
  return lamps;
}

function wiredSide() {
  var wired = wiredLamps();
  var byKey = {};
  wired.forEach(function (lamp) { byKey[lamp.key] = lamp; });
  return {wiring: wired, order: order.map(function (place) { return byKey[lampKey(place)]; })};
}

function lampsShown() {
  return Array.prototype.slice.call(document.querySelectorAll("#sides [id$=Run] li[data-key]"));
}

function lampNode(key) {
  return lampsShown().filter(function (node) { return node.dataset.key === key; })[0] || null;
}

function bringForward(keys, on) {
  keys.forEach(function (key) {
    document.querySelectorAll("#outPanel [data-key='" + key + "']").forEach(function (node) {
      node.toggleAttribute("data-hot", on);
    });
  });
}

function sidesSpan() {
  return document.getElementById("outChosen").getBoundingClientRect().top -
         document.getElementById("sides").getBoundingClientRect().top;
}

function renderConnectors() {
  var box = document.getElementById("wiringRow");
  var old = document.getElementById("wiringLines");
  if (old) old.remove();
  var wired = setupOn && BOARD.wiring_order;
  document.getElementById("outPanel").toggleAttribute("data-wired", wired);
  if (!wired) {
    replace(box);
    unwiredSpan = sidesSpan();
    return;
  }
  var side = wiredSide();
  var astray = astrayOf(side);
  astray.forEach(function (lamp) {
    var node = lampNode(lamp.key);
    if (node) node.dataset.astray = "";
  });
  var connectors = h("ol", {}, wiring.map(function (one, out) {
    var single = OUTPUTS[out].mono;
    var keys = placesOf(out).map(lampKey);
    return h("li", {title: outputSaid(out) + (one.broken && !single ? ", broken out into three" : ""),
                    onmouseenter: function () { bringForward(keys, true); },
                    onmouseleave: function () { bringForward(keys, false); }},
      h("span", {}, placesOf(out).map(function (place) {
        return h("i", {"data-key": lampKey(place),
                       "data-shape": place.channel === null ? "whole" : single ? "single" : "channel",
                       style: {background: place.channel !== null && !single ? CHANNEL_INKS[place.channel] : null}});
      })),
      h("small", {}, shortName({out: out, colour: true})));
  }));
  replace(box, connectors,
    h("p", {}, astray.length
      ? [h("b", {}, astray.length + " of " + side.order.length), " lights are out of wiring order, " +
         "numbered in bold. Hover over a light or connector to highlight its wire."]
      : "All lights are in wiring order. Hover over a light or connector to highlight its wire."));
  var short = unwiredSpan === null ? 0 : unwiredSpan - sidesSpan();
  connectors.style.setProperty("--reach", Math.max(0, short) + "px");
  drawLines();
}

function drawLines() {
  var panel = document.getElementById("outPanel");
  var from = panel.getBoundingClientRect();
  var paths = wiredLamps().map(function (lamp) {
    var node = lampNode(lamp.key);
    var pin = panel.querySelector("#wiringRow i[data-key='" + lamp.key + "']");
    if (!node || !pin) return null;
    var top = node.getBoundingClientRect();
    var bottom = pin.getBoundingClientRect();
    var start = {x: bottom.left + bottom.width / 2 - from.left, y: bottom.top - from.top};
    var end = {x: top.left + top.width / 2 - from.left, y: top.bottom - from.top};
    var rise = (start.y - end.y) / 2;
    return h("svg:path", {"data-key": lamp.key,
                          d: "M" + start.x + " " + start.y + " C" + start.x + " " + (start.y - rise) +
                             " " + end.x + " " + (end.y + rise) + " " + end.x + " " + end.y,
                          style: {stroke: lamp.channel === null || OUTPUTS[lamp.out].mono
                                    ? "var(--boardOuts)" : CHANNEL_INKS[lamp.channel]}});
  });
  panel.appendChild(h("svg:svg", {id: "wiringLines"}, paths));
}

function moveLamp(move) {
  slideFrom(lampKey(move.from));
  moveLampInScenes(move);
}

function placeInPanel(node) {
  var box = node.getBoundingClientRect();
  var panel = document.getElementById("outPanel").getBoundingClientRect();
  return {left: box.left - panel.left, top: box.top - panel.top};
}

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
    if (node.dataset.key === carried) node.dataset.moving = "";
    node.style.transition = "none";
    node.style.transform = "translate(" + dx + "px," + dy + "px)";
    node.getBoundingClientRect();
    node.style.transition = "transform " + SLIDE_MS + "ms cubic-bezier(.2,.7,.2,1)";
    node.style.transform = "";
    window.setTimeout(function () {
      delete node.dataset.moving;
      node.style.transition = "";
    }, SLIDE_MS + 40);
  });
}

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

function rejoin(out) {
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
  rejoinInScenes(out);
}

drawSteps.after.push(function () {
  renderConnectors();
  playSlide();
});

window.addEventListener("resize", function () { if (setupOn) draw(); });
