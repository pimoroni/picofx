import {h} from "./00_dom.js";
import {BOARD, LOOKS, canPlay, keyOf, lerp, lookLines, lookNamed, nameSet, r2} from "./01_looks.js";
import {COLOURED, lampTarget, lookLit} from "./02_preview.js";
import {
  CHANNELS, CHANNEL_WORDS, MIDDLING, OUTPUTS, Run, active, blank, copyBlinks, copyExact, draw,
  drawSteps, forwardTargetFor, isChannel, joinedItems, levelled, mono, nextOutput, outputSaid,
  outs, paintAll, pickOutput, rangeItem, runs, sectionAt, settle, wiring
} from "./03_runs.js";
import {carried} from "./04_scenes.js";
import {BLINK, blinkList, blinkWord} from "./06_blink.js";
import {renderLeds} from "./08_setup.js";
import {exactNow, withExact} from "./25_figures.js";
import {renderStretches} from "./31_stretch_bar.js";
import {renderEditor} from "./32_stretch_editor.js";

var OPENING_LOOK = BOARD.opening.colour;

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

var RISE_OF_DWELL = 0.15;
var RISE_OF_FLASH = 0.25;

function numberIn(line, key, otherwise) {
  var found = line.match(new RegExp(" " + key + "=(-?[\\d.]+)"));
  return found ? Math.abs(Number(found[1])) : otherwise;
}

function riseFor(seconds) {
  return Math.max(0.01, r2(seconds));
}

(function (scanner, chase) {
  scanner.mood = "Trail";
  chase.mood = "Trail";
  var scannerLine = scanner.entries;
  scanner.entries = function (target, pace, mood) {
    return scannerLine(target, pace, 0.5).map(function (line) {
      var speed = numberIn(line, "speed", 1);
      var length = numberIn(line, "length", 2);
      var extent = numberIn(line, "extent", 1);
      var dwell = 2 * extent / (speed * Math.max(1, length - 1));
      return line.replace(/ fade=[\d.]+/, " fade=" + riseFor(RISE_OF_DWELL * dwell) + "|" +
                                          lerp(0.15, 2, mood));
    });
  };
  function chaseLines(lines, mood) {
    return lines.map(function (line) {
      var flash = numberIn(line, "window", 0.4) * 0.5 / numberIn(line, "speed", 1);
      return line.replace(/ fade=[\d.]+/, " fade=" + riseFor(RISE_OF_FLASH * flash) + "|" +
                                          lerp(0.05, 0.8, mood));
    });
  }
  var chaseLine = chase.entries, chaseAlone = chase.alone;
  chase.entries = function (target, pace, mood) {
    return chaseLines(chaseLine(target, pace, 0.5), mood);
  };
  chase.alone = function (target, pace, mood) {
    return chaseLines(chaseAlone(target, pace, 0.5), mood);
  };
}(lookNamed("Scanner"), lookNamed("Chase")));

function blinkSpeed(pace) { return lerp(0.3, 3, pace); }
function blinkDuty(mood) { return lerp(0.1, 0.9, mood); }

LOOKS.splice(LOOKS.indexOf(lookNamed("Breathe")) + 1, 0, {
  name: "Blink", mood: "On time", spans: true, onMono: true,
  strip: ["#ff2d1a", "#111111", "#ff2d1a", "#111111", "#ff2d1a", "#111111", "#ff2d1a"],
  entries: function (target, pace, mood) {
    return [target.selector + " colour=red: blink speed=" + blinkSpeed(pace) +
            " duty=" + blinkDuty(mood)];
  },
  alone: function (target, pace, mood) {
    return this.entries(target, pace, mood);
  }
});

function marqueeGap(mood) { return Math.round(lerp(2, 6, mood)); }

LOOKS.splice(LOOKS.indexOf(lookNamed("Chase")) + 1, 0, {
  name: "Marquee", mood: "Spacing", detents: 5, spans: true, onMono: true,
  strip: ["#ffc27a", "#111111", "#111111", "#ffc27a", "#111111", "#111111", "#ffc27a"],
  entries: function (target, pace, mood) {
    var gap = marqueeGap(mood);
    return [target.selector + " colour=warm: blink_wave speed=" + lerp(0.2, 1.5, pace) +
            " length=" + gap + " duty=" + r2(1 / gap)];
  },
  alone: function (target, pace, mood) {
    return [target.selector + " colour=warm: blink speed=" + lerp(0.2, 1.5, pace) +
            " duty=" + r2(1 / marqueeGap(mood))];
  }
});

