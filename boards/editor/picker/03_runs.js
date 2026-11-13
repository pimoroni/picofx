import {BOARD, canPlay, lookNamed, rangify} from "./01_looks.js";
import {FRAME, beat, previewingStrip} from "./02_preview.js";
import {renderSides} from "./04_led_panels.js";
import {lampUnder, namesOf} from "./04_scenes.js";
import {
  START_MOODS, livePlay, sectionLines, spoken, startColour, stretchWash, stripSelector, targetFor
} from "./05_effects.js";
import {heldOutput, setupOn} from "./08_setup.js";
import {renderWiringRun} from "./09_wiring.js";
import {renderPreview} from "./18_drive.js";
import {keptLights, keptNow} from "./27_readback.js";
import {renderStretches} from "./31_stretch_bar.js";
import {renderEditor} from "./32_stretch_editor.js";
import {paintCards, renderGallery} from "./33_gallery.js";

// ---- the board's outputs, inside the sections system ------------------------------------
// A colour output is three PWM channels behind one lamp. Where the board lets an adapter tell
// those three apart, the output is either one colour lamp or three mono ones, and a board is
// a mix. A mono output is one light, always on the mono side. Everything below is the section
// model over a run of lamps: the only new idea is that the run's own length is something the
// wiring decides.

var OUTS = BOARD.outputs.length;
export var CHANNELS = ["r", "g", "b"];
export var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

// Each output as the file names it, split into its prefix and number: out3 is out and 3, and
// rgb, which has no number, is rgb alone
export var OUTPUTS = BOARD.outputs.map(function (output) {
  var named = output.name.match(/^([a-z]+)(\d*)$/);
  return {name: output.name, prefix: named[1], number: named[2] ? Number(named[2]) : null,
          mono: output.kind === "mono", breaks: !!output.breaks_out};
});

// Whether the mono side comes first, as on a board whose outputs start with its mono ones. The
// file names the lamps in the same order
export var MONO_FIRST = OUTPUTS.length > 0 && OUTPUTS[0].mono;
// The corner cut into a broken-out lamp, saying which of an output's three drives it
export var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

// A colour output is one lamp or three, and nothing between: the adapter brings all three
// channels out or it is not fitted. Two channels playing the same thing are two lamps in
// one stretch, which is sectioning and not wiring. A mono output is held as broken out for good
export var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: OUTPUTS[n].mono});

export function Run(name, mono) {
  return {name: name, mono: mono, lamps: [], sections: [], picked: 0,
          was: [], undone: []};
}

// The colour lamps and the mono ones are each a run of their own
export var outs = Run("out", false);
export var mono = Run("mono", true);
export var runs = MONO_FIRST ? [mono, outs] : [outs, mono];

// The one stretch being worked on, which is the run it is in and its place in that run.
// One set of looks can only be for one stretch, so the other run shows no mark at all
export var active = MONO_FIRST ? mono : outs;

// Which kind of lamp the one set of looks is drawn for. It follows whatever was last
// pointed at, so the cards are always the ones for the lights being worked on
var showing = MONO_FIRST;

// Where each lamp sits, which is the one thing about a board only its owner knows. It
// is a lamp and not an output that is placed: an output's three channels reach three
// separate LEDs through the adapter, and those can be anywhere in a build
export var order = [];
for (var m = 0; m < OUTS; m++) order = order.concat(placesOf(m));

// An output's places in the wiring order: a mono output's one light, a colour output whole, or
// broken out as its three channels
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

// ---- the lamps the wiring adds up to -----------------------------------------------------

