import {draw, drawSteps, paintSteps} from "./00_draw.js";
import {BOARD, canPlay, lookNamed, rangify} from "./01_looks.js";
import {beat, setPreviewingStrip} from "./02_preview.js";
import {lampUnder, namesOf} from "./04_scenes.js";
import {
  START_MOODS, livePlay, sectionLines, spoken, startColour, stretchWash, stripSelector, targetFor
} from "./05_effects.js";
import {holdOutput, setupOn} from "./08_setup.js";
import {filterKept, keptLights} from "./27_readback.js";

var OUTS = BOARD.outputs.length;
export var CHANNELS = ["r", "g", "b"];
export var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

export var OUTPUTS = BOARD.outputs.map(function (output) {
  var named = output.name.match(/^([a-z]+)(\d*)$/);
  return {name: output.name, prefix: named[1], number: named[2] ? Number(named[2]) : null,
          mono: output.kind === "mono", breaks: !!output.breaks_out};
});

export var MONO_FIRST = OUTPUTS.length > 0 && OUTPUTS[0].mono;
export var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

export var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: OUTPUTS[n].mono});

export function Run(name, mono) {
  return {name: name, mono: mono, lamps: [], sections: [], picked: 0,
          was: [], undone: []};
}

export var outs = Run("out", false);
export var mono = Run("mono", true);
export var runs = MONO_FIRST ? [mono, outs] : [outs, mono];

export var active = MONO_FIRST ? mono : outs;

export function activate(run) {
  active = run;
}

var showing = MONO_FIRST;

export var order = [];
for (var m = 0; m < OUTS; m++) order = order.concat(placesOf(m));

export function setLayout(wired, ordered) {
  wiring = wired;
  order = ordered;
}

export function placesOf(out) {
  if (OUTPUTS[out].mono) return [{out: out, channel: 0}];
  if (!wiring[out].broken) return [{out: out, channel: null}];
  return CHANNELS.map(function (letter, c) { return {out: out, channel: c}; });
}

export function sameLamp(a, b) { return a.out === b.out && a.channel === b.channel; }

function placeOf(lamp) {
  for (var i = 0; i < order.length; i++) {
    if (sameLamp(order[i], lamp)) return i;
  }
  return -1;
}

function lampsFor(run) {
  var found = [];
  if (run.strip) {
    for (var i = 0; i < run.leds; i++) found.push({colour: true, at: i, run: run});
    run.count = run.leds;
    return found;
  }
  order.forEach(function (place) {
    var colour = place.channel === null;
    if (colour !== !wiring[place.out].broken) return;
    if (colour === run.mono) return;
    found.push({out: place.out, colour: colour, channel: place.channel});
  });
  return found;
}

export function widthOf(section) { return section.to - section.from + 1; }

export function isChannel(lamp) { return !lamp.colour && !OUTPUTS[lamp.out].mono; }

export function selectorFor(lamp) {
  if (lamp.run) return lamp.run.name + (lamp.at + 1);
  var name = OUTPUTS[lamp.out].name;
  return isChannel(lamp) ? name + "." + CHANNELS[lamp.channel] : name;
}

export function nextOutput(out, step) {
  var here = OUTPUTS[out], there = OUTPUTS[out + step];
  return !!there && here.number !== null && there.prefix === here.prefix &&
         there.number === here.number + step;
}

export function joinedItems(items) {
  var prefix = null;
  return items.map(function (item) {
    var output = OUTPUTS[item.out];
    var said = output.number === null ? output.name + item.rest
             : (output.prefix === prefix ? "" : output.prefix) + item.rest;
    prefix = output.prefix;
    return said;
  }).join(",");
}

export function rangeItem(first, last, suffix) {
  var from = OUTPUTS[first].number, to = OUTPUTS[last].number;
  return {out: first,
          rest: (from === null ? "" : first === last ? String(from) : from + "-" + to) +
                (suffix ? "." + suffix : "")};
}

