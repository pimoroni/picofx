var BUILD = JSON.parse(document.getElementById("build").textContent);

export var BOARD = BUILD.board;

export var VERSION = BUILD.version;

export var CATALOGUE_ASSUMED = typeof CATALOGUE === "undefined";

if (CATALOGUE_ASSUMED) {
  var assumedPorts = BOARD.screens ? BOARD.screens.ports.map(function (port) { return port.id; }) : [];
  window.CATALOGUE = {board_settings: {}, screen_ports: assumedPorts,
                      strips: BOARD.strips.map(function (strip) { return strip.name; })};
  assumedPorts.forEach(function (id) { CATALOGUE.board_settings[id] = ["2.8", "1.54"]; });
}

export var HEADER = "# Written by the FX picker. Everything here can be edited by hand;\n" +
             "# MANUAL.html on this drive explains every line.\n";

function r2(n) { return Math.round(n * 100) / 100; }
function lerp(a, b, t) { return r2(a + (b - a) * t); }

function tone(palette, t) {
  return palette[Math.min(palette.length - 1, Math.floor(t * palette.length))];
}

function span(count, mood) {
  return Math.max(2, Math.round(count * lerp(2, 0.6, mood)));
}

export function quoted(name) {
  return name.indexOf(" ") >= 0 ? '"' + name + '"' : name;
}

export function rangify(list) {
  var parts = [];
  var i = 0;
  while (i < list.length) {
    var j = i;
    if (j + 1 < list.length && list[j + 1] === list[j] + 1) {
      while (j + 1 < list.length && list[j + 1] === list[j] + 1) j++;
    } else if (j + 1 < list.length && list[j + 1] === list[j] - 1) {
      while (j + 1 < list.length && list[j + 1] === list[j] - 1) j++;
    }
    var count = j - i + 1;
    if (count === 1) parts.push(String(list[i]));
    else if (count === 2) parts.push(list[i] + "," + list[j]);
    else parts.push(list[i] + "-" + list[j]);
    i = j + 1;
  }
  return parts.join(",");
}

function nameSet(target, set) {
  return target.nameSet ? target.nameSet(set) : target.name + rangify(set);
}

function roundRobin(playing, ways) {
  var groups = [];
  playing.forEach(function (which, i) {
    var at = i % ways;
    (groups[at] = groups[at] || []).push(which);
  });
  return groups;
}

function runThirds(name, count, reversed, ways, lights) {
  function light(place) { return lights ? lights[place - 1] : place; }
  var edges = [];
  for (var i = 0; i <= ways; i++) edges.push(Math.round(count * i / ways));
  var parts = [];
  for (var g = 0; g < ways; g++) {
    var from = edges[g] + 1;
    var to = edges[g + 1];
    if (to < from) continue;
    parts.push(reversed ? name + light(count - from + 1) + "-" + light(count - to + 1)
                        : name + light(from) + "-" + light(to));
  }
  return parts;
}

function withoutColour(line) {
  return line.replace(/\s+colour=[^\s:]+/g, "");
}

var BREATHE_TONES = ["blue", "cool", "cyan", "green", "warm"];
var SPARKLE_TONES = ["cyan", "cool", "white", "warm", "yellow"];
var SCANNER_TONES = ["magenta", "blue", "red", "yellow", "white"];
var CHASE_TONES = ["magenta", "white", "yellow", "cyan", "green"];
var COUNTER_TONES = ["white", "cyan", "green", "yellow", "red"];
var PARTY_FIRST = ["red", "blue", "magenta", "cyan", "white"];
var PARTY_SECOND = ["green", "white", "yellow", "warm", "red"];
var PARTY_THIRD = ["blue", "green", "cyan", "white", "magenta"];

