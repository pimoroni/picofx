import {h, replace} from "./00_dom.js";
import {BOARD, HEADER, lookNamed} from "./01_looks.js";
import {
  active, copyBlinks, copyExact, draw, drawSteps, lampLines, mono, outs, runs, settle, widthOf
} from "./03_runs.js";
import {boardLine} from "./07_board.js";
import {TAB_NAMES} from "./11_tabs.js";
import {renderSceneSettings} from "./20_scene_row.js";
import {featureIcon} from "./22_program.js";

export var state = {at: -1, always: {body: null}, scenes: []};

// What each output was carried from where a stand-in took its place, which is the
// scene's, so it is held in the body with the stretches it is about
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

// The look that plays on most of the outputs' lamps, which is what a tab's swatch shows. A board
// whose strips are what it is for shows what the first fitted strip playing anything plays, and
// its outputs' look only where none does
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

// The look that plays on most of the lamps of the runs given
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

// A scene holds every run's cutting and looks. The wiring, where each lamp sits and a strip's
// length are the board's, so they sit outside the body and are not captured. The parts below
// keep their own share of a scene in the body too, each registering how it captures, applies
// and blanks that share, whether the share has content, how it adds to the scene's lines, how
// it reads them back from a file's board line and kept lines, the names of what it plays, and
// the icon and name its scene tab shows where the scene sets it. Each runs after the runs' own,
// in the order the parts come
export var bodyParts = [];

// The parts that keep files on the FX drive, each registering how a walk of the drive finds
// them (begin, then file or folder for each entry, then land), what it found as text to tell
// one walk from the next, and how the scenes let go of a deleted file before the drive is walked
// again (forget) and after it (gone)
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
  active = runs.filter(function (run) { return run.name === body.active; })[0] || outs;
  settle();
  bodyParts.forEach(function (part) { if (part.apply) part.apply(body); });
}

// A scene with nothing playing in it, cut as the board is now, which is what the always-on
// tab is left holding once its content has been carried into the first
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

// ---- what a scene leaves to Always on -------------------------------------------------------
// The board plays Always on under every scene. Where a scene plays nothing of its own on a lamp,
// the board plays Always on's look there, and where Always on plays nothing either, it turns the
// lamp off if another scene plays on it. A scene tab shows the same, so its lamps look as the
// board will light them

// The scenes other than the one being edited, whose bodies are as they were last stored
export function otherScenes() {
  return state.scenes.filter(function (scene, at) { return at !== state.at; });
}

export function namesOf(scenes) { return scenes.map(function (scene) { return scene.name; }); }

// Grey out settings that show Always on's values in a scene, which are set on the Always on tab
export function frozen(node) {
  node.classList.add("frozen");
  node.title = "Set on the Always on tab";
  node.querySelectorAll("button, input, select").forEach(function (control) {
    control.disabled = true;
  });
}

// The stretch of a stored body's run that covers one lamp and plays a look, or null. A look
// this page does not offer writes no line, so its stretch plays nothing
function stretchPlaying(body, runName, at) {
  var run = body && body.runs[runName];
  if (!run) return null;
  for (var i = 0; i < run.sections.length; i++) {
    var section = run.sections[i];
    if (section.from <= at && at <= section.to) return lookNamed(section.look) ? section : null;
  }
  return null;
}

// What the board plays on a lamp the scene being edited plays nothing on. The result holds
// always=, Always on's stretch over the lamp, or off=, every other scene that plays on it where
// Always on does not. It is null where nothing plays on the lamp, and on the Always on tab
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
  // Where scenes can wait for a button, a new one does, as one made for a remote mostly stands
  // alone. The first waits, as a time would only bring it back to itself
  if (!state.scenes.length) {
    made = {name: "Scene 1", seconds: 10, restart: false, waits: true, body: capture()};
    state.always.body = blankBody();
    // What a part keeps with Always on rather than carrying into the first scene, such as what
    // the sensor's triggers do, which is meant for every scene
    bodyParts.forEach(function (part) { if (part.split) part.split(state.always.body, made.body); });
  } else {
    var before = state.scenes[state.scenes.length - 1];
    made = {name: freeSceneName(), seconds: before.seconds,
            restart: before.restart, waits: sceneCanWait(), body: copyBody(before.body)};
    // A scene that stayed alone takes its time again, without a sensor to move it on
    if (state.scenes.length === 1 && !sceneCanWait()) before.waits = false;
  }
  state.scenes.push(made);
  state.at = state.scenes.length - 1;
  apply(made.body);
  draw();
}

