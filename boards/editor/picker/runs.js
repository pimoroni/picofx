import {draw, drawParts} from "./draw.js";
import {filterKept, keptLights} from "./kept.js";
import {START_MOODS, sectionLines, startColour, targetFor} from "./lines.js";
import {BOARD, LOOKS, canPlay, lerp, lookNamed, r2} from "./looks.js";
import {MONO_FIRST, OUTPUTS, OUTS, order, placeOf, placesOf, setLayout, wiring} from "./outputs.js";

// ---- the runs and their stretches ---------------------------------------------------------------
// The colour lamps and the mono ones, each a run of stretches over the lamps the wiring adds up
// to, the one stretch being worked on, and the steps back and on through each run's changes.

export function Run(name, mono) {
  return {name: name, mono: mono, lamps: [], sections: [], picked: 0,
          was: [], undone: []};
}

// The colour lamps and the mono ones are each a run of their own
export var outs = Run("out", false);
export var mono = Run("mono", true);
export var runs = MONO_FIRST ? [mono, outs] : [outs, mono];

// The run holding the one stretch being worked on, which is that run's picked stretch. One set
// of looks can only be for one stretch, so the other run shows no mark at all
export var active = MONO_FIRST ? mono : outs;

// Make a run the one worked on
export function activate(run) {
  active = run;
}

// Whether the one set of looks is drawn for mono lamps. It follows whatever was last pointed at,
// so the cards are always the ones for the lights being worked on
export var showing = MONO_FIRST;
for (var m = 0; m < OUTS; m++) setLayout(wiring, order.concat(placesOf(m)));

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

// ---- sections over those lamps -----------------------------------------------------------

export function sectionAt(run, which) {
  for (var i = 0; i < run.sections.length; i++) {
    if (which >= run.sections[i].from && which <= run.sections[i].to) return i;
  }
  return 0;
}

// A stretch playing nothing yet. One on a strip starts at three quarters brightness, since a
// strip or LED panel at full is glaring up close
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

// Put a run's stretches back on the lamps they held. Lamps no stretch claims become one of their
// own, as an output's three channels are when it is broken out, and a stretch they land inside
// becomes two, so every other lamp keeps what it was playing
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
                      : blank(at, to, run));
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

// A cut is one run's step. A change to the wiring is every run's, since each holds lamps that
// moved, so its snapshots share one mark and are stepped over together
var thisStep = 0;

// Remember a run's stretches at mark=, clearing what it could step on to
function rememberAt(run, mark) {
  run.undone = [];
  run.was.push(JSON.stringify({mark: mark, sections: run.sections}));
  if (run.was.length > 40) run.was.shift();
}

export function remember(run) {
  rememberAt(run, thisStep);
  thisStep++;
}

// Remember every run as one step, as a change to the wiring is
function rememberAll() {
  runs.forEach(function (run) { rememberAt(run, thisStep); });
  thisStep++;
}