LOOKS.splice(LOOKS.indexOf(lookNamed("Pelican crossing")), 0, {
  name: "Traffic light", mood: "Fade", spans: false, onMono: true,
  strip: ["#ff0000", "#ff7800", "#00d28c", "#111111", "#111111", "#111111", "#111111"],
  entries: function (target, pace, mood) {
    var scale = lerp(2, 0.4, pace);
    var lamps = target.playing.slice(0, 3);
    var rest = target.playing.slice(3);
    var colours = ["red", "ff7800", "00d28c"].slice(0, lamps.length);
    var lines = [nameSet(target, lamps) + " colour=" + colours.join(",") +
                 " ease=" + lerp(0.05, 0.6, mood) +
                 ": traffic_light red_interval=" + r2(12 * scale) +
                 " red_amber_interval=" + r2(2 * scale) +
                 " green_interval=" + r2(12 * scale) +
                 " amber_interval=" + r2(3 * scale)];
    if (rest.length) lines.push(nameSet(target, rest) + ": none");
    return lines;
  },
  alone: false
});

var SETTING_NAMES = {"Rainbow": "Spread", "Wave": "Spread", "Campfire": "Intensity",
                     "Pelican crossing": "Fade"};
LOOKS.forEach(function (look) {
  if (SETTING_NAMES[look.name]) look.mood = SETTING_NAMES[look.name];
});

export var SIGNAL_TIMINGS = {
  "Traffic light": [["red_interval", "Red", 12, 2, 60],
                    ["red_amber_interval", "Red and amber", 2, 1, 10],
                    ["green_interval", "Green", 12, 2, 60],
                    ["amber_interval", "Amber", 3, 1, 10]],
  "Pelican crossing": [["red_interval", "Red", 8, 2, 60],
                       ["flashing_interval", "Flashing", 6, 1, 20],
                       ["green_interval", "Green", 20, 2, 60],
                       ["amber_interval", "Amber", 3, 1, 10]]
};

var sectionNow = null;

export function withSection(section, write) {
  var had = sectionNow;
  sectionNow = section;
  try {
    return write();
  } finally {
    sectionNow = had;
  }
}

function sectionLit(look, holder, t, slot, count, sim) {
  return withSection(holder && holder !== MIDDLING ? holder : null, function () {
    return lookLit(look, holder, t, slot, count, sim);
  });
}

export function timingOf(name, key) {
  var own = sectionNow && sectionNow.timings;
  if (own && own[key] !== undefined) return own[key];
  return SIGNAL_TIMINGS[name].filter(function (part) { return part[0] === key; })[0][2];
}

Object.keys(SIGNAL_TIMINGS).forEach(function (name) {
  var look = lookNamed(name);
  var ownLines = look.entries;
  look.entries = function (target, pace, mood) {
    return ownLines(target, pace, mood).map(function (line) {
      SIGNAL_TIMINGS[name].forEach(function (part) {
        line = line.replace(new RegExp(" " + part[0] + "=[\\d.]+"),
                            " " + part[0] + "=" + timingOf(name, part[0]));
      });
      return line;
    });
  };
});

function spreadRange(count) {
  return {low: Math.max(2, Math.round(count * 0.6)), high: Math.max(2, Math.round(count * 2))};
}

function spreadLength(count, mood) {
  var range = spreadRange(count);
  return range.low + Math.round(mood * (range.high - range.low));
}

function spreadStops(target) {
  var range = spreadRange(target.count);
  return range.high - range.low + 1;
}

