import {BOARD, LOOKS, canPlay, keyOf, lerp, lookLines, lookNamed, nameSet, r2} from "./01_looks.js";
import {COLOURED, lampTarget, lookLit} from "./02_preview.js";
import {
  BACK, CHANNELS, CHANNEL_WORDS, MIDDLING, ON, OUTPUTS, Run, active, blank, copyBlinks, copyExact,
  draw, drawSteps, forwardTargetFor, iconButton, isChannel, joinedItems, levelled, mono,
  nextOutput, outputSaid, outs, paintAll, pickOutput, rangeItem, renderCutting, runs, sectionAt,
  settle, stepBack, stepOn, wiring
} from "./03_runs.js";
import {carried} from "./04_scenes.js";
import {BLINK, blinkList, blinkWord} from "./06_blink.js";
import {renderLeds} from "./08_setup.js";
import {exactNow, withExact} from "./25_figures.js";
import {middleOfView, renderStretches, zoomOf, zoomTo, zooms} from "./31_stretch_bar.js";
import {renderEditor} from "./32_stretch_editor.js";

// The board opens as it ships, every colour output one colour lamp, each side whole and playing
// the look the board's description opens it with. The strips play nothing, what is wired to them
// being unknown
var OPENING_LOOK = BOARD.opening.colour;

// Every lamp of a stretch cycling through the same hue together, picofx's rainbow, which
// Rainbow plays only on a single lamp. It sits beside Rainbow in the gallery
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

// Scanner and Chase light each output as the light reaches it and let it go slowly, a fade
// split into its rise and its fall, as one fade both ways rises too slowly to reach full before
// the light moves on. The fall is the Trail the light leaves, a slider of its own, so Speed sets
// only how fast it moves: Scanner's runs long, as sweep_trail.py has it, and Chase's short, a
// runway light's
//
// The rise is sweep_trail.py's 0.05s in proportion, that being tuned to its one speed and
// spacing, as a fixed rise leaves a fast scanner's head short of full. There the
// head covers each light for about a third of a second, a sweep reaching extent lights either
// side and crossing length - 1 of them a cycle, so the rise is 15% of however long it covers
// one. A chase's flash lasts 0.2s at speed 1, window 0.4 at duty 0.5, so its rise is a quarter
// of the flash at whatever speed
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

// On and off at a pace, lit for a share of each beat, picofx's blink. Given several colours
// it blinks through them in turn, one a beat, which is rgb_blink (see 06_blink.js)
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

// Lights taking turns in a repeating pattern, a cinema sign's marquee, picofx's blink_wave.
// Its setting is how far apart the lit ones are, every second light to every sixth, and one
// of each group is lit at a time
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

// Red, red and amber, green, amber on three lamps, as Pelican crossing takes its five: the
// first three playing lights, any beyond them told to stay dark. The intervals keep a real
// signal's proportions, the pace scaling them all
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

// Each slider is named for what it sets, short. The signals' Fade writes ease, a fade that
// slows as it arrives, and its tip says so, the file having a fade of its own that crosses
// evenly
var SETTING_NAMES = {"Rainbow": "Spread", "Wave": "Spread", "Campfire": "Intensity",
                     "Pelican crossing": "Fade"};
LOOKS.forEach(function (look) {
  if (SETTING_NAMES[look.name]) look.mood = SETTING_NAMES[look.name];
});

// A signal's timings are its own sliders, one for each part of its sequence in seconds, each
// starting at a real signal's. They are the stretch's timings, which the lines read through the stretch being written or played
// Each part is its setting, its name, where it starts and the slider's two ends, in seconds
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

// The stretch whose lines are being written or played, for the looks that read more of it
// than a look is handed
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

// What a look lights with its stretch as the one being played
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

// Rainbow's and Wave's Spread is the length of one pass of the wave in lights, longer to the
// right as every slider's setting rises to the right. It stops at whole lights, from about a little over half the stretch to twice it
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

// Campfire's intensity is how far its flicker dips, the effect's own brightness held at full so
// the stretch's Brightness is the one that sets how bright it is. Its pace is the model's
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

// ---- the strips ---------------------------------------------------------------------------
// A strip is a run like the outputs: cut into stretches, each playing its own look, and
// cut per scene as everything else is. What it does not have is wiring, an output's three
// channels being the only thing that breaks out, so it takes the run model and leaves the
// breaking out alone.

