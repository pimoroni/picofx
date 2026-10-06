// ---- the lamps, lit by the line the look writes ---------------------------------------
// A card can say what a look is made of; only a lamp actually running it can say what it
// looks like. A lamp here plays the entry its look would write, read back and run through
// the same shapes picofx uses, so the page cannot show one thing and save another. A look
// whose effect the board does not have yet falls back to its palette, drawn still.

// The colour words an entry may use, as the page has to draw them. These are the words
// autofx names, drawn a little softer than their constants so a screen full of them is
// not glaring
var NAMED = {
  black: "#000000", blue: "#2b5cff", cool: "#cfe4ff", cyan: "#28e0e0",
  green: "#22c65a", magenta: "#ff36c8", orange: "#ff9022", pink: "#ff9a9a",
  purple: "#9a46ff", red: "#ff2d1a", warm: "#ffc27a", white: "#ffffff",
  yellow: "#ffd21f"
};

var UNLIT = "#ffd9a0";   // what a lamp is drawn in where its entry names no colour

function inkOf(word) {
  if (!word) return UNLIT;
  if (word.charAt(0) === "#") return word;
  return NAMED[word] || ("#" + word);
}

// ---- reading an entry back ------------------------------------------------------------

// The lights a selector names, as numbers. A name carries ranges and single numbers,
// "out1-3,7", and a bare name is the whole run
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
// milliseconds and wraps at a thousand, which the page does not reproduce: an effect slow
// enough that a frame adds nothing stands still there and drifts on here.

var TAU = Math.PI * 2;

function offsetOf(t, settings) {
  return ((t * num(settings.speed, 1)) + num(settings.phase, 0)) % 1;
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
// hurried; the entry keeps the intervals the sliders set
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

  rainbow_wave: function (t, s, pos) {
    var at = (t * num(s.speed, 1)) + pos / num(s.length, 1);
    return {level: 1, ink: hueInk((at % 1) * 360, s.sat, s.val)};
  },

  hue_step: function (t, s) {
    var steps = Math.max(1, num(s.steps, 8));
    var which = Math.floor(t / Math.max(0.001, num(s.interval, 1))) % steps;
    return {level: 1, ink: hueInk(which / steps * 360, s.sat, s.val)};
  },

  rgb_blink: function (t, s) {
    return {level: EFFECTS.blink(t, s), ink: inkOf(s.colour)};
  }
};

// ---- the curve a channel follows --------------------------------------------------------
// fade crosses at a steady rate and ease settles in as a bulb does, both of them the
// seconds a change takes to arrive. What they leave behind is the trail under anything
// travelling a run

function curved(sim, given, channel) {
  var fade = num(channel.fade, 0), ease = num(channel.ease, 0);
  if (!fade && !ease) return given;
  var was = sim.curve === undefined ? given : sim.curve;
  var now;
  if (fade) {
    var step = FRAME / fade;
    now = given > was ? Math.min(given, was + step) : Math.max(given, was - step);
  } else {
    now = was + (given - was) * Math.min(1, FRAME / ease);
  }
  sim.curve = Math.max(0, Math.min(1, now));
  return sim.curve;
}

// ---- what one lamp of a target is doing at time t ----------------------------------------

// The target a look writes for, built from what the lamp knows. Colour is always asked
// for, so an entry naming one says what to draw the lamp in; a caller showing mono lamps
// draws it its own way
function lampTarget(count) {
  var playing = [];
  for (var i = 1; i <= count; i++) playing.push(i);
  return {kind: count === 1 ? "one" : "outputs", id: "outputs", name: "out",
          label: "the outputs", colour: true, count: count, playing: playing,
          selector: "out" + (count === 1 ? "1" : "1-" + count)};
}

// slot is which lamp this is, counted from zero, of count playing
function livePlay(look, holder, t, slot, count, sim) {
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
var beat = 0;

var HOLDING_STILL = window.matchMedia &&
                    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
