import {sectionLines} from "./05_effects.js";

var FIGURE_KEYS = {
  pace: ["speed", "interval", "green_interval", "bright_max"],
  mood: ["length", "sat", "steps", "dimness", "duty", "flashes", "ease", "fade"]
};

var SIGNAL_GREEN = {"Traffic light": 12, "Pelican crossing": 20};

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

export var exactNow = null;

export function withExact(exact, write) {
  var had = exactNow;
  exactNow = exact || null;
  try {
    return write();
  } finally {
    exactNow = had;
  }
}

export function settingIn(lines, key) {
  var setting = new RegExp("(^|\\s)" + key + "=(?:[\\d.]+\\|)?(-?[\\d.]+)");
  for (var at = 0; at < lines.length; at++) {
    var found = lines[at].match(setting);
    if (found) return Math.abs(Number(found[2]));
  }
  return null;
}

export function linesAt(run, section, look, slider, value) {
  var at = Object.assign({}, section, {exact: null});
  at[slider] = value;
  return sectionLines(run, at, look);
}

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