function nameThese(lamps) {
  function allThree(at) {
    return at + 2 < lamps.length && isChannel(lamps[at]) &&
           lamps[at].channel === 0 && lamps[at + 1].channel === 1 &&
           lamps[at + 2].channel === 2 && lamps[at + 1].out === lamps[at].out &&
           lamps[at + 2].out === lamps[at].out;
  }

  var items = [];
  var at = 0;
  while (at < lamps.length) {
    if (!isChannel(lamps[at])) {
      var last = at;
      while (last + 1 < lamps.length && !isChannel(lamps[last + 1]) &&
             lamps[last + 1].colour === lamps[at].colour &&
             lamps[last + 1].out === lamps[last].out + 1 && nextOutput(lamps[last].out, 1)) {
        last++;
      }
      items.push(rangeItem(lamps[at].out, lamps[last].out, null));
      at = last + 1;
    } else if (allThree(at)) {
      var end = at;
      var highest = lamps[at].out;
      while (allThree(end + 3) && lamps[end + 3].out === highest + 1 && nextOutput(highest, 1)) {
        end += 3;
        highest++;
      }
      items.push(rangeItem(lamps[at].out, highest, "*"));
      at = end + 3;
    } else {
      items.push(rangeItem(lamps[at].out, lamps[at].out, CHANNELS[lamps[at].channel]));
      at++;
    }
  }
  return joinedItems(items);
}

export function shortName(lamp) {
  if (lamp.run) return String(lamp.at + 1);
  var output = OUTPUTS[lamp.out];
  if (output.number === null) {
    return isChannel(lamp) ? CHANNELS[lamp.channel].toUpperCase() : output.name.toUpperCase();
  }
  return isChannel(lamp) ? output.number + CHANNELS[lamp.channel] : String(output.number);
}

export function sectionAt(run, which) {
  for (var i = 0; i < run.sections.length; i++) {
    if (which >= run.sections[i].from && which <= run.sections[i].to) return i;
  }
  return 0;
}

export function blank(from, to, run) {
  return {from: from, to: to, look: null, pace: 0.45, mood: 0.5, colour: "#ffffff",
          level: run && run.strip ? 0.75 : 1};
}

export function copyBlinks(blinks) {
  return blinks ? {colours: blinks.colours.slice(), at: blinks.at} : undefined;
}

export function copyExact(exact) {
  return exact ? JSON.parse(JSON.stringify(exact)) : undefined;
}

export function lampKey(lamp) {
  if (lamp.run) return lamp.run.id + ":" + lamp.at;
  return lamp.out + "." + (lamp.channel === null ? "whole" : lamp.channel);
}

function whatEachHolds(run) {
  return run.sections.map(function (section) {
    return {look: section.look, pace: section.pace, mood: section.mood,
            colour: section.colour, reversed: section.reversed, level: section.level,
            custom: section.custom, blinks: copyBlinks(section.blinks),
            exact: copyExact(section.exact), timings: copyExact(section.timings),
            held: run.lamps.slice(section.from, section.to + 1).map(lampKey)};
  });
}

function putStretchesBack(run, was) {
  var mine = {};
  was.forEach(function (one, which) {
    one.held.forEach(function (key) { mine[key] = which; });
  });

  var sections = [];
  var at = 0;
  while (at < run.lamps.length) {
    var which = mine[lampKey(run.lamps[at])];
    var to = at;
    while (to + 1 < run.lamps.length &&
           mine[lampKey(run.lamps[to + 1])] === which) to++;
    var had = which === undefined ? null : was[which];
    sections.push(had ? {from: at, to: to, look: had.look, pace: had.pace,
                         mood: had.mood, colour: had.colour, reversed: had.reversed,
                         level: had.level, custom: had.custom,
                         blinks: copyBlinks(had.blinks), exact: copyExact(had.exact),
                         timings: copyExact(had.timings)}
                      : Object.assign(blank(at, to, run), {}));
    at = to + 1;
  }
  if (sections.length) run.sections = sections;
}

