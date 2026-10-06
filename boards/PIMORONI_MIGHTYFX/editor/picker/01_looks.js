<script>
// The FX picker, a page for choosing what the board plays and saving it as effects.txt. It is
// the numbered parts in this folder joined in order, each part able to replace what an earlier
// one defines, and this first part holds the looks.

// The catalogue is generated beside this page; without it the screen sizes and ports
// cannot be known, so say so instead of failing silently
if (typeof CATALOGUE === "undefined") {
  window.CATALOGUE = {board_settings: {screena: ["2.8", "1.54"], screenb: ["2.8", "1.54"]},
                      screen_ports: ["screena", "screenb"], strips: ["stripl", "stripr"]};
  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("banner").innerHTML =
      "<div class='banner warn'>catalogue.js is missing from this folder, so the " +
      "board's ports are assumed. Run tools/build_editor.py to write it.</div>";
  });
}

// The board the page is for, which says whether it offers the network looks
var BOARD = {wireless: false};

var HEADER = "# Written by the FX picker. Everything here can be edited by hand;\n" +
             "# MANUAL.html on this drive explains every line.\n";

// ---- helpers -------------------------------------------------------------------

function r2(n) { return Math.round(n * 100) / 100; }
function lerp(a, b, t) { return r2(a + (b - a) * t); }

// Each look picks from a palette of its own, so the middle of the slider is the
// colour its card shows and moving it stays within what suits that look
function tone(palette, t) {
  return palette[Math.min(palette.length - 1, Math.floor(t * palette.length))];
}

// A travelling effect's length scales with the run so the wave keeps its
// proportion whatever the light count
function span(count, mood) {
  return Math.max(2, Math.round(count * lerp(2, 0.6, mood)));
}

function quoted(name) {
  return name.indexOf(" ") >= 0 ? '"' + name + '"' : name;
}

