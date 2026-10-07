// ---- the board's outputs, inside the sections system ------------------------------------
// A colour output is three PWM channels behind one lamp. Where the board lets an adapter tell
// those three apart, the output is either one colour lamp or three mono ones, and a board is
// a mix. A mono output is one light, always on the mono side. Everything below is the section
// model over a run of lamps: the only new idea is that the run's own length is something the
// wiring decides.

var OUTS = BOARD.outputs.length;
var CHANNELS = ["r", "g", "b"];
var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

// Each output as the file names it, split into its prefix and number: out3 is out and 3, and
// rgb, which has no number, is rgb alone
var OUTPUTS = BOARD.outputs.map(function (output) {
  var named = output.name.match(/^([a-z]+)(\d*)$/);
  return {name: output.name, prefix: named[1], number: named[2] ? Number(named[2]) : null,
          mono: output.kind === "mono", breaks: !!output.breaks_out};
});

// Whether the mono side comes first, as on a board whose outputs start with its mono ones. The
// file names the lamps in the same order
var MONO_FIRST = OUTPUTS.length > 0 && OUTPUTS[0].mono;
document.getElementById("sides").classList.toggle("monofirst", MONO_FIRST);
document.querySelector("#outPanel > summary .says").textContent = BOARD.output_words.panel;

// The corner cut into a broken-out lamp, saying which of an output's three drives it
var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

// Every lamp on the page, by the output it belongs to, so pointing at one reaches the
// others without the page being drawn again
var kinOf = {};

// A colour output is one lamp or three, and nothing between: the adapter brings all three
// channels out or it is not fitted. Two channels playing the same thing are two lamps in
// one stretch, which is sectioning and not wiring. A mono output is held as broken out for good
var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: OUTPUTS[n].mono});

function Run(name, mono) {
  return {name: name, mono: mono, lamps: [], sections: [], picked: 0,
          was: [], undone: []};
}

// The colour lamps and the mono ones are each a run of their own
var outs = Run("out", false);
var mono = Run("mono", true);
var runs = MONO_FIRST ? [mono, outs] : [outs, mono];

// The one stretch being worked on, which is the run it is in and its place in that run.
// One set of looks can only be for one stretch, so the other run shows no mark at all
var active = MONO_FIRST ? mono : outs;

// Which kind of lamp the one set of looks is drawn for. It follows whatever was last
// pointed at, so the cards are always the ones for the lights being worked on
var showing = MONO_FIRST;

// Where each lamp sits, which is the one thing about a board only its owner knows. It
// is a lamp and not an output that is placed: an output's three channels reach three
// separate LEDs through the adapter, and those can be anywhere in a build
var order = [];
for (var m = 0; m < OUTS; m++) order = order.concat(placesOf(m));

// An output's places in the wiring order: a mono output's one light, a colour output whole, or
// broken out as its three channels
function placesOf(out) {
  if (OUTPUTS[out].mono) return [{out: out, channel: 0}];
  if (!wiring[out].broken) return [{out: out, channel: null}];
  return CHANNELS.map(function (letter, c) { return {out: out, channel: c}; });
}

function sameLamp(a, b) { return a.out === b.out && a.channel === b.channel; }

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

function widthOf(section) { return section.to - section.from + 1; }

// Whether a lamp is a channel of a colour output broken out, which the file names by its channel
function isChannel(lamp) { return !lamp.colour && !OUTPUTS[lamp.out].mono; }

// What one lamp is called, in the words the file uses
function selectorFor(lamp) {
  if (lamp.run) return lamp.run.name + (lamp.at + 1);
  var name = OUTPUTS[lamp.out].name;
  return isChannel(lamp) ? name + "." + CHANNELS[lamp.channel] : name;
}

// Whether the output after this one, counting by step, is the next of the same name
function nextOutput(out, step) {
  var here = OUTPUTS[out], there = OUTPUTS[out + step];
  return !!there && here.number !== null && there.prefix === here.prefix &&
         there.number === here.number + step;
}

