import {PAINT_ORDER, addStep, draw, drawParts, paintAll, paintSteps} from "./00_draw.js";
import {blinkDuty, blinkSpeed, keyOf, lookNamed, withSection} from "./01_looks.js";
import {BLINK, blinkWord} from "./02_blink.js";
import {
  SOLID_COLOUR, START_MOODS, forwardTargetFor, linesFor, ownColourFor, runsAWay, takesColour,
  withExact
} from "./03_lines.js";
import {widthOf} from "./03_outputs.js";
import {MIDDLING, remember, runs} from "./03_runs.js";
import {lampUnder} from "./04_scenes.js";

// ---- the lamps, lit by the line the look writes ---------------------------------------
// A card can say what a look is made of, but only a lamp actually running it can say what it
// looks like. A lamp here plays the entry its look would write, read back and run through
// the same shapes picofx uses, so the page cannot show one thing and save another. A lamp
// whose entry names an effect this page cannot play is drawn as playing nothing.

// The colour words an entry may use, as the page draws them. These are the words autofx
// names, drawn a little softer than their constants so a screen full of them is not glaring
var NAMED = {
  black: "#000000", blue: "#2b5cff", cool: "#cfe4ff", cyan: "#28e0e0",
  green: "#22c65a", magenta: "#ff36c8", orange: "#ff9022", pink: "#ff9a9a",
  purple: "#9a46ff", red: "#ff2d1a", warm: "#ffc27a", white: "#ffffff",
  yellow: "#ffd21f"
};

var UNLIT = "#ffd9a0";   // what a lamp is drawn in where its entry names no colour

export function inkOf(word) {
  if (!word) return UNLIT;
  if (word.charAt(0) === "#") return word;
  return NAMED[word] || ("#" + word);
}

// ---- reading an entry back ------------------------------------------------------------

// The lights a selector names, as numbers. A name carries ranges and single numbers, such
// as "out1-3,7", and a bare name is the whole run
function lightsOf(selector, count) {
  var parts = /^([a-z_]+)(.*)$/.exec(selector.trim());
  if (!parts) return [];
  var tail = parts[2];
  if (!tail) {
    var whole = [];
    for (var i = 1; i <= count; i++) whole.push(i);
    return whole;
  }
  var lights = [];
  tail.split(",").forEach(function (piece) {
    var span = /^(\d+)-(\d+)$/.exec(piece);
    if (span) {
      var from = parseInt(span[1], 10), to = parseInt(span[2], 10);
      var step = from <= to ? 1 : -1;
      for (var n = from; step > 0 ? n <= to : n >= to; n += step) lights.push(n);
    } else if (/^\d+$/.test(piece)) {
      lights.push(parseInt(piece, 10));
    }
  });
  return lights;
}

// The settings of one half of an entry, as numbers where they read as numbers. A value
// that is not a number stays a string, which is what carries a colour
function settingsOf(words) {
  var found = {};
  words.forEach(function (word) {
    var at = word.indexOf("=");
    if (at < 0) return;
    var name = word.slice(0, at), value = word.slice(at + 1);
    found[name] = /^-?\d+(\.\d+)?$/.test(value) ? parseFloat(value) : value;
  });
  return found;
}

// One entry, split where the colon divides the channel from the effect it plays
function parseEntry(line, count) {
  var at = line.indexOf(":");
  if (at < 0) return null;
  var left = line.slice(0, at).trim().split(/\s+/);
  var right = line.slice(at + 1).trim().split(/\s+/);
  return {lights: lightsOf(left.shift(), count), channel: settingsOf(left),
          effect: right.shift(), settings: settingsOf(right)};
}

// ---- the effects, at the settings the entry carries ------------------------------------
// Each is picofx's own shape at the same settings. The board steps its cycle in whole
// milliseconds and wraps at a thousand, which the page does not reproduce. An effect slow
// enough that a frame adds nothing stands still there and drifts on here.

var TAU = Math.PI * 2;

// Where in its cycle an effect is. A cycle running below zero wraps back into one, as picofx's
// modulo does, or a blink or a flash would read a negative point in its beat as lit
function offsetOf(t, settings) {
  var at = ((t * num(settings.speed, 1)) + num(settings.phase, 0)) % 1;
  return at < 0 ? at + 1 : at;
}