function lampsFor(run) {
  var found = [];
  // A strip's lamps are its LEDs, each a colour lamp, and the drawing asks it how many it has
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

// Whether a lamp is a channel of a colour output broken out, which the file names by its channel
export function isChannel(lamp) { return !lamp.colour && !OUTPUTS[lamp.out].mono; }

// What one lamp is called, in the words the file uses
export function selectorFor(lamp) {
  if (lamp.run) return lamp.run.name + (lamp.at + 1);
  var name = OUTPUTS[lamp.out].name;
  return isChannel(lamp) ? name + "." + CHANNELS[lamp.channel] : name;
}

// Whether the output after this one, counting by step, is the next of the same name
export function nextOutput(out, step) {
  var here = OUTPUTS[out], there = OUTPUTS[out + step];
  return !!there && here.number !== null && there.prefix === here.prefix &&
         there.number === here.number + step;
}

// A set of items as the file joins them: an item's prefix carries on to a bare number after it,
// so a numbered item says its prefix only where it differs from the one before, and an output
// with no number always says its name
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

// An item naming outputs first to last of one name, with a channel suffix or none
export function rangeItem(first, last, suffix) {
  var from = OUTPUTS[first].number, to = OUTPUTS[last].number;
  return {out: first,
          rest: (from === null ? "" : first === last ? String(from) : from + "-" + to) +
                (suffix ? "." + suffix : "")};
}

// The shortest way to name a set of lamps that the file still reads. Consecutive outputs taken
// whole, and consecutive mono outputs, are a range, and an output's three channels in order are
// its `.*`
function nameThese(lamps) {
  // An output's three channels, in order, starting here
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

// A lamp's label on the page: its number, and its channel where it is one, or for an output with
// no number its name, or its channel's letter
export function shortName(lamp) {
  if (lamp.run) return String(lamp.at + 1);
  var output = OUTPUTS[lamp.out];
  if (output.number === null) {
    return isChannel(lamp) ? CHANNELS[lamp.channel].toUpperCase() : output.name.toUpperCase();
  }
  return isChannel(lamp) ? output.number + CHANNELS[lamp.channel] : String(output.number);
}

// ---- sections over those lamps -----------------------------------------------------------

export function sectionAt(run, which) {
  for (var i = 0; i < run.sections.length; i++) {
    if (which >= run.sections[i].from && which <= run.sections[i].to) return i;
  }
  return 0;
}

// A stretch playing nothing yet. One on a strip starts at three quarters brightness, a strip or
// LED panel at full being glaring up close
export function blank(from, to, run) {
  return {from: from, to: to, look: null, pace: 0.45, mood: 0.5, colour: "#ffffff",
          level: run && run.strip ? 0.75 : 1};
}

// ---- keeping a stretch on its own lamps ----------------------------------------------------
// A stretch is a range of places in a run, and breaking an output out puts three lamps in
// at the output's own place. Every stretch after that would fall on different lights, so
// what each one holds is taken by lamp before the run changes and put back afterwards.

// A stretch's list of colours to blink through, copied so two stretches never share one
export function copyBlinks(blinks) {
  return blinks ? {colours: blinks.colours.slice(), at: blinks.at} : undefined;
}

// A stretch's values typed past its sliders' ends, by slider, or a signal's timings, copied
// as its blinks are
export function copyExact(exact) {
  return exact ? JSON.parse(JSON.stringify(exact)) : undefined;
}

// What holds a stretch to its lamps across a change to the wiring. A strip's lamps have no
// output to be named by, so they are named by the strip and their place
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

// Lamps no stretch claims become one of their own, which is what an output's three
// channels are the moment it is broken out. A stretch they land inside becomes two, so
// every other lamp keeps what it was playing
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

// Hold every run's stretches to their lamps across a change to the wiring
export function acrossWiring(change) {
  var was = {};
  runs.forEach(function (run) { was[run.name] = whatEachHolds(run); });
  change();
  settle();
  runs.forEach(function (run) { putStretchesBack(run, was[run.name]); });
  settle();
}

// A cut is one run's step. A change to the wiring is every run's, both of them holding
// lamps that moved, so the snapshots it takes share a mark and are stepped over together
var thisStep = 0;

export function remember(run) {
  run.undone = [];
  run.was.push(JSON.stringify({mark: thisStep, sections: run.sections}));
  if (run.was.length > 40) run.was.shift();
  thisStep++;
}

// The runs whose top step is the same one as this run's, which is every run where the
// wiring changed and only this one where a cut did
function steppingWith(run, stack) {
  var top = run[stack].length ? JSON.parse(run[stack][run[stack].length - 1]) : null;
  if (!top) return [];
  return runs.filter(function (other) {
    if (other === run || !other[stack].length) return false;
    var mine = JSON.parse(other[stack][other[stack].length - 1]);
    return Math.abs(mine.mark - top.mark) < runs.length;
  });
}

// A step back or on is the scene's, so it changes the stretches and never the board
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

// Every lamp is in exactly one section, and no section spans a colour lamp and a mono
// one: they do not play the same looks, so a stretch over both could not be given one
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
    // Close the gaps, so the sections cover the run exactly
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

    // A section straddling a colour lamp and a mono one is split where the kind changes
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

    // A look a lamp cannot play is not left sitting on it
    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (look && !canPlay(look, targetFor(run, section))) section.look = null;
    });
    run.picked = Math.max(0, Math.min(run.picked, run.sections.length - 1));
  });
}