export function acrossWiring(change) {
  var was = {};
  runs.forEach(function (run) { was[run.name] = whatEachHolds(run); });
  change();
  settle();
  runs.forEach(function (run) { putStretchesBack(run, was[run.name]); });
  settle();
}

var thisStep = 0;

export function remember(run) {
  run.undone = [];
  run.was.push(JSON.stringify({mark: thisStep, sections: run.sections}));
  if (run.was.length > 40) run.was.shift();
  thisStep++;
}

function steppingWith(run, stack) {
  var top = run[stack].length ? JSON.parse(run[stack][run[stack].length - 1]) : null;
  if (!top) return [];
  return runs.filter(function (other) {
    if (other === run || !other[stack].length) return false;
    var mine = JSON.parse(other[stack][other[stack].length - 1]);
    return Math.abs(mine.mark - top.mark) < runs.length;
  });
}

export function stepBack(run) {
  if (!run.was.length) return;
  var also = steppingWith(run, "was");
  [run].concat(also).forEach(function (one) {
    one.undone.push(JSON.stringify({mark: thisStep, sections: one.sections}));
    one.sections = JSON.parse(one.was.pop()).sections;
  });
  thisStep++;
  settle();
  draw();
}

export function stepOn(run) {
  if (!run.undone.length) return;
  var also = steppingWith(run, "undone");
  [run].concat(also).forEach(function (one) {
    one.was.push(JSON.stringify({mark: thisStep, sections: one.sections}));
    one.sections = JSON.parse(one.undone.pop()).sections;
  });
  thisStep++;
  settle();
  draw();
}

export function settle() {
  runs.forEach(function (run) {
    run.lamps = lampsFor(run);
    var kept = [];
    run.sections.forEach(function (section) {
      var from = Math.max(0, Math.min(section.from, run.lamps.length - 1));
      var to = Math.max(from, Math.min(section.to, run.lamps.length - 1));
      if (kept.length && from <= kept[kept.length - 1].to) return;
      kept.push({from: from, to: to, look: section.look, pace: section.pace,
                 mood: section.mood, colour: section.colour, reversed: section.reversed,
                 level: section.level, custom: section.custom,
                 blinks: copyBlinks(section.blinks),
                 exact: copyExact(section.exact), timings: copyExact(section.timings)});
    });
    if (!kept.length || kept[0].from !== 0) kept.unshift(blank(0, -1, run));
    var at = 0;
    var whole = [];
    kept.forEach(function (section, which) {
      section.from = at;
      section.to = Math.max(at, Math.min(section.to, run.lamps.length - 1));
      if (which === kept.length - 1) section.to = run.lamps.length - 1;
      if (section.to >= section.from) {
        whole.push(section);
        at = section.to + 1;
      }
    });
    run.sections = whole.length ? whole : [blank(0, run.lamps.length - 1, run)];

    var split = [];
    run.sections.forEach(function (section) {
      var start = section.from;
      for (var i = section.from; i < section.to; i++) {
        if (run.lamps[i].colour !== run.lamps[i + 1].colour) {
          split.push({from: start, to: i, look: section.look, pace: section.pace,
                      mood: section.mood, colour: section.colour,
                      reversed: section.reversed, level: section.level, custom: section.custom,
                      blinks: copyBlinks(section.blinks),
                      exact: copyExact(section.exact), timings: copyExact(section.timings)});
          start = i + 1;
        }
      }
      split.push({from: start, to: section.to, look: section.look, pace: section.pace,
                  mood: section.mood, colour: section.colour, reversed: section.reversed,
                  level: section.level, custom: section.custom,
                  blinks: copyBlinks(section.blinks),
                  exact: copyExact(section.exact), timings: copyExact(section.timings)});
    });
    run.sections = split.filter(function (section) {
      return section.to >= section.from;
    });

    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (look && !canPlay(look, targetFor(run, section))) section.look = null;
    });
    run.picked = Math.max(0, Math.min(run.picked, run.sections.length - 1));
  });
}

