// ---- Mighty FX's outputs, inside the sections system ------------------------------------
// Seven outputs, each three PWM channels behind one lamp. The adapter tells those three
// apart, so an output is either one colour lamp or up to three mono ones and a board is
// a mix. Everything below is the section model over a run of lamps: the only new idea is
// that the run's own length is something the wiring decides.

var MODE = "sided";
var OUTS = 7;
var CHANNELS = ["r", "g", "b"];
var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

// The corner cut into a broken-out lamp, saying which of an output's three drives it
var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

// Every lamp on the page, by the output it belongs to, so pointing at one reaches the
// others without the page being drawn again
var kinOf = {};

// An output is one lamp or three, and nothing between: the adapter brings all three
// channels out or it is not fitted. Two channels playing the same thing are two lamps in
// one stretch, which is sectioning and not wiring
var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: false});

// A mix, so no way is judged on the easy case
wiring[2] = {broken: true};
wiring[4] = {broken: true};

function Run(name, mono) {
  return {name: name, mono: mono, lamps: [], sections: [], picked: 0,
          was: [], undone: []};
}

// Some ways keep every output in one run; the others give each kind a run of its own
function splitRuns() { return MODE === "tworuns" || MODE === "sided"; }

var outs = Run("out", false);
var mono = Run("mono", true);
var runs = splitRuns() ? [outs, mono] : [outs];

// The one stretch being worked on, which is the run it is in and its place in that run.
// One set of looks can only be for one stretch, so the other run shows no mark at all
var active = outs;

// Which kind of lamp the one set of looks is drawn for. It follows whatever was last
// pointed at, so the cards are always the ones for the lights being worked on
var showing = false;

// Where each lamp sits, which is the one thing about a board only its owner knows. It
// is a lamp and not an output that is placed: an output's three channels reach three
// separate LEDs through the adapter, and those can be anywhere in a build
var order = [];
for (var m = 0; m < OUTS; m++) {
  if (wiring[m].broken) {
    CHANNELS.forEach(function (letter, c) { order.push({out: m, channel: c}); });
  } else {
    order.push({out: m, channel: null});
  }
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
  order.forEach(function (place) {
    var colour = place.channel === null;
    if (colour !== !wiring[place.out].broken) return;
    if (splitRuns() && colour === run.mono) return;
    found.push({out: place.out, colour: colour, channel: place.channel});
  });
  return found;
}

function widthOf(section) { return section.to - section.from + 1; }

// What one lamp is called, in the words the file uses
function selectorFor(lamp) {
  var name = "out" + (lamp.out + 1);
  return lamp.colour ? name : name + "." + CHANNELS[lamp.channel];
}

// The shortest way to name a set of lamps that the file still reads. Consecutive
// outputs taken whole are a range, an output's three channels in order are its `.*`, and
// the first item establishes the prefix so every one after it is a number and a channel
function nameThese(lamps) {
  // An output's three channels, in order, starting here
  function allThree(at) {
    return at + 2 < lamps.length && !lamps[at].colour &&
           lamps[at].channel === 0 && lamps[at + 1].channel === 1 &&
           lamps[at + 2].channel === 2 && lamps[at + 1].out === lamps[at].out &&
           lamps[at + 2].out === lamps[at].out;
  }
  function named(first, last, suffix) {
    return (first === last ? String(first + 1) : (first + 1) + "-" + (last + 1)) +
           (suffix ? "." + suffix : "");
  }

  var items = [];
  var at = 0;
  while (at < lamps.length) {
    if (lamps[at].colour) {
      var last = at;
      while (last + 1 < lamps.length && lamps[last + 1].colour &&
             lamps[last + 1].out === lamps[last].out + 1) {
        last++;
      }
      items.push(named(lamps[at].out, lamps[last].out, null));
      at = last + 1;
    } else if (allThree(at)) {
      var end = at;
      var highest = lamps[at].out;
      while (allThree(end + 3) && lamps[end + 3].out === highest + 1) {
        end += 3;
        highest++;
      }
      items.push(named(lamps[at].out, highest, "*"));
      at = end + 3;
    } else {
      items.push(named(lamps[at].out, lamps[at].out, CHANNELS[lamps[at].channel]));
      at++;
    }
  }
  return "out" + items.join(",");
}