export function removeScene(which) {
  store();
  var gone = state.scenes.splice(which, 1)[0];
  // Taking the last scene away leaves nothing playing, so its content comes back to
  // the tab that plays all the way through, which is where the page started
  if (!state.scenes.length && !hasContent(state.always.body))
    state.always.body = gone.body;
  state.at = state.scenes.length ? Math.min(which, state.scenes.length - 1) : -1;
  settleLoneScene();
  apply(slotAt(state.at).body);
  draw();
}

function copyBody(body) { return JSON.parse(JSON.stringify(body)); }

// ---- how a scene ends ---------------------------------------------------------------------------
// A scene either shows for its time and then goes to the scene after it, or waits until a button
// changes it. The scene after is the next in order unless the scene names another with then=, so
// a timed run of scenes need not follow the order the remote's numbers take

// A scene's mark, given once and kept while the scene is moved or renamed, by which another
// part names it
var sceneMarks = 0;
export function sceneMark(scene) {
  if (!scene.mark) scene.mark = "s" + (++sceneMarks);
  return scene.mark;
}

export function sceneMarked(mark) {
  return state.scenes.filter(function (scene) { return sceneMark(scene) === mark; })[0] || null;
}

// Whether something fitted can change scenes, so a scene can wait for it, which a board's sensor
// part answers. Without it a waiting scene waits forever
export var sceneCanWait = function () { return false; };

// The places of the scenes a scene in place `at` goes to on a button or motion, which the sensor
// part gives for what is fitted
export var sceneTriggerLeads = function (at) { return []; };

// What a waiting scene waits for, in words, which the sensor part says for what is fitted
export var sceneWaitsFor = function () { return "a button"; };

// The scene a timed scene goes to when its time is up, or null for one that waits
export function sceneAfter(scene) {
  if (scene.waits) return null;
  var named = scene.then ? sceneMarked(scene.then) : null;
  if (named) return named;
  var at = state.scenes.indexOf(scene);
  return state.scenes[(at + 1) % state.scenes.length];
}

// Whether a scene's time leads back to itself. Nothing would change then unless it restarts, so
// such a scene always does
export function sceneLoops(scene) {
  return !scene.waits && sceneAfter(scene) === scene;
}

// Whether a scene's effects begin again each time it starts, as its heading says. A scene that
// never shows again starts once, so it has nothing to restart
export function sceneRestarts(scene) {
  if (!sceneShowsAgain(scene)) return false;
  return scene.restart || sceneLoops(scene);
}

// The places of the scenes the scene in place `at` goes on to, by its time and by what is fitted
function sceneLeads(at) {
  var after = sceneAfter(state.scenes[at]);
  return sceneTriggerLeads(at).concat(after ? [state.scenes.indexOf(after)] : []);
}

// Which scenes can show from the places in `starts`, by place, those included
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

// Whether a scene can show again after it has shown, as it lies on a way back to itself
export function sceneShowsAgain(scene) {
  var at = state.scenes.indexOf(scene);
  return at >= 0 && scenesReachedFrom(sceneLeads(at))[at];
}

// Make the only scene stay where its time would change nothing, as the board reports a lone
// scene with a time and no restart
export function settleLoneScene() {
  if (state.scenes.length !== 1) return;
  var only = state.scenes[0];
  var namesItself = only.then && sceneMarked(only.then) === only;
  if (!only.waits && !only.restart && !namesItself) only.waits = true;
}

