import {h, replace} from "./00_dom.js";
import {BOARD} from "./01_looks.js";
import {MONO_FIRST, mono, outs, stepBack, stepOn} from "./03_runs.js";
import {middleOfView, zoomOf, zoomTo, zooms} from "./31_stretch_bar.js";

var UNDO = "<path d='M6.5 4.5 L2.5 8 L6.5 11.5'/><path d='M2.5 8 H9.5 A4 4 0 0 1 9.5 15'/>";
var REDO = "<path d='M9.5 4.5 L13.5 8 L9.5 11.5'/><path d='M13.5 8 H6.5 A4 4 0 0 0 6.5 15'/>";
var ZOOM_OUT = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
               "<path d='M5 7.2 L9.4 7.2'/>";
var ZOOM_IN = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
              "<path d='M5 7.2 L9.4 7.2 M7.2 5 L7.2 9.4'/>";
var ZOOM_STEP = 1.6;

function iconButton(drawing, says, off, done) {
  return h("button", {type: "button", title: says, "aria-label": says, disabled: off,
                      onclick: done},
    h("svg:svg", {viewBox: "0 0 17 17", width: 15, height: 15, fill: "none", stroke: "currentColor",
                  "stroke-width": 1.5, "stroke-linecap": "round", "stroke-linejoin": "round",
                  html: drawing}));
}

export function panelTools(run) {
  var zoom = zooms(run) ? [
    iconButton(ZOOM_OUT, "Zoom out", zoomOf(run) <= 1.001,
               function () { zoomTo(run, zoomOf(run) / ZOOM_STEP, middleOfView(run)); }),
    h("output", {}, Math.round(zoomOf(run) * 100) + "%"),
    iconButton(ZOOM_IN, "Zoom in", zoomOf(run) >= 23.9,
               function () { zoomTo(run, zoomOf(run) * ZOOM_STEP, middleOfView(run)); })
  ] : [];
  return h("span", {role: "group", "aria-label": "Steps"}, zoom,
    iconButton(UNDO, "Undo", !(run.was && run.was.length), function () { stepBack(run); }),
    iconButton(REDO, "Redo", !(run.undone && run.undone.length), function () { stepOn(run); }));
}

export function renderSides() {
  var words = BOARD.output_words;
  var two = mono.lamps.length > 0;
  [{run: outs, side: "sideA", head: "headA", title: words.colour, says: words.colour_says},
   {run: mono, side: "sideB", head: "headB", title: words.mono, says: words.mono_says}]
    .forEach(function (set) {
      var box = document.getElementById(set.side);
      var count = set.run.lamps.length;
      box.hidden = !count;
      var outputs = new Set(set.run.lamps.map(function (lamp) { return lamp.out; }));
      box.style.setProperty("--room", count + outputs.size);
      var head = document.getElementById(set.head);
      head.hidden = !two;
      replace(head, set.title, " ",
              count ? h("small", {}, count + (count === 1 ? " light, " : " lights, ") + set.says) : null);
    });
  document.getElementById("sides").toggleAttribute("data-unnamed", !two);
}

(function () {
  var after = document.getElementById("outPanel");
  BOARD.strips.forEach(function (strip) {
    var id = strip.name;
    var panel = h("details", {class: "panel", "data-strip": true, id: id + "Panel", open: true,
                              style: {"--strip": strip.colour}},
      h("summary", {}, strip.label.charAt(0).toUpperCase() + strip.label.slice(1),
        h("span", {class: "says"}, strip.says)),
      h("header", {id: id + "Leds"}),
      h("div", {id: id + "Bar"}),
      h("div", {id: id + "Chosen"}));
    after.parentNode.insertBefore(panel, after.nextSibling);
    after = panel;
  });
  document.getElementById("sides").toggleAttribute("data-mono-first", MONO_FIRST);
  document.querySelector("#outPanel > summary .says").textContent = BOARD.output_words.panel;
}());