function num(value, fallback) {
  return typeof value === "number" ? value : fallback;
}

// A value kept for a while, then a new one. Named per effect, so two of them on one lamp
// do not take each other's turn
function renewed(sim, where, dt, hold, then) {
  var walk = sim[where] || (sim[where] = {});
  walk.left = (walk.left === undefined ? 0 : walk.left) - dt;
  if (walk.left <= 0) {
    walk.left += hold();
    walk.value = then(walk.value);
  }
  return walk.value === undefined ? 0 : walk.value;
}

function betweenAt(low, high) {
  return low + Math.random() * (high - low);
}

var EFFECTS = {

  none: function () { return 0; },

  static: function (t, s) { return num(s.brightness, 1); },

  blink: function (t, s) {
    return offsetOf(t, s) % 1 < num(s.duty, 0.5) ? 1 : 0;
  },

  blink_wave: function (t, s, pos) {
    var at = (offsetOf(t, s) + pos / num(s.length, 1)) % 1;
    return at < num(s.duty, 0.5) ? 1 : 0;
  },

  pulse: function (t, s) {
    return (Math.sin(offsetOf(t, s) * TAU) + 1) / 2;
  },

  pulse_wave: function (t, s, pos) {
    var at = offsetOf(t, s) + pos / num(s.length, 1);
    return (Math.sin(at * TAU) + 1) / 2;
  },

  flash: function (t, s) {
    return flashing(offsetOf(t, s), s);
  },

  flash_sequence: function (t, s, pos) {
    return flashing(offsetOf(t, s) + pos / num(s.length, 1), s);
  },

  // A light sweeping the run and bouncing back, one pass out and one back to a cycle
  sweep: function (t, s, pos) {
    var swing = (t * num(s.speed, 1)) % 2;
    var head = (swing < 1 ? swing : 2 - swing) * (num(s.length, 1) - 1);
    return Math.max(0, 1 - Math.abs(pos - head) / num(s.extent, 1));
  },

  // The run read as a binary number, counting up from where the entry starts it
  binary_counter: function (t, s, pos) {
    var counter = num(s.count, 0) +
                  Math.floor(t / Math.max(0.001, num(s.interval, 0.1))) * num(s.step, 1);
    return (Math.floor(counter / Math.pow(2, pos)) % 2) ? 1 : 0;
  },

  // The guttering of a flame, held bright for a while and dim for a while
  flicker: function (t, s, pos, sim) {
    var bright = num(s.brightness, 1);
    var dim = bright * (1 - num(s.dimness, 0.5));
    return renewed(sim, "flicker", FRAME, function () {
      var walk = sim.flicker;
      walk.low = !walk.low;
      return walk.low ? betweenAt(num(s.dim_min, 0.02), num(s.dim_max, 0.04))
                      : betweenAt(num(s.bright_min, 0.05), num(s.bright_max, 0.1));
    }, function () { return sim.flicker.low ? dim : bright; });
  },

  random: function (t, s, pos, sim) {
    return renewed(sim, "random", FRAME, function () { return num(s.interval, 0.05); },
                function () {
                  return betweenAt(num(s.brightness_min, 0), num(s.brightness_max, 1));
                });
  },

  pelican_crossing: function (t, s, pos) {
    return phasing(t, pos, [
      [[1, 0, 0, 0, 1], num(s.red_interval, 8)],
      [[0, 1, 0, 0, 1], num(s.flashing_interval, 6)],
      [[0, 0, 1, 1, 0], num(s.green_interval, 20)],
      [[0, 1, 0, 1, 0], num(s.amber_interval, 3)]
    ], 1);
  },

  traffic_light: function (t, s, pos) {
    return phasing(t, pos, [
      [[1, 0, 0], num(s.red_interval, 10)],
      [[1, 1, 0], num(s.red_amber_interval, 5)],
      [[0, 0, 1], num(s.green_interval, 10)],
      [[0, 1, 0], num(s.amber_interval, 5)]
    ], -1);
  }
};

// A preview keeps a walk for each light, so these two already play each light its own way,
// which is what the _each effects do on the board
EFFECTS.flicker_each = EFFECTS.flicker;
EFFECTS.random_each = EFFECTS.random;

