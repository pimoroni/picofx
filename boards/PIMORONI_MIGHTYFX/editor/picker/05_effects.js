
// A card is tapped onto a stretch, with no colour and mono tabs over the cards
tabsWhere = "none";
carryLooks = false;

// The board opens as it ships, every output one colour lamp, and the outputs whole and
// playing Rainbow. The strips play nothing, what is wired to them being unknown
var OPENING_LOOK = "Rainbow";

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

// Emergency's second setting is the flashes in each burst, one to five, three in the
// middle. It was red and blue to amber, which is a choice of two and not a scale
(function (emergency) {
  function flashes(mood) { return Math.round(lerp(1, 5, mood)); }
  emergency.mood = "Flashes";
  emergency.detents = 5;
  emergency.entries = function (target, pace, mood) {
    var flash = ": flash speed=" + lerp(0.6, 2.5, pace) + " flashes=" + flashes(mood) +
                " window=0.5";
    var playing = target.playing;
    var half = playing.length === 1 ? 1 : Math.floor(playing.length / 2);
    var lines = [nameSet(target, playing.slice(0, half)) + " colour=red" + flash];
    if (playing.length > 1) {
      lines.push(nameSet(target, playing.slice(playing.length - half)) + " colour=blue" +
                 flash + " phase=0.5");
      var gap = playing.slice(half, playing.length - half);
      if (gap.length) lines.push(nameSet(target, gap) + ": none");
    }
    return lines;
  };
  emergency.alone = function (target, pace, mood) {
    return [target.selector + " colour=red: flash speed=" + lerp(0.6, 2.5, pace) +
            " flashes=" + flashes(mood) + " window=0.5"];
  };
}(lookNamed("Emergency")));

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

// The preview follows a split fade or ease as the board does, its rise going up and its fall
// coming down. One number is both, as before
curved = function (sim, given, channel) {
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
};

