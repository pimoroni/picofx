import {h, replace} from "./00_dom.js";
import {draw} from "./00_draw.js";
import {lookNamed} from "./01_looks.js";
import {shortName, widthOf} from "./03_outputs.js";
import {
  active, cutAt, inkAt, moveEdge, painters, pick, remember, settle, stretchUnder, uncut, washFor
} from "./03_runs.js";
import {targetFor, wherePlays} from "./04_lines.js";
import {keptLights} from "./27_readback.js";

var ZOOMS_OVER = 12;
var MOST_ZOOM = 24;

var dragging = null;
var dragged = false;

export function zoomOf(run) { return run.zoom || 1; }

export function zooms(run) { return !!run.strip && run.lamps.length > ZOOMS_OVER; }

function viewOf(run) {
  return document.querySelector("[data-stretches='" + run.name + "'] .stretches");
}

export function middleOfView(run) {
  var view = viewOf(run);
  if (!view) return 0.5;
  return (view.scrollLeft + view.clientWidth / 2) / view.firstChild.offsetWidth;
}

export function zoomTo(run, want, at, from) {
  want = Math.round(want * 1000) / 1000;
  if (Math.abs(want - 1) < 0.01) want = 1;
  run.zoom = Math.max(1, Math.min(MOST_ZOOM, want));
  draw();
  var view = viewOf(run);
  if (!view) return;
  var to = at * view.firstChild.offsetWidth - (from === undefined ? view.clientWidth / 2 : from);
  view.scrollLeft = Math.max(0, to);
  run.scrolled = view.scrollLeft;
}

export function renderStretches(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  if (!zooms(run)) {
    run.zoom = 1;
    run.scrolled = 0;
  }
  box.dataset.stretches = run.name;
  var faces = [];
  var kept = keptLights(run);
  var list = h("ol", {"data-kind": run.strip ? "strip" : "lamps",
                      "data-labelled": !run.strip || run.lamps.length <= ZOOMS_OVER,
                      style: {"--zoom": zoomOf(run)}},
               run.sections.map(function (section, at) {
                 return stretch(run, section, at, faces, kept);
               }));
  var view = h("div", {class: "stretches", "data-zoomed": zoomOf(run) > 1,
                       onscroll: function () { run.scrolled = view.scrollLeft; },
                       onwheel: function (event) { wheel(run, view, event); }}, list);
  replace(box, view);
  view.scrollLeft = run.scrolled || 0;
  turnLabelsInward(list);
  painters.push({run: run, paint: function (all) {
    faces.forEach(function (face, at) { paintFace(face, all[at], !run.strip); });
  }});
}

function stretch(run, section, at, faces, kept) {
  var look = lookNamed(section.look);
  var under = look ? null : stretchUnder(run, section);
  var wide = widthOf(section);
  var lamps = run.lamps.slice(section.from, section.to + 1);
  var claimed = lamps.map(function (lamp, i) { return kept[section.from + i]; });
  var firstClaim = claimed.filter(Boolean)[0];
  return h("li", {"aria-current": run === active && run.picked === at ? "true" : null,
                  "data-nothing": !look, "data-narrow": wide * 40 < run.lamps.length * 8,
                  style: {"--width": wide}},
    at > 0 ? edge(run, at - 1) : null,
    h("button", {type: "button",
                 "aria-label": (look ? look.name : "Nothing") + " on " + wherePlays(run, section, false),
                 title: firstClaim ? "used by a line the picker cannot edit: " + firstClaim[0].text
                      : under ? under.tip : targetFor(run, section).selector,
                 onclick: function () {
                   if (dragged) return;
                   pick(run, at);
                   draw();
                 }},
      h("span", {}, lamps.map(function (lamp, i) {
        var face = h("i");
        faces.push(face);
        return h("span", {"data-kept": !!claimed[i]}, face, h("small", {}, shortName(lamp)));
      })),
      band(run, section, look, under),
      h("strong", {}, look ? look.name : "Nothing", " ", h("small", {}, wide),
        under ? h("small", {}, under.note) : null)),
    lamps.slice(1).map(function (lamp, i) {
      return cut(run, section.from + i, i + 1, wide);
    }));
}

function band(run, section, look, under) {
  if (look) return h("i", {style: {"--wash": washFor(run, section, look)}});
  if (!under) return h("i");
  var panes = [];
  var start = 0;
  while (start < under.lamps.length) {
    var end = start + 1;
    while (end < under.lamps.length && sameShowing(under.lamps[end], under.lamps[start])) end++;
    panes.push(pane(run, under.lamps[start], start, end, under.lamps.length));
    start = end;
  }
  return h("i", {"data-through": true}, panes);
}

