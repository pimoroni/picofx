import {h, replace} from "./dom.js";
import {draw} from "./draw.js";
import {spoken} from "./lines.js";
import {BOARD, lookNamed} from "./looks.js";
import {widthOf} from "./outputs.js";
import {activate, active, copyBlinks, copyExact, mono, outs, runs, settle} from "./runs.js";

// ---- scenes ---------------------------------------------------------------------------
// Adding, removing and reordering scenes, and what a scene leaves to Always on. A scene's body is
// every run's cuts, what each stretch plays and its steps to undo, and other parts add their own
// share to it.

// What a lamp's tip says after its name where the scene plays nothing on it
export function underSaid(run, which) {
  var under = lampUnder(run.name, which);
  if (under && under.always) return ", playing " + lookNamed(under.always.look).name +
                                    " from Always on";
  if (under && under.off) return ", off here and lit only in " + spoken(namesOf(under.off));
  return ", playing Nothing";
}

// What a stretch the scene plays nothing on shows instead, or null where nothing plays on any of
// its lamps. The result holds a short note to follow the cell's "Nothing", a tip, and what each
// lamp shows, as "off", null or Always on's stretch and the lamp's place in it
export function stretchUnder(run, section) {
  var looks = [], scenes = [], lamps = [], played = 0;
  for (var at = section.from; at <= section.to; at++) {
    var under = lampUnder(run.name, at);
    lamps.push(!under ? null : under.off ? "off"
             : {section: under.always, at: at - under.always.from});
    if (!under) continue;
    played++;
    if (under.always) {
      var name = lookNamed(under.always.look).name;
      if (looks.indexOf(name) < 0) looks.push(name);
    } else {
      namesOf(under.off).forEach(function (name) {
        if (scenes.indexOf(name) < 0) scenes.push(name);
      });
    }
  }
  if (!played) return null;
  var whole = played === widthOf(section);
  var showing = lamps.filter(function (one) { return one && one !== "off"; }).length;
  var notes = [];
  if (looks.length) notes.push("Always on's " + spoken(looks) +
                               (showing < widthOf(section) ? " on " + showing : ""));
  // The scenes are named for what uses the lights anywhere in the file, never for which came first
  if (scenes.length) notes.push((looks.length || !whole ? (played - showing) + " off" : "off") +
                                ", lit only in " + spoken(scenes));
  var tips = [];
  if (looks.length) tips.push("Always on's " + spoken(looks) + " plays " +
                              (whole && !scenes.length ? "here" : "on some of these lights") +
                              " in this scene.");
  if (scenes.length) tips.push((looks.length ? "The rest is off here" : "Off here") +
                               " and lit only in " + spoken(scenes) + ".");
  return {note: notes.join(" and "), tip: tips.join(" "), lamps: lamps};
}

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
// keep their own share of a scene in the body too, and each runs after the runs' own, in the
// order BODY_ORDER states. A part registers how it captures, applies and blanks that share,
// whether the share has content, and how it adds to the scene's lines. It also registers how
// it reads its share back from a file's board line and kept lines, and the names of what it
// plays. A scene's tab shows the icon and name a part gives where the scene sets it, and when
// the first scene is made, a part keeps back for Always on what is meant for every scene
export var bodyParts = [];
export var BODY_ORDER = ["screens", "sound", "sensor", "hub", "screenSettings", "hubGroups",
                         "screenPair", "readback"];

// The parts that keep files on the FX drive, each registering how a walk of the drive finds
// them (begin, then file or folder for each entry, then land), what it found as text to tell
// one walk from the next, and how the scenes let go of a deleted file before the drive is walked
// again (forget) and after it (gone)
export var driveParts = [];
export var DRIVE_ORDER = ["screens", "sound", "hub"];

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

export function hasContent(body) {
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
// lamp off if another scene plays on it. A scene tab shows each lamp as the board will light it

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
export function stretchPlaying(body, runName, at) {
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

export function switchTo(which) {
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
            restart: before.restart, waits: sceneHooks.canWait(), body: copyBody(before.body)};
    // A scene that stayed alone takes its time again, without a sensor to move it on
    if (state.scenes.length === 1 && !sceneHooks.canWait()) before.waits = false;
  }
  state.scenes.push(made);
  state.at = state.scenes.length - 1;
  apply(made.body);
  draw();
}