export function pick(run, at) {
  if (setupOn) return;
  var was = active === run ? run.picked : -1;
  active = run;
  run.picked = Math.max(0, Math.min(at, run.sections.length - 1));
  if (run.picked !== was) choosingLook = false;
  showing = kindAt(run, run.picked);
}

export var choosingLook = false;

export function chooseLook(on) {
  choosingLook = on;
}

export function pickingLook(run) {
  var section = run && run.sections[run.picked];
  return !!section && (!lookNamed(section.look) || (choosingLook && run === active));
}

export function cutAt(run, after) {
  if (after < 0 || after >= run.lamps.length - 1) return;
  var at = sectionAt(run, after);
  var section = run.sections[at];
  if (section.to === after) return;
  remember(run);
  run.sections.splice(at + 1, 0, {from: after + 1, to: section.to, look: section.look,
                                  pace: section.pace, mood: section.mood,
                                  colour: section.colour, reversed: section.reversed,
                                  level: section.level, custom: section.custom,
                                  blinks: copyBlinks(section.blinks),
                                  exact: copyExact(section.exact),
                                  timings: copyExact(section.timings)});
  section.to = after;
  settle();
  pick(run, at);
  draw();
}

export function uncut(run, which) {
  var left = run.sections[which];
  var right = run.sections[which + 1];
  if (!right) return;
  remember(run);
  left.to = right.to;
  run.sections.splice(which + 1, 1);
  settle();
  pick(run, which);
  draw();
}

export function moveEdge(run, which, to) {
  var left = run.sections[which];
  var right = run.sections[which + 1];
  if (!right) return;
  to = Math.max(left.from - 1, Math.min(right.to, to));
  left.to = to;
  right.from = to + 1;
  run.sections = run.sections.filter(function (one) { return one.to >= one.from; });
  run.picked = Math.min(run.picked, run.sections.length - 1);
}

export function breakOutWiring(out) {
  if (wiring[out].broken) return;
  runs.forEach(remember);
  acrossWiring(function () {
    wiring[out] = {broken: true};
    var at = placeOf({out: out, channel: null});
    if (at >= 0) {
      order.splice(at, 1, {out: out, channel: 0}, {out: out, channel: 1},
                   {out: out, channel: 2});
    }
  });
  pickOutput(out);
  draw();
}

export function pickOutput(out) {
  if (setupOn) {
    holdOutput(out);
    return;
  }
  runs.some(function (run) {
    var at = run.lamps.map(function (lamp) { return lamp.out; }).indexOf(out);
    if (at < 0) return false;
    pick(run, sectionAt(run, at));
    return true;
  });
}

export function rejoinWiring(out) {
  if (!wiring[out].broken || OUTPUTS[out].mono) return;
  runs.forEach(remember);
  acrossWiring(function () {
    wiring[out] = {broken: false};
    var first = -1;
    order = order.filter(function (place) {
      if (place.out !== out) return true;
      if (first < 0) first = placeOf(place);
      return false;
    });
    order.splice(Math.max(0, first), 0, {out: out, channel: null});
  });
  pickOutput(out);
  draw();
}

function outputsNamed(places) {
  var items = [];
  var at = 0;
  while (at < places.length) {
    var output = OUTPUTS[places[at] - 1];
    var last = at;
    while (output.number !== null && last + 1 < places.length &&
           OUTPUTS[places[last + 1] - 1].number !== null &&
           OUTPUTS[places[last + 1] - 1].prefix === output.prefix) last++;
    var numbers = places.slice(at, last + 1).map(function (place) {
      return OUTPUTS[place - 1].number;
    });
    items.push({out: places[at] - 1, rest: output.number === null ? "" : rangify(numbers)});
    at = last + 1;
  }
  return joinedItems(items);
}

export function outputSaid(out) {
  var output = OUTPUTS[out];
  return output.number === null ? "the " + output.name.toUpperCase() + " output"
                                : "output " + output.number;
}

function colourOutputsSaid() {
  var colour = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono) colour.push(out); });
  return colour.length === 1 ? outputSaid(colour[0]) : "the colour lights";
}