// Flash's window and its count of flashes within it, shared by the two that use it
function flashing(at, s) {
  var offset = at % 1;
  var window = num(s.window, 1);
  if (offset >= window) return 0;
  return ((offset * num(s.flashes, 1)) / window) % 1 < num(s.duty, 0.5) ? 1 : 0;
}

// The phases a crossing steps through, and how long each lasts. A real crossing is long
// enough that a page showing it truthfully would look broken, so the whole sequence is
// shown in SEQUENCE seconds with its phases kept in proportion. Only the drawing is
// hurried, and the entry keeps the intervals the sliders set
var SEQUENCE = 8;
var FLASHING_CYCLE = 0.25;   // the amber and the figure, which flash at their real rate

function phasing(t, pos, states, flashes) {
  var whole = states.reduce(function (sum, one) { return sum + one[1]; }, 0);
  var at = (t / SEQUENCE) % 1 * whole;
  for (var i = 0; i < states.length; i++) {
    if (at < states[i][1]) {
      var lit = states[i][0][pos];
      if (i !== flashes || !lit) return lit === undefined ? 0 : lit;
      // Both flash off one clock, so the amber and the figure are never out of step
      return (t % FLASHING_CYCLE) < FLASHING_CYCLE / 2 ? 1 : 0;
    }
    at -= states[i][1];
  }
  return 0;
}

// ---- the effects that bring their own colour -------------------------------------------

function hueInk(hue, sat, val) {
  var c = num(val, 1) * num(sat, 1);
  var x = c * (1 - Math.abs(((hue / 60) % 2) - 1));
  var low = num(val, 1) - c;
  var rgb = hue < 60 ? [c, x, 0] : hue < 120 ? [x, c, 0] : hue < 180 ? [0, c, x]
          : hue < 240 ? [0, x, c] : hue < 300 ? [x, 0, c] : [c, 0, x];
  return "#" + rgb.map(function (part) {
    var v = Math.round((part + low) * 255).toString(16);
    return v.length < 2 ? "0" + v : v;
  }).join("");
}

var COLOURED = {

  rainbow: function (t, s) {
    return {level: 1, ink: hueInk(((t * num(s.speed, 1)) % 1) * 360, s.sat, s.val)};
  },

  // Wrapped as offsetOf is, or a hue would go out of range
  rainbow_wave: function (t, s, pos) {
    var at = ((t * num(s.speed, 1)) + pos / num(s.length, 1)) % 1;
    return {level: 1, ink: hueInk((at < 0 ? at + 1 : at) * 360, s.sat, s.val)};
  },

  hue_step: function (t, s) {
    var steps = Math.max(1, num(s.steps, 8));
    var which = Math.floor(t / Math.max(0.001, num(s.interval, 1))) % steps;
    return {level: 1, ink: hueInk(which / steps * 360, s.sat, s.val)};
  },

  // Given several colours, it moves to its next each time its beat comes round
  rgb_blink: function (t, s) {
    var colours = String(s.colour || "red").split("|");
    var beats = Math.floor(t * num(s.speed, 1) + num(s.phase, 0));
    var which = ((beats % colours.length) + colours.length) % colours.length;
    return {level: EFFECTS.blink(t, s), ink: inkOf(colours[which])};
  }
};

// ---- the curve a channel follows --------------------------------------------------------
// fade= crosses at a steady rate and ease= settles in as a bulb does, both of them the
// seconds a change takes to arrive. What they leave behind is the trail under anything
// travelling a run. A split fade or ease, written rise|fall, goes up at its rise and comes
// down at its fall, and a single number sets both

function curved(sim, given, channel) {
  function parts(value) {
    if (typeof value === "number") return [value, value];
    var split = String(value || "").split("|").map(Number);
    return split.length === 2 && split.every(isFinite) ? split : [0, 0];
  }
  var fade = parts(channel.fade), ease = parts(channel.ease);
  if (!fade[0] && !fade[1] && !ease[0] && !ease[1]) return given;
  var was = sim.curve === undefined ? given : sim.curve;
  var rising = given > was;
  var fadeFor = fade[rising ? 0 : 1], easeFor = ease[rising ? 0 : 1];
  var now;
  if (fade[0] || fade[1]) {
    now = !fadeFor ? given
        : rising ? Math.min(given, was + FRAME / fadeFor) : Math.max(given, was - FRAME / fadeFor);
  } else {
    now = !easeFor ? given : was + (given - was) * Math.min(1, FRAME / easeFor);
  }
  sim.curve = Math.max(0, Math.min(1, now));
  return sim.curve;
}

