import {h, replace} from "./00_dom.js";
import {paintSteps} from "./00_draw.js";
import {LOOKS, canPlay, isBanked, lookNamed, whyNot} from "./01_looks.js";
import {beat, livePlay} from "./02_preview.js";
import {
  MIDDLING, active, choosingLook, galleryRun, inkAt, landLook, lookKind, stretchFor
} from "./03_runs.js";
import {takesColour, targetFor} from "./04_lines.js";
import {state} from "./04_scenes.js";
import {groupsOpen} from "./26_drive_files.js";

var LOOK_GROUPS = [
  {name: "Along the lights", says: "travelling from one end to the other",
   looks: ["Rainbow", "Wave", "Scanner", "Chase", "Marquee"]},
  {name: "Ready-made", says: "combinations of other looks",
   looks: ["Campfire", "Emergency", "Party"]},
  {name: "All together", says: "every light shows the same",
   looks: ["Solid", "Colour cycle", "Colour steps", "Breathe", "Blink"]},
  {name: "Individual", says: "each light plays its own part",
   looks: ["Sparkle", "Counter", "Traffic light", "Pelican crossing"]}
];
var CARD_LIGHTS = 12;
var PALETTE = "<path d='M8 1.2a6.8 6.8 0 0 0 0 13.6c1.1 0 1.7-.6 1.7-1.4 0-.9-.7-1.1-.7-1.9 " +
              "0-.8.6-1.3 1.4-1.3h1.8a3 3 0 0 0 3-3C15.2 3.8 12 1.2 8 1.2Z'/>" +
              [[4.6, 8], [5.6, 4.6], [9, 3.6], [12, 5.6]].map(function (at) {
                return "<circle cx='" + at[0] + "' cy='" + at[1] + "' r='1.2' style='fill:var(--panel)'/>";
              }).join("");

var cardFaces = [];
var cardWalks = {};

function spanning() {
  return LOOKS.filter(function (look) { return look.spans || isBanked(look); });
}

function grouped(looks) {
  var named = [].concat.apply([], LOOK_GROUPS.map(function (group) { return group.looks; }));
  var groups = LOOK_GROUPS.map(function (group) {
    return {name: group.name, says: group.says, looks: group.looks.map(lookNamed).filter(function (look) {
      return looks.indexOf(look) >= 0;
    })};
  });
  var rest = looks.filter(function (look) { return named.indexOf(look.name) < 0; });
  if (rest.length) groups.push({name: "More", says: "", looks: rest});
  return groups.filter(function (group) { return group.looks.length; });
}

export function renderGallery() {
  var box = document.getElementById("looks");
  cardFaces = [];
  var mono = lookKind();
  var run = galleryRun(mono);
  var section = run.sections[run === active ? run.picked : stretchFor(run, mono)];
  var lamp = section && run.lamps[section.from];
  box.hidden = !!(section && lookNamed(section.look)) && !(choosingLook && run === active);
  var target = section ? targetFor(run, section) : null;
  var playing = lamp && lamp.colour === !mono ? section.look : undefined;

  function choose(name) {
    var into = galleryRun(mono);
    landLook(into, stretchFor(into, mono), name);
  }

  replace(box, h("div", {class: "looks"},
    nothingCard(playing === null, choose),
    grouped(spanning()).map(function (group) {
      var key = "looks:" + group.name;
      var details = h("details", {open: groupsOpen[key] !== false,
                                  ontoggle: function () { groupsOpen[key] = details.open; }},
        h("summary", {}, h("h4", {}, group.name), group.says ? h("small", {}, group.says) : null),
        h("ul", {}, group.looks.map(function (look) {
          return h("li", {}, lookCard(look, mono, target, playing === look.name, choose));
        })));
      return details;
    })));
}

function lookCard(look, mono, target, on, choose) {
  var can = !target || canPlay(look, target);
  var coloured = !mono && takesColour(look);
  var cells = [];
  for (var i = 0; i < CARD_LIGHTS; i++) cells.push(h("i"));
  cardFaces.push({cells: cells, look: look, mono: mono, key: (mono ? "m" : "c") + "-" + look.name});
  return h("button", {type: "button", "aria-pressed": can && on ? "true" : "false",
                      "aria-disabled": can ? null : "true",
                      title: can ? look.name + ": apply it to the selected stretch" +
                                   (coloured ? ". You can choose its colour" : "")
                                 : whyNot(look, target),
                      onclick: function () { if (can) choose(look.name); }},
    h("span", {}, cells),
    h("strong", {}, look.name,
      coloured ? h("svg:svg", {viewBox: "0 0 16 16", "aria-hidden": "true", html: PALETTE}) : null));
}

function nothingCard(on, choose) {
  return h("button", {type: "button", "aria-pressed": on ? "true" : "false",
                      title: state.at >= 0 ? "Play nothing of this scene's own on the selected stretch"
                                           : "turn a stretch off",
                      onclick: function () { choose(null); }},
    h("span"), "Nothing");
}

function paintCards() {
  cardFaces.forEach(function (one) {
    var store = cardWalks[one.key] || (cardWalks[one.key] = {});
    one.cells.forEach(function (cell, i) {
      var walk = store[i] || (store[i] = {});
      var lit = livePlay(one.look, MIDDLING, beat, i, CARD_LIGHTS, walk);
      cell.style.background = lit
        ? inkAt({level: lit.level, ink: one.mono ? "#ffd9a0" : lit.ink})
        : "#3a3f44";
    });
  });
}

paintSteps.push(paintCards);
