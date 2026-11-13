import {h, replace} from "./00_dom.js";
import {BOARD, HEADER, lookNamed} from "./01_looks.js";
import {
  activate, active, copyBlinks, copyExact, draw, drawSteps, lampLines, mono, outs, runs, settle,
  widthOf
} from "./03_runs.js";
import {boardLine} from "./07_board.js";
import {TAB_NAMES} from "./11_tabs.js";
import {renderSceneSettings} from "./20_scene_row.js";
import {featureIcon} from "./22_program.js";

export var state = {at: -1, always: {body: null}, scenes: []};

export var carried = {};

function copyRun(run) {
  return {sections: run.sections.map(function (section) {
            return {from: section.from, to: section.to, look: section.look,
                    pace: section.pace, mood: section.mood, colour: section.colour,
                    custom: section.custom, reversed: section.reversed,
                    level: section.level, blinks: copyBlinks(section.blinks),
                    exact: copyExact(section.exact), timings: copyExact(section.timings)};
          }),
          picked: run.picked, was: run.was.slice(), undone: run.undone.slice()};
}

function mostPlayed() {
  if (BOARD.strips_first) {
    var strips = runs.filter(function (run) { return run.strip && run.there; });
    for (var i = 0; i < strips.length; i++) {
      var look = mostPlayedOn([strips[i]]);
      if (look) return look;
    }
  }
  return mostPlayedOn([outs, mono]);
}

function mostPlayedOn(among) {
  var counted = {};
  var most = null;
  among.forEach(function (run) {
    run.sections.forEach(function (section) {
      if (!section.look) return;
      counted[section.look] = (counted[section.look] || 0) + widthOf(section);
      if (!most || counted[section.look] > counted[most]) most = section.look;
    });
  });
  return most;
}

export var bodyParts = [];

export var driveParts = [];

export function capture() {
  var body = {look: mostPlayed(), active: active.name, runs: {},
              carried: JSON.parse(JSON.stringify(carried))};
  runs.forEach(function (run) { body.runs[run.name] = copyRun(run); });
  bodyParts.forEach(function (part) { if (part.capture) part.capture(body); });
  return body;
}

export function apply(body) {
  carried = JSON.parse(JSON.stringify(body.carried));
  runs.forEach(function (run) {
    var was = copyRun(body.runs[run.name]);
    run.sections = was.sections;
    run.picked = was.picked;
    run.was = was.was;
    run.undone = was.undone;
  });
  activate(runs.filter(function (run) { return run.name === body.active; })[0] || outs);
  settle();
  bodyParts.forEach(function (part) { if (part.apply) part.apply(body); });
}

export function blankBody() {
  var body = capture();
  Object.keys(body.runs).forEach(function (name) {
    var run = body.runs[name];
    run.sections.forEach(function (section) { section.look = null; });
    run.was = [];
    run.undone = [];
  });
  body.look = null;
  body.carried = {};
  bodyParts.forEach(function (part) { if (part.blank) part.blank(body); });
  return body;
}

function hasContent(body) {
  return Object.keys(body.runs).some(function (name) {
    return body.runs[name].sections.some(function (section) { return section.look; });
  }) || bodyParts.some(function (part) { return part.hasContent && part.hasContent(body); });
}

export function slotAt(which) { return which < 0 ? state.always : state.scenes[which]; }

export function allBodies() {
  return [state.always.body].concat(state.scenes.map(function (scene) { return scene.body; }));
}

export function otherScenes() {
  return state.scenes.filter(function (scene, at) { return at !== state.at; });
}

export function namesOf(scenes) { return scenes.map(function (scene) { return scene.name; }); }

function stretchPlaying(body, runName, at) {
  var run = body && body.runs[runName];
  if (!run) return null;
  for (var i = 0; i < run.sections.length; i++) {
    var section = run.sections[i];
    if (section.from <= at && at <= section.to) return lookNamed(section.look) ? section : null;
  }
  return null;
}

export function lampUnder(runName, at) {
  if (state.at < 0) return null;
  var section = stretchPlaying(state.always.body, runName, at);
  if (section) return {always: section};
  var by = otherScenes().filter(function (scene) {
    return stretchPlaying(scene.body, runName, at);
  });
  return by.length ? {off: by} : null;
}

export function store() { slotAt(state.at).body = capture(); }

function switchTo(which) {
  store();
  state.at = which;
  apply(slotAt(which).body);
  draw();
}

export function addScene() {
  store();
  var made;
  if (!state.scenes.length) {
    made = {name: "Scene 1", seconds: 10, restart: false, waits: true, body: capture()};
    state.always.body = blankBody();
    bodyParts.forEach(function (part) { if (part.split) part.split(state.always.body, made.body); });
  } else {
    var before = state.scenes[state.scenes.length - 1];
    made = {name: freeSceneName(), seconds: before.seconds,
            restart: before.restart, waits: sceneHooks.canWait(), body: copyBody(before.body)};
    if (state.scenes.length === 1 && !sceneHooks.canWait()) before.waits = false;
  }
  state.scenes.push(made);
  state.at = state.scenes.length - 1;
  apply(made.body);
  draw();
}

export function removeScene(which) {
  store();
  var gone = state.scenes.splice(which, 1)[0];
  if (!state.scenes.length && !hasContent(state.always.body))
    state.always.body = gone.body;
  state.at = state.scenes.length ? Math.min(which, state.scenes.length - 1) : -1;
  settleLoneScene();
  apply(slotAt(state.at).body);
  draw();
}