export var LOOKS = [
  {
    name: "Solid", mood: "Brightness", spans: true, onMono: true, solid: true,
    strip: ["#d94a3d", "#e0a03a", "#3fa672", "#3a7fd9", "#8a4ad0", "#d94a9e", "#e8e2d6"],
    entries: function (target, pace, mood, colour) {
      return [target.selector + " colour=" + (colour || "ffffff").replace("#", "") +
              ": static brightness=" + lerp(0.05, 1, mood)];
    },
    alone: function (target, pace, mood, colour) {
      return this.entries(target, pace, mood, colour);
    }
  },
  {
    name: "Rainbow", mood: "Colour spread", spans: true, onMono: false,
    strip: ["#e33", "#e73", "#ea3", "#3a5", "#36c", "#63c", "#a3c"],
    entries: function (target, pace, mood) {
      return [target.selector + ": rainbow_wave speed=" + lerp(0.05, 0.8, pace) +
              " length=" + span(target.count, mood)];
    },
    alone: function (target, pace) {
      return [target.selector + ": rainbow speed=" + lerp(0.05, 0.8, pace)];
    }
  },
  {
    name: "Campfire", mood: "Intensity", spans: true, onMono: true,
    strip: ["#812200", "#c43a00", "#ff5a00", "#ff8c1a", "#ff5a00", "#c43a00", "#812200"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=ff5a00: flicker_each brightness=" + lerp(0.5, 1, mood) +
              " dimness=" + lerp(0.7, 0.35, mood) +
              " bright_min=" + lerp(0.1, 0.02, pace) + " bright_max=" + lerp(0.4, 0.1, pace) +
              " dim_min=" + lerp(0.08, 0.02, pace) + " dim_max=" + lerp(0.3, 0.08, pace)];
    }
  },
  {
    name: "Breathe", mood: "Colour", spans: true, onMono: true,
    strip: ["#2b7f8f", "#37a0b4", "#43c1d9", "#56d8f0", "#43c1d9", "#37a0b4", "#2b7f8f"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(BREATHE_TONES, mood) +
              " ease=" + lerp(0.8, 0.2, pace) + ": pulse speed=" + lerp(0.08, 0.5, pace)];
    }
  },
  {
    name: "Wave", mood: "Wave length", spans: true, onMono: true,
    strip: ["#122438", "#2a4a6a", "#4a7fb5", "#7fb5e6", "#4a7fb5", "#2a4a6a", "#122438"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=cool: pulse_wave speed=" + lerp(0.1, 1, pace) +
              " length=" + span(target.count, mood)];
    },
    alone: function (target, pace) {
      return [target.selector + " colour=cool: pulse speed=" + lerp(0.1, 1, pace)];
    }
  },
  {
    name: "Sparkle", mood: "Colour", spans: true, onMono: true,
    strip: ["#ffffff", "#999999", "#ffffff", "#cccccc", "#eeeeee", "#888888", "#ffffff"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(SPARKLE_TONES, mood) +
              ": random_each interval=" + lerp(0.25, 0.03, pace) +
              " brightness_min=0 brightness_max=1"];
    }
  },
  {
    name: "Scanner", mood: "Colour", spans: true, onMono: true,
    strip: ["#330000", "#660000", "#cc0000", "#ff3333", "#cc0000", "#660000", "#330000"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(SCANNER_TONES, mood) +
              " fade=" + lerp(0.5, 0.15, pace) + ": sweep speed=" + lerp(0.3, 2, pace) +
              " length=" + target.count +
              " extent=" + Math.max(1, Math.round(target.count / 8))];
    },
    alone: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(SCANNER_TONES, mood) +
              " ease=" + lerp(0.5, 0.15, pace) + ": pulse speed=" + lerp(0.3, 2, pace)];
    }
  },
  {
    name: "Chase", mood: "Colour", spans: true, onMono: true,
    strip: ["#111111", "#111111", "#ffff00", "#ffd24a", "#111111", "#111111", "#111111"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(CHASE_TONES, mood) +
              " fade=" + lerp(0.4, 0.1, pace) + ": flash_sequence speed=" + lerp(0.3, 2, pace) +
              " length=" + target.count + " flashes=1 window=0.4"];
    },
    alone: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(CHASE_TONES, mood) +
              " fade=" + lerp(0.4, 0.1, pace) + ": flash speed=" + lerp(0.3, 2, pace) +
              " flashes=1 window=0.4"];
    }
  },
  {
    name: "Counter", mood: "Colour", spans: true, onMono: true,
    strip: ["#00ff00", "#111111", "#00ff00", "#00ff00", "#111111", "#00ff00", "#111111"],
    entries: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(COUNTER_TONES, mood) +
              ": binary_counter interval=" + lerp(1, 0.08, pace)];
    }
  },
  {
    name: "Emergency", mood: "Flashes", detents: 5, spans: false, onMono: true,
    strip: ["#dd2222", "#2222dd", "#dd2222", "#111111", "#2222dd", "#dd2222", "#2222dd"],
    entries: function (target, pace, mood) {
      var flash = ": flash speed=" + lerp(0.6, 2.5, pace) + " flashes=" +
                  Math.round(lerp(1, 5, mood)) + " window=0.5";
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
    },
    alone: function (target, pace, mood) {
      return [target.selector + " colour=red: flash speed=" + lerp(0.6, 2.5, pace) +
              " flashes=" + Math.round(lerp(1, 5, mood)) + " window=0.5"];
    }
  },
  {
    name: "Pelican crossing", mood: "Fade", spans: false, onMono: true,
    strip: ["#ff0000", "#ff7800", "#00d28c", "#ff0000", "#00d28c", "#111111", "#111111"],
    entries: function (target, pace, mood) {
      var scale = lerp(2, 0.4, pace);
      var playing = target.playing;
      var lamps = playing.slice(0, 5);
      var rest = playing.slice(5);
      var colours = ["red", "ff7800", "00d28c", "red", "00d28c"].slice(0, lamps.length);
      var lines = [nameSet(target, lamps) + " colour=" + colours.join(",") +
                   " ease=" + lerp(0.05, 0.6, mood) +
                   ": pelican_crossing red_interval=" + r2(8 * scale) +
                   " flashing_interval=" + r2(6 * scale) +
                   " green_interval=" + r2(20 * scale) +
                   " amber_interval=" + r2(3 * scale)];
      if (rest.length) lines.push(nameSet(target, rest) + ": none");
      return lines;
    },
    alone: false
  },
  {
    name: "Party", mood: "Palette", detents: 5, spans: true, onMono: true,
    strip: ["#ff00ff", "#ffff00", "#00ffff", "#ff00ff", "#ffff00", "#00ffff", "#ff00ff"],
    entries: function (target, pace, mood) {
      var speed = lerp(1, 4, pace);
      var colours = [tone(PARTY_FIRST, mood), tone(PARTY_SECOND, mood),
                     tone(PARTY_THIRD, mood)];
      var groups;
      if (target.kind === "outputs") {
        groups = roundRobin(target.playing, Math.min(3, target.playing.length))
                 .map(function (group) {
                   return nameSet(target, group);
                 });
      } else {
        groups = runThirds(target.name, target.count, target.reversed,
                           Math.min(3, target.count),
                           target.lights && target.lights.slice().sort(function (a, b) {
                             return a - b;
                           }));
      }
      return groups.map(function (selector, i) {
        return selector + " colour=" + colours[i] + ": flash speed=" + speed +
               " flashes=1 window=0.5" + (i ? " phase=" + [0, 0.33, 0.67][i] : "");
      });
    },
    alone: function (target, pace, mood) {
      return [target.selector + " colour=" + tone(PARTY_FIRST, mood) +
              ": flash speed=" + lerp(1, 4, pace) + " flashes=1 window=0.5"];
    }
  }
];