// The runs whose top step is the same one as this run's, which is every run where the
// wiring changed and only this one where a cut did
function steppingWith(run, stack) {
  var top = run[stack].length ? JSON.parse(run[stack][run[stack].length - 1]) : null;
  if (!top) return [];
  return runs.filter(function (other) {
    if (other === run || !other[stack].length) return false;
    return JSON.parse(other[stack][other[stack].length - 1]).mark === top.mark;
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

// Fit the runs' stretches to their lamps again, so every lamp is in exactly one stretch and no
// stretch spans a colour lamp and a mono one, which do not play the same looks
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

// Make a stretch the one being worked on, so the mark, the tools and the set of looks are about
// the same thing. Setting up the board gives no stretch a look, so nothing is picked while it is on
export function pick(run, at) {
  if (setupOn) return;
  active = run;
  run.picked = Math.max(0, Math.min(at, run.sections.length - 1));
  showing = kindAt(run, run.picked);
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
export function joinAll(run) {
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
// One output broken out or put back, in the scene on show

export function breakOutWiring(out) {
  if (wiring[out].broken) return;
  rememberAll();
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

// Pick the stretch holding an output's lamps, since what follows breaking it out or putting it
// back is nearly always done to them. During setup the output is held, and picked once setup ends
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
  rememberAll();
  acrossWiring(function () {
    wiring[out] = {broken: false};
    // Wherever its three ended up, the one lamp takes the place of the first of them
    var first = -1;
    setLayout(wiring, order.filter(function (place) {
      if (place.out !== out) return true;
      if (first < 0) first = placeOf(place);
      return false;
    }));
    order.splice(Math.max(0, first), 0, {out: out, channel: null});
  });
  pickOutput(out);
  draw();
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

export function inkAt(lit) {
  var hex = (lit.ink || "#ffd9a0").replace("#", "");
  var mix = 0.1 + lit.level * 0.9;
  return "rgb(" + Math.round(parseInt(hex.slice(0, 2), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(2, 4), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(4, 6), 16) * mix) + ")";
}

// ---- the gallery, played on the chosen stretch --------------------------------------------

export var CARD_LIGHTS = 12;
export var MIDDLING = {pace: 0.5, mood: 0.5, colour: "#ffffff"};
export var cardFaces = [];
export var cardWalks = {};
export var carrying_lamp = null;

// Empty the cards' faces, which a draw makes afresh
function clearCardFaces() {
  cardFaces = [];
}
drawParts.clearCardFaces = clearCardFaces;

// Set the lamp being carried to a new place, or null when none is
export function setCarryingLamp(lamp) {
  carrying_lamp = lamp;
}

// The cut being dragged, and whether the pointer moved far enough for the release to be
// the end of a drag rather than a click
var holding = null;
export var dragged = false;

// Set the cut being dragged
export function setHolding(held) {
  holding = held;
}

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
  // End a drag at any release, including one that swallowed a stretch and let go of its cut
  // already. Otherwise every later click on the bar is taken for the end of a drag
  if (dragged) window.setTimeout(function () { dragged = false; }, 0);
  if (!holding) return;
  holding = null;
  draw();
});

// Give a look to a stretch. A line kept as written that already plays some of its lights is
// asked about first, since the board reports a light set twice. The kept lines go if the change is
// agreed, and nothing changes if not. A strip not fitted takes no look, and a new look starts in
// its own colour with its second setting afresh
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
  draw();
}

// The run the cards are for. A strip is a run of its own kind and has the cards while it is
// the one picked. Otherwise the cards follow the colour or mono side
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
// not worth landing, as there is nothing for them to land on until an output is broken out
export function haveKind(isMono) {
  return runs.some(function (run) {
    return run.lamps.some(function (lamp) { return lamp.colour === !isMono; });
  });
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

// Set whether the set of looks is drawn for mono lamps
export function setShowing(isMono) {
  showing = isMono;
}

// ---- crossing from one side to the other ---------------------------------------------------

export var RIGHT = "<path d='M3 8 H12'/><path d='M8.5 4.5 L12 8 L8.5 11.5'/>";
export var LEFT = "<path d='M13 8 H4'/><path d='M7.5 4.5 L4 8 L7.5 11.5'/>";

// ---- the step back and step on icons ------------------------------------------------------

export var BACK = "<path d='M6.5 4.5 L2.5 8 L6.5 11.5'/>" +
           "<path d='M2.5 8 H9.5 A4 4 0 0 1 9.5 15'/>";
export var ON = "<path d='M9.5 4.5 L13.5 8 L9.5 11.5'/>" +
         "<path d='M13.5 8 H6.5 A4 4 0 0 0 6.5 15'/>";

// Later parts' steps for the chosen stretch's panel, each drawn after the one before
export var chosenSteps = [];

// ---- the chosen stretch's panel, pointing at its stretch -------------------------------------

// Pixels the point stays from the panel's corners, and the least of a stretch it points at
export var NOTCH_INSET = 14;

settle();

// What later parts write above the scenes, each a list of functions giving lines. The lines of
// `under` go straight under the file's header and those of `above` after a blank line
export var fileHead = {under: [], above: []};

// The look the colour side opens playing, from the board's description. Every colour output opens
// as one colour lamp, and the strips play nothing since what is wired to them is unknown
export var OPENING_LOOK = BOARD.opening.colour;

// Every lamp cycling through the hues together, picofx's rainbow, which Rainbow plays on one lamp
LOOKS.splice(LOOKS.indexOf(lookNamed("Rainbow")) + 1, 0, {
  name: "Colour cycle", mood: "Saturation", spans: true, onMono: false,
  strip: ["#e33", "#ea3", "#3a5", "#3cc", "#36c", "#a3c", "#e33"],
  entries: function (target, pace, mood) {
    return [target.selector + ": rainbow speed=" + lerp(0.05, 0.8, pace) +
            " sat=" + lerp(0.2, 1, mood)];
  },
  alone: function (target, pace, mood) {
    return this.entries(target, pace, mood);
  }
});

// The same, stepping between evenly spaced hues, picofx's hue_step
LOOKS.splice(LOOKS.indexOf(lookNamed("Colour cycle")) + 1, 0, {
  name: "Colour steps", mood: "Steps", detents: 10, spans: true, onMono: false,
  strip: ["#e33", "#e33", "#ee3", "#ee3", "#3c5", "#3c5", "#36c"],
  entries: function (target, pace, mood) {
    return [target.selector + ": hue_step interval=" + r2(lerp(2, 0.25, pace)) +
            " steps=" + Math.round(lerp(3, 12, mood))];
  },
  alone: function (target, pace, mood) {
    return this.entries(target, pace, mood);
  }
});

// ---- where the board is set up ----------------------------------------------------------
// Every fact about the board stays beside what it is about, the wiring on the outputs, a
// strip's length on the strip, a screen's type on the screen. Each reads as a box in its
// section's own colour and is changed where it is shown, the outputs' wiring in a wiring view
// of its own.

// Whether the outputs' wiring view is open
export var setupOn = false;

// The panels that hold a board fact, and the colour each one's box takes
export var BOARD_CHIP_CLASSES = {outPanel: "outs"};

// Whether this panel's board facts can be changed now. The wiring changes only in its own view
export function canEdit(panel) { return panel === "outPanel" ? setupOn : true; }

// ---- selection waits while the board is set up ------------------------------------------------
// A stretch is picked to give it a look, which setup does not do, so a tap there picks
// nothing and nothing looks picked. What was picked is held by its lamp, since the wiring
// is free to move it, and is picked again when setup ends. An output broken out or put
// back meanwhile is picked instead, as it would have been outside setup

var heldPick = null;
var heldOutput = null;

// Turn setup on or off. Turned off, the stretch held while it was on is picked
export function setSetupMode(on) {
  if (on && !setupOn) {
    var section = active.sections[active.picked];
    heldPick = section ? lampKey(active.lamps[section.from]) : null;
    heldOutput = null;
  }
  setupOn = on;
  if (!on) {
    if (heldOutput !== null) {
      pickOutput(heldOutput);
    } else if (heldPick) {
      runs.some(function (run) {
        var at = run.lamps.map(lampKey).indexOf(heldPick);
        if (at >= 0) pick(run, sectionAt(run, at));
        return at >= 0;
      });
    }
    heldPick = null;
    heldOutput = null;
  }
}

// Whether a stretch is the one being worked on. A strip's stretch is picked through pick() too,
// so only one stretch on the page is ever marked
export function isPicked(run, at) { return run === active && run.picked === at; }

// ---- what a stretch plays, carried through the tools -----------------------------------------
// Everything a stretch holds besides where it is, copied, so splitting it keeps what it played.
// joinAll() starts from one stretch playing nothing
export function playsOf(section) {
  return {look: section.look, pace: section.pace, mood: section.mood, colour: section.colour,
          custom: section.custom, reversed: section.reversed, level: section.level,
          blinks: copyBlinks(section.blinks), exact: copyExact(section.exact),
          timings: copyExact(section.timings)};
}