function removeScene(which) {
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

// Stretch Always on's card down every row the scenes' cards and the add button wrap into, as
// many as the tray's width leaves room for. Where the scenes fill their last row, the add button
// is a thin bar the width of the tray under them, so it never takes a row as a lone card
export function spanTray() {
  var box = document.getElementById("tabs");
  var always = box.querySelector(".tab.always");
  if (!always) return;
  var plus = box.querySelector(".plus");
  plus.classList.remove("wide");
  plus.style.gridColumn = "";
  always.style.gridRow = "1";
  var columns = getComputedStyle(box).gridTemplateColumns.split(" ").length;
  var perRow = Math.max(1, columns - 1);
  var scenes = box.querySelectorAll(".tab:not(.always)").length;
  if (scenes % perRow === 0) {
    plus.classList.add("wide");
    plus.style.gridColumn = "2 / -1";
  }
  always.style.gridRow = "1 / span " + Math.ceil((scenes + 1) / perRow);
}

// Beside the frame's tab, where the picked scene comes in the turns and the way to remove it,
// or for Always on how many scenes it plays under
export function renderSceneAside() {
  var aside = document.getElementById("sceneAside");
  var count = state.scenes.length;
  if (!count) {
    replace(aside);
    return;
  }
  if (state.at < 0) {
    replace(aside, h("span", {className: "sceneplace"},
                     "Under " + count + (count === 1 ? " scene" : " scenes")));
    return;
  }
  var picked = state.scenes[state.at];
  var after = sceneAfter(picked);
  // The place says why while the name being typed breaks a rule, or why a scene never shows
  var problem = sceneNameProblem(picked, picked.name);
  var unreached = unreachedScenes();
  if (!problem && unreached.scenes.indexOf(picked) >= 0) {
    problem = unreached.stopper ? "Never shows, as " + unreached.stopper.name.trim() +
                                  " waits forever before it"
                                : "Never shows, as no scene goes on to it";
  }
  var ends = picked.waits ? "waits " + (sceneHooks.canWait() ? "for " + sceneHooks.waitsFor()
                                                             : "forever")
           : after === picked ? "then itself" : after ? "then " + after.name : "on its own";
  var said = problem || "Scene " + (state.at + 1) + " of " + count + ", " + ends;
  var which = state.at;
  replace(aside,
          h("span", {className: "sceneplace" + (problem ? " warn" : ""), title: said}, said),
          h("button", {type: "button", className: "sceneremove", title: "Remove this scene",
                       onclick: function () {
                         var name = picked.name.trim() || "this scene";
                         if (confirm("Remove " + name + " and everything it plays?"))
                           removeScene(which);
                       }}, "Remove scene"));
}

// ---- how a scene ends ---------------------------------------------------------------------------
// A scene either shows for its time and then goes to the scene after it, or waits until a button
// changes it. The scene after is the next in order unless the scene names another with then=, so
// a timed run of scenes need not follow the order the remote's numbers take

// A scene's mark, given once and kept while it is moved or renamed, by which other parts name it
var sceneMarks = 0;
export function sceneMark(scene) {
  if (!scene.mark) scene.mark = "s" + (++sceneMarks);
  return scene.mark;
}

export function sceneMarked(mark) {
  return state.scenes.filter(function (scene) { return sceneMark(scene) === mark; })[0] || null;
}

// What the sensor part says about scenes for what is fitted, filled in by sensor/ where the board
// has one. canWait says whether something fitted can change scenes, so a scene can wait for it,
// and without it a waiting scene waits forever. triggerLeads gives the places of the scenes a
// scene in place `at` goes to on a button or motion, waitsFor says in words what a waiting scene
// waits for, and numbers gives the remote's number buttons that go to a scene, which its card wears
export var sceneHooks = {
  canWait: function () { return false; },
  triggerLeads: function (at) { return []; },
  waitsFor: function () { return "a button"; },
  numbers: function (scene) { return []; }
};

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
  return sceneHooks.triggerLeads(at).concat(after ? [state.scenes.indexOf(after)] : []);
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
function unreachedScenes() {
  var reached = scenesReachedFrom(state.scenes.length ? [0] : []);
  var unreached = state.scenes.filter(function (scene, at) { return !reached[at]; });
  if (!unreached.length || sceneHooks.canWait()) return {scenes: unreached, stopper: null};

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