// A run of numbers as the file writes them: climbing or falling by one closes up
// into a range, a pair stays a pair, and anything else is listed
function rangify(list) {
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

// Some of a target's playing lamps as the file names them. A target whose lamps are not
// numbered outputs, such as mono channels, names its own sets
function nameSet(target, set) {
  return target.nameSet ? target.nameSet(set) : target.name + rangify(set);
}

// The playing outputs split round-robin into up to three groups, which is how a
// three-colour look lands one colour per light in turn
function roundRobin(playing, ways) {
  var groups = [];
  playing.forEach(function (which, i) {
    var at = i % ways;
    (groups[at] = groups[at] || []).push(which);
  });
  return groups;
}

// A run cut into up to three contiguous parts, as selectors, low end first or high
// end first to match how it is wired
function runThirds(name, count, reversed, ways, lights) {
  // Places along the stretch, numbered by the run's own lights where the stretch has them, so
  // a stretch partway along a strip names its own lights
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

// A mono output has no colour to be given, so the setting comes back off the line
// before it is written. What is left is the same effect, in whatever the lamp is
function withoutColour(line) {
  return line.replace(/\s+colour=[^\s:]+/g, "");
}

// ---- the looks -----------------------------------------------------------------
// Each look writes real entries for whatever target it is handed: a bank of outputs
// in the order they are to play, or a run of any length. alone() is the form it
// takes on a target of one light, and false where it has no such form.

var BREATHE_TONES = ["blue", "cool", "cyan", "green", "warm"];
var SPARKLE_TONES = ["cyan", "cool", "white", "warm", "yellow"];
var SCANNER_TONES = ["magenta", "blue", "red", "yellow", "white"];
var CHASE_TONES = ["magenta", "white", "yellow", "cyan", "green"];
var COUNTER_TONES = ["white", "cyan", "green", "yellow", "red"];
var PARTY_FIRST = ["red", "blue", "magenta", "cyan", "white"];
var PARTY_SECOND = ["green", "white", "yellow", "warm", "red"];
var PARTY_THIRD = ["blue", "green", "cyan", "white", "magenta"];

var LOOKS = [
  {
    // The one look with nothing moving in it. A scene that wants a lamp to sit at one
    // colour has no effect to reach for otherwise, and on a board whose only light of
    // its own is a single LED that is most of what it is for. The colour is chosen
    // rather than slid to, so this is the one look whose settings are not two sliders
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
    name: "Campfire", mood: "Embers to blaze", spans: true, onMono: true,
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
    // Two banks flashing against each other with a quiet gap between, landed on the
    // playing outputs in their order, so a lightbar of any width works
    name: "Emergency", mood: "Red and blue to amber", spans: false, onMono: true,
    strip: ["#dd2222", "#2222dd", "#dd2222", "#111111", "#2222dd", "#dd2222", "#2222dd"],
    entries: function (target, pace, mood) {
      var speed = lerp(0.6, 2.5, pace);
      var amber = mood > 0.75;
      var playing = target.playing;
      var half = playing.length === 1 ? 1 : Math.floor(playing.length / 2);
      var left = playing.slice(0, half);
      var right = playing.slice(playing.length - half);
      var gap = playing.slice(half, playing.length - half);
      var lines = [nameSet(target, left) + " colour=" + (amber ? "yellow" : "red") +
                   ": flash speed=" + speed + " flashes=3 window=0.5"];
      if (right.length && playing.length > 1)
        lines.push(nameSet(target, right) + " colour=" + (amber ? "yellow" : "blue") +
                   ": flash speed=" + speed + " flashes=3 window=0.5 phase=0.5");
      if (gap.length && playing.length > 1)
        lines.push(nameSet(target, gap) + ": none");
      return lines;
    },
    alone: function (target, pace, mood) {
      return [target.selector + " colour=" + (mood > 0.75 ? "yellow" : "red") +
              ": flash speed=" + lerp(0.6, 2.5, pace) + " flashes=3 window=0.5"];
    }
  },
  {
    // Five lamps in the crossing's own colours, landed on the first five playing
    // outputs; any beyond them are told to stay dark, and fewer take fewer lamps
    name: "Pelican crossing", mood: "How soft the change is", spans: false, onMono: true,
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
    // Three colours chase each other across whatever plays it: the lights split into
    // three sets, each flashing in its own colour a third of a beat apart
    name: "Party", mood: "Colour", spans: true, onMono: true,
    strip: ["#ff00ff", "#ffff00", "#00ffff", "#ff00ff", "#ffff00", "#00ffff", "#ff00ff"],
    entries: function (target, pace, mood) {
      var speed = lerp(1, 4, pace);
      var colours = [tone(PARTY_FIRST, mood), tone(PARTY_SECOND, mood),
                     tone(PARTY_THIRD, mood)];
      var groups;
      if (target.kind === "outputs") {
        // A target whose lamps are not whole outputs, broken-out channels say, names its
        // own sets of them
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

// Looks whose colour is not in the file at all: the board fetches it and plays what
// it is told. Only a wireless board is offered them
var NET_LOOKS = [
  {
    name: "CheerLights", mood: "How hard it lands", spans: true, onMono: false,
    net: true, says: "the colour everyone is sending to cheerlights.com",
    strip: ["#e02020", "#e08a20", "#20b060", "#2060e0", "#8a20e0", "#e02090", "#20c0c0"],
    entries: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(1.5, 0.1, mood) +
              ": cheerlights every=" + Math.round(lerp(60, 5, pace)) + "s"];
    },
    alone: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(1.5, 0.1, mood) +
              ": cheerlights every=" + Math.round(lerp(60, 5, pace)) + "s"];
    }
  },
  {
    name: "Time of day", mood: "Dawn to dusk", spans: true, onMono: true,
    net: true, says: "the clock the board sets itself by, drawn across the run",
    strip: ["#12204a", "#3a3f7a", "#c06a3a", "#ffb060", "#ffe6b0", "#7ea8d8", "#12204a"],
    entries: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(2, 0.2, pace) +
              ": clock length=" + span(target.count, mood) + " warmth=" + lerp(0, 1, mood)];
    },
    alone: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(2, 0.2, pace) +
              ": clock warmth=" + lerp(0, 1, mood)];
    }
  },
  {
    name: "Weather", mood: "Calm to stormy", spans: true, onMono: true,
    net: true, says: "what it is doing outside, taken from a forecast",
    strip: ["#9fb6c4", "#c8d6df", "#7f97a8", "#e8eef2", "#6d8496", "#b6c8d4", "#8fa6b6"],
    entries: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(1.2, 0.15, mood) +
              ": weather every=" + Math.round(lerp(30, 2, pace)) + "m" +
              " length=" + span(target.count, mood)];
    },
    alone: function (target, pace) {
      return [target.selector + ": weather every=" + Math.round(lerp(30, 2, pace)) + "m"];
    }
  },
  {
    name: "Whatever I send it", mood: "How long it holds", spans: true, onMono: true,
    net: true, says: "a colour posted to the board's own address",
    strip: ["#00857d", "#00857d", "#efece6", "#00857d", "#efece6", "#00857d", "#00857d"],
    entries: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(1, 0.05, pace) +
              ": posted hold=" + Math.round(lerp(5, 300, mood)) + "s"];
    },
    alone: function (target, pace, mood) {
      return [target.selector + " ease=" + lerp(1, 0.05, pace) +
              ": posted hold=" + Math.round(lerp(5, 300, mood)) + "s"];
    }
  }
];