(function (rainbow, wave) {
  rainbow.entries = function (target, pace, mood) {
    return [target.selector + ": rainbow_wave speed=" + lerp(0.05, 0.8, pace) +
            " length=" + spreadLength(target.count, mood)];
  };
  rainbow.detents = spreadStops;
  wave.entries = function (target, pace, mood) {
    return [target.selector + " colour=cool: pulse_wave speed=" + lerp(0.1, 1, pace) +
            " length=" + spreadLength(target.count, mood)];
  };
  wave.detents = spreadStops;
}(lookNamed("Rainbow"), lookNamed("Wave")));

(function (campfire) {
  campfire.entries = function (target, pace, mood) {
    return [target.selector + " colour=ff5a00: flicker_each dimness=" + lerp(0.15, 0.8, mood) +
            " bright_min=" + lerp(0.1, 0.02, pace) + " bright_max=" + lerp(0.4, 0.1, pace) +
            " dim_min=" + lerp(0.08, 0.02, pace) + " dim_max=" + lerp(0.3, 0.08, pace)];
  };
}(lookNamed("Campfire")));

outs.sections = [blank(0, outs.lamps.length - 1)];
outs.sections[0].look = OPENING_LOOK;
if (mono.lamps.length && BOARD.opening.mono) {
  mono.sections = [blank(0, mono.lamps.length - 1)];
  mono.sections[0].look = BOARD.opening.mono;
}
settle();

export var STRIPS = BOARD.strips.map(function (strip) {
  var brightness = strip.brightness === undefined ? null : strip.brightness;
  return {id: strip.name, name: strip.name, label: strip.label, leds: strip.leds, order: "",
          there: strip.fitted, brightness: brightness, made: brightness,
          connector: strip.connector, takes: strip.takes || []};
});

function stripRun(one) {
  var run = Run(one.name, false);
  run.strip = true;
  run.id = one.id;
  run.label = one.label;
  run.leds = one.leds;
  run.order = one.order;
  run.there = one.there;
  run.brightness = one.brightness;
  run.made = one.made;
  run.connector = one.connector;
  run.takes = one.takes;
  return run;
}

export function stripNamed(name) {
  var lower = name.toLowerCase();
  return runs.filter(function (run) { return run.strip && run.name === lower; })[0] || null;
}

export function stripSet(run, values) {
  var one = STRIPS.filter(function (strip) { return strip.id === run.id; })[0];
  Object.keys(values).forEach(function (key) {
    one[key] = values[key];
    run[key] = values[key];
  });
}

export function stripSelector(run, section) {
  if (section.from === 0 && section.to === run.lamps.length - 1) return run.name;
  return run.name + (section.from === section.to
    ? String(section.from + 1)
    : (section.from + 1) + "-" + (section.to + 1));
}

export function hexOf(rgb) {
  return rgb.map(function (v) {
    return ("0" + Math.round(v).toString(16)).slice(-2);
  }).join("");
}

function hueRgb(deg) {
  var h = ((deg % 360) + 360) % 360 / 60;
  var x = 255 * (1 - Math.abs((h % 2) - 1));
  var table = [[255, x, 0], [x, 255, 0], [0, 255, x],
               [0, x, 255], [x, 0, 255], [255, 0, x]];
  return table[Math.floor(h) % 6].map(Math.round);
}

function hueOf(rgb) {
  var top = Math.max.apply(null, rgb);
  var low = Math.min.apply(null, rgb);
  if (top === low || low > 0) return null;
  var span = top - low;
  var deg;
  if (top === rgb[0]) deg = ((rgb[1] - rgb[2]) / span) % 6;
  else if (top === rgb[1]) deg = (rgb[2] - rgb[0]) / span + 2;
  else deg = (rgb[0] - rgb[1]) / span + 4;
  deg *= 60;
  return (deg + 360) % 360;
}

export function takeApart(rgb) {
  var top = Math.max.apply(null, rgb) / 255;
  var low = Math.min.apply(null, rgb) / 255;
  return {hue: hueOf(rgb.map(function (v) {
            return top === low ? 0 : Math.round((v / 255 - low) / (top - low) * 255);
          })) || 0,
          sat: top ? (top - low) / top : 0,
          value: top};
}

export function hexRgb(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
          parseInt(hex.slice(5, 7), 16)];
}