function shortName(lamp) {
  if (lamp.colour) return String(lamp.out + 1);
  return (lamp.out + 1) + CHANNELS[lamp.channel];
}

// ---- sections over those lamps -----------------------------------------------------------

function sectionAt(run, which) {
  for (var i = 0; i < run.sections.length; i++) {
    if (which >= run.sections[i].from && which <= run.sections[i].to) return i;
  }
  return 0;
}

function blank(from, to) {
  return {from: from, to: to, look: null, pace: 0.45, mood: 0.5, colour: "#ff8c1a", level: 1};
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

function lampKey(lamp) {
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
                      : Object.assign(blank(at, to), {}));
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
  run.was.push(JSON.stringify({mark: thisStep, sections: run.sections,
                               wiring: wiring, order: order}));
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

function stepBack(run) {
  if (!run.was.length) return;
  var also = steppingWith(run, "was");
  [run].concat(also).forEach(function (one) {
    one.undone.push(JSON.stringify({mark: thisStep, sections: one.sections,
                                    wiring: wiring, order: order}));
    var had = JSON.parse(one.was.pop());
    one.sections = had.sections;
    if (one === run) {
      wiring = had.wiring;
      order = had.order;
    }
  });
  thisStep++;
  settle();
  draw();
}

function stepOn(run) {
  if (!run.undone.length) return;
  var also = steppingWith(run, "undone");
  [run].concat(also).forEach(function (one) {
    one.was.push(JSON.stringify({mark: thisStep, sections: one.sections,
                                 wiring: wiring, order: order}));
    var next = JSON.parse(one.undone.pop());
    one.sections = next.sections;
    if (one === run) {
      wiring = next.wiring;
      order = next.order;
    }
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
    if (!kept.length || kept[0].from !== 0) kept.unshift(blank(0, -1));
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
    run.sections = whole.length ? whole : [blank(0, run.lamps.length - 1)];

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
// the mark, the tools and the set of looks can never end up about different things
function pick(run, at) {
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

function joinAll(run) {
  remember(run);
  run.sections = [blank(0, run.lamps.length - 1)];
  settle();
  pick(run, 0);
  draw();
}

// ---- the wiring itself -------------------------------------------------------------------

function breakOut(out) {
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
// always to its lamps, so the mark and the set of looks go to the stretch holding them
function pickOutput(out) {
  runs.some(function (run) {
    var at = run.lamps.map(function (lamp) { return lamp.out; }).indexOf(out);
    if (at < 0) return false;
    pick(run, sectionAt(run, at));
    return true;
  });
}

function rejoin(out) {
  if (!wiring[out].broken) return;
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

// Which run a lamp of this output would be in, so an arrow can say where it is going
function otherSide(run) { return run === outs ? mono : outs; }

// ---- what the file says ------------------------------------------------------------------

function targetFor(run, section) {
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
                label: first.colour ? "the colour outputs" : "the mono lights"};
  if (first.colour) {
    target.playing = mine.map(function (lamp) { return lamp.out + 1; });
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

// What one stretch writes, at its brightness
function sectionLines(run, section, look) {
  return levelled(linesFor(look, targetFor(run, section), section.pace, section.mood,
                           section.colour), section.level);
}

function currentText() {
  var lines = [];
  runs.forEach(function (run) {
    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (!look) return;
      lines = lines.concat(sectionLines(run, section, look));
    });
  });
  if (!lines.length) return HEADER + "\n# Nothing is playing yet.";
  return HEADER + "\n" + lines.join("\n");
}

// ---- lighting -----------------------------------------------------------------------------

var painters = [];
var walks = {};

function litRun(run) {
  var out = [];
  var store = walks[run.name] || (walks[run.name] = {});
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
  return out;
}

function inkAt(lit) {
  var hex = (lit.ink || "#ffd9a0").replace("#", "");
  var mix = 0.1 + lit.level * 0.9;
  return "rgb(" + Math.round(parseInt(hex.slice(0, 2), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(2, 4), 16) * mix) + "," +
         Math.round(parseInt(hex.slice(4, 6), 16) * mix) + ")";
}

// ---- the gallery, carried onto a stretch --------------------------------------------------

var CARD_LIGHTS = 12;
var MIDDLING = {pace: 0.5, mood: 0.5, colour: "#ff8c1a"};
var cardFaces = [];
var cardWalks = {};
var carrying_look = null;
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

function takesLook(run) {
  return carrying_look !== null && (!splitRuns() || carrying_look.mono === run.mono);
}

function landLook(run, at, name) {
  var section = run.sections[at];
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

  card.draggable = carryLooks;
  card.title = look.name
    ? look.name + (carryLooks ? ": drag it onto a stretch of the bar or the run"
                              : ": play it on the stretch being worked on")
    : "leave a stretch dark";
  card.onclick = function () {
    var run = galleryRun(isMono);
    landLook(run, stretchFor(run, isMono), look.name);
  };
  card.ondragstart = function (event) {
    carrying_look = {mono: isMono, look: look.name};
    event.dataTransfer.effectAllowed = "copy";
    event.dataTransfer.setData("text/plain", look.name || "Nothing");
    document.body.classList.add("carrying");
  };
  card.ondragend = function () {
    carrying_look = null;
    document.body.classList.remove("carrying");
    draw();
  };
  return card;
}

function mono2run() { return splitRuns() ? mono : outs; }

// The run the cards are for. A run of another kind, a strip say, is its own kind and is
// worked on while it is the one picked; otherwise the cards follow the colour or mono side
function galleryRun(isMono) {
  if (active && active.strip) return active;
  return isMono ? mono2run() : outs;
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

// Where the two tabs go, which a page built on this one may set. "head" puts them over
// the cards with the set named above them; "foot" under, the cards being met first and
// saying plainly enough which kind they are, so the sentence goes and the tabs carry it
// as their title; "needed" is foot, shown only once the board has both kinds; "none"
// leaves the set to follow whatever stretch was last picked
var tabsWhere = "head";

// Whether a card is carried onto a stretch as well as tapped, which a page built on this
// one may turn off. With it off nothing is ever picked up, so every place that would take
// a card refuses of its own accord and the gallery is a shelf of what the picked stretch
// can play
var carryLooks = true;

function tabsAtFoot() { return tabsWhere !== "head"; }

function tabsWanted() {
  if (tabsWhere === "none") return false;
  if (tabsWhere !== "needed") return true;
  return haveKind(false) && haveKind(true);
}

var KINDS = [
  {mono: false, tab: "Colour outputs",
   says: "an output with no adapter on it is one light, any colour"},
  {mono: true, tab: "Mono lights",
   says: "brightness is all a broken-out channel has, so the cards show it"}
];

function renderGalleries() {
  // A kind the board has none of cannot be worked on, so the set goes back to the one it
  // has. Without this the cards would be for lights that are not there
  if (!haveKind(showing) && haveKind(!showing)) showing = !showing;

  var box = document.getElementById("looks");
  box.textContent = "";

  var tabs = document.createElement("div");
  tabs.className = "tabs";
  var of = document.createElement("span");
  of.className = "of";
  of.textContent = "Looks for";
  tabs.appendChild(of);
  function tabFor(kind) {
    var tab = document.createElement("button");
    tab.textContent = kind.tab;
    tab.className = showing === kind.mono ? "on" : "";
    tab.disabled = !haveKind(kind.mono);
    tab.title = tab.disabled
      ? "this board has none yet: break an output out, or put one back"
      : (tabsAtFoot() ? kind.says : "show the looks these lights can play");
    tab.onclick = function () {
      // The set follows the stretch, so changing the set moves the stretch to match:
      // leaving the mark on lights these cards cannot reach would say nothing true
      var run = galleryRun(kind.mono);
      pick(run, stretchFor(run, kind.mono));
      draw();
    };
    return tab;
  }

  var says = document.createElement("span");
  says.className = "says";
  says.textContent = (showing ? KINDS[1] : KINDS[0]).says;

  if (MODE === "sided") {
    // The lamps are colour on the left and mono on the right, so the two tabs go to
    // those ends as well and a tab's side says which lights it is for. They sit on the
    // edge of the cards they change, which is what makes them read as its tabs
    tabs.className = "tabs sides";
    tabs.textContent = "";
    if (tabsWanted()) {
      tabs.appendChild(tabFor(KINDS[0]));
      tabs.appendChild(tabFor(KINDS[1]));
    }
  } else {
    KINDS.forEach(function (kind) { tabs.appendChild(tabFor(kind)); });
    tabs.appendChild(says);
  }
  box.appendChild(tabs);

  var run = galleryRun(showing);
  var section = run.sections[run === active ? run.picked : stretchFor(run, showing)];
  var lamp = section && run.lamps[section.from];

  // What the stretch being worked on could actually be given. A look shaped to several
  // lamps has nothing to say on a stretch of one, and the model would clear it the moment
  // it landed: better to say so on the card than to take it and quietly drop it
  var target = section ? targetFor(run, section) : null;

  var shelf = box;
  if (MODE === "sided") {
    // The cards live in a box the tabs are the top edge of, and what the set is goes
    // inside it rather than between the two tabs, where it broke the row into a sentence
    shelf = document.createElement("div");
    // The box is what a tab is joined to. With no tabs there is nothing to join, so the
    // cards stand on the page as the rest of it does
    shelf.className = "shelf" + (tabsWanted() ? "" : " bare");
    if (!tabsAtFoot()) shelf.appendChild(says);
    box.appendChild(shelf);
  }

  var looks = document.createElement("div");
  looks.className = "gallery";
  spanning().concat([{name: null}]).forEach(function (look) {
    var can = !look.name || !target || canPlay(look, target);
    var on = can && lamp && lamp.colour === !showing && section.look === look.name;
    var card = lookCard(showing, look, on);
    if (!can) {
      card.className += " cannot";
      card.draggable = false;
      card.onclick = null;
      card.title = whyNot(look, target);
    }
    looks.appendChild(card);
  });
  shelf.appendChild(looks);
}

function spanning() {
  return LOOKS.filter(function (look) { return look.spans; });
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
    one.className = "lamp" + (run === active && mine === run.picked ? " ringed" : "") +
                    (lamp.colour ? " colourlamp" : " chan");
    if (!lamp.colour) {
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

    one.addEventListener("dragover", function (event) {
      if (!takesLook(run) || carrying_look.mono === lamp.colour) return;
      event.preventDefault();
      one.classList.add("landing");
    });
    one.addEventListener("dragleave", function () { one.classList.remove("landing"); });
    one.addEventListener("drop", function (event) {
      event.preventDefault();
      one.classList.remove("landing");
      if (!takesLook(run) || carrying_look.mono === lamp.colour) return;
      landLook(run, mine, carrying_look.look);
    });
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
  if (MODE === "sided") group.appendChild(crossing(lamp.out, lamp.colour));
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
}

// A lamp put down beside another, before it or after it, taking that place in the build
function moveLamp(move) {
  runs.forEach(remember);
  placeLamp(move);
  settle();
  draw();
}

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

// What a stretch's cell is washed in, which a page built on this one may make truer to
// what the stretch plays
function washFor(run, section, look) { return look.strip[2]; }

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
    cell.addEventListener("dragover", function (event) {
      if (!takesLook(run)) return;
      var first2 = run.lamps[section.from];
      if (!first2 || carrying_look.mono === first2.colour) return;
      event.preventDefault();
      cell.classList.add("landing");
    });
    cell.addEventListener("dragleave", function () { cell.classList.remove("landing"); });
    cell.addEventListener("drop", function (event) {
      event.preventDefault();
      cell.classList.remove("landing");
      if (!takesLook(run)) return;
      landLook(run, at, carrying_look.look);
    });
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

// ---- the wiring bar, for the way that keeps the two jobs apart ----------------------------

function renderWiring() {
  var box = document.getElementById("outWiring");
  box.textContent = "";
  if (MODE !== "wiring") return;

  var head = document.createElement("div");
  head.className = "wiring-head";
  head.appendChild(document.createTextNode("Wired as"));
  var says = document.createElement("span");
  says.className = "says";
  says.textContent = "cut an output to break it into three; \u00d7 puts it back to one";
  head.appendChild(says);
  box.appendChild(head);

  var wrap = document.createElement("div");
  wrap.className = "wiring";
  var bar = document.createElement("div");
  bar.className = "bar";

  // An output holds three channels' worth of the bar whichever it is, so the widths
  // stay put as one is broken out and put back
  wiring.forEach(function (one, at) {
    var mine = one.broken ? [0, 1, 2] : [null];
    mine.forEach(function (channel, which) {
      var cell = document.createElement("button");
      cell.className = "sec";
      cell.style.flex = (one.broken ? 1 : 3) + " 1 0";
      var wash = document.createElement("span");
      wash.className = "lit" + (one.broken ? "" : " out");
      cell.appendChild(wash);
      var said = document.createElement("span");
      said.className = "says";
      said.innerHTML = one.broken
        ? CHANNELS[channel].toUpperCase() + " <em>" + (at + 1) + "</em>"
        : (at + 1) + " <em>colour</em>";
      cell.appendChild(said);

      // The one act there is: an output comes apart into three, or it does not
      if (!one.broken) {
        var cuts = document.createElement("span");
        cuts.className = "cuts";
        cuts.appendChild(breakPoint(at));
        cell.appendChild(cuts);
      }
      cell.onclick = function () {
        if (!one.broken) breakOut(at);
      };
      bar.appendChild(cell);

      // Putting it back is asked for once, between the first two of its three
      if (one.broken && which === 0) {
        var edge = document.createElement("div");
        edge.className = "edge";
        var drop = document.createElement("button");
        drop.className = "drop";
        drop.textContent = "\u00d7";
        drop.title = "put output " + (at + 1) + " back to one colour light";
        drop.onclick = function (event) {
          event.stopPropagation();
          rejoin(at);
        };
        edge.appendChild(drop);
        bar.appendChild(edge);
      }
    });
  });
  wrap.appendChild(bar);
  box.appendChild(wrap);
}

// Where an output comes apart. There is one such place per output and not one per pair
// of channels: the adapter brings all three out or it is not fitted
function breakPoint(out) {
  var snip = document.createElement("i");
  snip.className = "cut inside";
  snip.style.left = "50%";
  snip.style.width = "min(14px, 40%)";
  snip.dataset.says = "R | G | B";
  snip.title = "break output " + (out + 1) + " into its three channels";
  snip.onclick = function (event) {
    event.stopPropagation();
    breakOut(out);
  };
  return snip;
}

// ---- the way that puts both acts in one bar -----------------------------------------------
// A cut between two lamps sections the run. A cut through a colour lamp breaks that
// output into its three channels, and the run grows there. Same gesture, so the one that
// changes the wiring is drawn apart, and a mark between an output's own three puts it back

function insideCutsFor(run, section, cell) {
  if (MODE !== "onebar") return;
  var wide = widthOf(section);
  var cuts = document.createElement("span");
  cuts.className = "cuts";
  for (var i = section.from; i <= section.to; i++) {
    var lamp = run.lamps[i];
    if (!lamp.colour) continue;
    cuts.appendChild(breakAt(lamp.out, i - section.from, wide));
  }
  cell.appendChild(cuts);

  // Where an output's own channels meet, offered as putting it back together
  for (var j = section.from; j < section.to; j++) {
    var here = run.lamps[j];
    var next = run.lamps[j + 1];
    if (here.colour || here.out !== next.out) continue;
    if (here.channel !== 0) continue;
    cuts.appendChild(mendAt(here.out, j - section.from + 1, wide));
  }
}

function breakAt(out, into, wide) {
  var snip = document.createElement("i");
  snip.className = "cut inside";
  snip.style.left = ((into + 0.5) / wide * 100) + "%";
  snip.style.width = "min(11px, " + (45 / wide) + "%)";
  snip.dataset.says = "R | G | B";
  snip.title = "break output " + (out + 1) + " into its three channels, which makes it " +
               "mono";
  snip.onclick = function (event) {
    event.stopPropagation();
    breakOut(out);
  };
  return snip;
}

function mendAt(out, into, wide) {
  var mend = document.createElement("i");
  mend.className = "cut inside mend";
  mend.style.left = (into / wide * 100) + "%";
  mend.style.width = "min(11px, " + (45 / wide) + "%)";
  mend.dataset.says = "back to one";
  mend.title = "put output " + (out + 1) + " back to one colour light";
  mend.onclick = function (event) {
    event.stopPropagation();
    rejoin(out);
  };
  return mend;
}

// ---- crossing from one side to the other ---------------------------------------------------

var RIGHT = "<path d='M3 8 H12'/><path d='M8.5 4.5 L12 8 L8.5 11.5'/>";
var LEFT = "<path d='M13 8 H4'/><path d='M7.5 4.5 L4 8 L7.5 11.5'/>";

// The one act there is, said as a direction: a colour output goes right and becomes
// three mono lights, and those three come back left as one colour output
function crossing(out, colour) {
  var made = document.createElement("button");
  made.className = "cross";
  var says = colour
    ? "break output " + (out + 1) + " into three mono lights"
    : "put output " + (out + 1) + " back to one colour light";
  made.title = says;
  made.setAttribute("aria-label", says);
  made.innerHTML = "<svg viewBox='0 0 16 16' width='12' height='12' fill='none' " +
                   "stroke='currentColor' stroke-width='1.7' stroke-linecap='round' " +
                   "stroke-linejoin='round'>" + (colour ? RIGHT : LEFT) + "</svg>";
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
  // Both sides of the sided page share one set of steps, above them, since a step back
  // is about the panel and not about one side of it
  if (MODE !== "sided") zoomAndSteps(box, run);
}

// The row above everything, where the sided page keeps the steps it shares
function renderPanelHead() {
  var box = document.getElementById("outHead");
  box.textContent = "";
  if (MODE !== "sided") return;
  var says = document.createElement("span");
  says.className = "what";
  says.textContent = "Drag a light to where it sits on your build";
  box.appendChild(says);
  zoomAndSteps(box, active);
}

function renderTools(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  box.textContent = "";
  var row = document.createElement("div");
  row.className = "tools";
  var whole = document.createElement("button");
  whole.textContent = "Join it all back";
  whole.disabled = run.sections.length < 2;
  whole.onclick = function () { joinAll(run); };
  row.appendChild(whole);

  var apart = document.createElement("button");
  apart.textContent = "One light each";
  apart.title = "a stretch per light, which is where most boards start";
  apart.onclick = function () {
    remember(run);
    run.sections = run.lamps.map(function (lamp, at) {
      var was = run.sections[sectionAt(run, at)];
      return {from: at, to: at, look: was.look, pace: was.pace, mood: was.mood,
              colour: was.colour, level: was.level, custom: was.custom,
              blinks: copyBlinks(was.blinks), exact: copyExact(was.exact),
              timings: copyExact(was.timings)};
    });
    settle();
    pick(run, run.picked);
    draw();
  };
  row.appendChild(apart);
  box.appendChild(row);
}

function renderChosen(where, run) {
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
  if (MODE !== "sided") return;
  [{run: outs, side: "sideA", head: "headA", title: "Colour outputs",
    says: "no adapter fitted"},
   {run: mono, side: "sideB", head: "headB", title: "Mono lights",
    says: "three to every output broken out"}].forEach(function (set) {
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
}

function renderLegend() {
  var box = document.getElementById("outLegend");
  box.textContent = "";
  if (MODE === "tworuns") {
    box.textContent = "An output moves between the two runs as it is broken out and put " +
                      "back. Nothing else about either run changes.";
    return;
  }
  if (MODE === "sided") {
    box.textContent = "The arrow on an output sends it across: one colour light becomes " +
                      "three mono ones, and the three come back as one. Each side is as " +
                      "wide as what it holds, so the divide moves with the board.";
    return;
  }
  [["", "a cut between lights, which sections the run"],
   ["inside", "a cut through an output, which breaks it into its three channels"],
   ["mend", "and the mark that puts one back to a single colour light"]]
    .forEach(function (pair) {
      var one = document.createElement("span");
      var mark = document.createElement("i");
      mark.className = pair[0];
      one.appendChild(mark);
      one.appendChild(document.createTextNode(pair[1]));
      box.appendChild(one);
    });
}

// ---- the file, painted -----------------------------------------------------------------------

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function paintLine(line) {
  var plain = escapeHtml(line);
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

function renderPreview() {
  document.getElementById("preview").innerHTML =
    currentText().split("\n").map(paintLine).join("\n");
}

// ---- drawing --------------------------------------------------------------------------------

function draw() {
  painters = [];
  cardFaces = [];
  kinOf = {};
  renderGalleries();
  renderPanelHead();
  renderRun("outRun", outs);
  renderWiring();
  renderCutting("outCut", outs);
  renderBar("outBar", outs);

  var second = document.getElementById("monoPanel");
  if (splitRuns()) {
    renderCutting("monoCut", mono);
    renderRun("monoRun", mono);
    renderBar("monoBar", mono);
  } else {
    document.getElementById("sideB").style.display = "none";
  }

  if (MODE === "sided") {
    // Both sides are in the one panel, so one set of tools serves whichever was last
    // worked on rather than a set under each
    second.style.display = "none";
    renderSides();
    renderTools("outTools", active);
    renderChosen("outChosen", active);
  } else if (MODE === "tworuns") {
    renderTools("outTools", outs);
    renderChosen("outChosen", outs);
    renderTools("monoTools", mono);
    renderChosen("monoChosen", mono);
  } else {
    second.style.display = "none";
    renderTools("outTools", outs);
    renderChosen("outChosen", outs);
  }

  // The cuts that change the wiring live in the bar on the way that puts them there
  if (MODE === "onebar") {
    var cells = document.querySelectorAll("#outBar .sec");
    outs.sections.forEach(function (section, at) {
      if (cells[at]) insideCutsFor(outs, section, cells[at]);
    });
  }

  renderLegend();
  renderPreview();
  levelSides();
  paintAll();
}

// Each side stacks its own rows, so a run whose lamps wrap onto a second row pushes its
// cutting and its bar below the other side's. Both runs take the height of the taller, so
// the two sides read across whatever either is holding
function levelSides() {
  if (!splitRuns()) return;
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

// A board with something on every lamp, so the page is read as a board and not as a
// blank one. A stretch over two colour outputs, and one over a broken output's channels
settle();
runs.forEach(function (run) {
  run.sections = run.lamps.map(function (lamp, at) { return blank(at, at); });
});
settle();

// Two stretches wider than one lamp, so the page opens on a board that has been cut
// rather than one where every lamp stands alone and there is nothing to cut
runs.forEach(function (run) {
  if (run.sections.length > 2) {
    run.sections[1].to = run.sections[2].to;
    run.sections.splice(2, 1);
  }
});
settle();

var DRESSED = {colour: ["Rainbow", "Breathe", "Party", "Campfire", "Solid"],
               mono: ["Campfire", "Sparkle", "Breathe", "Chase", "Solid"]};
runs.forEach(function (run) {
  var reached = {colour: 0, mono: 0};
  run.sections.forEach(function (section) {
    var lamp = run.lamps[section.from];
    if (!lamp) return;
    var kind = lamp.colour ? "colour" : "mono";
    section.look = DRESSED[kind][reached[kind] % DRESSED[kind].length];
    reached[kind]++;
  });
});
settle();
draw();
if (HOLDING_STILL) { beat = 0.37; paintAll(); } else { step(); }
