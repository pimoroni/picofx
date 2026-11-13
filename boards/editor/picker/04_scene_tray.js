import {h, replace} from "./00_dom.js";
import {draw} from "./00_draw.js";
import {BOARD, lookNamed} from "./01_looks.js";
import {runs} from "./03_runs.js";
import {
  addScene, bodyParts, capture, sceneAfter, sceneHooks, sceneLoops, sceneRestarts, state, store,
  stretchPlaying, switchTo
} from "./04_scenes.js";
import {TAB_NAMES} from "./11_tabs.js";
import {featureIcon} from "./22_program.js";

function sceneTurn(scene) {
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var turn = scene.waits ? "waits"
           : scene.seconds + "s" + (after === scene ? ", again" : after === inOrder ? ""
                                                    : ", then " + after.name);
  return turn + (sceneRestarts(scene) && !sceneLoops(scene) ? ", from the start" : "");
}

export var REMOTE_COLOURS = ["#ed1c24", "#00a651", "#2e3192", "#00aeef", "#ec008c", "#fff200",
                      "#fbad5d", "#ffffff", "#84c1ff"];

export var REMOTE_RAINBOW = ["#ed1c24", "#f7941d", "#fff200", "#8dc63f", "#00a651", "#00aeef",
                      "#0072bc", "#2e3192", "#92278f", "#ec008c"];

var ALWAYS_COLOUR = "#8f8a82";

var UNNUMBERED_COLOUR = "#b9b3a9";

function sceneColour(scene) {
  if (!scene) return ALWAYS_COLOUR;
  var at = state.scenes.indexOf(scene);
  return at < 9 ? REMOTE_COLOURS[at] : UNNUMBERED_COLOUR;
}

export function sceneBand(scene) {
  if (scene && state.scenes.indexOf(scene) === 9)
    return "linear-gradient(90deg, " + REMOTE_RAINBOW.join(", ") + ")";
  var colour = sceneColour(scene) === "#ffffff" ? "#d9d6d0" : sceneColour(scene);
  return "linear-gradient(" + colour + ", " + colour + ")";
}

export function sceneEdge(scene) {
  return scene && sceneIsPale(scene)
    ? "color-mix(in srgb, " + sceneColour(scene) + " 72%, #2b2a28)" : sceneColour(scene);
}

function sceneIsPale(scene) {
  var hex = sceneColour(scene).replace("#", "");
  var red = parseInt(hex.slice(0, 2), 16);
  var green = parseInt(hex.slice(2, 4), 16);
  var blue = parseInt(hex.slice(4, 6), 16);
  return 0.299 * red + 0.587 * green + 0.114 * blue > 200;
}

function sceneShade(scene) {
  return "color-mix(in srgb, " + sceneColour(scene) + " 65%, #2b2a28)";
}

var PART_FEATURES = {lights: "outputs", strip: "strip", screens: "screen", hub: "hub",
                     sound: "sound", remote: "remote"};

export var PART_DRAWINGS = {};

var PART_ORDER = ["lights", "strip", "screens", "sound", "pir", "remote", "hub"];

function partIcon(key) {
  if (PART_FEATURES[key]) return featureIcon(PART_FEATURES[key]);
  return h("svg:svg", {viewBox: "0 0 24 24", width: 18, height: 18, fill: "none", stroke: "currentColor",
                       "stroke-width": 1.8, "stroke-linecap": "round", "stroke-linejoin": "round",
                       "aria-hidden": "true",
                       html: PART_DRAWINGS[key]});
}

function partsSet(body, always) {
  var parts = [];
  function plays(list) {
    return list.some(function (run) {
      return run.lamps.some(function (lamp, at) { return stretchPlaying(body, run.name, at); });
    });
  }
  var outputs = runs.filter(function (run) { return !run.strip && run.lamps.length; });
  if (outputs.length && plays(outputs)) parts.push(["lights", BOARD.output_words.tab]);
  var strips = runs.filter(function (run) { return run.strip && run.there && plays([run]); });
  if (strips.length) {
    parts.push(["strip", strips.map(function (run) {
      return TAB_NAMES[run.name + "Panel"] || run.label;
    }).join(", ")]);
  }
  bodyParts.forEach(function (part) {
    var set = part.sets && part.sets(body, always);
    if (set) parts.push(set);
  });
  return parts.sort(function (a, b) { return PART_ORDER.indexOf(a[0]) - PART_ORDER.indexOf(b[0]); });
}

function alwaysSays(body) {
  var names = [];
  function add(name) { if (name && names.indexOf(name) < 0) names.push(name); }
  Object.keys(body.runs).forEach(function (name) {
    body.runs[name].sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (look) add(look.name);
    });
  });
  ["screens", "sound"].forEach(function (writes) {
    bodyParts.forEach(function (part) { if (part.writes === writes && part.named) part.named(body).forEach(add); });
  });
  if (!names.length) return "";
  return names.length <= 2 ? names.join(", ") : names[0] + " and " + (names.length - 1) + " more";
}