export function astrayOf(side) {
  var wired = side.order.map(function (lamp) { return side.wiring.indexOf(lamp); });
  var count = wired.length;
  var upTo = [];
  var onFrom = [];
  for (var at = 0; at < count; at++) {
    upTo[at] = 1;
    for (var earlier = 0; earlier < at; earlier++) {
      if (wired[earlier] < wired[at]) upTo[at] = Math.max(upTo[at], upTo[earlier] + 1);
    }
  }
  for (var back = count - 1; back >= 0; back--) {
    onFrom[back] = 1;
    for (var later = back + 1; later < count; later++) {
      if (wired[later] > wired[back]) onFrom[back] = Math.max(onFrom[back], onFrom[later] + 1);
    }
  }
  var longest = Math.max.apply(null, upTo.concat([0]));
  var atStep = {};
  upTo.forEach(function (steps, place) {
    if (steps + onFrom[place] - 1 === longest) atStep[steps] = (atStep[steps] || 0) + 1;
  });
  return side.order.filter(function (lamp, place) {
    var onOne = upTo[place] + onFrom[place] - 1 === longest;
    return !(onOne && atStep[upTo[place]] === 1);
  });
}

var STRIP_FEWEST = 1;
var STRIP_MOST = 300;

var STRIP_ORDERS = [["", "GRB (most strips)"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

var STRIP_BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

function stripPercent(brightness) { return Math.round(brightness * 100) + "%"; }

export function stripChipChoice(run) {
  if (run.made === null) {
    return h("select", {title: "The strip's colour order. Change it if red shows as another colour",
                        onchange: function (event) {
                          stripSet(run, {order: event.target.value});
                          draw();
                        }},
      STRIP_ORDERS.map(function (pair) {
        return h("option", {value: pair[0], selected: (run.order || "") === pair[0]}, pair[1]);
      }));
  }
  var offered = STRIP_BRIGHTNESSES.indexOf(run.brightness) < 0
    ? STRIP_BRIGHTNESSES.concat([run.brightness]).sort(function (a, b) { return a - b; })
    : STRIP_BRIGHTNESSES;
  return h("select", {title: "Overall strip brightness, applied on top of each stretch's level",
                      onchange: function (event) {
                        stripSet(run, {brightness: Number(event.target.value)});
                        draw();
                      }},
    offered.map(function (brightness) {
      return h("option", {value: brightness, selected: brightness === run.brightness},
               stripPercent(brightness) + (brightness === run.made ? " (default)" : ""));
    }));
}

export function stripLengthField(run) {
  return h("input", {type: "number", min: STRIP_FEWEST, max: STRIP_MOST, value: run.leds,
                     "aria-label": "LEDs on " + run.label,
                     onchange: function (event) {
                       var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST,
                                           parseInt(event.target.value, 10) || STRIP_FEWEST));
                       if (want === run.leds) return;
                       stripSet(run, {leds: want});
                       settle();
                       draw();
                     }});
}

export function stripChipShown(run) {
  return run.made === null ? (run.order || "grb").toUpperCase()
                           : stripPercent(run.brightness) + " brightness";
}

export function stripLengthTail(run) {
  if (run.made === null) return run.order ? "|" + run.order : "";
  return run.brightness === run.made ? "" : "|" + stripPercent(run.brightness);
}

export function readStripTail(run, tail) {
  if (run.made === null) {
    var order = tail.toLowerCase();
    if (order === "grb") order = "";
    var offered = STRIP_ORDERS.some(function (pair) { return pair[0] === order; });
    return offered ? {order: order} : null;
  }
  if (!tail) return {brightness: run.made};
  var percent = tail.match(/^(\d+(?:\.\d+)?)%$/);
  var brightness = percent ? Number(percent[1]) / 100 : Number(tail);
  return brightness >= 0 && brightness <= 1 ? {brightness: brightness} : null;
}

runs.push.apply(runs, STRIPS.map(stripRun));
settle();

drawSteps.after.push(function () {
  if (active.strip) {
    document.getElementById("outChosen").textContent = "";
  }
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    renderLeds(run.id + "Leds", run);
    renderStretches(run.id + "Bar", run);
    document.getElementById(run.id + "Chosen").textContent = "";
    if (run === active) {
      renderEditor(run.id + "Chosen", run);
    }
  });
  paintAll();
});