// The board's strips. A strip's order is the one it takes its colours in, empty for the board's
// own, and it is there as the board describes it until added or removed while the board is edited.
// A strip the description gives a brightness takes that after its length in place of an order,
// the description's being the board's own, and one it says takes other strips takes their terminals
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

// The strip run a file names, or null where this board has no strip by that name
export function stripNamed(name) {
  var lower = name.toLowerCase();
  return runs.filter(function (run) { return run.strip && run.name === lower; })[0] || null;
}

// The strip's entry, which a fresh run is made from, and the run itself, given the same values
export function stripSet(run, values) {
  var one = STRIPS.filter(function (strip) { return strip.id === run.id; })[0];
  Object.keys(values).forEach(function (key) {
    one[key] = values[key];
    run[key] = values[key];
  });
}

// A stretch of a strip is a range of its lights, and the whole of it is the bare name
export function stripSelector(run, section) {
  if (section.from === 0 && section.to === run.lamps.length - 1) return run.name;
  return run.name + (section.from === section.to
    ? String(section.from + 1)
    : (section.from + 1) + "-" + (section.to + 1));
}

var GLASS_OUT = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
                "<path d='M5 7.2 L9.4 7.2'/>";

var GLASS_IN = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
               "<path d='M5 7.2 L9.4 7.2 M7.2 5 L7.2 9.4'/>";

function stripZoomAndSteps(row, run) {
  var space = document.createElement("span");
  space.className = "gap";
  row.appendChild(space);
  if (zooms(run)) {
    row.appendChild(iconButton(GLASS_OUT, "Zoom out", zoomOf(run) <= 1.001,
                               function () {
                                 zoomTo(run, zoomOf(run) / 1.6, middleOfView(run));
                               }));
    var said = document.createElement("span");
    said.className = "howfar";
    said.textContent = Math.round(zoomOf(run) * 100) + "%";
    row.appendChild(said);
    row.appendChild(iconButton(GLASS_IN, "Zoom in", zoomOf(run) >= 23.9,
                               function () {
                                 zoomTo(run, zoomOf(run) * 1.6, middleOfView(run));
                               }));
  }
  row.appendChild(iconButton(BACK, "Undo", !(run.was && run.was.length),
                             function () { stepBack(run); }));
  row.appendChild(iconButton(ON, "Redo", !(run.undone && run.undone.length),
                             function () { stepOn(run); }));
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
  // The longest run in wired order ending at each lamp, and starting at it
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
  // A lamp is in every longest run when it is on one, and no other lamp on one could take
  // its step in the run
  var atStep = {};
  upTo.forEach(function (steps, place) {
    if (steps + onFrom[place] - 1 === longest) atStep[steps] = (atStep[steps] || 0) + 1;
  });
  return side.order.filter(function (lamp, place) {
    var onOne = upTo[place] + onFrom[place] - 1 === longest;
    return !(onOne && atStep[upTo[place]] === 1);
  });
}

// ---- how many lights are on one ------------------------------------------------------------
// The chip the drawing keeps its count in. A strip's length is a fact about the
// board, so it is the same in every scene and changing it here changes it in all of them

// A strip's length as the chip takes it. One LED is a strip autofx accepts
var STRIP_FEWEST = 1;
var STRIP_MOST = 300;