export function lookNamed(id) {
  return LOOKS.filter(function (l) { return (l.id || l.name) === id; })[0] || null;
}

export function keyOf(look) { return look.id || look.name; }

export function canPlay(look, target) {
  if (!look) return true;
  if (target.kind === "run" && isBanked(look)) return target.count > 1 || look.alone !== false;
  if (!target.colour && !look.onMono) return false;
  if (target.count === 1 && look.alone === false) return false;
  if (target.kind === "run" && !look.spans) return false;
  return true;
}

export function whyNot(look, target) {
  if (!target.colour && !look.onMono) return "this look needs colour, and " +
                                             target.label.toLowerCase() + " is mono";
  if (target.count === 1 && look.alone === false)
    return "this look needs several lights";
  if (target.kind === "run" && !look.spans) return "this look needs separate lights";
  return "play this on " + target.label.toLowerCase();
}

export function lookLines(look, target, pace, mood, colour) {
  if (!look || !canPlay(look, target)) return [];
  var lines = (target.count === 1 && look.alone)
    ? look.alone(target, pace, mood, colour)
    : look.entries(target, pace, mood, colour);
  return target.colour ? lines : lines.map(withoutColour);
}

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

export function blinkSpeed(pace) { return lerp(0.3, 3, pace); }

export function blinkDuty(mood) { return lerp(0.1, 0.9, mood); }

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

var BANKED_LOOKS = ["Emergency", "Traffic light", "Pelican crossing"];

export function isBanked(look) {
  return !!look && BANKED_LOOKS.indexOf(look.name) >= 0;
}

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
