import {sectionLines} from "./05_effects.js";

// ---- the figure beside each slider --------------------------------------------------------
// Each slider can show beside it the value the file writes, with its unit, in a box that takes
// one typed in. Typed within the slider's reach, the slider moves to it; typed past an end,
// the slider sits at that end and the value is kept as typed, so the file writes exactly it.
// The figures are in a drawer at the right of the sliders, shut until opened, one for the
// whole panel, and a viewer's page remembers which way they left it.
//
// Every figure rises as its slider goes right, as the setting does. So a speed set as
// an interval between steps is shown as how many times a second, and a signal's as how fast
// it runs against a real one. A slider moving several settings shows the first of its keys it
// changes, the rest following it. A wave's speed is shown without its sign, which way it runs
// being Reverse's to say.

// The settings a slider may be shown by, in the order they are looked for
var FIGURE_KEYS = {
  pace: ["speed", "interval", "green_interval", "bright_max"],
  mood: ["length", "sat", "steps", "dimness", "duty", "flashes", "ease", "fade"]
};

// A real signal's green interval, which a signal's speed is shown against
var SIGNAL_GREEN = {"Traffic light": 12, "Pelican crossing": 20};

// How a setting's value is shown, the figure rising as the slider does, and taken back
export function figureWay(key, look) {
  var times = {unit: "/s", show: function (v) { return 1 / v; },
               take: function (f) { return 1 / f; }};
  var same = function (unit) {
    return {unit: unit, show: function (v) { return v; }, take: function (f) { return f; }};
  };
  var percent = {unit: "%", show: function (v) { return v * 100; },
                 take: function (f) { return f / 100; }};
  if (key === "speed") return same("/s");
  if (key === "interval" || key === "bright_max") return times;
  if (key === "green_interval") {
    var real = SIGNAL_GREEN[look.name] || 12;
    return {unit: "\u00d7", show: function (v) { return real / v; },
            take: function (f) { return real / f; }};
  }
  if (key === "length") return same("lights");
  if (key === "ease" || key === "fade") return same("s");
  if (["sat", "dimness", "duty"].indexOf(key) >= 0) return percent;
  return same("");
}

// The typed values of the stretch whose lines are being written, which linesFor applies
export var exactNow = null;

// Both ways a stretch's lines are asked for carry its typed values: the file and the preview
export function withExact(exact, write) {
  var had = exactNow;
  exactNow = exact || null;
  try {
    return write();
  } finally {
    exactNow = had;
  }
}

// A setting's value in a stretch's lines, without its sign, or null where none names it. A
// fade is read as its fall, the part after its bar, which is what a trail is
export function settingIn(lines, key) {
  var setting = new RegExp("(^|\\s)" + key + "=(?:[\\d.]+\\|)?(-?[\\d.]+)");
  for (var at = 0; at < lines.length; at++) {
    var found = lines[at].match(setting);
    if (found) return Math.abs(Number(found[2]));
  }
  return null;
}

// The stretch's lines with one slider at a value and nothing typed
export function linesAt(run, section, look, slider, value) {
  var at = Object.assign({}, section, {exact: null});
  at[slider] = value;
  return sectionLines(run, at, look);
}

// The setting a slider moves, the first of its keys whose value it changes
export function figureKey(run, section, look, slider) {
  var low = linesAt(run, section, look, slider, 0);
  var high = linesAt(run, section, look, slider, 1);
  return FIGURE_KEYS[slider].filter(function (key) {
    return settingIn(low, key) !== null && settingIn(low, key) !== settingIn(high, key);
  })[0] || null;
}

export function figureSaid(value) {
  return String(Math.round(value * 100) / 100);
}

// The slider's place that writes nearest a value, looked for along its whole reach. Past its
// reach the slider sits at the nearer end, not at the first place that rounds to it
export function placeFor(run, section, look, slider, key, value) {
  var best = 0, nearest = Infinity;
  for (var step = 0; step <= 200; step++) {
    var place = step / 200;
    var gives = settingIn(linesAt(run, section, look, slider, place), key);
    if (gives !== null && Math.abs(gives - value) < nearest) {
      nearest = Math.abs(gives - value);
      best = place;
    }
  }
  if (nearest > 1e-6) {
    var low = settingIn(linesAt(run, section, look, slider, 0), key);
    var high = settingIn(linesAt(run, section, look, slider, 1), key);
    best = Math.abs(low - value) < Math.abs(high - value) ? 0 : 1;
  }
  return {place: best, off: nearest};
}