export function forwardTargetFor(run, section) {
  if (run.strip) {
    var lights = [];
    for (var at = section.from; at <= section.to; at++) lights.push(at + 1);
    return {kind: "run", id: run.id, name: run.name, label: run.label, colour: true,
            selector: stripSelector(run, section), count: widthOf(section), playing: [],
            lights: lights};
  }
  var first = run.lamps[section.from];
  if (!first) return {kind: "outputs", colour: false, selector: "out1", count: 1,
                      label: "nothing", playing: []};
  var mine = [];
  for (var i = section.from; i <= section.to; i++) mine.push(run.lamps[i]);
  var target = {kind: first.colour && widthOf(section) === 1 ? "single" : "outputs",
                name: "out", colour: first.colour, selector: nameThese(mine),
                count: widthOf(section), playing: [],
                label: first.colour ? colourOutputsSaid() : "the mono lights"};
  if (first.colour) {
    target.playing = mine.map(function (lamp) { return lamp.out + 1; });
    target.nameSet = outputsNamed;
  } else {
    target.playing = mine.map(function (lamp, at) { return at; });
    target.nameSet = function (set) {
      return nameThese(set.map(function (at) { return mine[at]; }));
    };
  }
  return target;
}

export function levelled(lines, level) {
  if (level === undefined || level >= 1) return lines;
  var said = " level=" + Math.round(level * 100) + "%";
  return lines.map(function (line) {
    var at = line.indexOf(":");
    if (at < 0 || /:\s*none\s*$/.test(line)) return line;
    return line.slice(0, at) + said + line.slice(at);
  });
}

export function lampLines() {
  var lines = [];
  runs.forEach(function (run) {
    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (!look) return;
      lines = lines.concat(sectionLines(run, section, look));
    });
  });
  return lines;
}

export var painters = [];

drawSteps.before.push(function () {
  painters = [];
});

paintSteps.push(function () {
  var lit = {};
  runs.forEach(function (run) { lit[run.name] = litRun(run); });
  painters.forEach(function (one) { one.paint(lit[one.run.name]); });
});
var walks = {};

function litRun(run) {
  var out = [];
  var store = walks[run.name] || (walks[run.name] = {});
  setPreviewingStrip(!!run.strip);
  try {
    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      var wide = widthOf(section);
      for (var i = 0; i < wide; i++) {
        var which = section.from + i;
        var lamp = run.lamps[which];
        if (!lamp) continue;
        var walk = store[which] || (store[which] = {});
        var lit = look ? livePlay(look, section, beat, i, wide, walk) : null;
        out[which] = lit
          ? {level: Math.max(0, Math.min(1, lit.level)),
             ink: lamp.colour ? lit.ink : "#ffd9a0"}
          : litUnder(run, which, lamp);
      }
    });
  } finally {
    setPreviewingStrip(false);
  }
  return out;
}