function playedBy(out) {
  var lamps = [];
  runs.forEach(function (run) {
    run.lamps.forEach(function (lamp, at) {
      if (lamp.out === out) lamps.push({channel: lamp.channel || 0,
                                        section: run.sections[sectionAt(run, at)]});
    });
  });
  lamps.sort(function (a, b) { return a.channel - b.channel; });
  var counted = [];
  lamps.forEach(function (one) {
    var seen = counted.filter(function (had) { return had.look === one.section.look; })[0];
    if (seen) seen.many++;
    else counted.push({look: one.section.look, section: one.section, many: 1});
  });
  var most = counted[0];
  counted.forEach(function (one) { if (one.many > most.many) most = one; });
  return most ? most.section : null;
}

var STAND_INS = {"Rainbow": "Wave"};

function carriedFrom() { return carried; }

export function standingIn(run, section) {
  var memo = null;
  run.lamps.slice(section.from, section.to + 1).forEach(function (lamp) {
    var had = carriedFrom()[lamp.out];
    if (had && had.as === section.look) memo = had;
  });
  return memo;
}

export function changeWiring(change, toColour) {
  return function (out) {
    if (!!wiring[out].broken !== toColour) return;
    var played = playedBy(out);
    played = played && {look: played.look, pace: played.pace, mood: played.mood,
                        colour: played.colour, level: played.level,
                        blinks: copyBlinks(played.blinks), exact: copyExact(played.exact),
                        timings: copyExact(played.timings)};
    var memo = carriedFrom()[out];
    delete carriedFrom()[out];
    change(out);
    runs.some(function (run) {
      var mine = run.sections.filter(function (section) {
        return run.lamps.slice(section.from, section.to + 1).every(function (lamp) {
          return lamp.out === out;
        });
      })[0];
      if (!mine) return false;
      if (played) {
        var look = lookNamed(played.look);
        var target = targetFor(run, mine);
        var standIn = lookNamed(STAND_INS[played.look]);
        if (toColour && memo && played.look === memo.as) {
          Object.assign(mine, {look: memo.look, pace: played.pace, mood: memo.mood,
                               colour: memo.colour, level: played.level});
        } else if (look && canPlay(look, target)) {
          Object.assign(mine, played);
        } else if (standIn && canPlay(standIn, target)) {
          Object.assign(mine, played, {look: keyOf(standIn)});
          carriedFrom()[out] = {as: keyOf(standIn), look: played.look, mood: played.mood,
                                colour: played.colour};
        }
      }
      return true;
    });
    settle();
    pickOutput(out);
    draw();
  };
}

export var WORDS = {
  red: [255, 0, 0], orange: [255, 128, 0], yellow: [255, 255, 0], green: [0, 255, 0],
  cyan: [0, 255, 255], blue: [0, 0, 255], purple: [128, 0, 255], magenta: [255, 0, 255],
  pink: [255, 128, 128], warm: [255, 192, 96], white: [255, 255, 255],
  cool: [96, 192, 255], black: [0, 0, 0]
};

export var SWATCHES = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta",
                "pink", "warm", "white", "cool"];

export function swatchesFor(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look === BLINK && section.blinks && section.blinks.colours.length > 1 &&
      first && first.colour) return ["black"].concat(SWATCHES);
  return SWATCHES;
}

export function rgbInk(rgb) { return "rgb(" + rgb.join(",") + ")"; }

export function wordFor(hex) {
  var lower = hex.replace("#", "").toLowerCase();
  return SWATCHES.filter(function (name) { return hexOf(WORDS[name]) === lower; })[0] || null;
}

var SET_LOOKS = ["Party"];

var FIXED_COLOUR_LOOKS = ["Wave", "Blink", "Marquee", "Scanner", "Chase"];

export function takesColour(look) {
  if (!look || SET_LOOKS.indexOf(look.name) >= 0) return false;
  return look.solid || look.mood === "Colour" || FIXED_COLOUR_LOOKS.indexOf(look.name) >= 0;
}

var MONO_WASH = "#f3c98b";