// A set of items as the file joins them: an item's prefix carries on to a bare number after it,
// so a numbered item says its prefix only where it differs from the one before, and an output
// with no number always says its name
function joinedItems(items) {
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
function rangeItem(first, last, suffix) {
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
function shortName(lamp) {
  if (lamp.run) return String(lamp.at + 1);
  var output = OUTPUTS[lamp.out];
  if (output.number === null) {
    return isChannel(lamp) ? CHANNELS[lamp.channel].toUpperCase() : output.name.toUpperCase();
  }
  return isChannel(lamp) ? output.number + CHANNELS[lamp.channel] : String(output.number);
}

// ---- sections over those lamps -----------------------------------------------------------

function sectionAt(run, which) {
  for (var i = 0; i < run.sections.length; i++) {
    if (which >= run.sections[i].from && which <= run.sections[i].to) return i;
  }
  return 0;
}

// A stretch playing nothing yet. One on a strip starts at three quarters brightness, a strip or
// LED panel at full being glaring up close
function blank(from, to, run) {
  return {from: from, to: to, look: null, pace: 0.45, mood: 0.5, colour: "#ff8c1a",
          level: run && run.strip ? 0.75 : 1};
}

// ---- keeping a stretch on its own lamps ----------------------------------------------------
// A stretch is a range of places in a run, and breaking an output out puts three lamps in
// at the output's own place. Every stretch after that would fall on different lights, so
// what each one holds is taken by lamp before the run changes and put back afterwards.

// A stretch's list of colours to blink through, copied so two stretches never share one
function copyBlinks(blinks) {
  return blinks ? {colours: blinks.colours.slice(), at: blinks.at} : undefined;
}

// A stretch's values typed past its sliders' ends, by slider, or a signal's timings, copied
// as its blinks are
function copyExact(exact) {
  return exact ? JSON.parse(JSON.stringify(exact)) : undefined;
}

// What holds a stretch to its lamps across a change to the wiring. A strip's lamps have no
// output to be named by, so they are named by the strip and their place
function lampKey(lamp) {
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
function acrossWiring(change) {
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

function remember(run) {
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
function stepBack(run) {
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

function stepOn(run) {
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
function settle() {
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
// the mark, the tools and the set of looks can never end up about different things.
// Setting up the board gives no stretch a look, so nothing is picked while it is on
function pick(run, at) {
  if (setupOn) return;
  active = run;
  run.picked = Math.max(0, Math.min(at, run.sections.length - 1));
  showing = kindAt(run, run.picked);
}

function cutAt(run, after) {
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

function uncut(run, which) {
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
function moveEdge(run, which, to) {
  var left = run.sections[which];
  var right = run.sections[which + 1];
  if (!right) return;
  to = Math.max(left.from - 1, Math.min(right.to, to));
  left.to = to;
  right.from = to + 1;
  run.sections = run.sections.filter(function (one) { return one.to >= one.from; });
  run.picked = Math.min(run.picked, run.sections.length - 1);
}

// Joined back into one, the run plays what the stretch picked was playing
function joinAll(run) {
  var section = run.sections[run.picked];
  var had = section && playsOf(section);
  remember(run);
  run.sections = [blank(0, run.lamps.length - 1, run)];
  settle();
  pick(run, 0);
  draw();
  if (had && run.sections.length === 1) {
    Object.assign(run.sections[0], had);
    settle();
    draw();
  }
}

// ---- the wiring itself -------------------------------------------------------------------
// One output broken out or put back, in the scene on show. The wiring part does it to every
// scene and slides the lamps

function breakOutWiring(out) {
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
function pickOutput(out) {
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

function rejoinWiring(out) {
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
function outputSaid(out) {
  var output = OUTPUTS[out];
  return output.number === null ? "the " + output.name.toUpperCase() + " output"
                                : "output " + output.number;
}

// The board's colour outputs in words, as one where there is only one
function colourOutputsSaid() {
  var colour = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono) colour.push(out); });
  return colour.length === 1 ? outputSaid(colour[0]) : "the colour outputs";
}

// What a stretch plays on, as though it ran from its near end
function forwardTargetFor(run, section) {
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
function levelled(lines, level) {
  if (level === undefined || level >= 1) return lines;
  var said = " level=" + Math.round(level * 100) + "%";
  return lines.map(function (line) {
    var at = line.indexOf(":");
    if (at < 0 || /:\s*none\s*$/.test(line)) return line;
    return line.slice(0, at) + said + line.slice(at);
  });
}

// What the lamps play, a line or more for each stretch with a look
function lampLines() {
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

var painters = [];
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
          : {level: 0, ink: "#3a3f44", nothing: true};
      }
    });
  } finally {
    previewingStrip = false;
  }
  return out;
}

function inkAt(lit) {
  var hex = (lit.ink || "#ffd9a0").replace("#", "");
  var mix = 0.1 + lit.level * 0.9;
  return "rgb(" + Math.round(parseInt(hex.slice(0, 2), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(2, 4), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(4, 6), 16) * mix) + ")";
}

// ---- the gallery, played on the chosen stretch --------------------------------------------

var CARD_LIGHTS = 12;
var MIDDLING = {pace: 0.5, mood: 0.5, colour: "#ff8c1a"};
var cardFaces = [];
var cardWalks = {};
var carrying_lamp = null;

// The cut being dragged, and whether the pointer moved far enough for the release to be
// the end of a drag rather than a click
var holding = null;
var dragged = false;

document.addEventListener("mousemove", function (event) {
  if (!holding) return;
  var bar = document.getElementById(holding.where).querySelector(".bar");
  if (!bar) return;
  var box = bar.getBoundingClientRect();
  if (!box.width) return;
  var across = (event.clientX - box.left) / box.width;
  var lamp = Math.round(across * holding.run.lamps.length) - 1;
  var left = holding.run.sections[holding.which];
  if (!left || left.to === lamp) return;
  dragged = true;
  moveEdge(holding.run, holding.which, lamp);
  settle();
  pick(holding.run, holding.which);
  draw();
  // A drag that swallowed a stretch has done the one thing a drag can do. Letting it
  // carry on would eat the rest of the run in the same few pixels
  if (holding.run.sections.length !== holding.had) holding = null;
});

document.addEventListener("mouseup", function () {
  if (!holding) return;
  holding = null;
  draw();
  window.setTimeout(function () { dragged = false; }, 0);
});

// A look given to a stretch. A line kept as written that already plays some of its lights is
// asked about first, since the board refuses a light set twice: agreed, the kept lines go;
// declined, nothing changes. A strip not fitted takes no look, and a new look starts in its
// own colour, its second setting afresh
function landLook(run, at, name) {
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
      if (!confirm((clashing.length === 1 ? "A line kept as written already plays some of " +
                    "these lights:" : "Lines kept as written already play some of these " +
                    "lights:") + "\n\n" + lines + "\n\nTake " +
                   (clashing.length === 1 ? "it" : "them") + " out of the file and play " +
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
  draw();
}

function lookCard(isMono, look, on) {
  var card = document.createElement("div");
  card.className = "card" + (on ? " picked" : "") + (look.name ? "" : " nothing");
  var face = document.createElement("div");
  face.className = "face";
  if (look.name) {
    var cells = [];
    for (var i = 0; i < CARD_LIGHTS; i++) {
      var cell = document.createElement("span");
      face.appendChild(cell);
      cells.push(cell);
    }
    cardFaces.push({cells: cells, look: look, mono: isMono,
                    key: (isMono ? "m" : "c") + "-" + look.name});
  }
  card.appendChild(face);
  var name = document.createElement("div");
  name.className = "name";
  name.textContent = look.name || "Nothing";
  card.appendChild(name);

  card.title = look.name ? look.name + ": play it on the stretch being worked on"
                         : "leave a stretch dark";
  card.onclick = function () {
    var run = galleryRun(isMono);
    landLook(run, stretchFor(run, isMono), look.name);
  };
  if (!isMono && takesColour(lookNamed(look.name))) {
    card.appendChild(paletteMark());
    card.title += ". You can choose its colour";
  }
  return card;
}

// The run the cards are for. A run of another kind, a strip say, is its own kind and is
// worked on while it is the one picked; otherwise the cards follow the colour or mono side
function galleryRun(isMono) {
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

function stretchFor(run, isMono) {
  var section = run.sections[run.picked];
  var lamp = section && run.lamps[section.from];
  if (lamp && lamp.colour === !isMono) return run.picked;
  for (var i = 0; i < run.sections.length; i++) {
    var first = run.lamps[run.sections[i].from];
    if (first && first.colour === !isMono) return i;
  }
  return run.picked;
}

// The cards follow whatever stretch was last picked, so the gallery is a shelf of what that
// stretch can play
function renderGalleries() {
  // A kind the board has none of cannot be worked on, so the set goes back to the one it
  // has. Without this the cards would be for lights that are not there
  if (!haveKind(showing) && haveKind(!showing)) showing = !showing;

  var box = document.getElementById("looks");
  box.textContent = "";

  var tabs = document.createElement("div");
  tabs.className = "tabs sides";
  box.appendChild(tabs);

  var run = galleryRun(showing);
  var section = run.sections[run === active ? run.picked : stretchFor(run, showing)];
  var lamp = section && run.lamps[section.from];

  // What the stretch being worked on could actually be given. A look shaped to several
  // lamps has nothing to say on a stretch of one, and the model would clear it the moment
  // it landed: better to say so on the card than to take it and quietly drop it
  var target = section ? targetFor(run, section) : null;

  var shelf = document.createElement("div");
  shelf.className = "shelf bare";
  box.appendChild(shelf);

  var looks = document.createElement("div");
  looks.className = "gallery";
  spanning().concat([{name: null}]).forEach(function (look) {
    var can = !look.name || !target || canPlay(look, target);
    var on = can && lamp && lamp.colour === !showing && section.look === look.name;
    var card = lookCard(showing, look, on);
    if (!can) {
      card.className += " cannot";
      card.onclick = null;
      card.title = whyNot(look, target);
    }
    looks.appendChild(card);
  });
  shelf.appendChild(looks);
  groupGallery();
}

// The looks a run of several lamps can play, a banked one dealing its banks along it
function spanning() {
  return LOOKS.filter(function (look) { return look.spans || isBanked(look); });
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

// ---- the run: lamps left to right, an output's own kept together --------------------------

function renderRun(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var lamps = document.createElement("div");
  lamps.className = "lamps";
  var faces = [];
  var group = null;
  var groupOut = -1;

  run.lamps.forEach(function (lamp, at) {
    // An output's lamps stay together, so the connector they share is still one thing.
    // Its number and, where there is one, the arrow it crosses on sit in a column of
    // their own, so neither ever comes between two lamps
    if (lamp.out !== groupOut) {
      group = outputGroup(lamp);
      lamps.appendChild(group);
      groupOut = lamp.out;
    }
    var mine = sectionAt(run, at);
    var one = document.createElement("div");
    // A mono output's lamp is one light, with no channel's corner and no kin
    one.className = "lamp" + (run === active && mine === run.picked ? " ringed" : "") +
                    (lamp.colour ? " colourlamp" : isChannel(lamp) ? " chan" : " chan single");
    if (!lamp.colour && isChannel(lamp)) {
      one.style.setProperty("--chan", CHANNEL_INKS[lamp.channel]);
      // Which three would gather if this output were put back to one colour lamp, which
      // is the question being asked whenever one of them is pointed at
      (kinOf[lamp.out] = kinOf[lamp.out] || []).push(one);
      one.onmouseenter = function () { showKin(lamp.out, true); };
      one.onmouseleave = function () { showKin(lamp.out, false); };
    }
    one.title = selectorFor(lamp) + ", playing " +
                (lookNamed(run.sections[mine].look) || {name: "Nothing"}).name;
    one.onclick = function () {
      pick(run, mine);
      draw();
    };
    takesPlace(one, lamp);
    var face = document.createElement("i");
    one.appendChild(face);
    var said = document.createElement("b");
    said.textContent = shortName(lamp);
    one.appendChild(said);
    faces.push(face);
    group.appendChild(one);
  });

  box.appendChild(lamps);
  painters.push({run: run, paint: function (all) {
    faces.forEach(function (face, at) {
      var one = all[at] || {level: 0, ink: "#e4e0d9"};
      face.style.background = one.nothing ? "#2a2d30" : inkAt(one);
      face.style.boxShadow = one.level > 0.05
        ? "inset 0 0 0 1px rgba(0,0,0,.2), 0 0 " + (3 + one.level * 8).toFixed(1) +
          "px rgba(255,217,160," + (one.level * 0.5).toFixed(2) + ")"
        : "inset 0 0 0 1px rgba(0,0,0,.2)";
    });
  }});
}

// One output's lamps, kept together. Every lamp already says which output and channel
// it is, so the group carries no number of its own: it is a space in the run and the
// place the arrow appears when the output is pointed at
function outputGroup(lamp) {
  var group = document.createElement("div");
  group.className = "outgroup" + (lamp.colour ? " whole" : "");
  group.appendChild(crossing(lamp.out, lamp.colour));
  return group;
}

// A lamp is dragged to where it sits on the build. A colour output is one lamp so it
// moves whole; a broken-out one moves a channel at a time, since its three LEDs are
// three separate things once the adapter is on
function takesPlace(node, lamp) {
  var me = {out: lamp.out, channel: lamp.colour ? null : lamp.channel};
  node.draggable = true;
  node.addEventListener("dragstart", function (event) {
    carrying_lamp = me;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", shortName(lamp));
    node.classList.add("carried");
  });
  node.addEventListener("dragend", function () {
    carrying_lamp = null;
    draw();
  });
  // Put down on a lamp's right half, the carried one goes after it, which is the only way
  // to reach the far end of the run
  function after(event) {
    var box = node.getBoundingClientRect();
    return event.clientX > box.left + box.width / 2;
  }
  node.addEventListener("dragover", function (event) {
    if (!carrying_lamp || sameLamp(carrying_lamp, me)) return;
    event.preventDefault();
    node.classList.add("landing");
    node.classList.toggle("after", after(event));
  });
  node.addEventListener("dragleave", function () { node.classList.remove("landing", "after"); });
  node.addEventListener("drop", function (event) {
    event.preventDefault();
    node.classList.remove("landing", "after");
    if (!carrying_lamp || sameLamp(carrying_lamp, me)) return;
    var carried = carrying_lamp;
    carrying_lamp = null;
    moveLamp({from: carried, to: me, after: after(event)});
  });
  if (!lampsMovable()) node.draggable = false;
  // Every lamp can be found by what it is, which is what the lines and the slide go by
  var key = lampKey(me);
  node.dataset.key = key;
  node.addEventListener("mouseenter", function () { bringForward([key], true); });
  node.addEventListener("mouseleave", function () { bringForward([key], false); });
}

// A lamp put down beside another, before it or after it, taking that place in the build
function placeLamp(move) {
  var moved = order.splice(placeOf(move.from), 1)[0];
  order.splice(placeOf(move.to) + (move.after ? 1 : 0), 0, moved);
}

// Lighting an output's three channels, each at its own edge and in its own colour. The
// arrow that gathers them shows on every group holding one of the three, so what would
// come back is visible before anything is pressed
function showKin(out, on) {
  (kinOf[out] || []).forEach(function (node) {
    node.classList.toggle("kin", on);
    if (node.parentNode) node.parentNode.classList.toggle("kin", on);
  });
}

// ---- the bar: one cell per stretch, cut between them --------------------------------------

// What a stretch's cell is washed in, the colours it plays
function washFor(run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
}

function renderBar(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var scroller = document.createElement("div");
  scroller.className = "scroller";
  var bar = document.createElement("div");
  bar.className = "bar";

  run.sections.forEach(function (section, at) {
    var cell = document.createElement("button");
    cell.className = "sec" + (run === active && run.picked === at ? " picked" : "");
    cell.style.flex = widthOf(section) + " 1 0";
    var first = run.lamps[section.from];
    cell.title = (first && first.colour ? "colour" : "mono") + ", " +
                 targetFor(run, section).selector;

    var look = lookNamed(section.look);
    var wash = document.createElement("span");
    wash.className = "lit" + (look ? "" : " nothing");
    if (look) wash.style.background = washFor(run, section, look);
    cell.appendChild(wash);

    var says = document.createElement("span");
    says.className = "says";
    says.innerHTML = (look ? look.name : "Nothing") + " <em>" + widthOf(section) +
                     "</em>";
    cell.appendChild(says);

    // Where this stretch can be cut, one place between two lamps
    var inside = document.createElement("span");
    inside.className = "cuts";
    for (var i = section.from; i < section.to; i++) {
      inside.appendChild(cutPoint(run, i, widthOf(section), section.from));
    }
    cell.appendChild(inside);

    cell.onclick = function () {
      if (dragged) return;
      pick(run, at);
      draw();
    };
    bar.appendChild(cell);

    if (at < run.sections.length - 1) {
      var edge = document.createElement("div");
      edge.className = "edge";
      edge.title = "drag to move this cut, or take it out below";
      edge.onmousedown = function (event) {
        event.preventDefault();
        remember(run);
        // The stretch being resized is the one being worked on, whichever side it is on
        pick(run, at);
        // The bar is rebuilt on every move, so what is held onto is where the bar lives
        // and not the bar itself, which would be a node already thrown away
        holding = {run: run, which: at, where: where, had: run.sections.length};
        edge.classList.add("holding");
      };
      // Taking the cut out is its own target, so it is never confused with moving it
      var drop = document.createElement("button");
      drop.className = "drop";
      drop.textContent = "\u00d7";
      drop.title = "take this cut out, joining the two stretches";
      drop.onmousedown = function (event) { event.stopPropagation(); };
      drop.onclick = function (event) {
        event.stopPropagation();
        uncut(run, at);
      };
      edge.appendChild(drop);
      bar.appendChild(edge);
    }
  });
  scroller.appendChild(bar);
  box.appendChild(scroller);
}

function cutPoint(run, after, wide, from) {
  var snip = document.createElement("i");
  snip.className = "cut";
  snip.style.left = ((after - from + 1) / wide * 100) + "%";
  snip.style.width = "min(11px, " + (55 / wide) + "%)";
  snip.dataset.says = shortName(run.lamps[after]) + " | " +
                      shortName(run.lamps[after + 1]);
  snip.title = "cut between " + snip.dataset.says.replace(" | ", " and ");
  snip.onclick = function (event) {
    event.stopPropagation();
    cutAt(run, after);
  };
  return snip;
}

// ---- crossing from one side to the other ---------------------------------------------------

var RIGHT = "<path d='M3 8 H12'/><path d='M8.5 4.5 L12 8 L8.5 11.5'/>";
var LEFT = "<path d='M13 8 H4'/><path d='M7.5 4.5 L4 8 L7.5 11.5'/>";

// The one act there is, said as a direction: a colour output crosses to the mono side and
// becomes three mono lights, and those three cross back as one colour output. It shows only
// where the wiring can be changed, in the board's colour, and only on an output that breaks out
function crossing(out, colour) {
  if (!canEdit("outPanel") || OUTPUTS[out].mono || !OUTPUTS[out].breaks) return noArrow();
  var made = document.createElement("button");
  made.className = "cross boardarrow";
  var says = colour
    ? "break " + outputSaid(out) + " into three mono lights"
    : "put " + outputSaid(out) + " back to one colour light";
  made.title = says;
  made.setAttribute("aria-label", says);
  made.innerHTML = "<svg viewBox='0 0 16 16' width='12' height='12' fill='none' " +
                   "stroke='currentColor' stroke-width='1.7' stroke-linecap='round' " +
                   "stroke-linejoin='round'>" + (colour === MONO_FIRST ? LEFT : RIGHT) + "</svg>";
  made.onclick = function (event) {
    event.stopPropagation();
    if (colour) breakOut(out); else rejoin(out);
  };
  return made;
}

// ---- the rows around the bar ---------------------------------------------------------------

function zoomAndSteps(row, run) {
  var space = document.createElement("span");
  space.className = "gap";
  row.appendChild(space);
  row.appendChild(iconButton(BACK, "Undo", !run.was.length,
                             function () { stepBack(run); }));
  row.appendChild(iconButton(ON, "Redo", !run.undone.length,
                             function () { stepOn(run); }));
}

var BACK = "<path d='M6.5 4.5 L2.5 8 L6.5 11.5'/>" +
           "<path d='M2.5 8 H9.5 A4 4 0 0 1 9.5 15'/>";
var ON = "<path d='M9.5 4.5 L13.5 8 L9.5 11.5'/>" +
         "<path d='M13.5 8 H6.5 A4 4 0 0 0 6.5 15'/>";

function iconButton(drawing, says, off, done) {
  var made = document.createElement("button");
  made.className = "round";
  made.title = says;
  made.setAttribute("aria-label", says);
  made.disabled = off;
  made.innerHTML = "<svg viewBox='0 0 17 17' width='15' height='15' fill='none' " +
                   "stroke='currentColor' stroke-width='1.5' stroke-linecap='round' " +
                   "stroke-linejoin='round'>" + drawing + "</svg>";
  made.onclick = done;
  return made;
}

function renderCutting(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  box.textContent = "";
  box.className = "head cutting";
  var says = document.createElement("span");
  says.className = "what";
  says.textContent = "Cut into " + run.sections.length +
                     (run.sections.length === 1 ? " stretch" : " stretches");
  box.appendChild(says);
  // The steps the two sides share go on the cutting row of the side at the right, as a strip
  // keeps its own on its cutting row. That is the second side while it has lamps
  var first = MONO_FIRST ? mono : outs, second = MONO_FIRST ? outs : mono;
  var right = second.lamps.length ? second : first;
  if (where === (right === mono ? "monoCut" : "outCut")) zoomAndSteps(box, active);
}

// The chosen stretch's panel. The parts below add to it, each after the one before, whatever the
// panel drew
var chosenSteps = [];

function renderChosen(where, run) {
  renderChosenPanel(where, run);
  chosenSteps.forEach(function (step) { step(where, run); });
}

function renderChosenPanel(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  box.textContent = "";
  var section = run.sections[run.picked];
  if (!section) return;
  var wrap = document.createElement("div");
  wrap.className = "chosen";
  var who = document.createElement("div");
  who.className = "who";
  var first = run.lamps[section.from];
  who.innerHTML = "<b>" + targetFor(run, section).selector + "</b>, " +
                  widthOf(section) + (widthOf(section) === 1 ? " light" : " lights") +
                  ", " + (first && first.colour ? "colour" : "mono");
  wrap.appendChild(who);

  var look = lookNamed(section.look);
  if (look) {
    var tuning = document.createElement("div");
    tuning.className = "tuning";
    tuning.appendChild(labelled(look.solid ? "Brightness" : "Speed"));
    tuning.appendChild(slider(look.solid ? "mood" : "pace"));
    if (!look.solid) {
      tuning.appendChild(labelled(look.mood));
      tuning.appendChild(slider("mood"));
    }
    wrap.appendChild(tuning);
  }
  box.appendChild(wrap);

  function labelled(words) {
    var label = document.createElement("label");
    label.textContent = words;
    return label;
  }
  function slider(key) {
    var range = document.createElement("input");
    range.type = "range";
    range.min = 0;
    range.max = 1;
    range.step = 0.01;
    range.value = section[key];
    range.dataset.focus = where + "-" + key;
    // Through the run, as a page that makes the stretches afresh leaves this one behind
    range.oninput = function () {
      run.sections[run.picked][key] = Number(range.value);
      renderPreview();
    };
    return range;
  }
}

// The two sides: each as wide as what it holds, so the divide between them moves as
// outputs are broken out and put back
function renderSides() {
  var words = BOARD.output_words;
  [{run: outs, side: "sideA", head: "headA", title: words.colour, says: words.colour_says},
   {run: mono, side: "sideB", head: "headB", title: words.mono,
    says: words.mono_says}].forEach(function (set) {
    var box = document.getElementById(set.side);
    var count = set.run.lamps.length;
    var groups = {};
    set.run.lamps.forEach(function (lamp) { groups[lamp.out] = true; });
    // Each output is a space in the run as well as its lamps, so the spaces are counted
    // too or the last output wraps onto a row of its own
    var room = count + Object.keys(groups).length;
    // A side with nothing on it is not there at all: an output comes back from the arrow
    // on one of its channels, so nothing is reached by keeping an empty column open, and
    // the side that holds every lamp gets the whole width
    box.style.display = count ? "" : "none";
    box.style.flex = room + " 1 0";
    box.className = "side";

    var head = document.getElementById(set.head);
    head.textContent = "";
    head.appendChild(document.createTextNode(set.title));
    var says = document.createElement("span");
    // A side with nothing in it has no count to give, and no room to give one in
    says.textContent = count
      ? count + (count === 1 ? " light, " : " lights, ") + set.says
      : "";
    head.appendChild(says);
  });
  // A side is named only while there are two, telling the colour lamps from the mono ones.
  // With every output one colour lamp, the board's box says so already
  var two = mono.lamps.length > 0;
  ["headA", "headB"].forEach(function (id) {
    document.getElementById(id).style.display = two ? "" : "none";
  });
  document.getElementById("sides").classList.toggle("unnamed", !two);
}

// ---- the file, painted -----------------------------------------------------------------------

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function paintLine(line) {
  var plain = escapeHtml(line);
  // A scene heading carries a colon, which would read as the one dividing a channel from its
  // effect, so headings are taken first
  if (line.charAt(0) === "[") return "<span class='s-scene'>" + plain + "</span>";
  if (/^\s*#/.test(line)) return "<span class='s-comment'>" + plain + "</span>";
  var at = line.indexOf(":");
  if (at < 0) return plain;
  function settings(text) {
    return (text.match(/"[^"]*"|\S+|\s+/g) || []).map(function (token) {
      var pair = token.match(/^([^=\s]+)(=)(.*)$/);
      if (!pair) return escapeHtml(token);
      return "<span class='s-name'>" + escapeHtml(pair[1]) + "</span>" +
             "<span class='s-punc'>=</span>" +
             "<span class='s-value'>" + escapeHtml(pair[3]) + "</span>";
    }).join("");
  }
  var left = line.slice(0, at), right = line.slice(at + 1);
  var selector = left.match(/^(\s*)(\S+)(.*)$/);
  var head = selector
    ? escapeHtml(selector[1]) + "<span class='s-target'>" + escapeHtml(selector[2]) +
      "</span>" + settings(selector[3])
    : escapeHtml(left);
  var effect = right.match(/^(\s*)(\S+)(.*)$/);
  var tail = effect
    ? escapeHtml(effect[1]) + "<span class='s-effect'>" + escapeHtml(effect[2]) +
      "</span>" + settings(effect[3])
    : escapeHtml(right);
  return head + "<span class='s-colon'>:</span>" + tail;
}

// ---- drawing --------------------------------------------------------------------------------
// The parts below add their own steps to a draw: what each readies before the page is drawn, and
// what each draws after the outputs, both in the order the parts come

var drawSteps = {before: [], after: []};

// Whether drawing waits, while the page is changed in a way a draw would store half done
var drawHeld = false;

function draw() {
  if (drawHeld) return;
  // A draw empties and refills much of the page, and reads its layout part way through, and a
  // browser may move the scroll to hold something in view while it is half drawn, seen in Chrome
  // as a jump of the whole page when a tab was chosen. So the page ends a draw scrolled where it
  // began. A scroll a page means, such as holding a pressed button still, is made after the draw
  var across = window.scrollX;
  var down = window.scrollY;
  drawSteps.before.forEach(function (step) { step(); });

  painters = [];
  cardFaces = [];
  kinOf = {};
  renderGalleries();
  renderRun("outRun", outs);
  renderCutting("outCut", outs);
  renderBar("outBar", outs);
  renderCutting("monoCut", mono);
  renderRun("monoRun", mono);
  renderBar("monoBar", mono);

  // Both sides are in the one panel, so one set of tools serves whichever was last worked
  // on rather than a set under each
  renderSides();
  renderTools("outTools", active);
  renderChosen("outChosen", active);

  renderPreview();
  levelSides();
  paintAll();

  drawSteps.after.forEach(function (step) { step(); });
  if (window.scrollX !== across || window.scrollY !== down) window.scrollTo(across, down);
}

// Each side stacks its own rows, so a run whose lamps wrap onto a second row pushes its
// cutting and its bar below the other side's. Both runs take the height of the taller, so
// the two sides read across whatever either is holding
function levelSides() {
  var both = [document.getElementById("outRun"), document.getElementById("monoRun")];
  both.forEach(function (box) { box.style.minHeight = ""; });
  var tallest = 0;
  both.forEach(function (box) {
    tallest = Math.max(tallest, box.getBoundingClientRect().height);
  });
  both.forEach(function (box) { box.style.minHeight = tallest + "px"; });
}

function paintAll() {
  var lit = {};
  runs.forEach(function (run) { lit[run.name] = litRun(run); });
  painters.forEach(function (one) { one.paint(lit[one.run.name]); });
  paintCards();
}

function step() {
  beat += FRAME;
  paintAll();
  window.setTimeout(step, FRAME * 1000);
}

settle();