// ---- what one lamp of a target is doing at time t ----------------------------------------

// Whether a strip's stretches are being played, so the looks take the strip's form
var previewingStrip = false;

// The target a look writes for, built from what the lamp knows. Colour is always asked
// for, so an entry naming one says what to draw the lamp in, and a caller showing mono lamps
// draws it its own way. The preview plays a stretch as that many lamps of its own
function lampTarget(count) {
  var playing = [];
  for (var i = 1; i <= count; i++) playing.push(i);
  var target = {kind: count === 1 ? "one" : "outputs", id: "outputs", name: "out",
                label: "the outputs", colour: true, count: count, playing: playing,
                selector: "out" + (count === 1 ? "1" : "1-" + count)};
  if (previewingStrip) Object.assign(target, {strip: true, lights: playing.slice()});
  return target;
}

// What a look's entries light at slot, which lamp this is counted from zero, of count playing.
// The effects part plays a stretch through this as the board will
function lookLit(look, holder, t, slot, count, sim) {
  if (!look || !look.entries) return null;
  var lines;
  try {
    lines = linesFor(look, lampTarget(count), holder.pace, holder.mood, holder.colour);
  } catch (e) {
    return null;
  }

  // The entry that names this lamp, the last one winning where two do, as the board
  // reads them in order
  var mine = null, place = 0;
  lines.forEach(function (line) {
    var entry = parseEntry(line, count);
    if (!entry) return;
    var at = entry.lights.indexOf(slot + 1);
    if (at >= 0) { mine = entry; place = at; }
  });
  if (!mine) return null;

  var coloured = COLOURED[mine.effect];
  if (coloured) {
    var shown = coloured(t, mine.settings, place, sim);
    return {level: curved(sim, shown.level, mine.channel), ink: shown.ink};
  }

  var effect = EFFECTS[mine.effect];
  if (!effect) return null;
  // A colour list gives each light of the entry its own, in order
  var colours = String(mine.channel.colour || "").split(",");
  return {level: curved(sim, effect(t, mine.settings, place, sim), mine.channel),
          ink: inkOf(colours[Math.min(place, colours.length - 1)])};
}

// ---- painting them, forty times a second ---------------------------------------------

var FRAME = 1 / 40;
export var beat = 0;

// Set the beat the lights are painted at
export function setBeat(at) {
  beat = at;
}

export var HOLDING_STILL = window.matchMedia &&
                    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- lighting -----------------------------------------------------------------------------

export var painters = [];
var walks = {};

// Empty the painters, which a draw makes afresh
function clearPainters() {
  painters = [];
}
drawParts.clearPainters = clearPainters;

// Light every lamp the painters hold as its run plays at the beat
addStep(paintSteps, PAINT_ORDER, "lamps", function () {
  var lit = {};
  runs.forEach(function (run) { lit[run.name] = litRun(run); });
  painters.forEach(function (one) { one.paint(lit[one.run.name]); });
});

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

// What a lamp the scene plays nothing on shows, marked unset= for its tile. As on the board, it
// plays Always on's look where Always on has one there, and is off where another scene plays on it
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

export function step() {
  beat += FRAME;
  paintAll();
  window.setTimeout(step, FRAME * 1000);
}

// What a look lights with its stretch as the one being played
function sectionLit(look, holder, t, slot, count, sim) {
  return withSection(holder && holder !== MIDDLING ? holder : null, function () {
    return lookLit(look, holder, t, slot, count, sim);
  });
}

// The gallery's cards play each look at middling settings, which carry one colour for all of
// them. A card of a look given a colour plays in its look's own, the one a stretch given it
// starts in, kept here by look
var cardSettings = {};