// The scenes nothing leads to from the first, as the board reports them, and the scene that
// waits forever before them where that is what leaves them out, or null
export function unreachedScenes() {
  var reached = scenesReachedFrom(state.scenes.length ? [0] : []);
  var unreached = state.scenes.filter(function (scene, at) { return !reached[at]; });
  if (!unreached.length || sceneCanWait()) return {scenes: unreached, stopper: null};

  // Without a sensor the turns are one line from the first scene, which a waiting scene ends
  var stop = state.scenes[0];
  var seen = [];
  while (!stop.waits && seen.indexOf(stop) < 0) {
    seen.push(stop);
    stop = sceneAfter(stop);
  }
  return {scenes: unreached, stopper: stop.waits ? stop : null};
}

// What is wrong with a name for a scene, or "" where nothing is. A scene needs a name of its own,
// as another scene's heading can name it after "then", and Always on's is taken
export function sceneNameProblem(scene, name) {
  var wanted = name.trim().toLowerCase();
  if (!wanted) return "A scene needs a name";
  if (wanted === "always on") return "That name is Always on's";
  var other = state.scenes.filter(function (one) {
    return one !== scene && one.name.trim().toLowerCase() === wanted;
  })[0];
  return other ? "Another scene is called " + other.name.trim() : "";
}

// The first of Scene 1, Scene 2 and so on that no scene is called
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

// The colours of the Aye Arr Remote's number buttons, 1 to 9, from its artwork, and the rainbow
// round its 0. Scene 1 takes button 1, so a scene's colour is the button that goes to it. Scene
// 10 takes 0, and a later scene has no button and a neutral colour
export var REMOTE_COLOURS = ["#ed1c24", "#00a651", "#2e3192", "#00aeef", "#ec008c", "#fff200",
                      "#fbad5d", "#ffffff", "#84c1ff"];
export var REMOTE_RAINBOW = ["#ed1c24", "#f7941d", "#fff200", "#8dc63f", "#00a651", "#00aeef",
                      "#0072bc", "#2e3192", "#92278f", "#ec008c"];
var ALWAYS_COLOUR = "#8f8a82";
var UNNUMBERED_COLOUR = "#b9b3a9";

// The remote's number buttons that go to a scene, which its card wears. None on a board with no
// sensor part, which replaces this with its own
export var sceneNumbers = function (scene) { return []; };

// A scene's colour, its number button's, which moves with the scene's place in the order
function sceneColour(scene) {
  if (!scene) return ALWAYS_COLOUR;
  var at = state.scenes.indexOf(scene);
  return at < 9 ? REMOTE_COLOURS[at] : UNNUMBERED_COLOUR;
}

// A scene's band, the background along the top of its card and its frame's tab. The remote's
// white is a light grey, since white does not show on the page, and button 0's is its rainbow
export function sceneBand(scene) {
  if (scene && state.scenes.indexOf(scene) === 9)
    return "linear-gradient(90deg, " + REMOTE_RAINBOW.join(", ") + ")";
  var colour = sceneColour(scene) === "#ffffff" ? "#d9d6d0" : sceneColour(scene);
  return "linear-gradient(" + colour + ", " + colour + ")";
}

// A scene's outline colour, a darker shade where its colour is too pale to show on the page
export function sceneEdge(scene) {
  return scene && sceneIsPale(scene)
    ? "color-mix(in srgb, " + sceneColour(scene) + " 72%, #2b2a28)" : sceneColour(scene);
}

// Check if a scene's colour is too pale to show against the page, as the remote's white and
// yellow are, by its luma
function sceneIsPale(scene) {
  var hex = sceneColour(scene).replace("#", "");
  var red = parseInt(hex.slice(0, 2), 16);
  var green = parseInt(hex.slice(2, 4), 16);
  var blue = parseInt(hex.slice(4, 6), 16);
  return 0.299 * red + 0.587 * green + 0.114 * blue > 200;
}

// A dark shade of a scene's colour, which reads on its tint and on the page
function sceneShade(scene) {
  return "color-mix(in srgb, " + sceneColour(scene) + " 65%, #2b2a28)";
}