// The looks this board offers
function everyLook() {
  return LOOKS.concat(BOARD.wireless ? NET_LOOKS : []);
}

function lookNamed(id) {
  return everyLook().filter(function (l) { return (l.id || l.name) === id; })[0] || null;
}

// What a look is kept as, which is its own id where it has one and its name otherwise
function keyOf(look) { return look.id || look.name; }

function luminance(colour) {
  var hex = colour.replace("#", "");
  return (0.299 * parseInt(hex.slice(0, 2), 16) + 0.587 * parseInt(hex.slice(2, 4), 16) +
          0.114 * parseInt(hex.slice(4, 6), 16)) / 255;
}

// The brightest a look ever asks for, which is the lamp a mono run drives at full
function peakOf(look) {
  if (!look || !look.strip.length) return 1;
  return Math.max.apply(null, look.strip.map(luminance)) || 1;
}

// What a colour comes to on a lamp that has none: the brightness it would drive, in
// the warm white a mono output actually lights. Scaled against the look's own
// brightest, so a look made of deep colours is not drawn as a row of dark lamps
function asMono(colour, peak) {
  var lit = Math.min(1, luminance(colour) / (peak || 1));
  return "rgb(" + Math.round(255 * lit) + "," + Math.round(226 * lit) + "," +
         Math.round(178 * lit) + ")";
}

// Whether a look has anything to give a target: a colour look cannot land on a mono
// lamp, a banked look cannot land on a run, and some have no single-light form
function canPlay(look, target) {
  if (!look) return true;
  if (!target.colour && !look.onMono) return false;
  if (target.count === 1 && look.alone === false) return false;
  if (target.kind === "run" && !look.spans) return false;
  return true;
}

// Why not, in the words of the thing that cannot happen
function whyNot(look, target) {
  if (!target.colour && !look.onMono) return "this look is all colour, and " +
                                             target.label.toLowerCase() + " is mono";
  if (target.count === 1 && look.alone === false)
    return "this look is shaped to several lights";
  if (target.kind === "run" && !look.spans) return "this look is shaped to separate lights";
  return "play this on " + target.label.toLowerCase();
}

// The lines one look writes for one target, in the form that target can take
function linesFor(look, target, pace, mood, colour) {
  if (!look || !canPlay(look, target)) return [];
  var lines = (target.count === 1 && look.alone)
    ? look.alone(target, pace, mood, colour)
    : look.entries(target, pace, mood, colour);
  return target.colour ? lines : lines.map(withoutColour);
}