function coloursWritten(look, section, run) {
  var colours = blinkList(run, section);
  if (colours) return colours.map(function (hex) { return rgbInk(hexRgb(hex)); });
  var target = targetFor(run, section);
  var found = [];
  linesFor(look, target, section.pace, section.mood, section.colour).forEach(function (line) {
    var said = line.match(/colour=([^\s:]+)/);
    if (!said) return;
    var value = said[1].toLowerCase();
    var ink = WORDS[value] ? rgbInk(WORDS[value])
            : /^[0-9a-f]{6}$/.test(value) ? "#" + value : null;
    if (ink && found.indexOf(ink) < 0) found.push(ink);
  });
  return found;
}

export function stretchWash(look, section, run, mono) {
  if (mono) return MONO_WASH;
  var inks = run && section ? coloursWritten(look, section, run) : [];
  if (!takesColour(look) && inks.length < 2) inks = look.strip || [];
  if (inks.length > 1) return "linear-gradient(90deg," + inks.join(",") + ")";
  return inks[0] || "rgba(138,131,120,0.16)";
}

function ownColourFor(look, target, pace, mood, colour) {
  var lines = target.count === 1 && look.alone
    ? look.alone(target, pace, mood, colour)
    : look.entries(target, pace, mood, colour);
  var said = (lines[0] || "").match(/colour=([^\s:]+)/);
  if (!said) return null;
  var value = said[1].toLowerCase();
  return WORDS[value] ? "#" + hexOf(WORDS[value]) : /^[0-9a-f]{6}$/.test(value) ? "#" + value : null;
}

function ownColour(look, run, section) {
  return ownColourFor(look, targetFor(run, section), section.pace, section.mood,
                      section.colour);
}

var cardSettings = {};

export var START_MOODS = {"Solid": 1, "Colour cycle": 1, "Colour steps": 1 / 3,
                   "Pelican crossing": 0.1, "Traffic light": 0.1, "Marquee": 0.25};

var SOLID_COLOUR = "#" + hexOf(WORDS.yellow);