// Each part's icon, the drawing the programs page gives the same thing, so the two pages agree.
// A part the programs page has no drawing for gives its own in PART_DRAWINGS, on the same grid
var PART_FEATURES = {lights: "outputs", strip: "strip", screens: "screen", hub: "hub",
                     sound: "sound", remote: "remote"};
export var PART_DRAWINGS = {};

function partIcon(key) {
  if (PART_FEATURES[key]) return featureIcon(PART_FEATURES[key]);
  return h("svg:svg", {viewBox: "0 0 24 24", class: "featureicon", "aria-hidden": "true",
                       html: PART_DRAWINGS[key]});
}

// The parts of the board a slot's body sets itself, each as [icon, name]. A body's parts add
// their own, each saying from its share of the body whether it is set. always= is whether the
// body is Always on's
function partsSet(body, always) {
  var parts = [];
  function plays(list) {
    return list.some(function (run) {
      return run.lamps.some(function (lamp, at) { return stretchPlaying(body, run.name, at); });
    });
  }
  var outputs = runs.filter(function (run) { return !run.strip && run.lamps.length; });
  if (outputs.length && plays(outputs)) parts.push(["lights", BOARD.output_words.tab]);
  // One icon for the strips, as nothing in it could say which, its tip naming those that play
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

// What the Always on tab says it plays, its looks, pictures and sounds by name, which is empty
// where it plays nothing yet
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
  var addButton = h("button", {type: "button", class: "plus",
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
  return h("span", {class: "parts", style: {color: sceneShade(scene)}},
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
    h("span", {class: "grip", title: "Drag to move this scene", "aria-hidden": "true"}),
    partIcons(body, false, scene),
    h("small", {}, sceneTurn(scene)),
    remoteBadges(scene));
}

function remoteBadges(scene) {
  var numbers = sceneNumbers(scene);
  if (!numbers.length) return null;
  return h("span", {class: "remote"}, numbers.map(function (number) {
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

// ---- what the whole file says now -------------------------------------------------------

// The lamps' lines are written from the runs as they stand, so each scene's body is applied in
// turn, which keeps one writer for all of them
function entriesOf(body) {
  apply(body);
  var lines = lampLines().filter(function (line) { return line.trim(); });
  bodyParts.forEach(function (part) { if (part.entries) lines = part.entries(body, lines); });
  return lines;
}

// A scene's heading. One read from a file with no time waits, and is written back without one.
// A heading read from a file is written back as it was while the scene still says the same
function sceneHeading(scene) {
  // A scene after other than the next in order is named after "then", a proposed word autofx does
  // not read yet. "then" comes last, as the rest of the heading after it is the name
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var named = after && after !== inOrder ? after.name.trim() || "Scene" : null;
  var read = scene.read;
  // A scene after that the file names but no scene is called keeps its heading as written
  var sameAfter = read && (read.after === named || (read.after && !scene.then &&
    !state.scenes.some(function (other) { return other.name === read.after; })));
  if (read && read.written && scene.name === read.name && sceneRestarts(scene) === read.restart &&
      sameAfter && (read.seconds === null ? scene.waits
                                          : !scene.waits && scene.seconds === read.seconds)) {
    return read.written;
  }
  // A scene going back to itself is written with restart, which the board needs to change anything
  var settings = (scene.waits ? [] : [scene.seconds + "s"])
    .concat(sceneRestarts(scene) ? ["restart"] : [])
    .concat(named !== null ? ["then " + named] : []);
  return "[" + (scene.name.trim() || "Scene") + (settings.length ? ": " + settings.join(" ") : "") +
         "]";
}

// What the parts below write above the scenes: lines straight under the file's header, then,
// after a blank line, lines above the board line. Each is a list of functions giving lines
export var fileHead = {under: [], above: []};

export function currentText() {
  store();
  var lines = entriesOf(state.always.body);
  state.scenes.forEach(function (scene) {
    lines.push("");
    // Comments a file had above the heading, where it was read from one
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