// The one stretch being worked on. Everything that changes it comes through here, so
// the mark, the settings and the set of looks can never end up about different things.
// Setting up the board gives no stretch a look, so nothing is picked while it is on
export function pick(run, at) {
  if (setupOn) return;
  var was = active === run ? run.picked : -1;
  active = run;
  run.picked = Math.max(0, Math.min(at, run.sections.length - 1));
  if (run.picked !== was) choosingLook = false;
  showing = kindAt(run, run.picked);
}

export var choosingLook = false;

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

// Moving a cut takes lamps from the stretch on one side and gives them to the other. A
// stretch squeezed to nothing is gone, which is how a drag joins two
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

// ---- the wiring itself -------------------------------------------------------------------
// One output broken out or put back, in the scene on show. The wiring part does it to every
// scene and slides the lamps

export function breakOutWiring(out) {
  if (wiring[out].broken) return;
  runs.forEach(remember);
  acrossWiring(function () {
    wiring[out] = {broken: true};
    // The three take the place the one held, and are free to be moved apart from there
    var at = placeOf({out: out, channel: null});
    if (at >= 0) {
      order.splice(at, 1, {out: out, channel: 0}, {out: out, channel: 1},
                   {out: out, channel: 2});
    }
  });
  pickOutput(out);
  draw();
}

// Breaking out and putting back are done to one output, and what is done next is nearly
// always to its lamps, so the mark and the set of looks go to the stretch holding them.
// While the board is set up the output is held, and picked once setting up ends
export function pickOutput(out) {
  if (setupOn) {
    heldOutput = out;
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
    // Wherever its three ended up, the one lamp takes the place of the first of them
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

// ---- what the file says ------------------------------------------------------------------

// Some outputs by their place counted from one, as the file names them: those of one name in a
// row as a set of numbers, an output with no number by its name
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

// An output in words: output 3, or the RGB output for one with no number
export function outputSaid(out) {
  var output = OUTPUTS[out];
  return output.number === null ? "the " + output.name.toUpperCase() + " output"
                                : "output " + output.number;
}

// The board's colour outputs in words, as one where there is only one
function colourOutputsSaid() {
  var colour = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono) colour.push(out); });
  return colour.length === 1 ? outputSaid(colour[0]) : "the colour lights";
}