// On and off at a pace, lit for a share of each beat, picofx's blink. Given several colours
// it blinks through them in turn, one a beat, which is rgb_blink (see _blink_colours.js)
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
var SIGNAL_TIMINGS = {
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

function withSection(section, write) {
  var had = sectionNow;
  sectionNow = section;
  try {
    return write();
  } finally {
    sectionNow = had;
  }
}

var oneSignalSection = sectionLines;

sectionLines = function (run, section, look) {
  return withSection(section, function () { return oneSignalSection(run, section, look); });
};

var oneSignalPlay = livePlay;

livePlay = function (look, holder, t, slot, count, sim) {
  return withSection(holder && holder !== MIDDLING ? holder : null, function () {
    return oneSignalPlay(look, holder, t, slot, count, sim);
  });
};

function timingOf(name, key) {
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

// Party's slider picks one of five sets of three colours, so it is its Palette, stopping at each
lookNamed("Party").mood = "Palette";
lookNamed("Party").detents = 5;

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

wiring = wiring.map(function () { return {broken: false}; });
order = wiring.map(function (one, out) { return {out: out, channel: null}; });
settle();
outs.sections = [blank(0, outs.lamps.length - 1)];
outs.sections[0].look = OPENING_LOOK;
settle();

// ---- the strips ---------------------------------------------------------------------------
// A strip is a run like the outputs: cut into stretches, each playing its own look, and
// cut per scene as everything else is. What it does not have is wiring, an output's three
// channels being the only thing that breaks out, so it takes the run model and leaves the
// breaking out alone.

// A strip's order is the one it takes its colours in, empty for the board's own, and it is
// fitted until removed while the board is edited
var STRIPS = [
  {id: "stripl", name: "stripl", label: "the left strip", leds: 30, order: "", there: true},
  {id: "stripr", name: "stripr", label: "the right strip", leds: 18, order: "", there: true}
];

function stripRun(one) {
  var run = Run(one.name, false);
  run.strip = true;
  run.id = one.id;
  run.label = one.label;
  run.leds = one.leds;
  run.order = one.order;
  run.there = one.there;
  return run;
}

// ---- what the page below has to be told about them -------------------------------------

var oneLampsFor = lampsFor;

lampsFor = function (run) {
  if (!run.strip) return oneLampsFor(run);
  var found = [];
  for (var i = 0; i < run.leds; i++) found.push({colour: true, at: i, run: run});
  // The drawing asks a run how many lights it has under this name
  run.count = run.leds;
  return found;
};

// A stretch is held to its lamps by name across a change to the wiring, and a strip's
// lamps have no output to be named by, so they are named by the strip and their place
var oneLampKey = lampKey;

lampKey = function (lamp) {
  return lamp.run ? lamp.run.id + ":" + lamp.at : oneLampKey(lamp);
};

// A stretch of a strip is a range of its lights, and the whole of it is the bare name
function stripSelector(run, section) {
  if (section.from === 0 && section.to === run.lamps.length - 1) return run.name;
  return run.name + (section.from === section.to
    ? String(section.from + 1)
    : (section.from + 1) + "-" + (section.to + 1));
}

var oneTargetFor = targetFor;

targetFor = function (run, section) {
  if (!run.strip) return oneTargetFor(run, section);
  // The stretch's lights by number, for the looks that deal them out themselves
  var lights = [];
  for (var at = section.from; at <= section.to; at++) lights.push(at + 1);
  return {kind: "run", id: run.id, name: run.name, label: run.label, colour: true,
          selector: stripSelector(run, section), count: widthOf(section), playing: [],
          lights: lights};
};

var oneSelectorFor = selectorFor;

selectorFor = function (lamp) {
  if (!lamp.run) return oneSelectorFor(lamp);
  return lamp.run.name + (lamp.at + 1);
};

var oneShortName = shortName;

shortName = function (lamp) {
  return lamp.run ? String(lamp.at + 1) : oneShortName(lamp);
};

// ---- drawing one -----------------------------------------------------------------------
// Beads on a wire that runs between them, a bead at the lead in and a ring at the tail, and a whole stretch taking the click rather than only the lights in it

var SVG = "http://www.w3.org/2000/svg";

function tag(name, attrs) {
  var made = document.createElementNS(SVG, name);
  Object.keys(attrs).forEach(function (key) { made.setAttribute(key, attrs[key]); });
  return made;
}

function spanRows(section, place) {
  var rows = {};
  for (var n = section.from; n <= section.to; n++) {
    var spot = place(n);
    var row = rows[spot.row] || (rows[spot.row] = {y: spot.y, low: spot.x, high: spot.x});
    row.low = Math.min(row.low, spot.x);
    row.high = Math.max(row.high, spot.x);
  }
  return Object.keys(rows).map(function (which) { return rows[which]; });
}

function wireRun(run) {
  var SIZE = 11, GAP = 2.5, PER_ROW = 30;
  var EDGE = 10, TAIL = 6;
  var rows = Math.ceil(run.count / PER_ROW);
  var across = Math.min(run.count, PER_ROW);
  var wide = across * SIZE + (across - 1) * GAP;
  var pitch = SIZE + GAP * 2;
  var high = rows * pitch - GAP * 2 + 2;
  var full = EDGE * 2 + wide;
  // The ring around a picked stretch stands outside the lights it goes round, so the
  // drawing is given a margin rather than shaving the ring off at the top and bottom
  var ROOM = 4;

  function place(i) {
    var row = Math.floor(i / PER_ROW);
    var col = i % PER_ROW;
    if (row % 2) col = PER_ROW - 1 - col;
    return {x: EDGE + col * (SIZE + GAP), y: row * pitch + 1, row: row};
  }
  function middleOf(row) { return row * pitch + 1 + SIZE / 2; }

  var svg = tag("svg", {viewBox: (-ROOM) + " " + (-ROOM) + " " + (full + ROOM * 2) +
                                 " " + (high + ROOM * 2),
                        preserveAspectRatio: "xMinYMid meet"});

  for (var r = 0; r < rows - 1; r++) {
    var atRight = r % 2 === 0;
    var x = atRight ? EDGE + wide : EDGE;
    var bulge = atRight ? x + EDGE : x - EDGE;
    svg.appendChild(tag("path", {
      d: "M" + x + " " + middleOf(r) + " C" + bulge + " " + middleOf(r) + " " +
         bulge + " " + middleOf(r + 1) + " " + x + " " + middleOf(r + 1),
      fill: "none", stroke: "#c9c3b9", "stroke-width": 1.8}));
  }
  for (var row = 0; row < rows; row++) {
    var ends = [];
    for (var n = row * PER_ROW; n < Math.min(run.count, (row + 1) * PER_ROW); n++) {
      ends.push(place(n).x);
    }
    if (!ends.length) continue;
    svg.appendChild(tag("path", {
      d: "M" + Math.min.apply(null, ends) + " " + middleOf(row) +
         " L" + (Math.max.apply(null, ends) + SIZE) + " " + middleOf(row),
      stroke: "#c9c3b9", "stroke-width": 1.8, fill: "none"}));
  }

  var first = place(0);
  svg.appendChild(tag("path", {d: "M0 " + middleOf(0) + " L" + first.x + " " + middleOf(0),
                               stroke: "#c9c3b9", "stroke-width": 1.8, fill: "none"}));
  svg.appendChild(tag("rect", {x: 0, y: middleOf(0) - 3.4, width: 4.6, height: 6.8,
                               rx: 1.4, fill: "#8f8a81"}));

  var beads = [];
  for (var i = 0; i < run.count; i++) {
    var spot = place(i);
    var bead = tag("rect", {x: spot.x, y: spot.y, width: SIZE, height: SIZE, rx: 2.4,
                            stroke: "rgba(0,0,0,.12)", "stroke-width": 0.6});
    svg.appendChild(bead);
    beads.push(bead);
  }

  // A stretch is one thing to point at, so the whole span it covers takes the click and
  // not only the beads in it. A stretch that wraps takes one span per row it is on
  run.sections.forEach(function (section, at) {
    spanRows(section, place).forEach(function (row) {
      var plate = tag("rect", {"class": "span", x: row.low - GAP / 2, y: row.y - 2.2,
                               width: row.high - row.low + SIZE + GAP,
                               height: SIZE + 4.4, rx: 4});
      plate.onclick = function () { pick(run, at); draw(); };
      takesDrop(plate, run, at, "span");
      var says = tag("title", {});
      says.textContent = "lights " + (section.from + 1) + " to " + (section.to + 1) +
                         ", playing " +
                         (lookNamed(section.look) || {name: "Nothing"}).name;
      plate.appendChild(says);
      svg.appendChild(plate);
    });
  });

  // The stretch being edited, ringed on the run so the bar and the preview say the same
  // thing about what is being worked on
  var picked = run.sections[run.picked];
  if (picked && isPicked(run, run.picked)) {
    spanRows(picked, place).forEach(function (row) {
      svg.appendChild(tag("rect", {"class": "ringed", x: row.low - GAP / 2, y: row.y - 2.2,
                                   width: row.high - row.low + SIZE + GAP,
                                   height: SIZE + 4.4, rx: 4}));
    });
  }

  // No cut marks here. The run is the preview window and the bar is where the cutting
  // is done, so the run is left saying only what the lights are doing

  var last = place(run.count - 1);
  var goingRight = last.row % 2 === 0;
  var from = goingRight ? last.x + SIZE : last.x;
  var to = from + (goingRight ? TAIL : -TAIL);
  svg.appendChild(tag("path", {d: "M" + from + " " + middleOf(last.row) + " L" + to +
                                  " " + middleOf(last.row),
                               stroke: "#c9c3b9", "stroke-width": 1.8, fill: "none"}));
  svg.appendChild(tag("circle", {cx: to, cy: middleOf(last.row), r: 2.4, fill: "#fff",
                                 stroke: "#a9a49b", "stroke-width": 1.6}));

  return {svg: svg, paint: function (all) {
    for (var n = 0; n < beads.length; n++) {
      var one = all[n] || {level: 0, ink: "#e4e0d9"};
      beads[n].setAttribute("fill", one.nothing ? "#e4e0d9" : inkAt(one));
    }
  }};
}

function washOf(look, mono) {
  var brightest = null;
  var most = -1;
  (look.strip || []).forEach(function (colour) {
    var lit = luminance(colour);
    if (lit > most) { most = lit; brightest = colour; }
  });
  if (!brightest) return "rgba(138,131,120,0.16)";
  // A mono lamp's colour comes back already worked out, so both forms are read here
  var said = mono ? asMono(brightest, peakOf(look)) : brightest;
  var parts;
  if (said.charAt(0) === "#") {
    parts = [said.slice(1, 3), said.slice(3, 5), said.slice(5, 7)].map(function (pair) {
      return parseInt(pair, 16);
    });
  } else {
    parts = said.replace(/[^0-9,]/g, "").split(",").map(Number);
  }
  return "rgba(" + parts.join(",") + ",0.22)";
}

var GLASS_OUT = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
                "<path d='M5 7.2 L9.4 7.2'/>";

var GLASS_IN = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
               "<path d='M5 7.2 L9.4 7.2 M7.2 5 L7.2 9.4'/>";

function zoomOf(run) { return run.zoom || 1; }

function divide(run, ways) {
  var section = run.sections[run.picked];
  if (!section || ways < 2 || widthOf(section) < ways) return;
  remember(run);
  var made = [];
  var edges = [];
  for (var i = 0; i <= ways; i++) {
    edges.push(section.from + Math.round(widthOf(section) * i / ways));
  }
  for (var g = 0; g < ways; g++) {
    made.push({from: edges[g], to: edges[g + 1] - 1, look: section.look,
               pace: section.pace, mood: section.mood, colour: section.colour});
  }
  run.sections.splice.apply(run.sections, [run.picked, 1].concat(made));
  draw();
}

function fill(run, many) {
  var pattern = run.sections.slice(run.picked, run.picked + many);
  if (!pattern.length) return;
  remember(run);
  var kept = run.sections.slice(0, run.picked + many);
  var at = pattern[pattern.length - 1].to + 1;
  var i = 0;
  while (at < run.count) {
    var from = pattern[i % pattern.length];
    var wide = widthOf(from);
    kept.push({from: at, to: Math.min(run.count - 1, at + wide - 1), look: from.look,
               pace: from.pace, mood: from.mood, colour: from.colour});
    at += wide;
    i++;
  }
  run.sections = kept;
  draw();
}

function renderStripBar(where, run) {
  var box = document.getElementById(where);
  var was = box.querySelector(".scroller");
  var kept = was ? was.scrollLeft : run.scrolled || 0;
  box.textContent = "";

  // Zoomed in, the bar is wider than the room it has and scrolls inside it. That is
  // what puts a single light of a long strip within reach of a pointer
  var scroller = document.createElement("div");
  scroller.className = "scroller";
  var bar = document.createElement("div");
  bar.className = "bar";
  bar.style.width = (zoomOf(run) * 100) + "%";

  run.sections.forEach(function (section, at) {
    var wide = widthOf(section);
    var cell = document.createElement("button");
    cell.className = "sec" + (isPicked(run, at) ? " picked" : "") +
                     (wide * 40 < run.count * 8 ? " narrow" : "");
    cell.style.flex = wide + " 1 0";
    cell.title = "lights " + (section.from + 1) + " to " + (section.to + 1);

    // The bar says where the cuts are and what each stretch was given. Showing the
    // effect here as well would be the same picture twice and, now the lights move,
    // a still palette does not stand for one anyway. So a stretch is washed in a
    // colour of its look and named, and the run below is where it is watched
    var look = lookNamed(section.look);
    var wash = document.createElement("span");
    wash.className = "lit" + (look ? "" : " nothing");
    if (look) wash.style.background = washOf(look, run.mono, section, run);
    cell.appendChild(wash);

    var says = document.createElement("span");
    says.className = "says";
    says.innerHTML = (look ? look.name : "Nothing") + " <em>" + wide + "</em>";
    cell.appendChild(says);

    // Where this stretch could be cut, one click to a place between two lights
    var inside = document.createElement("span");
    inside.className = "cuts";
    for (var n = section.from; n < section.to; n++) {
      inside.appendChild(cutPoint(run, n, wide, section.from));
    }
    cell.appendChild(inside);

    cell.onclick = function () { pick(run, at); draw(); };
    takesDrop(cell, run, at, "sec");
    bar.appendChild(cell);

    // The cut this section shares with the next: dragged to move it, clicked to take it
    // out, which joins the two either side
    if (at < run.sections.length - 1) {
      var edge = document.createElement("div");
      edge.className = "edge";
      edge.title = "drag to move this cut, or click to take it out and join the two";
      edge.onmousedown = function (e) {
        e.preventDefault();
        // The bar is rebuilt on every move, so what is held onto is where it lives and
        // not the bar itself, which would be a node that has already been thrown away
        holding = {run: run, which: at, where: where, had: run.sections.length};
        edge.classList.add("holding");
      };
      // Taking the cut out is its own target, so it is never confused with moving it
      var drop = document.createElement("button");
      drop.className = "drop";
      drop.textContent = "\u00d7";
      drop.title = "take this cut out, joining the two stretches";
      drop.onmousedown = function (e) { e.stopPropagation(); };
      drop.onclick = function (e) {
        e.stopPropagation();
        uncut(run, at);
      };
      edge.appendChild(drop);
      bar.appendChild(edge);
    }
  });
  scroller.appendChild(bar);
  box.appendChild(scroller);
  scroller.scrollLeft = kept;
  scroller.onscroll = function () { run.scrolled = scroller.scrollLeft; };

  // Rolling the wheel over the bar zooms into the light under the pointer, keeping it
  // where it is on the screen. The buttons do the same in steps, which is what says the
  // zooming is there at all
  scroller.onwheel = function (e) {
    if (run.count <= 12) return;
    e.preventDefault();
    // The wheel holds the light under the pointer; the buttons hold the middle of what
    // is on screen, since a button press has no place on the run to hold onto
    var box2 = scroller.getBoundingClientRect();
    var at = (scroller.scrollLeft + (e.clientX - box2.left)) / bar.offsetWidth;
    zoomTo(run, zoomOf(run) * (e.deltaY < 0 ? 1.25 : 0.8), at, e.clientX - box2.left);
  };

  // Which light is which, while there are few enough of them to be worth saying. They
  // go between the bar and the run above it, so they read as naming both
  if (run.count <= 12) {
    var ticks = document.createElement("div");
    ticks.className = "ticks";
    for (var n = 0; n < run.count; n++) {
      var tick = document.createElement("span");
      tick.textContent = (run.name === "out" ? run.order[n] : n) + 1;
      ticks.appendChild(tick);
    }
    box.insertBefore(ticks, scroller);
  }
}

function stripZoomAndSteps(row, run) {
  var space = document.createElement("span");
  space.className = "gap";
  row.appendChild(space);

  // Zooming is only any use where there are more lights than a panel can show. The
  // buttons hold the middle of the view, since a press has no place on the run to hold
  if (run.count > 12) {
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

function renderStripTools(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var row = document.createElement("div");
  row.className = "tools";
  var section = run.sections[run.picked];

  row.appendChild(document.createTextNode("Split into"));
  var ways = document.createElement("input");
  ways.type = "number";
  ways.min = 2;
  ways.max = Math.max(2, section ? widthOf(section) : 2);
  ways.value = run.ways || 3;
  ways.dataset.focus = where + "-ways";
  ways.onchange = function () { run.ways = Number(ways.value); };
  row.appendChild(ways);

  var cut = document.createElement("button");
  cut.textContent = "Split";
  cut.disabled = !section || widthOf(section) < 2;
  cut.onclick = function () { divide(run, Number(ways.value)); };
  row.appendChild(cut);

  // Cutting by number was here and has gone: clicking the place in the bar is quicker
  // at every length, and the cut says which two lights it falls between as it is aimed
  var whole = document.createElement("button");
  whole.textContent = "Join it all back";
  whole.disabled = run.sections.length < 2;
  whole.onclick = function () { joinAll(run); };
  row.appendChild(whole);

  var filler = document.createElement("button");
  filler.textContent = "Fill with the next " + (run.pattern || 2);
  filler.title = "take this stretch and the ones after it as a pattern, and repeat it " +
                 "to the end of the run";
  filler.disabled = run.picked + (run.pattern || 2) > run.sections.length;
  filler.onclick = function () { fill(run, run.pattern || 2); };
  row.appendChild(filler);

  var many = document.createElement("input");
  many.type = "number";
  many.min = 1;
  many.max = 8;
  many.value = run.pattern || 2;
  many.dataset.focus = where + "-pattern";
  many.onchange = function () { run.pattern = Number(many.value); draw(); };
  row.appendChild(many);

  box.appendChild(row);
}

function hexOf(rgb) {
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

function takeApart(rgb) {
  var top = Math.max.apply(null, rgb) / 255;
  var low = Math.min.apply(null, rgb) / 255;
  return {hue: hueOf(rgb.map(function (v) {
            return top === low ? 0 : Math.round((v / 255 - low) / (top - low) * 255);
          })) || 0,
          sat: top ? (top - low) / top : 0,
          value: top};
}

function hexRgb(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16),
          parseInt(hex.slice(5, 7), 16)];
}

function astrayOf(side) {
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


// wireRun asks a run how many lights it has under the name that page gives it, and lands
// a card on a stretch, which this page does not do, nothing being carried here
function takesDrop() {}

// The drawing picks through the runs' pick(), which makes the strip the
// run being worked on, so only one stretch on the page is ever marked
function isPicked(run, at) { return run === active && run.picked === at; }

// How wide the drawing draws a full row of thirty lights, in its own units
var FULL_ROW_DRAWN = Number(wireRun({count: 30, sections: [], lamps: []}).svg
                              .getAttribute("viewBox").split(" ")[2]);

// A strip run says how many lights it has under the name the drawing asks for
function renderStrip(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  run.count = run.lamps.length;
  var made = wireRun(run);
  // The drawing fills the width at a full row of lights, and a shorter strip keeps that
  // size of light, not growing to fill the width
  var drawn = Number(made.svg.getAttribute("viewBox").split(" ")[2]);
  made.svg.style.maxWidth = Math.min(100, drawn / FULL_ROW_DRAWN * 100) + "%";
  box.appendChild(made.svg);
  painters.push({run: run, paint: made.paint});
}

// ---- how many lights are on one ------------------------------------------------------------
// The chip the drawing keeps its count in. A strip's length is a fact about the
// board, so it is the same in every scene and changing it here changes it in all of them

// A strip's length as the chip takes it. One LED is a strip autofx accepts
var STRIP_FEWEST = 1;
var STRIP_MOST = 300;

// The orders a strip can take its colours in, as the file writes them after its length,
// the board's own being written as nothing
var STRIP_ORDERS = [["", "GRB, as most strips"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

function renderLeds(where, run) {
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
    STRIPS.filter(function (one) { return one.id === run.id; })[0].leds = want;
    run.leds = want;
    settle();
    draw();
  };
  chip.appendChild(count);
  var unit = document.createElement("small");
  unit.textContent = "LEDs";
  chip.appendChild(unit);
  var order = document.createElement("select");
  STRIP_ORDERS.forEach(function (pair) {
    var option = document.createElement("option");
    option.value = pair[0];
    option.textContent = pair[1];
    if ((run.order || "") === pair[0]) option.selected = true;
    order.appendChild(option);
  });
  order.title = "The order the strip takes its colours in. Change it if red shows as another colour";
  order.onchange = function () {
    STRIPS.filter(function (one) { return one.id === run.id; })[0].order = order.value;
    run.order = order.value;
    draw();
  };
  chip.appendChild(order);
  box.appendChild(chip);
  var says = document.createElement("span");
  says.className = "says";
  says.textContent = "the same in every scene, being how the board is built";
  box.appendChild(says);
}

// ---- zooming a strip's bar --------------------------------------------------------------------
// The drawing finds a bar by which of two runs it is for. Here a bar is found by the strip's
// own id, so these stand in for those two

// The most lights a strip can have and not be zoomed, which the zoom buttons are
// hidden at. Must match their test, `run.count > 12`
var ZOOMS_OVER = 12;

function middleOfView(run) {
  var scroller = document.querySelector("#" + run.id + "Bar .scroller");
  if (!scroller) return 0.5;
  var bar = scroller.querySelector(".bar");
  return (scroller.scrollLeft + scroller.clientWidth / 2) / bar.offsetWidth;
}

// Zooming keeps whatever was under the pointer under the pointer, which is the only way a
// zoom on a long run is any use: otherwise the thing being aimed at runs away
function zoomTo(run, want, at, from) {
  // Held to three places, and to exactly 1 near it, since the buttons step by 1.6 each way and
  // coming back out left 1.0000000000000002, a bar a hair wider than its box that scrolls
  want = Math.round(want * 1000) / 1000;
  if (Math.abs(want - 1) < 0.01) want = 1;
  run.zoom = Math.max(1, Math.min(24, want));
  draw();
  var scroller = document.querySelector("#" + run.id + "Bar .scroller");
  if (!scroller) return;
  var bar = scroller.querySelector(".bar");
  var to = at * bar.offsetWidth - (from === undefined ? scroller.clientWidth / 2 : from);
  scroller.scrollLeft = Math.max(0, to);
  run.scrolled = scroller.scrollLeft;
}

// ---- what a stretch plays, carried through the tools -----------------------------------------
// Everything a stretch holds besides where it is, copied, so splitting, filling and joining it
// all back keep what it played. The drawing's own split and fill copy only its look, pace,
// setting and colour, and its join makes one stretch playing nothing
function playsOf(section) {
  return {look: section.look, pace: section.pace, mood: section.mood, colour: section.colour,
          custom: section.custom, reversed: section.reversed, level: section.level,
          blinks: copyBlinks(section.blinks), exact: copyExact(section.exact),
          timings: copyExact(section.timings)};
}

var oneDivide = divide;

divide = function (run, ways) {
  var section = run.sections[run.picked];
  if (!section) return;
  var had = playsOf(section);
  var at = run.picked, count = run.sections.length;
  oneDivide(run, ways);
  for (var made = at; made < at + run.sections.length - count + 1; made++) {
    Object.assign(run.sections[made], playsOf(had));
  }
  draw();
};

var oneFill = fill;

fill = function (run, many) {
  var pattern = run.sections.slice(run.picked, run.picked + many).map(playsOf);
  var kept = run.picked + many;
  oneFill(run, many);
  for (var made = kept; made < run.sections.length; made++) {
    Object.assign(run.sections[made], playsOf(pattern[(made - kept) % pattern.length]));
  }
  draw();
};

// Joined back into one, the run plays what the stretch picked was playing
var oneJoinAll = joinAll;

joinAll = function (run) {
  var section = run.sections[run.picked];
  var had = section && playsOf(section);
  oneJoinAll(run);
  if (had && run.sections.length === 1) {
    Object.assign(run.sections[0], had);
    settle();
    draw();
  }
};

// ---- the tools under a run -------------------------------------------------------------------
// One row for the outputs, the mono lights and the strips alike, in the screens' button style:
// split the stretch picked, into a number of parts or into lengths of a number of lights, join
// them all back, and repeat the stretches from the picked one to the end of the run. Each is
// one outlined group read as a sentence, its words first, then its number, then the buttons
// that act, so a number is never apart from what it is for.

// The picked stretch cut every so many lights from its start, a shorter one last where they
// do not divide it evenly
function divideLengths(run, each) {
  var section = run.sections[run.picked];
  if (!section || each < 1 || each >= widthOf(section)) return;
  remember(run);
  var had = playsOf(section);
  var made = [];
  for (var from = section.from; from <= section.to; from += each) {
    made.push(Object.assign({from: from, to: Math.min(section.to, from + each - 1)},
                            playsOf(had)));
  }
  run.sections.splice.apply(run.sections, [run.picked, 1].concat(made));
  settle();
  draw();
}

function toolButton(icon, words, off, act, title) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "stoggle";
  button.innerHTML = "<span aria-hidden='true'>" + icon + "</span> " + words;
  button.disabled = off;
  button.title = title;
  button.dataset.act = act;
  return button;
}

function toolNumber(value, low, high, focus, change) {
  var box = document.createElement("input");
  box.type = "number";
  box.min = low;
  box.max = high;
  box.value = value;
  box.dataset.focus = focus;
  box.onchange = function () {
    change(Math.max(low, Math.min(high, Number(box.value) || low)));
    draw();
  };
  return box;
}

function renderStretchTools(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  box.textContent = "";
  var section = run.sections[run.picked];
  var wide = section ? widthOf(section) : 1;
  var row = document.createElement("div");
  row.className = "tools stretchtools";

  var ways = run.ways || 3;
  var split = toolGroup("&#9986;", "Split into");
  split.appendChild(toolNumber(ways, 1, Math.max(2, wide), where + "-ways",
                               function (value) { run.ways = value; }));
  var parts = toolAct("stretches", wide < 2 || ways < 2, "split",
                      "cut the picked stretch into " + ways + " equal parts");
  parts.onclick = function () { divide(run, Math.min(ways, wide)); };
  split.appendChild(parts);
  var lengths = toolAct("lights each", ways >= wide, "lengths",
                        "cut the picked stretch every " + ways +
                        (ways === 1 ? " light" : " lights") + ", a shorter one last where " +
                        "they do not divide it evenly");
  lengths.onclick = function () { divideLengths(run, ways); };
  split.appendChild(lengths);
  row.appendChild(split);

  var join = toolButton("&#10231;", "Join all", run.sections.length < 2, "join",
                        "one stretch the whole length, playing what the picked one plays");
  join.onclick = function () { joinAll(run); };
  row.appendChild(join);

  var many = run.pattern || 2;
  var repeat = toolGroup("&#8649;", "Repeat");
  repeat.appendChild(toolNumber(many, 1, 8, where + "-pattern",
                                function (value) { run.pattern = value; }));
  // What it copies, a swatch for each stretch of the pattern, since a result that looks like
  // what was there says nothing of what was taken
  var pattern = run.sections.slice(run.picked, run.picked + many);
  var chips = document.createElement("span");
  chips.className = "repeatchips";
  pattern.forEach(function (section) {
    var look = lookNamed(section.look);
    var chip = document.createElement("span");
    chip.className = "repeatchip" + (look ? "" : " nothing");
    if (look) chip.style.background = washFor(run, section, look);
    chip.title = look ? look.name : "Nothing";
    chips.appendChild(chip);
  });
  repeat.appendChild(chips);
  var along = toolAct("to the end", run.picked + many > run.sections.length, "repeat",
                      "the picked stretch" + (many === 1 ? "" : many === 2
                        ? " and the one after it" : " and the " + (many - 1) + " after it") +
                      ", repeated along to the end of the run in place of what is there");
  along.onclick = function () { fill(run, many); };
  repeat.appendChild(along);
  // Pointed at, the bar outlines what it copies and fades what it would replace
  function marking(on) {
    barCells(run).forEach(function (cell, at) {
      cell.classList.toggle("repeatfrom", on && at >= run.picked && at < run.picked + many);
      cell.classList.toggle("repeatover", on && at >= run.picked + many);
    });
  }
  repeat.onmouseenter = function () { marking(true); };
  repeat.onmouseleave = function () { marking(false); };
  repeat.addEventListener("focusin", function () { marking(true); });
  repeat.addEventListener("focusout", function () { marking(false); });
  row.appendChild(repeat);

  box.appendChild(row);
}

// A run's stretches as its bar draws them, in order
function barCells(run) {
  var bar = run.strip ? run.id + "Bar" : run === mono ? "monoBar" : "outBar";
  return Array.prototype.slice.call(document.querySelectorAll("#" + bar + " .bar > .sec"));
}

// One outlined group: its icon and words, then what is put inside it
function toolGroup(icon, words) {
  var group = document.createElement("span");
  group.className = "toolset";
  var said = document.createElement("span");
  said.className = "toolsays";
  said.innerHTML = "<span aria-hidden='true'>" + icon + "</span> " + words;
  group.appendChild(said);
  return group;
}

// A button inside a group that does what the group says
function toolAct(words, off, act, title) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "toolact";
  button.textContent = words;
  button.disabled = off;
  button.title = title;
  button.dataset.act = act;
  return button;
}

// The strips' row and the outputs' are one
renderTools = renderStretchTools;
renderStripTools = renderStretchTools;

// The drawing's fill runs to its run's count, which the outputs do not keep
var oneCountedFill = fill;

fill = function (run, many) {
  run.count = run.lamps.length;
  oneCountedFill(run, many);
};

// ---- joining them to the page below -----------------------------------------------------

// The strips are runs of the page below from here on. Each scene keeps its own cutting of
// them in its body, which captures every run
runs = runs.concat(STRIPS.map(stripRun));
settle();

// ---- drawing the page -------------------------------------------------------------------

var oneReviewDraw = draw;

draw = function () {
  oneReviewDraw();
  // The outputs' tools and settings are for the stretch being worked on, which while a
  // strip is picked is under that strip instead
  if (active.strip) {
    document.getElementById("outTools").textContent = "";
    document.getElementById("outChosen").textContent = "";
  }
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    // A strip made too short to zoom has no zoom buttons, so it is not left zoomed in
    if (run.lamps.length <= ZOOMS_OVER) {
      run.zoom = 1;
      run.scrolled = 0;
    }
    renderLeds(run.id + "Leds", run);
    renderStrip(run.id + "Run", run);
    // The count of stretches, then the zoom and the steps beside it, all the drawing's own, so
    // the bar scrolls when zoomed in
    renderCutting(run.id + "Cut", run);
    stripZoomAndSteps(document.getElementById(run.id + "Cut"), run);
    renderStripBar(run.id + "Bar", run);
    document.getElementById(run.id + "Tools").textContent = "";
    document.getElementById(run.id + "Chosen").textContent = "";
    if (run === active) {
      renderStripTools(run.id + "Tools", run);
      renderChosen(run.id + "Chosen", run);
    }
  });
  fitBars();
  // The page below paints what it drew and is done before these are made, so a fresh
  // bead would hold the default fill until the next frame and show black
  paintAll();
};

// A cut's label, which lights it falls between, is centred on the cut, so near either end of a
// bar it overhung the bar and, hidden until pointed at but still taking its room, made an
// unzoomed bar scroll: a strip of 300 LEDs was 888px wide in an 866px box. A label within its
// own width of an end is turned inward, and a bar at its whole width does not scroll at all
function fitBars() {
  document.querySelectorAll(".scroller").forEach(function (scroller) {
    var bar = scroller.querySelector(".bar");
    if (!bar) return;
    var zoomed = bar.style.width && parseFloat(bar.style.width) > 100;
    scroller.style.overflowX = zoomed ? "auto" : "hidden";
    scroller.classList.toggle("zoomed", !!zoomed);
    var edges = bar.getBoundingClientRect();
    bar.querySelectorAll(".cut").forEach(function (cut) {
      var at = cut.getBoundingClientRect();
      var middle = (at.left + at.right) / 2;
      cut.classList.toggle("nearstart", middle - edges.left < 40);
      cut.classList.toggle("nearend", edges.right - middle < 40);
    });
  });
}

// ---- what an output's lamps play when its wiring changes ----------------------------------
// The new lamps are carried what the output played, both ways: broken out into three mono
// lamps, and three put back as one colour lamp. The page below gives them a stretch of
// their own, starting dark, and this fills it where the look plays on them
var oneBreakOut = breakOut;
var oneRejoin = rejoin;

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
function standingIn(run, section) {
  var memo = null;
  run.lamps.slice(section.from, section.to + 1).forEach(function (lamp) {
    var had = carriedFrom()[lamp.out];
    if (had && had.as === section.look) memo = had;
  });
  return memo;
}

function changeWiring(change, toColour) {
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

breakOut = changeWiring(oneBreakOut, false);
rejoin = changeWiring(oneRejoin, true);

// ---- choosing a colour ---------------------------------------------------------------------
// Under the stretch it is for, twelve swatches and a custom one
// that opens a hue and saturation field with a hex box beside it. Brightness is not in
// any of it. A swatch is written as its word, since every one is now a word autofx names,
// and the field writes hex.

// The words the file names and their values, which are picofx's own. A swatch is drawn in
// its true value, the round trip from a written word to a swatch being the point of them
var WORDS = {
  red: [255, 0, 0], orange: [255, 128, 0], yellow: [255, 255, 0], green: [0, 255, 0],
  cyan: [0, 255, 255], blue: [0, 0, 255], purple: [128, 0, 255], magenta: [255, 0, 255],
  pink: [255, 128, 128], warm: [255, 192, 96], white: [255, 255, 255],
  cool: [96, 192, 255], black: [0, 0, 0]
};

// Eight hues thirty or sixty degrees apart, then the white axis with pink on it. Black is
// not offered: it says a lamp is off, which brightness says and Nothing says better
var SWATCHES = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta",
                "pink", "warm", "white", "cool"];

// The swatches a stretch is offered. Black is none of them, being a light turned off, which
// a look that blinks through colours can want as one of its turns
function swatchesFor(run, section) { return SWATCHES; }

function rgbInk(rgb) { return "rgb(" + rgb.join(",") + ")"; }

// The word for a colour where it is one of the swatches, else null
function wordFor(hex) {
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
function takesColour(look) {
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

// Each colour a stretch's lines name, in the order they name them, once each
function coloursWritten(look, section, run) {
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
function stretchWash(look, section, run, mono) {
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

// The gallery's cards play each look at middling settings, which carry one colour for
// all of them, so every card of a look given a colour was that colour. Each such card
// plays in its look's own colour instead, the one a stretch given it starts in
var cardSettings = {};

var oneCardPlay = livePlay;

// The second setting a look starts at, on its card and on a stretch given it, where middling
// does not suit it. Solid starts at full brightness, Colour cycle at full saturation, Colour
// steps at picofx's six, and Pelican crossing's lamps fade in about a tenth of a second, as a
// crossing's do
var START_MOODS = {"Solid": 1, "Colour cycle": 1, "Colour steps": 1 / 3,
                   "Pelican crossing": 0.1, "Traffic light": 0.1, "Marquee": 0.25};

// Solid's own colour, which a stretch given it starts in and its card shows, still and at full
// brightness. Stepping through the swatches, the card read as Colour steps, and its palette
// mark says a colour is chosen
var SOLID_COLOUR = "#" + hexOf(WORDS.yellow);

livePlay = function (look, holder, t, slot, count, sim) {
  if (holder === MIDDLING && look && look.solid) {
    // Drawn in the swatch's value, the word it writes taking the lamps' softer shade
    var solid = oneCardPlay(look, {pace: MIDDLING.pace, mood: START_MOODS.Solid,
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
  return oneCardPlay(look, holder, t, slot, count, sim);
};

// The looks shaped to separate lamps. They play on outputs, mono lamps and strips
var BANKED_LOOKS = ["Emergency", "Traffic light", "Pelican crossing"];

// The lamps a signal is built from, which a strip's stretch is cut into blocks of
var SIGNAL_LAMPS = {"Traffic light": 3, "Pelican crossing": 5};

function isBanked(look) {
  return !!look && BANKED_LOOKS.indexOf(look.name) >= 0;
}

var oneCanPlay = canPlay;

canPlay = function (look, target) {
  if (target.kind === "run" && isBanked(look)) return target.count > 1 || look.alone !== false;
  return oneCanPlay(look, target);
};

var oneBankedLines = linesFor;

linesFor = function (look, target, pace, mood, colour) {
  if (!(target.kind === "run" || target.strip) || !isBanked(look) || target.count === 1)
    return oneBankedLines(look, target, pace, mood, colour);
  return stripLines(look, target, pace, mood);
};

// The preview plays a stretch as that many lamps of its own, so while it plays a strip's it
// is told to, and these looks take the strip's form there too
var previewingStrip = false;

var oneBankedLitRun = litRun;

litRun = function (run) {
  previewingStrip = !!run.strip;
  try {
    return oneBankedLitRun(run);
  } finally {
    previewingStrip = false;
  }
};

var oneBankedLampTarget = lampTarget;

lampTarget = function (count) {
  var target = oneBankedLampTarget(count);
  if (previewingStrip) Object.assign(target, {strip: true, lights: target.playing.slice()});
  return target;
};

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

spanning = function () {
  return LOOKS.filter(function (look) {
    return look.spans || BANKED_LOOKS.indexOf(look.name) >= 0;
  });
};

// A card carries a painter's palette where its look takes a colour, and the stretch being
// worked on can be given one
function paletteMark() {
  var palette = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  palette.setAttribute("viewBox", "0 0 16 16");
  palette.setAttribute("class", "tint palette");
  palette.innerHTML =
    "<path fill='currentColor' d='M8 1.2a6.8 6.8 0 0 0 0 13.6c1.1 0 1.7-.6 1.7-1.4 " +
    "0-.9-.7-1.1-.7-1.9 0-.8.6-1.3 1.4-1.3h1.8a3 3 0 0 0 3-3C15.2 3.8 12 1.2 8 1.2Z'/>" +
    [[4.6, 8], [5.6, 4.6], [9, 3.6], [12, 5.6]].map(function (at) {
      return "<circle cx='" + at[0] + "' cy='" + at[1] + "' r='1.2' fill='var(--panel)'/>";
    }).join("");
  return palette;
}

var oneLookCard = lookCard;

lookCard = function (isMono, look, on) {
  var card = oneLookCard(isMono, look, on);
  if (isMono || !takesColour(lookNamed(look.name))) return card;
  card.appendChild(paletteMark());
  card.title += ". You can choose its colour";
  return card;
};

function startColour(run, section, look) {
  if (!takesColour(look)) return;
  var own = look.solid ? SOLID_COLOUR : ownColour(look, run, section);
  if (own) {
    section.colour = own;
    section.custom = false;
  }
}

var oneLandLook = landLook;

landLook = function (run, at, name) {
  var section = run.sections[at];
  var look = lookNamed(name);
  if (section && look && section.look !== name) {
    startColour(run, section, look);
    // The second setting means something of each look's own, so it starts afresh
    section.mood = START_MOODS[look.name] !== undefined ? START_MOODS[look.name] : MIDDLING.mood;
  }
  oneLandLook(run, at, name);
};

// The looks the board opens playing start in their own colours too
[outs, mono].forEach(function (run) {
  run.sections.forEach(function (section) {
    var look = lookNamed(section.look);
    if (look) startColour(run, section, look);
  });
});

washFor = function (run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
};

washOf = function (look, mono, section, run) { return stretchWash(look, section, run, mono); };

// Every draw settles the model and settling makes the stretches afresh, so a handler
// that kept the stretch it was made with would write onto one the run no longer holds.
// Each reaches the live one through the run when it fires
// The last custom colour of each stretch and its own brightness, by its run and first lamp,
// kept while a swatch is chosen so custom comes back to both, as a screen's background does.
// Kept here, the stretches being made afresh on every draw
var customColours = {};

// The picker is the one a screen's background has: one row of swatches spanning the stretch's
// width, named under them when there is room, the custom field under the row with the hex
// beside it over the colour itself
function renderColourPick(box, run) {
  var section = run.sections[run.picked];
  function live() { return run.sections[run.picked]; }
  var remembered = run.id + ":" + section.from;
  var wrap = document.createElement("div");
  wrap.className = "colourpick groundpick";

  var swatches = document.createElement("div");
  swatches.className = "sswatches";
  var offered = swatchesFor(run, section);
  var chosenHex = (section.colour || "#ffffff").replace("#", "").toLowerCase();
  var chosenWord = offered.filter(function (name) {
    return hexOf(WORDS[name]) === chosenHex;
  })[0] || null;
  offered.forEach(function (name) {
    var swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "swatch" + (chosenWord === name ? " on" : "");
    swatch.style.background = rgbInk(WORDS[name]);
    swatch.title = name;
    var tag = document.createElement("b");
    tag.textContent = name;
    swatch.appendChild(tag);
    swatch.onclick = function () {
      live().colour = "#" + hexOf(WORDS[name]);
      live().custom = false;
      draw();
    };
    swatches.appendChild(swatch);
  });

  // The last one is not a colour but the way to every other one
  var custom = document.createElement("button");
  custom.type = "button";
  custom.className = "swatch custom" + (section.custom || !chosenWord ? " on" : "");
  // Its middle is the custom colour at its own brightness, kept while a swatch is chosen, and
  // empty until there is one
  if (section.custom || !chosenWord) {
    customColours[remembered] = {colour: section.colour || "#ffffff",
                                 level: section.level === undefined ? 1 : section.level};
  }
  var kept = customColours[remembered];
  if (kept) custom.style.setProperty("--picked", atBrightness(kept.colour, kept.level));
  custom.title = "any hue and how deep it is, at a brightness of its own";
  var ctag = document.createElement("b");
  ctag.textContent = "custom";
  custom.appendChild(ctag);
  // A swatch keeps the brightness already set, and custom comes back at its own
  custom.onclick = function () {
    live().custom = true;
    if (kept) {
      live().colour = kept.colour;
      live().level = kept.level;
    }
    draw();
  };
  swatches.appendChild(custom);
  wrap.appendChild(swatches);

  // The field, open only while custom is the choice. Hue across and saturation down, at
  // full value throughout, so a colour means the same thing at any brightness
  var holds = document.createElement("div");
  var open = section.custom || !chosenWord;
  holds.className = "customholds scustom";
  holds.style.display = open ? "" : "none";
  var parts = takeApart(hexRgb(section.colour || "#ffffff"));
  var field = document.createElement("div");
  field.className = "field";
  var at = document.createElement("div");
  at.className = "at";
  at.style.left = (parts.hue / 360 * 100) + "%";
  at.style.top = ((1 - parts.sat) * 100) + "%";
  at.style.background = rgbInk(fieldColour(parts.hue, parts.sat));
  field.appendChild(at);

  // Held down and dragged. Only the mark and the box move while the pointer is down, so
  // the field is never rebuilt under it
  function pointingAt(event) {
    var box2 = field.getBoundingClientRect();
    var across = Math.max(0, Math.min(1, (event.clientX - box2.left) / box2.width));
    var down = Math.max(0, Math.min(1, (event.clientY - box2.top) / box2.height));
    var rgb = fieldColour(across * 360, 1 - down);
    live().colour = "#" + hexOf(rgb);
    live().custom = true;
    at.style.left = (across * 100) + "%";
    at.style.top = (down * 100) + "%";
    at.style.background = rgbInk(rgb);
    hex.value = atBrightness(live().colour, live().level);
    preview.style.background = hex.value;
    renderPreview();
  }
  field.onpointerdown = function (event) {
    field.setPointerCapture(event.pointerId);
    pointingAt(event);
  };
  field.onpointermove = function (event) {
    if (field.hasPointerCapture(event.pointerId)) pointingAt(event);
  };
  field.onpointerup = function () { draw(); };
  holds.appendChild(field);

  // A hex is how a colour arrives from somewhere else, so it is typed rather than hunted
  // for. It is the colour as written, at the stretch's brightness, as a screen's background
  // has it: one typed in sets the colour and the brightness both
  var typed = document.createElement("div");
  typed.className = "hexline";
  var label = document.createElement("label");
  label.textContent = "Hex";
  typed.appendChild(label);
  var hex = document.createElement("input");
  hex.type = "text";
  hex.maxLength = 7;
  hex.spellcheck = false;
  hex.value = atBrightness(section.colour || "#ffffff", section.level);
  hex.title = "the colour as it is written, at its brightness. Paste one in and its hue " +
              "and depth land on the field, and how bright it is on the brightness below";
  hex.oninput = function () {
    var said = hex.value.replace("#", "").trim();
    if (!/^[0-9a-fA-F]{6}$/.test(said)) return;
    var typedRgb = hexRgb("#" + said.toLowerCase());
    var got = takeApart(typedRgb);
    var rgb = fieldColour(got.hue, got.sat);
    live().colour = "#" + hexOf(rgb);
    live().level = Math.max(FAINTEST, Math.max.apply(null, typedRgb) / 255);
    live().custom = true;
    at.style.left = (got.hue / 360 * 100) + "%";
    at.style.top = ((1 - got.sat) * 100) + "%";
    at.style.background = rgbInk(rgb);
    preview.style.background = "#" + said.toLowerCase();
    renderPreview();
  };
  hex.onblur = function () { draw(); };
  typed.appendChild(hex);

  // Beside the field, the hex over the colour itself, as large as the room allows, as a
  // screen's custom background has it
  var side = document.createElement("div");
  side.className = "scustomside";
  side.appendChild(typed);
  var preview = document.createElement("div");
  preview.className = "scustompreview";
  preview.style.background = atBrightness(section.colour || "#ffffff", section.level);
  preview.title = "The colour as it is written, at its brightness";
  side.appendChild(preview);
  holds.appendChild(side);
  wrap.appendChild(holds);

  box.appendChild(wrap);
}

// A hue at full value, brought toward white by how far the saturation is from full
function fieldColour(hue, sat) {
  return hueRgb(hue).map(function (v) { return Math.round(v + (255 - v) * (1 - sat)); });
}

// The stretch's settings, with the colour choice in place of a slider that stepped tones
var oneRenderChosen = renderChosen;

// A second setting that is a count, such as Emergency's flashes, stops only at its values,
// with a tick at each while there are few enough to tell apart
var MOST_TICKS = 16;

function detented(box, where, count) {
  var range = box.querySelector("input[data-focus='" + where + "-mood']");
  if (!range || count < 2) return;
  range.step = 1 / (count - 1);
  if (count > MOST_TICKS) return;
  var ticks = document.createElement("datalist");
  ticks.id = where + "-detents";
  for (var at = 0; at < count; at++) {
    var tick = document.createElement("option");
    tick.value = at / (count - 1);
    ticks.appendChild(tick);
  }
  range.parentNode.appendChild(ticks);
  range.setAttribute("list", ticks.id);
}

renderChosen = function (where, run) {
  oneRenderChosen(where, run);
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var memo = box && section && standingIn(run, section);
  if (memo) {
    var note = document.createElement("div");
    note.className = "standin";
    note.textContent = look.name + ", in place of " + memo.look + ", which mono lights " +
                       "cannot play. Put back, it plays " + memo.look + " again.";
    box.querySelector(".chosen").appendChild(note);
  }
  // A count of stops may depend on the stretch, as Spread's lengths do on its lights
  if (box && look && look.detents) {
    detented(box, where, typeof look.detents === "function"
      ? look.detents(targetFor(run, section)) : look.detents);
  }
  var wrap = box && box.querySelector(".chosen");
  if (!wrap || !look) return;
  var tuning = wrap.querySelector(".tuning");
  if (!tuning) {
    tuning = document.createElement("div");
    tuning.className = "tuning";
    wrap.appendChild(tuning);
  }
  // Solid's own slider was its brightness, which the one every look has now is
  if (look.solid) tuning.textContent = "";
  // A mono lamp has no colour to be given
  var first = run.lamps[section.from];
  var coloured = takesColour(look) && !!first && first.colour;
  // The second slider stepped a table of tones for these looks, and the swatches take
  // its place. On mono lights it has nothing to set, a mono light having no colour
  var mono = !!first && !first.colour;
  var toneless = look.mood === "Colour" || (mono && look.mood === "Palette");
  if ((coloured || mono) && toneless && tuning.children.length >= 4) {
    tuning.removeChild(tuning.children[3]);
    tuning.removeChild(tuning.children[2]);
  }
  brightnessSlider(tuning, run, where);
  // The colour leads and the sliders follow it, brightness the first of them
  if (coloured) {
    renderColourPick(wrap, run);
    wrap.appendChild(tuning);
  }
};

// ---- how bright a stretch is -------------------------------------------------------------
// Every look has a brightness, the first slider in the list, written only below full. A look
// given a custom colour writes it in that colour's hex, dimmed, as a screen's background is.
// Any other, a swatch's word included, writes it as the stretch's level=, which scales
// whatever the look plays
var FAINTEST = 0.05;

function atBrightness(hex, level) {
  if (!(level < 1)) return hex;
  return "#" + hexOf(hexRgb(hex).map(function (v) { return Math.round(v * level); }));
}

// Whether this stretch is given a custom colour here, so its brightness goes into the hex
function coloursItself(run, section, look) {
  var first = run.lamps[section.from];
  var custom = section.custom || !wordFor(section.colour || "#ffffff");
  return takesColour(look) && !!first && first.colour && custom;
}

var oneSectionLines = sectionLines;

sectionLines = function (run, section, look) {
  if (!coloursItself(run, section, look) || !(section.level < 1))
    return oneSectionLines(run, section, look);
  return linesFor(look, targetFor(run, section), section.pace, section.mood,
                  atBrightness(section.colour || "#ffffff", section.level));
};

function brightnessSlider(tuning, run, where) {
  var section = run.sections[run.picked];
  var ahead = tuning.firstChild;
  var label = document.createElement("label");
  label.textContent = "Brightness";
  tuning.insertBefore(label, ahead);
  var range = document.createElement("input");
  range.type = "range";
  range.min = FAINTEST;
  range.max = 1;
  range.step = 0.01;
  range.value = section.level === undefined ? 1 : section.level;
  range.dataset.focus = where + "-level";
  range.oninput = function () {
    run.sections[run.picked].level = Number(range.value);
    renderPreview();
  };
  // A colour's hex and its preview show the brightness, so they are drawn again once it is set
  range.onchange = function () { draw(); };
  tuning.insertBefore(range, ahead);
}

// Solid is written at full, its brightness being the stretch's own
var oneSolidLines = linesFor;

linesFor = function (look, target, pace, mood, colour) {
  if (!look || !look.solid) return oneSolidLines(look, target, pace, mood, colour);
  return oneSolidLines(look, target, pace, 1, colour).map(function (line) {
    return line.replace(/ brightness=1(?=\s|$)/, "");
  });
};

// The preview plays a stretch at its brightness, as the board will. A card plays at full
var oneLevelPlay = livePlay;

livePlay = function (look, holder, t, slot, count, sim) {
  var lit = oneLevelPlay(look, holder, t, slot, count, sim);
  if (!lit || !holder || holder === MIDDLING || !(holder.level < 1)) return lit;
  return Object.assign({}, lit, {level: lit.level * holder.level});
};

// What a stretch writes, with the colour it was given. Solid already writes it. The looks
// whose slider stepped tones write a tone, so the colour they wrote is replaced with the
// chosen one, as a word where it is a swatch and as hex from the field
var oneLinesFor = linesFor;

linesFor = function (look, target, pace, mood, colour) {
  var lines = oneLinesFor(look, target, pace, mood, colour);
  if (!takesColour(look) || !target.colour || !colour) return lines;
  var word = wordFor(colour);
  var said = word || colour.replace("#", "").toLowerCase();
  return lines.map(function (line) {
    return line.replace(/colour=[^\s:]+/, "colour=" + said);
  });
};

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

var oneWaveLines = linesFor;

linesFor = function (look, target, pace, mood, colour) {
  return oneWaveLines(look, target, pace, mood, colour).map(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    if (WAVES.indexOf(effect) < 0) return line;
    return line.replace(/ speed=(\d)/, " speed=-$1");
  });
};

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

// The preview wraps a cycle running below zero back into one, as picofx's modulo does, or a
// blink or a flash reads a negative point in its beat as lit and a hue goes out of range
offsetOf = function (t, settings) {
  var at = ((t * num(settings.speed, 1)) + num(settings.phase, 0)) % 1;
  return at < 0 ? at + 1 : at;
};

COLOURED.rainbow_wave = function (t, s, pos) {
  var at = ((t * num(s.speed, 1)) + pos / num(s.length, 1)) % 1;
  return {level: 1, ink: hueInk((at < 0 ? at + 1 : at) * 360, s.sat, s.val)};
};

// Whether reversing this stretch would change what it plays, judged from its lines as written
function runsAWay(look, target, section) {
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
      return !lamp.colour && lamp.out === out && lamp.channel === 2 - i;
    });
    if (!whole) break;
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
      items.push((lamps[at].out + 1) + "-" + (lamps[at].out - outputs + 2) + ".*");
      at += 3 * outputs;
      continue;
    }
    var last = at;
    while (lamps[at].colour && last + 1 < lamps.length && lamps[last + 1].colour &&
           lamps[last + 1].out === lamps[last].out - 1) last++;
    items.push(last > at ? (lamps[at].out + 1) + "-" + (lamps[last].out + 1)
                         : shortSelector(lamps[at]));
    at = last + 1;
  }
  return "out" + items.join(",");
}

function shortSelector(lamp) {
  return lamp.colour ? String(lamp.out + 1) : (lamp.out + 1) + "." + CHANNELS[lamp.channel];
}

var oneWayTargetFor = targetFor;

targetFor = function (run, section) {
  var target = oneWayTargetFor(run, section);
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
};

// The preview plays a reversed stretch from its far end, as the board will
var oneWayPlay = livePlay;

livePlay = function (look, holder, t, slot, count, sim) {
  var backwards = holder && holder.reversed && count > 1 &&
                  runsAWay(look, lampTarget(count), holder);
  return oneWayPlay(look, holder, t, backwards ? count - 1 - slot : slot, count, sim);
};

// A light at the end the stretch starts from and an arrow the way it runs
// A toggle in the screens' style, its word and its pressed state as Loop's and Restart's are,
// the light in its icon at the end the stretch starts from
function directionToggle(run, section) {
  var button = document.createElement("button");
  button.type = "button";
  var look = lookNamed(section.look);
  var moves = runsAWay(look, oneWayTargetFor(run, section), section);
  button.className = "stoggle direction" + (section.reversed ? " reversed" : "") +
                     (section.reversed && moves ? " on" : "");
  button.setAttribute("aria-pressed", section.reversed && moves ? "true" : "false");
  button.disabled = !moves;
  button.title = !moves ? (!look ? "Which end it starts from, once it has a look that runs"
                                 : widthOf(section) < 2 ? "One light has no direction"
                                 : look.name + " looks the same from either end")
               : section.reversed ? "Starting from the far end, running back"
                                  : "Starting from the near end, running on";
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

// ---- what heads a stretch's settings ------------------------------------------------------------
// The look's name, the panel being its settings, then where it plays in words: outputs
// 1 to 7, LEDs 11 to 20 of the left strip, output 3's red and green. The file's selector is the
// file view's to show, and whether the lights are colour or mono the tab's

var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

// A list said as English does: one, two and three
function spoken(items) {
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
function wherePlays(run, section, reversed) {
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
  if (lamps.every(function (lamp) { return lamp.colour; })) {
    var numbers = lamps.map(function (lamp) { return lamp.out + 1; });
    return (numbers.length === 1 ? "output " : "outputs ") + numbersSaid(numbers);
  }
  // Mono lights, each output's channels together, in the order they play
  var groups = [];
  lamps.forEach(function (lamp) {
    var last = groups[groups.length - 1];
    if (last && last.out === lamp.out) last.channels.push(lamp.channel);
    else groups.push({out: lamp.out, channels: [lamp.channel]});
  });
  return spoken(groups.map(function (group) {
    return "output " + (group.out + 1) + "'s " + spoken(group.channels.map(function (channel) {
      return CHANNEL_WORDS[CHANNELS[channel]];
    }));
  }));
}

// ---- a signal's states, drawn ----------------------------------------------------------------
// Each timing is named by the state it holds, drawn as the signal shows it: a head of three
// lamps, red, amber and green top to bottom, with those lit in their colour, and for a
// crossing the two figures beside it, the red one standing and the green one walking. Its
// slider takes the state's colour. The word stays beside the drawing
var SIGNAL_INK = {red: "#e8392c", amber: "#f5a623", green: "#20b35c", dark: "#3b3f44"};

// The lamps each state lights: 1 lit, 0 dark, "f" flashing
var SIGNAL_STATES = {
  "Traffic light": {red_interval: [1, 0, 0], red_amber_interval: [1, 1, 0],
                    green_interval: [0, 0, 1], amber_interval: [0, 1, 0]},
  "Pelican crossing": {red_interval: [1, 0, 0, 0, 1], flashing_interval: [0, "f", 0, 0, "f"],
                       green_interval: [0, 0, 1, 1, 0], amber_interval: [0, 1, 0, 1, 0]}
};

// A slider's tint, amber and green a shade deeper than the lamps: a browser gives a light
// accent a dark track, which read as a slider filled to its end
var SIGNAL_TINT = {red_interval: SIGNAL_INK.red, red_amber_interval: "#a86600",
                   green_interval: "#16894a", amber_interval: "#a86600",
                   flashing_interval: "#a86600"};

function signalFace(name, key) {
  var lit = SIGNAL_STATES[name][key];
  function lamp(state, ink) {
    if (!state) return SIGNAL_INK.dark;
    return ink;
  }
  function flashing(state) { return state === "f" ? " class='flashing'" : ""; }
  var head = [SIGNAL_INK.red, SIGNAL_INK.amber, SIGNAL_INK.green].map(function (ink, at) {
    return "<circle cx='6' cy='" + (4.5 + at * 6.5) + "' r='2.6' fill='" + lamp(lit[at], ink) +
           "'" + flashing(lit[at]) + "/>";
  }).join("");
  var wide = 12;
  var figures = "";
  // A crossing's pedestrian lights are drawn as its figures, the red one standing and the
  // green one walking, so they read as figures and not as a second head of lamps
  if (lit.length > 3) {
    wide = 22;
    var stand = lamp(lit[3], SIGNAL_INK.red), walk = lamp(lit[4], SIGNAL_INK.green);
    figures = "<rect x='12.5' y='1' width='9' height='22' rx='2' fill='#1c1f22'/>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + stand + "'" +
      flashing(lit[3]) + "><circle cx='17' cy='3.6' r='1.1' fill='" + stand + "' stroke='none'/>" +
      "<path d='M17 5.2 V8.6 M15.6 6.4 H18.4 M16.3 8.6 V11 M17.7 8.6 V11'/></g>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + walk + "'" +
      flashing(lit[4]) + "><circle cx='17.4' cy='13.6' r='1.1' fill='" + walk + "' stroke='none'/>" +
      "<path d='M17.2 15.2 L16.8 18.3 M15.6 16.8 L18.6 16 M16.8 18.3 L15.4 21 M16.8 18.3 " +
      "L18.6 20.8'/></g>";
  }
  return "<svg class='signalface' viewBox='0 0 " + wide + " 24' width='" + wide * 0.9 +
         "' height='21.6' aria-hidden='true'><rect x='1' y='0' width='10' height='24' rx='3' " +
         "fill='#1c1f22'/>" + head + figures + "</svg>";
}

// A signal's timings take Speed's place, each a slider in seconds under its own name
var oneTimingChosen = renderChosen;

renderChosen = function (where, run) {
  oneTimingChosen(where, run);
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning || !look || !SIGNAL_TIMINGS[look.name]) return;
  var speed = tuning.querySelector("input[data-focus='" + where + "-pace']");
  var after = speed ? speed.nextSibling : null;
  if (speed) {
    tuning.removeChild(speed.previousElementSibling);
    tuning.removeChild(speed);
  }
  // Ease is about every state, so it comes before them, after Brightness
  var ease = tuning.querySelector("input[data-focus='" + where + "-mood']");
  if (ease) {
    var easeLabel = ease.previousElementSibling;
    if (after === easeLabel) after = ease.nextSibling;
    tuning.insertBefore(easeLabel, after);
    tuning.insertBefore(ease, after);
    after = ease.nextSibling;
  }
  SIGNAL_TIMINGS[look.name].forEach(function (part) {
    var label = document.createElement("label");
    label.className = "signalstate";
    label.innerHTML = signalFace(look.name, part[0]) + "<span>" + part[1] + "</span>";
    var range = document.createElement("input");
    range.style.accentColor = SIGNAL_TINT[part[0]];
    range.type = "range";
    range.min = part[3];
    range.max = part[4];
    range.step = 0.5;
    range.value = withSection(section, function () { return timingOf(look.name, part[0]); });
    range.dataset.focus = where + "-timing-" + part[0];
    range.dataset.timing = part[0];
    range.title = "seconds, " + part[1].toLowerCase();
    range.oninput = function () {
      var mine = run.sections[run.picked];
      mine.timings = Object.assign({}, mine.timings);
      mine.timings[part[0]] = Number(range.value);
      renderPreview();
    };
    tuning.insertBefore(label, after);
    tuning.insertBefore(range, after);
  });
};

// ---- an icon for each setting ------------------------------------------------------------------
// Each slider's name has a small line drawing before it, in the name's own grey, as the toggles
// have theirs, so a panel reads at a glance. A signal's states keep their coloured
// drawings, colour being what they are about. The word stays, the icon only hinting
var SETTING_ICONS = {
  "Brightness": "<circle cx='8' cy='8' r='2.8'/><path d='M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8" +
                "M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3'/>",
  "Speed": "<path d='M2.4 12A6 6 0 1 1 13.6 12'/><path d='M8 10.2L11 5.6'/>" +
           "<circle cx='8' cy='10.4' r='1' class='filled'/>",
  "Fade": "<path d='M5.6 10.4C4 9.3 3.6 7.9 3.6 6.8a4.4 4.4 0 0 1 8.8 0c0 1.1-.4 2.5-2 3.6'/>" +
          "<path d='M6 12.4h4M6.6 14.4h2.8'/><path d='M6.4 6.8c.5-1 1.1-1.5 1.6-1.5'/>",
  "Spread": "<path d='M1.5 8h13M4 5.5L1.5 8 4 10.5M12 5.5L14.5 8 12 10.5'/>",
  "Steps": "<path d='M2 13.5h3v-3h3v-3h3v-3h3'/>",
  "Trail": "<circle cx='12.4' cy='8' r='2.2' class='filled'/><path d='M1.6 8h6.8M3.2 5.2h5.2" +
           "M3.2 10.8h5.2'/>",
  "Flashes": "<path d='M9.2 1.6L4.2 9h3.9l-1.3 5.4L11.8 7H7.9z'/>",
  "On time": "<circle cx='8' cy='8' r='5.8'/><path d='M8 2.2a5.8 5.8 0 0 1 0 11.6z' class='filled'/>",
  "Spacing": "<circle cx='2.6' cy='8' r='1.4' class='filled'/><circle cx='8' cy='8' r='1.4'/>" +
             "<circle cx='13.4' cy='8' r='1.4' class='filled'/>",
  "Saturation": "<path d='M8 1.8C8 1.8 3.6 7.2 3.6 10a4.4 4.4 0 0 0 8.8 0C12.4 7.2 8 1.8 8 1.8z'/>",
  "Intensity": "<path d='M8 1.6c1.5 2.7 4.5 4.3 4.5 7.8a4.5 4.5 0 0 1-9 0c0-2 1.4-3 2-4.4" +
               "c.9 1.4 1.4 1.9 1.9 1.9 0-2 .1-3.5.6-5.3z'/>",
  "Palette": "<path d='M8 1.6a6.4 6.4 0 0 0 0 12.8c1 0 1.6-.6 1.6-1.3 0-.9-.7-1.1-.7-1.8 0-.8.6-1.2" +
             " 1.3-1.2h1.7a2.8 2.8 0 0 0 2.8-2.8C14.7 4 11.8 1.6 8 1.6z'/>" +
             "<circle cx='4.9' cy='7.6' r='.9' class='filled'/><circle cx='6.2' cy='4.7' r='.9' " +
             "class='filled'/><circle cx='9.3' cy='4' r='.9' class='filled'/>"
};

var oneIconChosen = renderChosen;

renderChosen = function (where, run) {
  oneIconChosen(where, run);
  var box = document.getElementById(where);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning) return;
  // Every slider keeps the picked stretch's colours on the bar with it as it moves, a slider
  // that picks colours as Palette does changing them, and redraws the panel once let go. The
  // sliders only played the preview as they moved, so the bar kept what was there before
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  Array.prototype.forEach.call(tuning.querySelectorAll("input[type=range]"), function (range) {
    var moved = range.oninput;
    range.oninput = function () {
      if (moved) moved.call(range);
      var live = run.sections[run.picked];
      var cell = barCells(run)[run.picked];
      var wash = cell && cell.querySelector(".lit");
      if (wash && look) wash.style.background = washFor(run, live, look);
    };
    if (!range.onchange) range.onchange = function () { draw(); };
  });
  Array.prototype.forEach.call(tuning.querySelectorAll(":scope > label"), function (label) {
    var drawn = SETTING_ICONS[label.textContent];
    if (!drawn || label.querySelector(".settingicon")) return;
    if (label.textContent === "Fade") {
      label.title = "how long each lamp takes to come on and go off, written as ease, a fade " +
                    "that slows as it arrives";
    }
    label.classList.add("withicon");
    label.insertAdjacentHTML("afterbegin", "<svg class='settingicon' viewBox='0 0 16 16' " +
                                           "aria-hidden='true'>" + drawn + "</svg>");
  });
};

var oneHeadChosen = renderChosen;

renderChosen = function (where, run) {
  oneHeadChosen(where, run);
  var box = document.getElementById(where);
  var who = box && box.querySelector(".chosen .who");
  var section = run && run.sections[run.picked];
  if (!who || !section) return;
  var look = lookNamed(section.look);
  who.innerHTML = "";
  var named = document.createElement("b");
  named.textContent = look ? look.name : "Nothing";
  who.appendChild(named);
  var reversed = section.reversed && runsAWay(look, oneWayTargetFor(run, section), section);
  who.appendChild(document.createTextNode(" on " + wherePlays(run, section, reversed)));
  who.title = targetFor(run, section).selector;
};

var oneWayChosen = renderChosen;

renderChosen = function (where, run) {
  oneWayChosen(where, run);
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var who = box && box.querySelector(".chosen .who");
  if (!section || !who) return;
  // The name and its count stay one piece of text, the toggle set apart at the end
  var named = document.createElement("span");
  while (who.firstChild) named.appendChild(who.firstChild);
  who.appendChild(named);
  who.classList.add("withway");
  who.appendChild(directionToggle(run, section));
};

// The page opens on one board playing all the way through
state.always.body = capture();
draw();