function cardLit(look, holder, t, slot, count, sim) {
  if (holder === MIDDLING && look && look.solid) {
    var solid = sectionLit(look, {pace: MIDDLING.pace, mood: START_MOODS.Solid,
                                  colour: SOLID_COLOUR}, t, slot, count, sim);
    return solid && {level: solid.level, ink: SOLID_COLOUR};
  } else if (holder === MIDDLING && look && START_MOODS[look.name] !== undefined) {
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

var BANKED_LOOKS = ["Emergency", "Traffic light", "Pelican crossing"];

var SIGNAL_LAMPS = {"Traffic light": 3, "Pelican crossing": 5};

export function isBanked(look) {
  return !!look && BANKED_LOOKS.indexOf(look.name) >= 0;
}

function bankedLines(look, target, pace, mood, colour) {
  if (!(target.kind === "run" || target.strip) || !isBanked(look) || target.count === 1)
    return lookLines(look, target, pace, mood, colour);
  return stripLines(look, target, pace, mood);
}

function stripLines(look, target, pace, mood) {
  function dealt(playing) {
    return Object.assign({}, target, {kind: "outputs", playing: playing});
  }
  var parts = SIGNAL_LAMPS[look.name];
  if (!parts) return look.entries(dealt(target.lights), pace, mood);
  var blocks = [];
  var from = 0;
  for (var part = 0; part < parts; part++) {
    var size = Math.floor(target.lights.length / parts) +
               (part < target.lights.length % parts ? 1 : 0);
    if (size) blocks.push(target.lights.slice(from, from + size));
    from += size;
  }
  var lines = [];
  for (var place = 0; place < blocks[0].length; place++) {
    var lights = blocks.filter(function (block) { return place < block.length; })
                       .map(function (block) { return block[place]; });
    lines.push(look.entries(dealt(lights), pace, mood)[0]);
  }
  return lines;
}

export function startColour(run, section, look) {
  if (!takesColour(look)) return;
  var own = look.solid ? SOLID_COLOUR : ownColour(look, run, section);
  if (own) {
    section.colour = own;
    section.custom = false;
  }
}

[outs, mono].forEach(function (run) {
  run.sections.forEach(function (section) {
    var look = lookNamed(section.look);
    if (look) startColour(run, section, look);
  });
});

export function fieldColour(hue, sat) {
  return hueRgb(hue).map(function (v) { return Math.round(v + (255 - v) * (1 - sat)); });
}

export var FAINTEST = 0.05;

export function atBrightness(hex, level) {
  if (!(level < 1)) return hex;
  return "#" + hexOf(hexRgb(hex).map(function (v) { return Math.round(v * level); }));
}

function coloursItself(run, section, look) {
  var first = run.lamps[section.from];
  var custom = section.custom || !wordFor(section.colour || "#ffffff");
  return takesColour(look) && !!first && first.colour && custom;
}

export function sectionLines(run, section, look) {
  return withExact(section.exact, function () {
    var colours = blinkList(run, section);
    if (colours) {
      var line = targetFor(run, section).selector + ": rgb_blink colour=" +
                 colours.map(blinkWord).join("|") + " speed=" + blinkSpeed(section.pace) +
                 " duty=" + blinkDuty(section.mood);
      return levelled([line], section.level);
    }
    if (coloursItself(run, section, look) && section.level < 1) {
      return linesFor(look, targetFor(run, section), section.pace, section.mood,
                      atBrightness(section.colour || "#ffffff", section.level));
    }
    return withSection(section, function () {
      return levelled(linesFor(look, targetFor(run, section), section.pace, section.mood,
                               section.colour), section.level);
    });
  });
}

export function linesFor(look, target, pace, mood, colour) {
  var lines;
  if (look && look.solid) {
    lines = bankedLines(look, target, pace, 1, colour).map(function (line) {
      return line.replace(/ brightness=1(?=\s|$)/, "");
    });
  } else {
    lines = bankedLines(look, target, pace, mood, colour);
  }

  if (takesColour(look) && target.colour && colour) {
    var said = wordFor(colour) || colour.replace("#", "").toLowerCase();
    lines = lines.map(function (line) { return line.replace(/colour=[^\s:]+/, "colour=" + said); });
  }

  lines = lines.map(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    if (WAVES.indexOf(effect) < 0) return line;
    return line.replace(/ speed=(\d)/, " speed=-$1");
  });

  if (!exactNow) return lines;
  Object.keys(exactNow).forEach(function (slider) {
    var typed = exactNow[slider];
    if (!typed) return;
    if (typed.key === "fade") {
      lines = lines.map(function (line) {
        return line.replace(/(\sfade=[\d.]+\|)[\d.]+/, "$1" + typed.value);
      });
      return;
    }
    var setting = new RegExp("(^|\\s)" + typed.key + "=(-?)[\\d.]+");
    lines = lines.map(function (line) {
      return line.replace(setting, function (all, space, sign) {
        return space + typed.key + "=" + sign + typed.value;
      });
    });
  });
  return lines;
}

var TRAVELLING = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence", "sweep",
                  "binary_counter", "pelican_crossing", "traffic_light", "clock"];

var WAVES = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence"];

(function (party) {
  var partyLines = party.entries;
  party.entries = function (target, pace, mood) {
    return partyLines(target, pace, mood).map(function (line) {
      return line.replace(/ phase=0\.(33|67)\b/, function (all, third) {
        return " phase=0." + (third === "33" ? "67" : "33");
      });
    });
  };
}(lookNamed("Party")));

export function runsAWay(look, target, section) {
  if (!look || target.count < 2) return false;
  var lines = linesFor(look, target, section.pace, section.mood, section.colour);
  if (lines.length > 1) return true;
  return lines.some(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    return TRAVELLING.indexOf(effect) >= 0 || / length=/.test(line);
  });
}

function wholeOutputsDown(lamps, at) {
  var count = 0;
  while (at + 3 * count + 2 < lamps.length) {
    var three = lamps.slice(at + 3 * count, at + 3 * count + 3);
    var out = lamps[at].out - count;
    var whole = three.every(function (lamp, i) {
      return isChannel(lamp) && lamp.out === out && lamp.channel === 2 - i;
    });
    if (!whole || (count && !nextOutput(out + 1, -1))) break;
    count++;
  }
  return count;
}

