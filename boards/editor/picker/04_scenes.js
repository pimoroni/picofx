import {draw} from "./00_draw.js";
import {BOARD, lookNamed} from "./01_looks.js";
import {spoken} from "./03_lines.js";
import {widthOf} from "./03_outputs.js";
import {activate, active, copyBlinks, copyExact, mono, outs, runs, settle} from "./03_runs.js";

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

export function stretchPlaying(body, runName, at) {
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

export function switchTo(which) {
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

export function underSaid(run, which) {
  var under = lampUnder(run.name, which);
  if (under && under.always) return ", playing " + lookNamed(under.always.look).name +
                                    " from Always on";
  if (under && under.off) return ", off here and lit only in " + spoken(namesOf(under.off));
  return ", playing Nothing";
}

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