function sameShowing(one, other) {
  return one === other ||
         !!(one && other && one.section && other.section && one.section === other.section);
}

function pane(run, shows, start, end, wide) {
  var place = {left: (start * 100 / wide) + "%", width: ((end - start) * 100 / wide) + "%"};
  if (!shows) return h("span", {"data-shows": "empty", style: place});
  if (shows === "off") return h("span", {"data-shows": "off", style: place});
  return h("span", {style: place},
    h("span", {style: {width: (widthOf(shows.section) * 100 / (end - start)) + "%",
                       left: (-shows.at * 100 / (end - start)) + "%",
                       background: washFor(run, shows.section, lookNamed(shows.section.look))}}));
}

function cut(run, after, place, wide) {
  var says = shortName(run.lamps[after]) + " | " + shortName(run.lamps[after + 1]);
  return h("button", {type: "button", "data-says": says,
                      "aria-label": "cut between " + says.replace(" | ", " and "),
                      style: {"--at": (place / wide * 100) + "%",
                              "--reach": "min(11px, " + (55 / wide) + "%)"},
                      onclick: function () { cutAt(run, after); }});
}

function edge(run, which) {
  return h("span", {role: "separator",
                    title: "drag to move this cut, or click \u00d7 to remove it",
                    onmousedown: function (event) {
                      event.preventDefault();
                      remember(run);
                      pick(run, which);
                      dragging = {run: run, which: which, had: run.sections.length};
                      event.currentTarget.dataset.holding = "";
                    }},
    h("button", {type: "button", "aria-label": "remove this cut and join the two stretches",
                 onmousedown: function (event) { event.stopPropagation(); },
                 onclick: function (event) {
                   event.stopPropagation();
                   uncut(run, which);
                 }}, "\u00d7"));
}

function wheel(run, view, event) {
  if (!zooms(run)) return;
  event.preventDefault();
  var box = view.getBoundingClientRect();
  var at = (view.scrollLeft + (event.clientX - box.left)) / view.firstChild.offsetWidth;
  zoomTo(run, zoomOf(run) * (event.deltaY < 0 ? 1.25 : 0.8), at, event.clientX - box.left);
}

function turnLabelsInward(list) {
  var edges = list.getBoundingClientRect();
  list.querySelectorAll("button[data-says]").forEach(function (one) {
    var at = one.getBoundingClientRect();
    var middle = (at.left + at.right) / 2;
    one.dataset.near = middle - edges.left < 40 ? "start" : edges.right - middle < 40 ? "end" : "";
  });
}

function paintFace(face, lit, glows) {
  var one = lit || {level: 0, ink: "#e4e0d9"};
  face.style.background = one.nothing ? "#2a2d30" : inkAt(one);
  face.toggleAttribute("data-unset", !!one.unset);
  if (!glows) return;
  face.style.boxShadow = one.level > 0.05
    ? "inset 0 0 0 1px rgba(0,0,0,.2), 0 0 " + (3 + one.level * 8).toFixed(1) +
      "px rgba(255,217,160," + (one.level * 0.5).toFixed(2) + ")"
    : "inset 0 0 0 1px rgba(0,0,0,.2)";
}

export function stretchCells(run) {
  return Array.prototype.slice.call(
    document.querySelectorAll("[data-stretches='" + run.name + "'] ol > li"));
}

document.addEventListener("mousemove", function (event) {
  if (!dragging) return;
  var list = document.querySelector("[data-stretches='" + dragging.run.name + "'] ol");
  if (!list) return;
  var box = list.getBoundingClientRect();
  if (!box.width) return;
  var lamp = Math.round((event.clientX - box.left) / box.width * dragging.run.lamps.length) - 1;
  var left = dragging.run.sections[dragging.which];
  if (!left || left.to === lamp) return;
  dragged = true;
  moveEdge(dragging.run, dragging.which, lamp);
  settle();
  pick(dragging.run, dragging.which);
  draw();
  if (dragging.run.sections.length !== dragging.had) dragging = null;
});

document.addEventListener("mouseup", function () {
  if (dragged) window.setTimeout(function () { dragged = false; }, 0);
  if (!dragging) return;
  dragging = null;
  draw();
});