// What a stretch plays on, as though it ran from its near end
export function forwardTargetFor(run, section) {
  if (run.strip) {
    // The stretch's lights by number, for the looks that deal them out themselves
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
  // What a stretch plays on, in build order, which a look sharing its lamps out between
  // sets of its own, as Party does, deals from. A colour stretch's are its outputs; a mono
  // stretch's are its lamps, which are channels, so it names each set itself
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

// A stretch below full brightness says so before the colon of each line it writes, as
// level=, which scales whatever the effect plays. A line playing nothing is left alone
export function levelled(lines, level) {
  if (level === undefined || level >= 1) return lines;
  var said = " level=" + Math.round(level * 100) + "%";
  return lines.map(function (line) {
    var at = line.indexOf(":");
    if (at < 0 || /:\s*none\s*$/.test(line)) return line;
    return line.slice(0, at) + said + line.slice(at);
  });
}

// What the lamps play, a line or more for each stretch with a look
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

// ---- lighting -----------------------------------------------------------------------------

export var painters = [];
var walks = {};

// What each lamp of a run shows now. A strip's stretches are played in the strip's form
function litRun(run) {
  var out = [];
  var store = walks[run.name] || (walks[run.name] = {});
  previewingStrip = !!run.strip;
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
    previewingStrip = false;
  }
  return out;
}

// What a lamp the scene plays nothing on shows, marked unset= for its tile. It plays Always on's
// look where Always on has one there, and is off where another scene plays on it, as the board
// has it
function litUnder(run, which, lamp) {
  var under = lampUnder(run.name, which);
  if (under && under.always) {
    var section = under.always;
    // Always on's lamps keep their own walks, so a scene's stretch never steps one on
    var store = walks["always " + run.name] || (walks["always " + run.name] = {});
    var walk = store[which] || (store[which] = {});
    var lit = livePlay(lookNamed(section.look), section, beat, which - section.from,
                       widthOf(section), walk);
    return {level: Math.max(0, Math.min(1, lit.level)), ink: lamp.colour ? lit.ink : "#ffd9a0",
            always: true, unset: true};
  }
  return {level: 0, ink: "#3a3f44", nothing: true, off: !!(under && under.off), unset: true};
}

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

export function inkAt(lit) {
  var hex = (lit.ink || "#ffd9a0").replace("#", "");
  var mix = 0.1 + lit.level * 0.9;
  return "rgb(" + Math.round(parseInt(hex.slice(0, 2), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(2, 4), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(4, 6), 16) * mix) + ")";
}

// ---- the gallery, played on the chosen stretch --------------------------------------------

export var MIDDLING = {pace: 0.5, mood: 0.5, colour: "#ffffff"};
// A look given to a stretch. A line kept as written that already plays some of its lights is
// asked about first, since the board refuses a light set twice: agreed, the kept lines go;
// declined, nothing changes. A strip not fitted takes no look, and a new look starts in its
// own colour, its second setting afresh
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
      keptNow = keptNow.filter(function (one) { return clashing.indexOf(one) < 0; });
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

// The run the cards are for. A run of another kind, a strip say, is its own kind and is
// worked on while it is the one picked; otherwise the cards follow the colour or mono side
export function galleryRun(isMono) {
  if (active && active.strip) return active;
  return isMono ? mono : outs;
}

// Whether a stretch is mono, which is what the set of looks follows
function kindAt(run, at) {
  var section = run.sections[at];
  var lamp = section && run.lamps[section.from];
  return lamp ? !lamp.colour : false;
}

// Whether the board has any lamp of a kind. With none, its looks are worth offering but
// not worth landing: there is nothing for them to land on until an output is broken out
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

// ---- the run: lamps left to right, an output's own kept together --------------------------

// A lamp put down beside another, before it or after it, taking that place in the build
export function placeLamp(move) {
  var moved = order.splice(placeOf(move.from), 1)[0];
  order.splice(placeOf(move.to) + (move.after ? 1 : 0), 0, moved);
}

// ---- the bar: one cell per stretch, cut between them --------------------------------------

// What a stretch's cell is washed in, the colours it plays
export function washFor(run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
}

// ---- crossing from one side to the other ---------------------------------------------------

// ---- the rows around the bar ---------------------------------------------------------------

// ---- the file, painted -----------------------------------------------------------------------

export function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function paintLine(line) {
  var plain = escapeHtml(line);
  // A scene heading carries a colon, which would read as the one dividing a channel from its
  // effect, so headings are taken first
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

// ---- drawing --------------------------------------------------------------------------------
// The parts below add their own steps to a draw: what each readies before the page is drawn, and
// what each draws after the outputs, both in the order the parts come

export var drawSteps = {before: [], after: []};

// Whether drawing waits, while the page is changed in a way a draw would store half done
export var drawHeld = false;

export function draw() {
  if (drawHeld) return;
  // A draw empties and refills much of the page, and reads its layout part way through, and a
  // browser may move the scroll to hold something in view while it is half drawn, seen in Chrome
  // as a jump of the whole page when a tab was chosen. So the page ends a draw scrolled where it
  // began. A scroll a page means, such as holding a pressed button still, is made after the draw
  var across = window.scrollX;
  var down = window.scrollY;
  var focused = focusPlace();
  drawSteps.before.forEach(function (step) { step(); });

  painters = [];
  renderGallery();
  renderWiringRun("outRun", outs);
  renderStretches("outBar", outs);
  renderWiringRun("monoRun", mono);
  renderStretches("monoBar", mono);

  // Both sides are in the one panel, so one set of settings serves whichever was last worked
  // on rather than a set under each
  renderSides();
  renderEditor("outChosen", active);

  renderPreview();
  paintAll();

  drawSteps.after.forEach(function (step) { step(); });
  refocus(focused);
  if (window.scrollX !== across || window.scrollY !== down) window.scrollTo(across, down);
}

// The fields a draw gives focus back to, those typed in or chosen from, so a pressed button is left
// as the browser leaves it
var FIELDS = "input, select, textarea";

// Where the focused field is, as {field, key, box, index, caret}, or null where none is. A draw
// makes most fields afresh, and a load that ends while someone types draws too, as each of the
// drive's pictures does once read. The field is found again by its data-focus, or by its place
// among the fields of the nearest box with an id
function focusPlace() {
  var field = document.activeElement;
  if (!field || field === document.body || !field.matches(FIELDS)) return null;
  var place = {field: field, key: field.dataset.focus || null, box: null, index: -1, caret: null};
  if (!place.key) {
    var box = field.parentElement ? field.parentElement.closest("[id]") : null;
    if (!box) return null;
    place.box = box.id;
    place.index = Array.prototype.indexOf.call(box.querySelectorAll(FIELDS), field);
  }
  // Only text fields have a caret, and asking another type for one throws
  try {
    if (typeof field.selectionStart === "number") place.caret = [field.selectionStart, field.selectionEnd];
  } catch (e) {
    place.caret = null;
  }
  return place;
}

// Focus the field made where the focused one was, if the draw took that one away. A field still on
// the page keeps or loses focus as it would have
function refocus(place) {
  if (!place || place.field.isConnected || document.activeElement !== document.body) return;
  var field = null;
  if (place.key) {
    field = document.querySelector("[data-focus='" + place.key + "']");
  } else {
    var box = document.getElementById(place.box);
    field = box ? box.querySelectorAll(FIELDS)[place.index] || null : null;
  }
  if (!field || field.disabled) return;
  field.focus({preventScroll: true});
  if (place.caret) {
    try {
      field.setSelectionRange(place.caret[0], place.caret[1]);
    } catch (e) {
      // A field made as another type has no caret to place
    }
  }
}

export function paintAll() {
  var lit = {};
  runs.forEach(function (run) { lit[run.name] = litRun(run); });
  painters.forEach(function (one) { one.paint(lit[one.run.name]); });
  paintCards();
}

export function step() {
  beat += FRAME;
  paintAll();
  window.setTimeout(step, FRAME * 1000);
}

settle();