function nameBackwards(lamps) {
  var items = [];
  var at = 0;
  while (at < lamps.length) {
    var outputs = wholeOutputsDown(lamps, at);
    if (outputs >= 2) {
      items.push(rangeItem(lamps[at].out, lamps[at].out - outputs + 1, "*"));
      at += 3 * outputs;
      continue;
    }
    var last = at;
    while (!isChannel(lamps[at]) && last + 1 < lamps.length && !isChannel(lamps[last + 1]) &&
           lamps[last + 1].colour === lamps[at].colour &&
           lamps[last + 1].out === lamps[last].out - 1 && nextOutput(lamps[last].out, -1)) last++;
    items.push(rangeItem(lamps[at].out, lamps[last].out,
                         isChannel(lamps[at]) ? CHANNELS[lamps[at].channel] : null));
    at = last + 1;
  }
  return joinedItems(items);
}

export function targetFor(run, section) {
  var target = forwardTargetFor(run, section);
  if (!section.reversed || !runsAWay(lookNamed(section.look), target, section)) return target;
  if (run.strip) {
    var whole = section.from === 0 && section.to === run.lamps.length - 1;
    return Object.assign(target, {
      selector: run.name + (whole ? run.lamps.length + "-1"
                                  : (section.to + 1) + "-" + (section.from + 1)),
      lights: target.lights.slice().reverse(), reversed: true});
  }
  var mine = run.lamps.slice(section.from, section.to + 1).reverse();
  target.selector = nameBackwards(mine);
  target.reversed = true;
  if (target.colour) {
    target.playing = mine.map(function (lamp) { return lamp.out + 1; });
  } else {
    target.nameSet = function (set) {
      return nameBackwards(set.map(function (at) { return mine[at]; }));
    };
  }
  return target;
}

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

export function spoken(items) {
  if (items.length < 2) return items.join("");
  return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
}

function numbersSaid(numbers) {
  var said = [];
  var at = 0;
  while (at < numbers.length) {
    var last = at;
    var step = numbers[at + 1] - numbers[at];
    if (step === 1 || step === -1) {
      while (last + 1 < numbers.length && numbers[last + 1] - numbers[last] === step) last++;
    }
    if (last - at >= 2) {
      said.push(numbers[at] + " to " + numbers[last]);
    } else {
      said = said.concat(numbers.slice(at, last + 1).map(String));
    }
    at = last + 1;
  }
  return spoken(said);
}

export function wherePlays(run, section, reversed) {
  var lamps = run.lamps.slice(section.from, section.to + 1);
  if (reversed) lamps.reverse();
  if (run.strip) {
    var from = section.from + 1, to = section.to + 1;
    if (reversed) {
      var swap = from;
      from = to;
      to = swap;
    }
    return (from === to ? "LED " + from : "LEDs " + from + " to " + to) + " of " + run.label;
  }
  var groups = [];
  lamps.forEach(function (lamp) {
    var last = groups[groups.length - 1];
    var numbered = !isChannel(lamp) && OUTPUTS[lamp.out].number !== null;
    if (numbered && last && last.numbers) last.numbers.push(OUTPUTS[lamp.out].number);
    else if (numbered) groups.push({numbers: [OUTPUTS[lamp.out].number]});
    else if (!isChannel(lamp)) groups.push({said: outputSaid(lamp.out)});
    else if (last && last.out === lamp.out) last.channels.push(lamp.channel);
    else groups.push({out: lamp.out, channels: [lamp.channel]});
  });
  return spoken(groups.map(function (group) {
    if (group.numbers) {
      return (group.numbers.length === 1 ? "output " : "outputs ") + numbersSaid(group.numbers);
    }
    if (group.said) return group.said;
    var output = OUTPUTS[group.out];
    var whose = output.number === null ? "the " + output.name.toUpperCase()
                                       : "output " + output.number;
    return whose + "'s " + spoken(group.channels.map(function (channel) {
      return CHANNEL_WORDS[CHANNELS[channel]];
    }));
  }));
}