function copyBody(body) { return JSON.parse(JSON.stringify(body)); }

var sceneMarks = 0;
export function sceneMark(scene) {
  if (!scene.mark) scene.mark = "s" + (++sceneMarks);
  return scene.mark;
}

export function sceneMarked(mark) {
  return state.scenes.filter(function (scene) { return sceneMark(scene) === mark; })[0] || null;
}

export var sceneHooks = {
  canWait: function () { return false; },
  triggerLeads: function (at) { return []; },
  waitsFor: function () { return "a button"; },
  numbers: function (scene) { return []; }
};



export function sceneAfter(scene) {
  if (scene.waits) return null;
  var named = scene.then ? sceneMarked(scene.then) : null;
  if (named) return named;
  var at = state.scenes.indexOf(scene);
  return state.scenes[(at + 1) % state.scenes.length];
}

export function sceneLoops(scene) {
  return !scene.waits && sceneAfter(scene) === scene;
}

export function sceneRestarts(scene) {
  if (!sceneShowsAgain(scene)) return false;
  return scene.restart || sceneLoops(scene);
}

function sceneLeads(at) {
  var after = sceneAfter(state.scenes[at]);
  return sceneHooks.triggerLeads(at).concat(after ? [state.scenes.indexOf(after)] : []);
}

function scenesReachedFrom(starts) {
  var reached = state.scenes.map(function () { return false; });
  var waiting = [];
  function reach(place) {
    if (place < 0 || reached[place]) return;
    reached[place] = true;
    waiting.push(place);
  }
  starts.forEach(reach);
  while (waiting.length) sceneLeads(waiting.pop()).forEach(reach);
  return reached;
}

export function sceneShowsAgain(scene) {
  var at = state.scenes.indexOf(scene);
  return at >= 0 && scenesReachedFrom(sceneLeads(at))[at];
}

export function settleLoneScene() {
  if (state.scenes.length !== 1) return;
  var only = state.scenes[0];
  var namesItself = only.then && sceneMarked(only.then) === only;
  if (!only.waits && !only.restart && !namesItself) only.waits = true;
}

export function unreachedScenes() {
  var reached = scenesReachedFrom(state.scenes.length ? [0] : []);
  var unreached = state.scenes.filter(function (scene, at) { return !reached[at]; });
  if (!unreached.length || sceneHooks.canWait()) return {scenes: unreached, stopper: null};

  var stop = state.scenes[0];
  var seen = [];
  while (!stop.waits && seen.indexOf(stop) < 0) {
    seen.push(stop);
    stop = sceneAfter(stop);
  }
  return {scenes: unreached, stopper: stop.waits ? stop : null};
}

export function sceneNameProblem(scene, name) {
  var wanted = name.trim().toLowerCase();
  if (!wanted) return "A scene needs a name";
  if (wanted === "always on") return "That name is Always on's";
  var other = state.scenes.filter(function (one) {
    return one !== scene && one.name.trim().toLowerCase() === wanted;
  })[0];
  return other ? "Another scene is called " + other.name.trim() : "";
}

function freeSceneName() {
  for (var number = 1; ; number++) {
    if (!sceneNameProblem(null, "Scene " + number)) return "Scene " + number;
  }
}

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
  return parts;
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
  bodyParts.forEach(function (part) { if (part.named) part.named(body).forEach(add); });
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

function entriesOf(body) {
  apply(body);
  var lines = lampLines().filter(function (line) { return line.trim(); });
  bodyParts.forEach(function (part) { if (part.entries) lines = part.entries(body, lines); });
  return lines;
}

function sceneHeading(scene) {
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var named = after && after !== inOrder ? after.name.trim() || "Scene" : null;
  var read = scene.read;
  var sameAfter = read && (read.after === named || (read.after && !scene.then &&
    !state.scenes.some(function (other) { return other.name === read.after; })));
  if (read && read.written && scene.name === read.name && sceneRestarts(scene) === read.restart &&
      sameAfter && (read.seconds === null ? scene.waits
                                          : !scene.waits && scene.seconds === read.seconds)) {
    return read.written;
  }
  var settings = (scene.waits ? [] : [scene.seconds + "s"])
    .concat(sceneRestarts(scene) ? ["restart"] : [])
    .concat(named !== null ? ["then " + named] : []);
  return "[" + (scene.name.trim() || "Scene") + (settings.length ? ": " + settings.join(" ") : "") +
         "]";
}

export var fileHead = {under: [], above: []};

export function currentText() {
  store();
  var lines = entriesOf(state.always.body);
  state.scenes.forEach(function (scene) {
    lines.push("");
    lines = lines.concat(scene.comments || []);
    lines.push(sceneHeading(scene));
    lines = lines.concat(entriesOf(scene.body));
  });
  apply(slotAt(state.at).body);

  var head = [];
  fileHead.under.forEach(function (lines) { head = head.concat(lines()); });
  head.push("");
  fileHead.above.forEach(function (lines) { head = head.concat(lines()); });
  var board = boardLine();
  if (board) head.push(board, "");
  return HEADER + head.join("\n") + "\n" +
         (lines.length ? lines.join("\n") : "# Nothing is playing yet.");
}

drawSteps.after.push(function () {
  renderSceneTray();
  renderSceneSettings();
});