// The orders a strip can take its colours in, as the file writes them after its length,
// the board's own being written as nothing
var STRIP_ORDERS = [["", "GRB (most strips)"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

// The brightnesses a strip with one of its own can be given, as the file writes them after its
// length, the board's own being written as nothing
var STRIP_BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

function stripPercent(brightness) { return Math.round(brightness * 100) + "%"; }

// What follows a strip's length on the board line, its brightness or its colour order, as the
// choice on its chip
function stripChipChoice(run) {
  var choice = document.createElement("select");
  if (run.made === null) {
    STRIP_ORDERS.forEach(function (pair) {
      var option = document.createElement("option");
      option.value = pair[0];
      option.textContent = pair[1];
      if ((run.order || "") === pair[0]) option.selected = true;
      choice.appendChild(option);
    });
    choice.title = "The strip's colour order. Change it if red shows as another colour";
    choice.onchange = function () {
      stripSet(run, {order: choice.value});
      draw();
    };
    return choice;
  }
  // A brightness read from a file stays offered, though the list does not hold it
  var offered = STRIP_BRIGHTNESSES.indexOf(run.brightness) < 0 ?
    STRIP_BRIGHTNESSES.concat([run.brightness]).sort(function (a, b) { return a - b; }) :
    STRIP_BRIGHTNESSES;
  offered.forEach(function (brightness) {
    var option = document.createElement("option");
    option.value = brightness;
    option.textContent = stripPercent(brightness) + (brightness === run.made ? " (default)" : "");
    if (brightness === run.brightness) option.selected = true;
    choice.appendChild(option);
  });
  choice.title = "Overall strip brightness, applied on top of each stretch's level";
  choice.onchange = function () {
    stripSet(run, {brightness: Number(choice.value)});
    draw();
  };
  return choice;
}

// The same as words, where the chip cannot be changed
export function stripChipShown(run) {
  return run.made === null ? (run.order || "grb").toUpperCase()
                           : stripPercent(run.brightness) + " brightness";
}

// The same as the file writes it after the length, nothing for the board's own
export function stripLengthTail(run) {
  if (run.made === null) return run.order ? "|" + run.order : "";
  return run.brightness === run.made ? "" : "|" + stripPercent(run.brightness);
}

// The same read back from the file, as the values to set, or null for one the page does not
// offer, which stays as written for the board to answer
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

// A strip's chip, its length and its order to set, which the board's setup shows while it is on
export function renderStripChip(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var chip = document.createElement("div");
  chip.className = "chip strip";
  chip.appendChild(document.createTextNode("Strip"));
  var count = document.createElement("input");
  count.type = "number";
  count.min = STRIP_FEWEST;
  count.max = STRIP_MOST;
  count.value = run.leds;
  count.onchange = function () {
    var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST, parseInt(count.value, 10) ||
                                                           STRIP_FEWEST));
    if (want === run.leds) return;
    stripSet(run, {leds: want});
    settle();
    draw();
  };
  chip.appendChild(count);
  var unit = document.createElement("small");
  unit.textContent = "LEDs";
  chip.appendChild(unit);
  chip.appendChild(stripChipChoice(run));
  box.appendChild(chip);
  var says = document.createElement("span");
  says.className = "says";
  says.textContent = "shared by every scene";
  box.appendChild(says);
}

// ---- zooming a strip's bar --------------------------------------------------------------------
// The drawing finds a bar by which of two runs it is for. Here a bar is found by the strip's
// own id, so these stand in for those two

// ---- joining them to the page below -----------------------------------------------------

// Each strip has a panel after the outputs', in the board's order, and its board box takes the
// strip's own colour
(function () {
  var colours = document.createElement("style");
  var after = document.getElementById("outPanel");
  BOARD.strips.forEach(function (strip) {
    var id = strip.name;
    var panel = document.createElement("details");
    panel.className = "panel strip";
    panel.id = id + "Panel";
    panel.open = true;
    panel.innerHTML = "<summary>" + strip.label.charAt(0).toUpperCase() + strip.label.slice(1) +
                      "<span class='says'>" + strip.says + "</span></summary>" +
                      "<div class='leds' id='" + id + "Leds'></div>" +
                      "<div class='head' id='" + id + "Cut'></div>" +
                      "<div id='" + id + "Bar'></div>" +
                      "<div id='" + id + "Chosen'></div>";
    after.parentNode.insertBefore(panel, after.nextSibling);
    after = panel;
    colours.textContent += ".boardchip." + id + "{background:" + strip.colour + "}\n";
  });
  document.head.appendChild(colours);
}());

// The strips are runs of the page below from here on. Each scene keeps its own cutting of
// them in its body, which captures every run
runs = runs.concat(STRIPS.map(stripRun));
settle();

// ---- drawing the page -------------------------------------------------------------------

drawSteps.after.push(function () {
  // The outputs' settings are for the stretch being worked on, which while a strip is picked
  // is under that strip instead
  if (active.strip) {
    document.getElementById("outChosen").textContent = "";
  }
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    renderLeds(run.id + "Leds", run);
    // The count of stretches, then the zoom and the steps beside it, all the drawing's own, so
    // the bar scrolls when zoomed in
    renderCutting(run.id + "Cut", run);
    stripZoomAndSteps(document.getElementById(run.id + "Cut"), run);
    renderStretches(run.id + "Bar", run);
    document.getElementById(run.id + "Chosen").textContent = "";
    if (run === active) {
      renderEditor(run.id + "Chosen", run);
    }
  });
  // The page painted what it drew before these were made, so a fresh bead would hold the
  // default fill until the next frame and show black
  paintAll();
});