// What a look lights, a card's middling settings made its own
function cardLit(look, holder, t, slot, count, sim) {
  if (holder === MIDDLING && look && look.solid) {
    // Drawn in the swatch's value, since the word it writes would take the lamps' softer shade
    var solid = sectionLit(look, {pace: MIDDLING.pace, mood: START_MOODS.Solid,
                                  colour: SOLID_COLOUR}, t, slot, count, sim);
    return solid && {level: solid.level, ink: SOLID_COLOUR};
  } else if (holder === MIDDLING && look && START_MOODS[look.name] !== undefined) {
    // A look given a colour plays in its own at the setting it starts at, as below
    var mood = START_MOODS[look.name];
    var start = takesColour(look) &&
                ownColourFor(look, lampTarget(count), MIDDLING.pace, mood, MIDDLING.colour);
    holder = {pace: MIDDLING.pace, mood: mood, colour: start || MIDDLING.colour};
  } else if (holder === MIDDLING && takesColour(look)) {
    var key = keyOf(look);
    if (!cardSettings[key]) {
      var own = ownColourFor(look, lampTarget(count), MIDDLING.pace, MIDDLING.mood,
                             MIDDLING.colour);
      cardSettings[key] = {pace: MIDDLING.pace, mood: MIDDLING.mood,
                           colour: own || MIDDLING.colour};
    }
    holder = cardSettings[key];
  }
  return sectionLit(look, holder, t, slot, count, sim);
}

// What a look lights at slot of count lamps playing, as the board will play it. That is with the
// stretch's typed values, a blink through several colours as its list, a reversed stretch from
// its far end, and a stretch at its brightness. A card plays at full
export function livePlay(look, holder, t, slot, count, sim) {
  var exact = holder && holder !== MIDDLING ? holder.exact : null;
  return withExact(exact, function () {
    var colours = holder && holder !== MIDDLING && look && look.name === BLINK &&
                  holder.blinks && holder.blinks.colours.length > 1 ? holder.blinks.colours : null;
    if (colours) {
      var blinked = COLOURED.rgb_blink(t, {colour: colours.map(blinkWord).join("|"),
                                           speed: blinkSpeed(holder.pace),
                                           duty: blinkDuty(holder.mood)});
      return {level: blinked.level * (holder.level < 1 ? holder.level : 1), ink: blinked.ink};
    }
    var backwards = holder && holder.reversed && count > 1 &&
                    runsAWay(look, lampTarget(count), holder);
    var lit = cardLit(look, holder, t, backwards ? count - 1 - slot : slot, count, sim);
    if (!lit || !holder || holder === MIDDLING || !(holder.level < 1)) return lit;
    return Object.assign({}, lit, {level: lit.level * holder.level});
  });
}

// A toggle in the screens' style, its word and its pressed state as Loop's and Restart's are.
// Its icon has a light at the end the stretch starts from and an arrow the way it runs
export function directionToggle(run, section) {
  var button = document.createElement("button");
  button.type = "button";
  var look = lookNamed(section.look);
  var moves = runsAWay(look, forwardTargetFor(run, section), section);
  button.className = "stoggle direction" + (section.reversed ? " reversed" : "") +
                     (section.reversed && moves ? " on" : "");
  button.setAttribute("aria-pressed", section.reversed && moves ? "true" : "false");
  button.disabled = !moves;
  button.title = !moves ? (!look ? "Which end it starts from, for looks that travel"
                                 : widthOf(section) < 2 ? "One light has no direction"
                                 : look.name + " looks the same from either end")
               : section.reversed ? "Travels from the far end"
                                  : "Travels from the near end";
  button.innerHTML = "<svg width='28' height='13' viewBox='0 0 28 13' aria-hidden='true'>" +
    (section.reversed
      ? "<rect x='19' y='2.5' width='8' height='8' rx='2' fill='currentColor'/>" +
        "<path d='M17 6.5 L11.5 6.5 M14 3.5 L11 6.5 L14 9.5'/>"
      : "<rect x='1' y='2.5' width='8' height='8' rx='2' fill='currentColor'/>" +
        "<path d='M11 6.5 L16.5 6.5 M14 3.5 L17 6.5 L14 9.5'/>") + "</svg> Reverse";
  // Through the run, as a page that makes the stretches afresh leaves this one behind
  button.onclick = function () {
    remember(run);
    var live = run.sections[run.picked];
    live.reversed = !live.reversed;
    draw();
  };
  return button;
}