export function renderSceneTray() {
  var tray = document.getElementById("tabs");
  var addButton = h("button", {type: "button", id: "addScene",
                               title: state.scenes.length ? "Add another scene"
                                                          : "Split into scenes that play one after another",
                               onclick: addScene},
    h("svg:svg", {width: 11, height: 11, viewBox: "0 0 11 11", "aria-hidden": "true"},
      h("svg:path", {d: "M5.5 1 L5.5 10 M1 5.5 L10 5.5", stroke: "currentColor", "stroke-width": 1.8,
                     "stroke-linecap": "round"})),
    state.scenes.length ? "another scene" : "split into scenes");
  var body = document.getElementById("sceneBody");
  if (!state.scenes.length) {
    tray.removeAttribute("role");
    tray.removeAttribute("aria-label");
    replace(tray, addButton);
    body.removeAttribute("role");
    body.removeAttribute("aria-labelledby");
    body.removeAttribute("data-framed");
    return;
  }
  tray.setAttribute("role", "tablist");
  tray.setAttribute("aria-label", "Scenes");
  replace(tray, alwaysTab(),
          h("div", {role: "none"}, state.scenes.map(sceneTab), addButton));
  widenAddButton();
  var picked = state.at < 0 ? null : state.scenes[state.at];
  body.setAttribute("role", "tabpanel");
  body.setAttribute("aria-labelledby", sceneTabId(state.at));
  body.toggleAttribute("data-framed", true);
  body.style.setProperty("--frame", sceneEdge(picked));
}

function widenAddButton() {
  var grid = document.querySelector("#tabs > div");
  if (!grid) return;
  var columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
  grid.lastChild.toggleAttribute("data-wide", state.scenes.length % columns === 0);
}

window.addEventListener("resize", widenAddButton);

function sceneTabId(which) {
  return which < 0 ? "sceneTabAlways" : "sceneTab" + which;
}

function tabProps(which, title) {
  var selected = state.at === which;
  return {type: "button", role: "tab", id: sceneTabId(which), title: title,
          "aria-selected": selected ? "true" : "false", "aria-controls": "sceneBody",
          tabindex: selected ? "0" : "-1",
          onclick: function () { if (state.at !== which) switchTo(which); },
          onkeydown: function (event) { stepTabs(event, which); }};
}

function stepTabs(event, which) {
  var last = state.scenes.length - 1;
  var goTo = {ArrowRight: Math.min(last, which + 1), ArrowDown: Math.min(last, which + 1),
              ArrowLeft: Math.max(-1, which - 1), ArrowUp: Math.max(-1, which - 1),
              Home: -1, End: last}[event.key];
  if (goTo === undefined) return;
  event.preventDefault();
  if (goTo !== state.at) switchTo(goTo);
  document.getElementById(sceneTabId(state.at)).focus();
}

function partIcons(body, always, scene) {
  return h("span", {style: {color: sceneShade(scene)}},
    partsSet(body, always).map(function (part) {
      var icon = partIcon(part[0]);
      icon.prepend(h("svg:title", {text: part[1]}));
      return icon;
    }));
}

function alwaysTab() {
  var body = state.at < 0 ? capture() : state.always.body;
  var says = alwaysSays(body);
  var props = tabProps(-1, "Always on");
  props["data-always"] = true;
  props.style = {"--scene": sceneColour(null)};
  return h("button", props,
    h("strong", {}, "Always on"),
    h("small", {}, "Plays under every scene"),
    says ? h("small", {}, says) : null,
    partIcons(body, true, null));
}

function sceneTab(scene, which) {
  var body = state.at === which ? capture() : scene.body;
  var props = tabProps(which, scene.name);
  props.draggable = "true";
  props["data-pale"] = sceneIsPale(scene);
  props.style = {"--scene": sceneColour(scene), "--band": sceneBand(scene)};
  props.ondragstart = function (event) {
    carriedTab = which;
    event.currentTarget.toggleAttribute("data-carried", true);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(which));
  };
  props.ondragend = function () {
    carriedTab = null;
    draw();
  };
  props.ondragover = function (event) {
    if (carriedTab === null || carriedTab === which) return;
    event.preventDefault();
    event.currentTarget.toggleAttribute("data-landing", true);
  };
  props.ondragleave = function (event) {
    event.currentTarget.removeAttribute("data-landing");
  };
  props.ondrop = function (event) {
    event.preventDefault();
    if (carriedTab === null || carriedTab === which) return;
    moveScene(carriedTab, which);
    carriedTab = null;
    draw();
  };
  return h("button", props,
    h("strong", {}, scene.name),
    h("span", {title: "Drag to move this scene", "aria-hidden": "true"}),
    partIcons(body, false, scene),
    h("small", {}, sceneTurn(scene)),
    remoteBadges(scene));
}

function remoteBadges(scene) {
  var numbers = sceneHooks.numbers(scene);
  if (!numbers.length) return null;
  return h("span", {}, numbers.map(function (number) {
    return h("kbd", {title: "Press " + number + " on the remote for this scene",
                     "data-rainbow": number === 0,
                     style: {"--ring": number === 0 ? null
                                     : number === 8 ? "#cfccc6" : REMOTE_COLOURS[number - 1]}},
             String(number));
  }));
}

function moveScene(from, to) {
  store();
  var editing = state.at >= 0 ? state.scenes[state.at] : null;
  var moved = state.scenes.splice(from, 1)[0];
  state.scenes.splice(to, 0, moved);
  state.at = editing ? state.scenes.indexOf(editing) : -1;
}

var carriedTab = null;