// ---- what an output's lamps play when its wiring changes ----------------------------------
// The new lamps are carried what the output played, both ways: broken out into three mono
// lamps, and three put back as one colour lamp. The wiring change gives them a stretch of
// their own, starting dark, and this fills it where the look plays on them

// The stretch an output's lamps played. Put back from three that differ, it is the one
// most of them played, and the first channel's where all three differ
function playedBy(out) {
  var lamps = [];
  runs.forEach(function (run) {
    run.lamps.forEach(function (lamp, at) {
      if (lamp.out === out) lamps.push({channel: lamp.channel || 0,
                                        section: run.sections[sectionAt(run, at)]});
    });
  });
  // A channel can be dragged apart from its two, so they are counted in channel order
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

// The nearest look for lamps a look cannot play on. Rainbow's colours travel along the
// lamps, and on mono lamps the nearest is brightness travelling
var STAND_INS = {"Rainbow": "Wave"};

// What each output was carried from where a stand-in took its place, so putting the
// output back gives the look it had. Held by output, not on the stretch, since every
// settle makes the stretches afresh, and captured with the scene
function carriedFrom() { return carried; }

// The stand-in a stretch is playing, and what for, where it is one
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
          // Back from a stand-in, it plays what it was carried from, at the pace it was
          // given since
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

// ---- choosing a colour ---------------------------------------------------------------------
// Under the stretch it is for, twelve swatches and a custom one
// that opens a hue and saturation field with a hex box beside it. Brightness is not in
// any of it. A swatch is written as its word, since every one is now a word autofx names,
// and the field writes hex.

// The words the file names and their values, which are picofx's own. A swatch is drawn in
// its true value, the round trip from a written word to a swatch being the point of them
export var WORDS = {
  red: [255, 0, 0], orange: [255, 128, 0], yellow: [255, 255, 0], green: [0, 255, 0],
  cyan: [0, 255, 255], blue: [0, 0, 255], purple: [128, 0, 255], magenta: [255, 0, 255],
  pink: [255, 128, 128], warm: [255, 192, 96], white: [255, 255, 255],
  cool: [96, 192, 255], black: [0, 0, 0]
};

// Eight hues thirty or sixty degrees apart, then the white axis with pink on it. Black is
// left out, since brightness and Nothing say a lamp is off better
export var SWATCHES = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta",
                "pink", "warm", "white", "cool"];

// The swatches a stretch offers. A blink through several colours offers black too, as a turn
// with the light off
export function swatchesFor(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look === BLINK && section.blinks && section.blinks.colours.length > 1 &&
      first && first.colour) return ["black"].concat(SWATCHES);
  return SWATCHES;
}

export function rgbInk(rgb) { return "rgb(" + rgb.join(",") + ")"; }

// The word for a colour where it is one of the swatches, else null
export function wordFor(hex) {
  var lower = hex.replace("#", "").toLowerCase();
  return SWATCHES.filter(function (name) { return hexOf(WORDS[name]) === lower; })[0] || null;
}

// Looks whose colour setting steps through sets of several colours, not one: Party plays
// three at once, and its setting picks which three. They keep their setting and their own
// colours, one chosen colour in all three places being no longer Party
var SET_LOOKS = ["Party"];

// Base effects written in one fixed colour, which take a colour beside their own settings
var FIXED_COLOUR_LOOKS = ["Wave", "Blink", "Marquee", "Scanner", "Chase"];

// Whether a look is given its colour here. Solid takes one already, the looks whose second
// slider stepped a table of tones take one instead of that slider, and the fixed colour
// ones take one as well
export function takesColour(look) {
  if (!look || SET_LOOKS.indexOf(look.name) >= 0) return false;
  return look.solid || look.mood === "Colour" || FIXED_COLOUR_LOOKS.indexOf(look.name) >= 0;
}

// ---- what a stretch is drawn in wherever it is shown in small -------------------------------
// The colours it plays, never only the colour of its look's card: three Solid stretches
// set red, blue and yellow were all drawn in Solid's card green. They are read from the
// lines the stretch writes, so they cannot disagree with the file: one colour is drawn
// whole, several across the stretch's width, and a look that writes none, as Rainbow does,
// in its card's colours. A mono stretch is drawn in the warm white its lamps give. The bars
// under the lamps and the tabs' swatches all ask here
var MONO_WASH = "#f3c98b";