function litUnder(run, which, lamp) {
  var under = lampUnder(run.name, which);
  if (under && under.always) {
    var section = under.always;
    var store = walks["always " + run.name] || (walks["always " + run.name] = {});
    var walk = store[which] || (store[which] = {});
    var lit = livePlay(lookNamed(section.look), section, beat, which - section.from,
                       widthOf(section), walk);
    return {level: Math.max(0, Math.min(1, lit.level)), ink: lamp.colour ? lit.ink : "#ffd9a0",
            always: true, unset: true};
  }
  return {level: 0, ink: "#3a3f44", nothing: true, off: !!(under && under.off), unset: true};
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

export function inkAt(lit) {
  var hex = (lit.ink || "#ffd9a0").replace("#", "");
  var mix = 0.1 + lit.level * 0.9;
  return "rgb(" + Math.round(parseInt(hex.slice(0, 2), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(2, 4), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(4, 6), 16) * mix) + ")";
}

export var MIDDLING = {pace: 0.5, mood: 0.5, colour: "#ffffff"};
export function landLook(run, at, name) {
  var section = run.sections[at];
  if (section && name) {
    var named = keptLights(run);
    var clashing = [];
    for (var lamp = section.from; lamp <= section.to; lamp++) {
      (named[lamp] || []).forEach(function (one) {
        if (clashing.indexOf(one) < 0) clashing.push(one);
      });
    }
    if (clashing.length) {
      var lines = clashing.map(function (one) { return one.text; }).join("\n");
      if (!confirm((clashing.length === 1 ? "A line the picker " +
                    "cannot edit already uses some of these lights:" : "Lines the picker cannot " +
                    "edit already use some of these lights:") + "\n\n" + lines + "\n\nRemove " +
                   (clashing.length === 1 ? "it" : "them") + " from the file and play " +
                   name + " instead?")) return;
      filterKept(function (one) { return clashing.indexOf(one) < 0; });
    }
  }
  if (run.strip && !run.there) return;
  var look = lookNamed(name);
  if (section && look && section.look !== name) {
    startColour(run, section, look);
    section.mood = START_MOODS[look.name] !== undefined ? START_MOODS[look.name] : MIDDLING.mood;
  }
  if (!section) return;
  if (section.look !== name) {
    remember(run);
    section.look = name;
  }
  settle();
  pick(run, at);
  choosingLook = false;
  draw();
}

export function galleryRun(isMono) {
  if (active && active.strip) return active;
  return isMono ? mono : outs;
}

function kindAt(run, at) {
  var section = run.sections[at];
  var lamp = section && run.lamps[section.from];
  return lamp ? !lamp.colour : false;
}

function haveKind(isMono) {
  return runs.some(function (run) {
    return run.lamps.some(function (lamp) { return lamp.colour === !isMono; });
  });
}

export function lookKind() {
  if (!haveKind(showing) && haveKind(!showing)) showing = !showing;
  return showing;
}

export function stretchFor(run, isMono) {
  var section = run.sections[run.picked];
  var lamp = section && run.lamps[section.from];
  if (lamp && lamp.colour === !isMono) return run.picked;
  for (var i = 0; i < run.sections.length; i++) {
    var first = run.lamps[run.sections[i].from];
    if (first && first.colour === !isMono) return i;
  }
  return run.picked;
}

export function placeLamp(move) {
  var moved = order.splice(placeOf(move.from), 1)[0];
  order.splice(placeOf(move.to) + (move.after ? 1 : 0), 0, moved);
}

export function washFor(run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
}

export function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function paintLine(line) {
  var plain = escapeHtml(line);
  if (line.charAt(0) === "[") return "<span data-s='scene'>" + plain + "</span>";
  if (/^\s*#/.test(line)) return "<span data-s='comment'>" + plain + "</span>";
  var at = line.indexOf(":");
  if (at < 0) return plain;
  function settings(text) {
    return (text.match(/"[^"]*"|\S+|\s+/g) || []).map(function (token) {
      var pair = token.match(/^([^=\s]+)(=)(.*)$/);
      if (!pair) return escapeHtml(token);
      return "<span data-s='name'>" + escapeHtml(pair[1]) + "</span>" +
             "<span data-s='punc'>=</span>" +
             "<span data-s='value'>" + escapeHtml(pair[3]) + "</span>";
    }).join("");
  }
  var left = line.slice(0, at), right = line.slice(at + 1);
  var selector = left.match(/^(\s*)(\S+)(.*)$/);
  var head = selector
    ? escapeHtml(selector[1]) + "<span data-s='target'>" + escapeHtml(selector[2]) +
      "</span>" + settings(selector[3])
    : escapeHtml(left);
  var effect = right.match(/^(\s*)(\S+)(.*)$/);
  var tail = effect
    ? escapeHtml(effect[1]) + "<span data-s='effect'>" + escapeHtml(effect[2]) +
      "</span>" + settings(effect[3])
    : escapeHtml(right);
  return head + "<span data-s='colon'>:</span>" + tail;
}

settle();