// Each colour a stretch's lines name, in the order they name them, once each. A blink through
// several colours names them all
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

// A look given a colour is drawn in it, and one playing several, as Party does, in those.
// Any other look is drawn in its card's colours, one colour in its line being no picture
// of what it plays: Campfire's single flame colour is not the flicker its card shows
export function stretchWash(look, section, run, mono) {
  if (mono) return MONO_WASH;
  var inks = run && section ? coloursWritten(look, section, run) : [];
  if (!takesColour(look) && inks.length < 2) inks = look.strip || [];
  if (inks.length > 1) return "linear-gradient(90deg," + inks.join(",") + ")";
  return inks[0] || "rgba(138,131,120,0.16)";
}

// ---- the colour a look starts with -------------------------------------------------------------
// A look given a stretch starts in its own colour, the one its tone setting gave at the
// stretch's setting, and not whatever the stretch was left holding, which left every look
// starting orange. Solid, having no tone setting, starts in SOLID_COLOUR
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

// The gallery's cards play each look at middling settings, which carry one colour for all of
// them. A card of a look given a colour plays in its look's own, the one a stretch given it
// starts in, kept here by look
var cardSettings = {};

// The second setting a look starts at, on its card and on a stretch given it, where middling
// does not suit it. Solid starts at full brightness, Colour cycle at full saturation, Colour
// steps at picofx's six, and Pelican crossing's lamps fade in about a tenth of a second, as a
// crossing's do
export var START_MOODS = {"Solid": 1, "Colour cycle": 1, "Colour steps": 1 / 3,
                   "Pelican crossing": 0.1, "Traffic light": 0.1, "Marquee": 0.25};

// Solid's own colour, which a stretch given it starts in and its card shows, still and at full
// brightness. Stepping through the swatches, the card read as Colour steps, and its palette
// mark says a colour is chosen
var SOLID_COLOUR = "#" + hexOf(WORDS.yellow);

// What a look lights, a card's middling settings made its own
function cardLit(look, holder, t, slot, count, sim) {
  if (holder === MIDDLING && look && look.solid) {
    // Drawn in the swatch's value, the word it writes taking the lamps' softer shade
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

// The looks shaped to separate lamps. They play on outputs, mono lamps and strips
var BANKED_LOOKS = ["Emergency", "Traffic light", "Pelican crossing"];

// The lamps a signal is built from, which a strip's stretch is cut into blocks of
var SIGNAL_LAMPS = {"Traffic light": 3, "Pelican crossing": 5};

export function isBanked(look) {
  return !!look && BANKED_LOOKS.indexOf(look.name) >= 0;
}

// The lines a look writes, a banked look on a run or a strip dealing its banks out along it
function bankedLines(look, target, pace, mood, colour) {
  if (!(target.kind === "run" || target.strip) || !isBanked(look) || target.count === 1)
    return lookLines(look, target, pace, mood, colour);
  return stripLines(look, target, pace, mood);
}

// On a strip, Emergency deals out the stretch's lights as it does outputs. A signal takes a
// set number of lamps, five for a crossing and three for a traffic light, so the stretch is
// cut into that many blocks, the longer ones first, and one entry is written per place
// within a block: its lights, one from each block, take the signal's parts in order, and a
// block too short for a place drops off the end
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

// The looks the board opens playing start in their own colours too
[outs, mono].forEach(function (run) {
  run.sections.forEach(function (section) {
    var look = lookNamed(section.look);
    if (look) startColour(run, section, look);
  });
});

// A hue at full value, brought toward white by how far the saturation is from full
export function fieldColour(hue, sat) {
  return hueRgb(hue).map(function (v) { return Math.round(v + (255 - v) * (1 - sat)); });
}

// ---- how bright a stretch is -------------------------------------------------------------
// Every look has a brightness, the first slider in the list, written only below full. A look
// given a custom colour writes it in that colour's hex, dimmed, as a screen's background is.
// Any other, a swatch's word included, writes it as the stretch's level=, which scales
// whatever the look plays
export var FAINTEST = 0.05;

export function atBrightness(hex, level) {
  if (!(level < 1)) return hex;
  return "#" + hexOf(hexRgb(hex).map(function (v) { return Math.round(v * level); }));
}

// Whether this stretch is given a custom colour here, so its brightness goes into the hex
function coloursItself(run, section, look) {
  var first = run.lamps[section.from];
  var custom = section.custom || !wordFor(section.colour || "#ffffff");
  return takesColour(look) && !!first && first.colour && custom;
}

// What one stretch writes, at its brightness and with its typed values. A blink through several
// colours is written as its list, and a custom colour carries its brightness in its hex
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

// The lines a look writes for a target, as the board will play them
export function linesFor(look, target, pace, mood, colour) {
  var lines;
  if (look && look.solid) {
    // Solid is written at full, its brightness being the stretch's own
    lines = bankedLines(look, target, pace, 1, colour).map(function (line) {
      return line.replace(/ brightness=1(?=\s|$)/, "");
    });
  } else {
    lines = bankedLines(look, target, pace, mood, colour);
  }

  // The colour it was given. Solid already writes it. The looks whose slider stepped tones
  // write a tone, so the colour they wrote is replaced with the chosen one, as a word where it
  // is a swatch and as hex from the field
  if (takesColour(look) && target.colour && colour) {
    var said = wordFor(colour) || colour.replace("#", "").toLowerCase();
    lines = lines.map(function (line) { return line.replace(/colour=[^\s:]+/, "colour=" + said); });
  }

  // A wave is written with its speed below zero, so it goes forward as every look does
  lines = lines.map(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    if (WAVES.indexOf(effect) < 0) return line;
    return line.replace(/ speed=(\d)/, " speed=-$1");
  });

  // The values typed for the stretch whose lines are being written
  if (!exactNow) return lines;
  Object.keys(exactNow).forEach(function (slider) {
    var typed = exactNow[slider];
    if (!typed) return;
    // A trail is the fall of a split fade, so a typed one replaces the part after its bar
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

// ---- which way a stretch runs --------------------------------------------------------------
// A stretch can start from its far end, which writes its lamps counting down. Only a look
// that differs from lamp to lamp can show it, so for the rest the toggle is greyed and the
// stretch is written as it runs

// The effects that give each lamp of an entry its place, and a length= does the same
var TRAVELLING = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence", "sweep",
                  "binary_counter", "pelican_crossing", "traffic_light", "clock"];

// picofx's wave effects move their pattern toward the start of the lights they are given as
// time runs, where a sweep, a counter and the signals begin at the start and go on from it.
// So that a stretch goes forward the same way whatever its look, the waves are written
// with their speed below zero, which the manual allows, and Reverse counts the lights down
var WAVES = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence"];

// Party flashes its three sets a third of a beat apart, and the phases it was given, 0, 0.33
// and 0.67, lit the first set, then the third, then the second: a step back toward the start
// each time. Swapped, its sets light in order, away from the start as every look goes
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

// Whether reversing this stretch would change what it plays, judged from its lines as written
export function runsAWay(look, target, section) {
  if (!look || target.count < 2) return false;
  var lines = linesFor(look, target, section.pace, section.mood, section.colour);
  // A look that deals the stretch out, as Party and Emergency do, deals from the start
  if (lines.length > 1) return true;
  return lines.some(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    return TRAVELLING.indexOf(effect) >= 0 || / length=/.test(line);
  });
}

// How many whole outputs from here run counting down with their channels blue, green, red,
// which a descending range with .* writes as one item
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

// Outputs named from the far end, a run counting down written as one range
function nameBackwards(lamps) {
  var items = [];
  var at = 0;
  while (at < lamps.length) {
    // Two or more whole mono outputs counting down, since one alone as .* would run r, g, b
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

// What a stretch plays on, counting its lights down where it starts from its far end and its
// look shows which way it runs
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

// What a look lights at slot of count lamps playing, as the board will play it: with the
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

// ---- what heads a stretch's settings ------------------------------------------------------------
// The look's name, the panel being its settings, then where it plays in words: outputs
// 1 to 7, LEDs 11 to 20 of the left strip, output 3's red and green. The file's selector is the
// file view's to show, and whether the lights are colour or mono the tab's

// A list said as English does: one, two and three
export function spoken(items) {
  if (items.length < 2) return items.join("");
  return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
}

// Numbers as English says them: three or more climbing or falling by one are "a to b", and the
// rest are listed, so 1-7 is "1 to 7" and 5,6 is "5 and 6"
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

// A reversed stretch is said in the order it plays, from its far end, as the file writes it
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
  // Whole outputs and mono ones by number, an output with no number by name, and a broken-out
  // output's channels together, each group in the order they play
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

