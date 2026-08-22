# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# Generated from editor/*.html and the autofx tables by tools/build_editor.py.
# Edit those and rebuild; edits here are lost.


PICKER = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>FX Picker</title>
<script src="catalogue.js"></script>
<style>
:root{
 --bg:#f5f3ef; --panel:#fff; --ink:#26221e; --dim:#8a8378; --line:#e2ddd4;
 --accent:#00857d; --accent-ink:#fff; --warn:#b33; --warn-bg:#fbeaea;
}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
header{display:flex;align-items:center;gap:.8rem;padding:.8rem 1.4rem;background:var(--panel);
 border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header h1{font-size:1.1rem;margin:0 auto 0 0}
button{font:inherit;padding:.5rem 1rem;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
button:disabled{opacity:.4;cursor:default}
main{max-width:44rem;margin:1.5rem auto;padding:0 1.4rem}
#status{font-size:.85rem;color:var(--dim)}
.banner{padding:.8rem 1.1rem;border-radius:10px;margin:1rem 0;background:#e7f2f1}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.banner pre{margin:.4rem 0 0;white-space:pre-wrap;font-size:.85rem}

.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(12.5rem,1fr));gap:1rem;margin:1rem 0}
.card{background:var(--panel);border:2px solid var(--line);border-radius:14px;padding:0;
 overflow:hidden;cursor:pointer;text-align:left;transition:border-color .15s, transform .1s}
.card:hover{transform:translateY(-2px)}
.card.picked{border-color:var(--accent)}
.card .strip{height:3.2rem;display:flex}
.card .strip span{flex:1}
.card .label{padding:.6rem .9rem .8rem}
.card .label b{display:block;font-size:1rem}

.sliders{background:var(--panel);border:1px solid var(--line);border-radius:14px;
 padding:1.1rem 1.4rem;margin:1.2rem 0;display:none}
.sliders.shown{display:block}
.slider{display:grid;grid-template-columns:6.5rem 1fr 6.5rem;align-items:center;gap:1rem;margin:.7rem 0}
.slider label{font-weight:600}
.slider input{width:100%;accent-color:var(--accent)}
.slider .ends{font-size:.8rem;color:var(--dim);text-align:right}
.slider .ends:first-of-type{text-align:left}
.actions{display:flex;gap:.8rem;align-items:center;margin-top:1rem;flex-wrap:wrap}
.actions .grow{margin-left:auto}

.screens{background:var(--panel);border:1px solid var(--line);border-radius:14px;
 padding:1.1rem 1.4rem;margin:1.2rem 0;display:none}
.screens.shown{display:block}
.screens h2{font-size:1rem;margin:0 0 .3rem}
.screens .hint{font-size:.85rem;color:var(--dim);margin:.2rem 0 .6rem}
.screen-row{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin:.6rem 0}
.screen-row .port{font-weight:600;width:5.5rem}
.thumb{width:4.6rem;height:3.2rem;border:2px solid var(--line);border-radius:8px;overflow:hidden;
 padding:0;background:var(--panel);display:flex;align-items:center;justify-content:center;
 font-size:.7rem;color:var(--dim);flex-direction:column;line-height:1.2}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.thumb.picked{border-color:var(--accent)}
.thumb small{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:0 .2rem}
.screen-row input[type=number]{font:inherit;font-size:.85rem;width:4.5rem;padding:.3rem .4rem;
 border:1px solid var(--line);border-radius:6px}
.opt{display:flex;align-items:center;gap:.35rem;font-size:.85rem;color:var(--dim);cursor:pointer}
.screen-row .drop{margin-left:auto;border:none;background:none;color:var(--dim);
 font-size:1.2rem;line-height:1;padding:.1rem .5rem}
.screen-row .drop:hover{color:var(--warn)}
.screens h2 + .hint{margin-top:0}
.screens h2:not(:first-child){margin-top:1rem}

details{margin:1.2rem 0}
summary{cursor:pointer;color:var(--dim);font-size:.9rem}
pre.file{font:.9rem/1.5 ui-monospace,Consolas,monospace;background:var(--panel);
 border:1px solid var(--line);border-radius:10px;padding:1rem;white-space:pre-wrap}
footer{max-width:44rem;margin:0 auto 2rem;padding:0 1.4rem;font-size:.8rem;color:var(--dim)}
</style>
</head>
<body>
<header>
 <h1>Make some lights</h1>
 <span id="status"></span>
 <button id="open">Open the FX drive</button>
 <button id="save" class="primary" disabled>Put it on the board</button>
 <button id="check" disabled>Did it work?</button>
</header>
<main>
 <div id="banner"></div>
 <p>Pick a look. Slide until it feels right. Put it on the board.</p>
 <div class="gallery" id="gallery"></div>
 <div class="sliders" id="sliders">
  <div class="slider">
   <label>Pace</label>
   <input type="range" id="pace" min="0" max="1" step="0.01" value="0.5">
  </div>
  <div class="slider">
   <label id="mood-label">Colour</label>
   <input type="range" id="mood" min="0" max="1" step="0.01" value="0.5">
  </div>
  <div class="actions">
   <span id="picked-name" style="font-weight:600"></span>
   <label class="opt grow"><input type="checkbox" id="outputs" checked>
    play on the board's own lights</label>
   <label class="opt" title="The board plays the file as soon as it is saved, with no eject"><input type="checkbox" id="straight">
    play it as soon as I save</label>
  </div>
 </div>
 <div class="screens" id="screens"></div>
 <details>
  <summary>The file this writes (effects.txt, editable by hand too)</summary>
  <pre class="file" id="preview"></pre>
 </details>
</main>
<footer>
A concept. Each look writes a complete effects.txt, which stays a plain file
anyone can open and edit by hand.
</footer>

<script>
"use strict";

// ---- prefabs ---------------------------------------------------------------
// Each look is a writer of a whole effects.txt, taking pace and mood as 0..1.
// Pace is tempo. Mood is the look's own second decision, named per look, so a
// slider always does something visible for that look. Values are rounded so
// the written file reads as something a person could have typed.

function r2(n) { return Math.round(n * 100) / 100; }
function lerp(a, b, t) { return r2(a + (b - a) * t); }

// A palette the mood slider walks: warm embers to cold blues via full colour
var MOODS = ["red", "warm", "yellow", "green", "cyan", "cool", "blue"];
function moodColour(t) { return MOODS[Math.min(MOODS.length - 1, Math.floor(t * MOODS.length))]; }

// Each look picks from a palette of its own, so the middle of the slider is the
// colour its card shows and moving it stays within what suits that look
function tone(palette, t) {
  return palette[Math.min(palette.length - 1, Math.floor(t * palette.length))];
}

// A travelling effect's length scales with the strip so the wave keeps its
// proportion whatever the LED count
function span(count, mood) {
  return Math.max(2, Math.round(count * lerp(2, 0.6, mood)));
}

// Looks with spans true play along any strip handed to write() as
// {selector, count} pairs; those shaped to named lamps sit strips out.
// Between them they cover every effect that travels across the outputs:
// rainbow_wave, pulse_wave, blink_wave, flash_sequence, sweep and binary_counter.
var LOOKS = [
  {
    name: "Rainbow", mood: "Colour spread", spans: true,
    strip: ["#e33", "#e73", "#ea3", "#3a5", "#36c", "#63c", "#a3c"],
    write: function (pace, mood, strips) {
      var speed = lerp(0.05, 0.8, pace);
      var lines = "out1-7: rainbow_wave speed=" + speed +
                  " length=" + Math.round(lerp(14, 4, mood)) + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + ": rainbow_wave speed=" + speed +
                 " length=" + span(s.count, mood) + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Campfire", mood: "Embers to blaze", spans: true,
    strip: ["#812200", "#c43a00", "#ff5a00", "#ff8c1a", "#ff5a00", "#c43a00", "#812200"],
    write: function (pace, mood, strips) {
      var flicker = "flicker brightness=" + lerp(0.5, 1, mood) +
                    " dimness=" + lerp(0.7, 0.35, mood) +
                    " bright_min=" + lerp(0.1, 0.02, pace) + " bright_max=" + lerp(0.4, 0.1, pace) +
                    " dim_min=" + lerp(0.08, 0.02, pace) + " dim_max=" + lerp(0.3, 0.08, pace);
      var lines = "out1-7 colour=ff5a00: " + flicker + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=ff5a00: " + flicker + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Breathe", mood: "Colour", spans: true,
    strip: ["#2b7f8f", "#37a0b4", "#43c1d9", "#56d8f0", "#43c1d9", "#37a0b4", "#2b7f8f"],
    write: function (pace, mood, strips) {
      var colour = tone(["blue", "cool", "cyan", "green", "warm"], mood);
      var pulse = "pulse speed=" + lerp(0.08, 0.5, pace);
      var ease = lerp(0.8, 0.2, pace);
      var lines = "out1-7 colour=" + colour + " ease=" + ease + ": " + pulse + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=" + colour + " ease=" + ease + ": " + pulse + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Wave", mood: "Wave length", spans: true,
    strip: ["#122438", "#2a4a6a", "#4a7fb5", "#7fb5e6", "#4a7fb5", "#2a4a6a", "#122438"],
    write: function (pace, mood, strips) {
      var speed = lerp(0.1, 1, pace);
      var lines = "out1-7 colour=cool: pulse_wave speed=" + speed +
                  " length=" + Math.round(lerp(14, 4, mood)) + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=cool: pulse_wave speed=" + speed +
                 " length=" + span(s.count, mood) + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Sparkle", mood: "Colour", spans: true,
    strip: ["#ffffff", "#999999", "#ffffff", "#cccccc", "#eeeeee", "#888888", "#ffffff"],
    write: function (pace, mood, strips) {
      var colour = tone(["cyan", "cool", "white", "warm", "yellow"], mood);
      var random = "random interval=" + lerp(0.25, 0.03, pace) +
                   " brightness_min=0 brightness_max=1";
      var lines = "out1-7 colour=" + colour + ": " + random + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=" + colour + ": " + random + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Scanner", mood: "Colour", spans: true,
    strip: ["#330000", "#660000", "#cc0000", "#ff3333", "#cc0000", "#660000", "#330000"],
    write: function (pace, mood, strips) {
      var colour = tone(["magenta", "blue", "red", "yellow", "white"], mood);
      var fade = lerp(0.5, 0.15, pace);
      var speed = lerp(0.3, 2, pace);
      var lines = "out1-7 colour=" + colour + " fade=" + fade +
                  ": sweep speed=" + speed + " length=7 extent=1\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=" + colour + " fade=" + fade +
                 ": sweep speed=" + speed + " length=" + s.count +
                 " extent=" + Math.max(1, Math.round(s.count / 8)) + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Chase", mood: "Colour", spans: true,
    strip: ["#111111", "#111111", "#ffff00", "#ffd24a", "#111111", "#111111", "#111111"],
    write: function (pace, mood, strips) {
      var colour = tone(["magenta", "white", "yellow", "cyan", "green"], mood);
      var speed = lerp(0.3, 2, pace);
      var fade = lerp(0.4, 0.1, pace);
      var lines = "out1-7 colour=" + colour + " fade=" + fade +
                  ": flash_sequence speed=" + speed + " length=7 flashes=1 window=0.4\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=" + colour + " fade=" + fade +
                 ": flash_sequence speed=" + speed + " length=" + s.count +
                 " flashes=1 window=0.4\\n";
      });
      return lines;
    }
  },
  {
    name: "Counter", mood: "Colour", spans: true,
    strip: ["#00ff00", "#111111", "#00ff00", "#00ff00", "#111111", "#00ff00", "#111111"],
    write: function (pace, mood, strips) {
      var colour = tone(["white", "cyan", "green", "yellow", "red"], mood);
      var interval = lerp(1, 0.08, pace);
      var lines = "out1-7 colour=" + colour + ": binary_counter interval=" + interval + "\\n";
      (strips || []).forEach(function (s) {
        lines += s.selector + " colour=" + colour + ": binary_counter interval=" +
                 interval + "\\n";
      });
      return lines;
    }
  },
  {
    name: "Emergency", mood: "Red and blue to amber", spans: false,
    strip: ["#dd2222", "#2222dd", "#dd2222", "#111111", "#2222dd", "#dd2222", "#2222dd"],
    write: function (pace, mood) {
      var speed = lerp(0.6, 2.5, pace);
      var amber = mood > 0.75;
      var left = amber ? "yellow" : "red";
      var right = amber ? "yellow" : "blue";
      return "out1-3 colour=" + left + ": flash speed=" + speed + " flashes=3 window=0.5\\n" +
             "out5-7 colour=" + right + ": flash speed=" + speed + " flashes=3 window=0.5 phase=0.5\\n" +
             "out4: none\\n";
    }
  },
  {
    name: "Pelican crossing", mood: "Lamp softness", spans: false,
    strip: ["#ff0000", "#ff7800", "#00d28c", "#ff0000", "#00d28c", "#111111", "#111111"],
    write: function (pace, mood) {
      var scale = lerp(2, 0.4, pace);
      return "out1-5 colour=red,ff7800,00d28c,red,00d28c ease=" + lerp(0.05, 0.6, mood) +
             ": pelican_crossing red_interval=" + r2(8 * scale) +
             " flashing_interval=" + r2(6 * scale) +
             " green_interval=" + r2(20 * scale) +
             " amber_interval=" + r2(3 * scale) + "\\n" +
             "out6-7: none\\n";
    }
  },
  {
    name: "Party", mood: "Colour", spans: true,
    strip: ["#ff00ff", "#ffff00", "#00ffff", "#ff00ff", "#ffff00", "#00ffff", "#ff00ff"],
    write: function (pace, mood, strips) {
      var hold = Math.round(lerp(20, 6, pace));
      // A colour per scene, so the three on the card are the three it plays
      var first = tone(["red", "blue", "magenta", "cyan", "white"], mood);
      var second = tone(["green", "white", "yellow", "warm", "red"], mood);
      var third = tone(["blue", "green", "cyan", "white", "magenta"], mood);
      var chase = "", strobe = "", twinkle = "";
      (strips || []).forEach(function (s) {
        chase += s.selector + " colour=" + first + ": blink_wave speed=" +
                 lerp(0.6, 3, pace) + " length=" + span(s.count, mood) + "\\n";
        strobe += s.selector + " colour=" + second + ": flash speed=" + lerp(1, 4, pace) +
                  " flashes=2 window=0.3\\n";
        twinkle += s.selector + " colour=" + third + ": random interval=" +
                   lerp(0.2, 0.03, pace) + "\\n";
      });
      return "[Chase: " + hold + "s]\\n" +
             "out1-7 colour=" + first + ": blink_wave speed=" + lerp(0.6, 3, pace) +
             " length=" + Math.round(lerp(10, 3, mood)) + "\\n" + chase +
             "[Strobe: " + hold + "s]\\n" +
             "out1-7 colour=" + second + ": flash speed=" + lerp(1, 4, pace) +
             " flashes=2 window=0.3\\n" + strobe +
             "[Twinkle: " + hold + "s]\\n" +
             "out1-7 colour=" + third + ": random interval=" + lerp(0.2, 0.03, pace) +
             "\\n" + twinkle;
    }
  },
];

var HEADER = "# Written by the FX picker. Everything here can be edited by hand;\\n" +
             "# MANUAL.html on this drive explains every line.\\n";

// ---- state and rendering -----------------------------------------------------

var state = {
  look: null, dirHandle: null, fileHandle: null,
  boardResidue: [],  // board entry settings that are not screens or strips, kept as written
  ports: [],         // screens in play, as written in entries ("screenA")
  sizes: {},         // port -> "2.8" | "1.54", or null where the file leaves it unsaid
  kept: {},          // port -> its existing entry lines, for the keep-as-is choice
  carried: {},       // port -> the entry's channel settings less rotation, reused on new lines
  rotations: {},     // port -> quarter turn, or null to write none
  pingpong: {},      // port -> play a chosen gif or slideshow back and forth
  holds: {},         // port -> seconds to wait where it turns around, or none
  choices: {},       // port -> {mode: "keep"|"none"|"media", media}
  strips: [],        // strips in play, as written ("stripL")
  lengths: {},       // strip -> LED count, or null where the file leaves it unsaid
  reversed: {},      // strip -> wired far end first, written as a descending range
  stripKept: {},     // strip -> its existing entry lines
  stripChoices: {},  // strip -> {mode: "look"|"keep"|"none"}
  media: [],         // {name, kind: "gif"|"image"|"folder"} found on the drive
  outputs: true,     // whether the look plays on the board's own seven lights
};


function withoutOutputs(text) {
  // What is left of a look with the board's own lights out of it. A scene with
  // nothing left in it goes too, since a heading with no entries under it is a
  // scene that shows nothing and says so in errors.txt
  var kept = text.split("\\n").filter(function (line) {
    return !/^out\\d/i.test(line.trim());
  });
  var plays = kept.some(function (line) {
    var held = line.trim();
    return held.indexOf(":") >= 0 && held.charAt(0) !== "[" && held.charAt(0) !== "#";
  });
  if (!plays) {
    kept = kept.filter(function (line) { return line.trim().charAt(0) !== "["; });
  }
  return kept.join("\\n");
}

// What the board's file already says: hardware settings to carry, screens and
// strips to offer. Pure text in, so the same reading is checkable off the drive.
// Screen sizes, rotations and strip lengths are managed here so they can be
// chosen; every other board setting is carried through untouched.
function absorbText(text) {
  state.boardResidue = [];
  state.straight = false;
  state.ports = [];
  state.sizes = {};
  state.kept = {};
  state.carried = {};
  state.rotations = {};
  state.pingpong = {};
  state.holds = {};
  state.strips = [];
  state.lengths = {};
  state.reversed = {};
  state.stripKept = {};
  state.soundKept = null;
  state.sound = null;
  state.soundLoop = false;
  text.split("\\n").forEach(function (line) {
    var board = line.match(/^\\s*board\\s*:\\s*(.*)$/i);
    if (board) {
      board[1].split(/\\s+/).forEach(function (token) {
        if (token === "") return;
        var reload = token.match(/^reload=(.+)$/i);
        if (reload) {
          state.straight = reload[1].toLowerCase() === "auto";
          return;
        }
        var size = token.match(/^(screen[ab])=(.+)$/i);
        var count = token.match(/^(strip[lr])=(.+)$/i);
        if (size) state.sizes[declarePort(size[1])] = size[2];
        else if (count) state.lengths[declareStrip(count[1])] = count[2];
        else state.boardResidue.push(token);
      });
      return;
    }
    var entry = line.match(/^\\s*(screen[ab])\\b([^:]*):/i);
    if (entry) {
      var port = declarePort(entry[1]);
      (state.kept[port] = state.kept[port] || []).push(line);
      if (!(port in state.carried)) state.carried[port] = entry[2].trim();
      return;
    }
    var sound = line.match(/^\\s*audio\\b[^:]*:/i);
    if (sound) {
      state.soundKept = line;
      var named = line.match(/file\\s*=\\s*"?([^"\\s]+)"?/i);
      if (named) state.sound = named[1];
      state.soundLoop = /loop\\s*=\\s*(true|yes|on)\\b/i.test(line);
      return;
    }
    var strip = line.match(/^\\s*(strip[lr])\\b[^:]*:/i);
    if (strip) {
      var name = declareStrip(strip[1]);
      (state.stripKept[name] = state.stripKept[name] || []).push(line);
    }
  });
  document.getElementById("straight").checked = state.straight;
  state.ports.forEach(function (port) {
    if (!(port in state.sizes)) state.sizes[port] = null;
    state.choices[port] = { mode: state.kept[port] ? "keep" : "none" };
    state.rotations[port] = null;
    state.pingpong[port] = false;
    state.holds[port] = "";
    // rotation is chosen in the picker, so it comes out of the carried settings
    if (state.carried[port]) {
      var rest = [];
      state.carried[port].split(/\\s+/).forEach(function (token) {
        var turn = token.match(/^rotation=(\\d+)$/i);
        if (turn) state.rotations[port] = turn[1];
        else if (token !== "") rest.push(token);
      });
      state.carried[port] = rest.join(" ");
    }
  });
  state.strips.forEach(function (name) {
    if (!(name in state.lengths)) state.lengths[name] = null;
    state.reversed[name] = false;
    state.stripChoices[name] = { mode: state.stripKept[name] ? "keep" : "look" };
  });
  // The board builds its strips once, at start, so only these come up on a reload;
  // one added later needs the board turning off and on, and the save says so
  state.stripsAtStart = state.strips.slice();
}

function showing(port) {
  // Whether a screen is in the file at all: one showing nothing is not
  // declared either, since a declaration the file never uses is a panel the
  // board brings up for no one
  var choice = state.choices[port];
  return choice !== undefined && choice.mode !== "none";
}


function boardLine() {
  var tokens = state.boardResidue.slice();
  if (state.straight) tokens.push("reload=auto");
  state.ports.forEach(function (port) {
    if (state.sizes[port] && showing(port)) {
      tokens.push(port.toLowerCase() + "=" + state.sizes[port]);
    }
  });
  state.strips.forEach(function (name) {
    var choice = state.stripChoices[name];
    if (state.lengths[name] && choice && choice.mode !== "none") {
      tokens.push(name.toLowerCase() + "=" + state.lengths[name]);
    }
  });
  return tokens.length ? "board: " + tokens.join(" ") : "";
}

function portName(name) {
  return "screen" + name.slice(-1).toUpperCase();
}

function declarePort(name) {
  var port = portName(name);
  if (state.ports.indexOf(port) < 0) state.ports.push(port);
  return port;
}

function stripName(name) {
  return "strip" + name.slice(-1).toUpperCase();
}

function declareStrip(name) {
  var strip = stripName(name);
  if (state.strips.indexOf(strip) < 0) state.strips.push(strip);
  return strip;
}

function quoted(name) {
  return name.indexOf(" ") >= 0 ? '"' + name + '"' : name;
}

function screenLine(port, media, pace) {
  var selector = port;
  if (state.carried[port]) selector += " " + state.carried[port];
  if (state.rotations[port] != null) selector += " rotation=" + state.rotations[port];
  var back = state.pingpong[port] ? " ping_pong=true" : "";
  if (state.holds[port]) back += " hold=" + state.holds[port];
  if (media.kind === "folder")
    return selector + ": sequence folder=" + quoted(media.name) +
           " fps=" + lerp(1, 10, pace) + back;
  if (media.kind === "gif")
    return selector + ": gif file=" + quoted(media.name) + back;
  return selector + ": image file=" + quoted(media.name);
}

function soundLine() {
  // Sound does not follow scenes, so this goes above every heading
  if (state.sound)
    return "audio: wav file=" + quoted(state.sound) +
           (state.soundLoop ? " loop=true" : "");
  return state.soundKept;
}

function currentText() {
  if (!state.look) return "";
  var pace = parseFloat(document.getElementById("pace").value);
  var mood = parseFloat(document.getElementById("mood").value);
  var parts = [HEADER];
  var board = boardLine();
  if (board) parts.push(board + "\\n");
  state.ports.forEach(function (port) {
    var choice = state.choices[port];
    if (!choice || choice.mode === "none") return;
    if (choice.mode === "keep")
      (state.kept[port] || []).forEach(function (line) { parts.push(line + "\\n"); });
    else
      parts.push(screenLine(port, choice.media, pace) + "\\n");
  });
  var inPlay = [];
  state.strips.forEach(function (name) {
    var choice = state.stripChoices[name];
    if (!choice || choice.mode === "none") return;
    if (choice.mode === "keep") {
      (state.stripKept[name] || []).forEach(function (line) { parts.push(line + "\\n"); });
      return;
    }
    var count = Number(state.lengths[name]);
    if (!count) return;
    inPlay.push({ selector: state.reversed[name] ? name + count + "-1" : name, count: count });
  });
  var sound = soundLine();
  if (sound) parts.push(sound + "\\n");
  if (parts.length > 1) parts.push("\\n");
  var played = state.look.write(pace, mood, inPlay);
  parts.push(state.outputs ? played : withoutOutputs(played));
  return parts.join("");
}

function renderGallery() {
  var gallery = document.getElementById("gallery");
  LOOKS.forEach(function (look) {
    var card = document.createElement("button");
    card.className = "card";
    var strip = document.createElement("div");
    strip.className = "strip";
    look.strip.forEach(function (colour) {
      var cell = document.createElement("span");
      cell.style.background = colour;
      strip.appendChild(cell);
    });
    var label = document.createElement("div");
    label.className = "label";
    var name = document.createElement("b");
    name.textContent = look.name;
    label.appendChild(name);
    card.appendChild(strip);
    card.appendChild(label);
    card.onclick = function () { pick(look, card); };
    gallery.appendChild(card);
  });
}

function pick(look, card) {
  state.look = look;
  document.querySelectorAll(".card").forEach(function (c) { c.classList.remove("picked"); });
  card.classList.add("picked");
  document.getElementById("sliders").classList.add("shown");
  document.getElementById("picked-name").textContent = look.name;
  document.getElementById("mood-label").textContent = look.mood;
  renderScreens();
  update();
}

function update() {
  var text = currentText();
  document.getElementById("preview").textContent = text;
  document.getElementById("save").disabled = !(state.look && state.fileHandle) && !state.look;
  try { localStorage.setItem("fx-draft", text); } catch (e) {}
}

function banner(text, warn, detail) {
  var box = document.getElementById("banner");
  box.textContent = "";
  if (!text) return;
  var note = document.createElement("div");
  note.className = "banner" + (warn ? " warn" : "");
  note.textContent = text;
  if (detail) {
    var pre = document.createElement("pre");
    pre.textContent = detail;
    note.appendChild(pre);
  }
  box.appendChild(note);
}

// ---- screens ------------------------------------------------------------------

async function scanMedia(dir) {
  // What the drive holds that a screen can show: gifs and stills, PNG or JPEG,
  // and folders of them, which play as a slideshow
  state.media = [];
  state.sounds = [];
  for await (var pair of dir.entries()) {
    var name = pair[0], handle = pair[1];
    if (handle.kind === "file") {
      if (/\\.gif$/i.test(name)) state.media.push({ name: name, kind: "gif", handle: handle });
      else if (/\\.(png|jpe?g)$/i.test(name)) state.media.push({ name: name, kind: "image", handle: handle });
      else if (/\\.wav$/i.test(name)) state.sounds.push(name);
    } else if (name !== "System Volume Information") {
      for await (var inner of handle.entries()) {
        if (inner[1].kind === "file" && /\\.(gif|png|jpe?g)$/i.test(inner[0])) {
          state.media.push({ name: name, kind: "folder" });
          break;
        }
      }
    }
  }
}

function thumbButton(port, label, mode, media) {
  var button = document.createElement("button");
  button.className = "thumb";
  var choice = state.choices[port] || {};
  if (choice.mode === mode && (!media || choice.media === media)) button.classList.add("picked");
  if (media && media.handle) {
    media.handle.getFile().then(function (file) {
      var img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      button.insertBefore(img, button.firstChild);
    }).catch(function () {});
  }
  var caption = document.createElement("small");
  caption.textContent = label;
  button.appendChild(caption);
  button.onclick = function () {
    state.choices[port] = { mode: mode, media: media };
    renderScreens();
    update();
  };
  return button;
}

function sizeSelect(port) {
  // The panel sizes the board offers, plus silence where the file already relies
  // on the board's own default; choosing a size writes it into the board entry
  var pick = document.createElement("select");
  var offered = CATALOGUE.board_settings[port.toLowerCase()] || [];
  if (state.sizes[port] === null) {
    var quiet = document.createElement("option");
    quiet.textContent = "size as fitted";
    pick.appendChild(quiet);
  }
  offered.forEach(function (size) {
    var option = document.createElement("option");
    option.value = size;
    option.textContent = size + " inch";
    if (state.sizes[port] === size) option.selected = true;
    pick.appendChild(option);
  });
  pick.onchange = function () {
    if (pick.value) state.sizes[port] = pick.value;
    update();
  };
  return pick;
}

function renderScreens() {
  var box = document.getElementById("screens");
  box.textContent = "";
  box.className = "screens shown";
  var head = document.createElement("h2");
  head.textContent = "Screens";
  box.appendChild(head);
  var hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = !state.fileHandle
    ? "What each screen shows. Open the FX drive to see the pictures on it."
    : state.media.length
      ? "What each screen shows, from the pictures on the drive."
      : "No pictures on the drive yet. Drop a gif or png onto it and reopen.";
  box.appendChild(hint);
  CATALOGUE.screen_ports.forEach(function (name) {
    var port = portName(name);
    var row = document.createElement("div");
    row.className = "screen-row";
    var label = document.createElement("span");
    label.className = "port";
    label.textContent = "Screen " + port.slice(-1).toUpperCase();
    row.appendChild(label);
    if (state.ports.indexOf(port) < 0) {
      var add = document.createElement("button");
      add.textContent = "add this screen";
      add.onclick = function () {
        declarePort(port);
        state.sizes[port] = (CATALOGUE.board_settings[name] || ["2.8"])[0];
        state.choices[port] = { mode: "none" };
        state.rotations[port] = null;
        state.pingpong[port] = false;
        state.holds[port] = "";
        renderScreens();
        update();
      };
      row.appendChild(add);
      box.appendChild(row);
      return;
    }
    row.appendChild(sizeSelect(port));
    row.appendChild(turnSelect(port));
    if (state.kept[port]) row.appendChild(thumbButton(port, "as it is", "keep", null));
    state.media.forEach(function (media) {
      row.appendChild(thumbButton(port, media.name, "media", media));
    });
    var choice = state.choices[port] || {};
    if (choice.mode === "media" && choice.media.kind !== "image") {
      row.appendChild(optionCheck("back and forth",
        "Play it forwards then backwards, no jump at the loop", state.pingpong[port],
        function (on) { state.pingpong[port] = on; }));
      row.appendChild(holdBox(port));
    }
    row.appendChild(removeButton("screen", function () {
      state.ports = state.ports.filter(function (name) { return name !== port; });
      delete state.sizes[port];
      delete state.kept[port];
      delete state.carried[port];
      delete state.rotations[port];
      delete state.pingpong[port];
      delete state.holds[port];
      delete state.choices[port];
    }));
    box.appendChild(row);
  });
  renderStrips(box);
  renderSound(box);
}

function renderSound(box) {
  var head = document.createElement("h2");
  head.textContent = "Sound";
  box.appendChild(head);
  var hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = !state.fileHandle
    ? "A WAV played alongside the lights. Open the FX drive to see the sounds on it."
    : state.sounds.length
      ? "A WAV played alongside the lights, one at a time."
      : "No sounds on the drive yet. Drop a wav onto it and reopen.";
  box.appendChild(hint);

  var row = document.createElement("div");
  row.className = "screen-row";
  var label = document.createElement("span");
  label.className = "port";
  label.textContent = "Plays";
  row.appendChild(label);

  if (state.soundKept && !state.sound) row.appendChild(soundChoice("as it is", null));
  state.sounds.forEach(function (name) {
    row.appendChild(soundChoice(name, name));
  });
  if (state.sound || state.soundKept) {
    if (state.sound)
      row.appendChild(optionCheck("over and over",
        "Play it again as it ends, rather than once as the board starts",
        state.soundLoop, function (on) { state.soundLoop = on; }));
    row.appendChild(removeButton("sound", function () {
      state.sound = null;
      state.soundKept = null;
      state.soundLoop = false;
    }));
  }
  box.appendChild(row);
}

function soundChoice(label, name) {
  var button = document.createElement("button");
  button.className = "thumb";
  if (state.sound === name && (name || state.soundKept)) button.classList.add("picked");
  var caption = document.createElement("small");
  caption.textContent = label;
  button.appendChild(caption);
  button.onclick = function () {
    state.sound = name;
    if (name) state.soundKept = null;
    renderScreens();
    update();
  };
  return button;
}

function removeButton(what, drop) {
  var button = document.createElement("button");
  button.className = "drop";
  button.textContent = "\\u00d7";
  button.title = "Take this " + what + " out of the file, so the board does not set it up";
  button.onclick = function () {
    drop();
    renderScreens();
    update();
  };
  return button;
}


function holdBox(port) {
  // Seconds to wait where the playing turns around, which is what pauses a
  // ping-pong at each end instead of bouncing straight off
  var wrap = document.createElement("label");
  wrap.className = "opt";
  wrap.title = "Seconds to wait where it turns around";
  wrap.appendChild(document.createTextNode("hold"));
  var box = document.createElement("input");
  box.type = "number";
  box.min = 0;
  box.step = 0.5;
  box.value = state.holds[port] || "";
  box.placeholder = "0";
  box.onchange = function () {
    state.holds[port] = box.value && Number(box.value) > 0 ? box.value : "";
    update();
  };
  wrap.appendChild(box);
  return wrap;
}


function turnSelect(port) {
  // How the panel is mounted, in quarter turns; silence writes no rotation
  var pick = document.createElement("select");
  [["", "not turned"], ["90", "turned 90"], ["180", "turned 180"], ["270", "turned 270"]]
    .forEach(function (turn) {
      var option = document.createElement("option");
      option.value = turn[0];
      option.textContent = turn[1];
      if (state.rotations[port] === (turn[0] || null)) option.selected = true;
      pick.appendChild(option);
    });
  pick.onchange = function () {
    state.rotations[port] = pick.value || null;
    update();
  };
  return pick;
}

function optionCheck(label, title, on, apply) {
  var wrap = document.createElement("label");
  wrap.className = "opt";
  wrap.title = title;
  var tick = document.createElement("input");
  tick.type = "checkbox";
  tick.checked = on;
  tick.onchange = function () { apply(tick.checked); update(); };
  wrap.appendChild(tick);
  wrap.appendChild(document.createTextNode(label));
  return wrap;
}

function stripChoice(name, label, mode) {
  var button = document.createElement("button");
  button.className = "thumb";
  if ((state.stripChoices[name] || {}).mode === mode) button.classList.add("picked");
  var caption = document.createElement("small");
  caption.textContent = label;
  button.appendChild(caption);
  button.onclick = function () {
    state.stripChoices[name] = { mode: mode };
    renderScreens();
    update();
  };
  return button;
}

function renderStrips(box) {
  var head = document.createElement("h2");
  head.textContent = "Strips";
  box.appendChild(head);
  var hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = state.look && state.look.spans === false
    ? "The picked look is shaped to the board's own lights, so strips sit this one out."
    : "How many LEDs each strip has; the look plays along it.";
  box.appendChild(hint);
  CATALOGUE.strips.forEach(function (lower) {
    var name = stripName(lower);
    var row = document.createElement("div");
    row.className = "screen-row";
    var label = document.createElement("span");
    label.className = "port";
    label.textContent = "Strip " + name.slice(-1).toUpperCase();
    row.appendChild(label);
    if (state.strips.indexOf(name) < 0) {
      var add = document.createElement("button");
      add.textContent = "add this strip";
      add.onclick = function () {
        declareStrip(name);
        state.lengths[name] = 30;
        state.reversed[name] = false;
        state.stripChoices[name] = { mode: "look" };
        renderScreens();
        update();
      };
      row.appendChild(add);
      box.appendChild(row);
      return;
    }
    var count = document.createElement("input");
    count.type = "number";
    count.min = 1;
    count.placeholder = "LEDs";
    count.title = "How many LEDs the strip has";
    if (state.lengths[name]) count.value = state.lengths[name];
    count.onchange = function () {
      state.lengths[name] = count.value ? Number(count.value) : null;
      update();
    };
    row.appendChild(count);
    row.appendChild(optionCheck("far end first",
      "The strip is wired from the far end, so effects travel the other way",
      state.reversed[name], function (on) { state.reversed[name] = on; }));
    if (state.stripKept[name]) row.appendChild(stripChoice(name, "as it is", "keep"));
    row.appendChild(stripChoice(name, "with the look", "look"));
    row.appendChild(removeButton("strip", function () {
      state.strips = state.strips.filter(function (held) { return held !== name; });
      delete state.lengths[name];
      delete state.reversed[name];
      delete state.stripKept[name];
      delete state.stripChoices[name];
    }));
    box.appendChild(row);
  });
}

// ---- the drive ---------------------------------------------------------------

async function connect() {
  var dir = await window.showDirectoryPicker({ mode: "readwrite" });
  state.dirHandle = dir;
  state.fileHandle = await dir.getFileHandle("effects.txt");
  absorbText(await (await state.fileHandle.getFile()).text());
  await scanMedia(dir);
  renderScreens();
  document.getElementById("check").disabled = false;
  document.getElementById("status").textContent = "connected to the drive";
}

document.getElementById("save").onclick = async function () {
  if (!state.look) return;
  try {
    if (!state.fileHandle) await connect();
    var onBoard = await (await state.fileHandle.getFile()).text();
    var lastWritten = null;
    try { lastWritten = localStorage.getItem("fx-picker-wrote"); } catch (e) {}
    if (onBoard.indexOf("Written by the FX picker") < 0 && onBoard !== lastWritten &&
        onBoard.trim() !== "") {
      if (!confirm("The file on the board was written some other way, maybe by hand. Replace it?"))
        return;
    }
    var text = currentText();
    var writable = await state.fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    var back = await (await state.fileHandle.getFile()).text();
    if (back !== text) throw new Error("the file read back differently");
    try { localStorage.setItem("fx-picker-wrote", text); } catch (e) {}
    var newStrips = state.strips.filter(function (name) {
      return state.lengths[name] && (state.stripsAtStart || []).indexOf(name) < 0;
    });
    banner("On its way. Eject the FX drive on this computer, and the board plays it. " +
           "Double-press the board's button to bring the drive back, then ask 'Did it work?'." +
           (newStrips.length ? " The strip you added only comes up when the board starts, " +
                               "so turn it off and on once the eject is done." : ""));
  } catch (e) {
    state.fileHandle = null;
    state.dirHandle = null;
    banner("That didn't reach the board: " + e.name + ". Is the FX drive showing? " +
           "A double press of its button brings it back; then try again.", true);
  }
};

document.getElementById("check").onclick = async function () {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    var text = await (await handle.getFile()).text();
    banner("The board wasn't happy with some of it:", true, text.trim());
  } catch (e) {
    if (e.name === "NotFoundError")
      banner("All good. The board read the file and found nothing wrong.");
    else
      banner("Couldn't look: " + e.name + ". Is the drive showing?", true);
  }
};

document.getElementById("open").onclick = async function () {
  try {
    await connect();
    banner("");
    update();
  } catch (e) {
    banner("Could not open the drive: " + e.name + ". Is it showing? " +
           "A double press of the board's button brings it back.", true);
  }
};

document.getElementById("pace").oninput = update;
document.getElementById("mood").oninput = update;
document.getElementById("straight").onchange = function () {
  state.straight = document.getElementById("straight").checked;
  update();
};
document.getElementById("outputs").onchange = function () {
  state.outputs = document.getElementById("outputs").checked;
  update();
};

renderGallery();
renderScreens();
document.getElementById("save").disabled = false;
</script>
</body>
</html>
"""

EDITOR = """\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>FX Editor</title>
<script src="catalogue.js"></script>
<style>
:root{
 --bg:#f5f3ef; --panel:#fff; --ink:#26221e; --dim:#8a8378; --line:#e2ddd4;
 --accent:#00857d; --accent-ink:#fff; --warn:#b33; --warn-bg:#fbeaea;
 --target:#1f6feb; --effect:#0a7f78; --value:#a8500a; --scene:#7b3fb8;
 --comment:#8a8378; --faint:#5d656e;
}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
header{display:flex;align-items:center;gap:.8rem;padding:.8rem 1.4rem;background:var(--panel);
 border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header h1{font-size:1.1rem;margin:0 auto 0 0}
button{font:inherit;padding:.5rem 1rem;border:1px solid var(--line);border-radius:8px;
 background:var(--panel);cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
button:disabled{opacity:.4;cursor:default}
main{max-width:52rem;margin:1.5rem auto;padding:0 1.4rem}
#status{font-size:.85rem;color:var(--dim)}
.banner{padding:.8rem 1.1rem;border-radius:10px;margin:1rem 0;background:#e7f2f1}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.banner pre{margin:.4rem 0 0;white-space:pre-wrap;font-size:.85rem}

.editor{position:relative;background:var(--panel);border:1px solid var(--line);
 border-radius:14px;overflow:hidden;height:24rem}
.editor pre, .editor textarea{
 position:absolute;inset:0;margin:0;padding:1rem 1.2rem;border:0;
 font:14px/1.6 ui-monospace,Consolas,"Cascadia Mono",monospace;
 white-space:pre;overflow:auto;tab-size:4;
}
.editor pre{pointer-events:none;background:transparent;color:var(--ink);z-index:1;
 scrollbar-width:none}
.editor pre::-webkit-scrollbar{display:none}
.editor textarea{background:transparent;color:transparent;caret-color:var(--ink);
 resize:none;outline:none;z-index:2}
.editor textarea::selection{background:rgba(0,133,125,.18)}

.s-target{color:var(--target)}
.s-effect{color:var(--effect);font-weight:600}
.s-value{color:var(--value)}
.s-scene{color:var(--scene);font-weight:600}
.s-name{color:var(--ink)}
.s-punc{color:var(--faint)}
.s-colon{color:var(--ink);font-weight:700}
.s-comment{color:var(--comment);font-style:italic}
.s-bad{text-decoration:underline wavy var(--warn);text-decoration-skip-ink:none}

.suggest{position:fixed;z-index:6;background:var(--panel);border:1px solid var(--line);
 border-radius:10px;box-shadow:0 6px 18px rgba(0,0,0,.12);min-width:12rem;max-width:24rem;
 max-height:14rem;overflow:auto;display:none;font:13px/1.5 ui-monospace,Consolas,monospace}
.suggest.shown{display:block}
.suggest div{padding:.25rem .8rem;cursor:pointer;display:flex;gap:.8rem;align-items:baseline}
.suggest div small{color:var(--dim);font:12px/1.4 system-ui,sans-serif;margin-left:auto;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.suggest div.lit{background:var(--accent);color:var(--accent-ink)}
.suggest div.lit small{color:var(--accent-ink)}
.suggest div.rule{border-top:1px solid var(--line);margin:.25rem 0;padding:0;cursor:default}

.hint{font-size:.85rem;color:var(--dim);margin:.6rem .2rem;min-height:1.3rem}
.foot{font-size:.85rem;color:var(--dim);margin:1.2rem .2rem}
.foot a{color:var(--accent)}
</style>
</head>
<body>
<header>
<h1>FX Editor</h1>
<span id="status">nothing open yet</span>
<button id="open">Open the drive</button>
<button id="save" class="primary">Put it on the board</button>
<button id="check" disabled>Did it work?</button>
</header>
<main>
<div id="banners"></div>
<div class="editor">
<pre id="paint"><code id="painted"></code></pre>
<textarea id="entry" spellcheck="false" autocapitalize="off" autocomplete="off" wrap="off"></textarea>
<div id="suggest" class="suggest"></div>
</div>
<div id="hint" class="hint"></div>
<p class="foot">One entry per line: which lights, a colon, then the effect.
The board checks the file when the drive ejects, and "Did it work?" reads what it made
of each line. Rather pick from cards? <a href="PICKER.html">PICKER.html</a> on this
drive writes the file for you.</p>
</main>
<script>
"use strict";

// The page still paints without the catalogue beside it; the hint line says why
// nothing can be offered
if (typeof CATALOGUE === "undefined") window.CATALOGUE = null;

// ---- what the file may say, from the same tables the board reads ---------------

var TYPE_HINTS = {
  fraction: "0 to 1, or a percent such as 50%",
  seconds: "a time in seconds",
  number: "a number",
  count: "a whole number",
  span: "how many lights it spreads over",
  whole: "a whole number",
  byte: "0 to 255",
  angle: "degrees, 0 to 360",
  colour: "a name such as warm, or six-digit hex with no #",
  boolean: "true or false",
  quarter: "0, 90, 180 or 270",
  name: "a file on this drive"
};

// The left side's own settings have shapes the type table does not carry
var CHANNEL_HINTS = {
  colour: "a name such as warm, or six-digit hex with no #",
  offset: "where the picture goes, as x|y, * centring that side",
  background: "the colour around the picture",
  bg: "the colour around the picture",
  tile: "repeat or mirror to fill the screen with copies, as across|down"
};

var TARGETS = [
  ["out1-7", "all seven outputs"],
  ["screenA", "a screen on SP/CE A"],
  ["screenB", "a screen on SP/CE B"],
  ["stripL", "an LED strip on L"],
  ["stripR", "an LED strip on R"],
  ["audio", "a sound played beside the effects"],
  ["board", "settings for the board itself"],
  ["[", "a scene heading, [Name: 10s]; entries above the first are always on"]
];

var BOARD_HINTS = {
  drive: "manual keeps the drive hidden until asked for",
  reload: "auto plays the file the moment it is saved, no eject needed",
  program: "a Python file to run instead of the effects",
  args: "what to pass that program, divided by |",
  screena: "what size of screen is on SP/CE A",
  screenb: "what size of screen is on SP/CE B",
  stripl: "how many LEDs are on a strip plugged into L",
  stripr: "the same for R"
};

// The spelling a completion inserts, where the file reads best in mixed case
var BOARD_CASE = {screena: "screenA", screenb: "screenB",
                  stripl: "stripL", stripr: "stripR"};

function targetKind(word) {
  var lowered = word.toLowerCase();
  if (lowered === "board") return "board";
  if (CATALOGUE && lowered === CATALOGUE.audio) return "audio";
  if (lowered.slice(0, 6) === "screen") return "screen";
  if (lowered.slice(0, 5) === "strip") return "strip";
  return "output";
}

function channelSettings(kind) {
  // A sound answers to none of the channel settings, autofx saying so where one
  // is written
  if (!CATALOGUE || kind === "board" || kind === "audio") return [];
  if (kind === "screen") return CATALOGUE.screen_settings || [];
  return CATALOGUE.output_settings || [];
}

function effectNames(kind) {
  if (!CATALOGUE) return [];
  if (kind === "screen") return Object.keys(CATALOGUE.screen_effects);
  if (kind === "audio") return Object.keys(CATALOGUE.audio_effects);
  return Object.keys(CATALOGUE.effects);
}

function effectTakes(name, kind) {
  if (!CATALOGUE) return null;
  if (kind === "screen") return CATALOGUE.screen_effects[name.toLowerCase()] || null;
  if (kind === "audio") return CATALOGUE.audio_effects[name.toLowerCase()] || null;
  var effect = CATALOGUE.effects[name.toLowerCase()];
  return effect ? effect.takes : null;
}

function settingType(name, kind) {
  if (!CATALOGUE) return null;
  var lowered = name.toLowerCase();
  return CATALOGUE.channel_kinds[lowered] ||
         (kind !== "board" && CATALOGUE.settings[lowered]) || null;
}

function valuesFor(name, kind) {
  if (!CATALOGUE) return null;
  var lowered = name.toLowerCase();
  if (kind === "board") {
    var allowed = CATALOGUE.board_settings[lowered];
    return allowed && allowed.length ? allowed.map(String) : null;
  }
  if (lowered === "colour" || lowered === "background" || lowered === "bg")
    return CATALOGUE.colours;
  if (lowered === "rotation") return ["0", "90", "180", "270"];
  if (lowered === "tile") return CATALOGUE.tiling || [];
  if (settingType(name, kind) === "boolean") return ["true", "false"];
  return null;
}

// ---- painting, the same roles the manual gives each word -----------------------

function esc(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function mark(role, text) {
  return text ? '<span class="' + role + '">' + text + "</span>" : text;
}

function settingTok(token) {
  var trailing = "";
  while (token.slice(-1) === ",") {
    trailing = "," + trailing;
    token = token.slice(0, -1);
  }
  var at = token.indexOf("=");
  if (at < 0) return mark("s-name", token) + trailing;
  return mark("s-name", token.slice(0, at)) + mark("s-punc", "=") +
         mark("s-value", token.slice(at + 1)) + trailing;
}

function tokens(text, asWord) {
  return text.split(/(\\s+)/).map(function (word) {
    return !word.trim() ? word : asWord(word);
  }).join("");
}

// What is marked as likely wrong is only what the tables know: names. Values are
// left unjudged, % and deg and lists living there, and the board stays the judge
function badWrap(marked) {
  return '<span class="s-bad">' + marked + "</span>";
}

function validSelector(word) {
  var bare = word.toLowerCase().replace(/^,+|,+$/g, "");
  if (!bare) return true;
  if (bare === "board" || /^screen[ab]$/.test(bare)) return true;
  if (CATALOGUE && bare === CATALOGUE.audio) return true;
  if (/^strip[lr]([0-9][0-9,\\-]*)?$/.test(bare)) return true;
  if (/^out[0-9][0-9,\\-.rgb*]*$/.test(bare)) return true;
  // A group after a comma names its outputs bare: 2, 5-3, 3.r
  return /^[0-9][0-9,\\-]*(\\.(r|g|b|\\*))?$/.test(bare);
}

function checkedSetting(word, allowed) {
  var marked = settingTok(word);
  if (!allowed) return marked;
  var name = word.split("=")[0].replace(/,+$/, "").toLowerCase();
  if (name === "bg") name = "background";
  return allowed.indexOf(name) >= 0 ? marked : badWrap(marked);
}

function highlightLine(line, continuation, context, inScene) {
  var hash = line.indexOf("#");
  var body = hash < 0 ? line : line.slice(0, hash);
  var comment = hash < 0 ? "" : mark("s-comment", esc(line.slice(hash)));

  if (!body.trim()) return esc(body) + comment;
  if (body.replace(/^\\s+/, "").slice(0, 1) === "[")
    return mark("s-scene", esc(body)) + comment;

  var at = body.indexOf(":");
  if (at < 0) {
    // A continuation line carries only settings; anything else continues nothing
    if (!continuation) return badWrap(esc(body)) + comment;
    var allowed = context && CATALOGUE && context.effect
                ? effectTakes(context.effect, context.kind) : null;
    return tokens(esc(body), function (word) {
      return word.indexOf("=") >= 0 ? checkedSetting(word, allowed) : word;
    }) + comment;
  }

  var opening = body.slice(0, at).match(/^\\s*([^\\s]+)/);
  var kind = opening ? targetKind(opening[1]) : "output";
  // Sound does not follow scenes, so its entry belongs above every heading
  var misplaced = kind === "audio" && inScene;
  var leftAllowed = CATALOGUE
                  ? (kind === "board" ? [] : channelSettings(kind)) : null;

  var mono = false;
  var left = tokens(esc(body.slice(0, at)), function (word) {
    if (word.indexOf("=") >= 0) return checkedSetting(word, leftAllowed);
    if (kind === "output" && word.indexOf(".") >= 0) mono = true;
    var marked = mark("s-target", word);
    return validSelector(word) && !misplaced ? marked : badWrap(marked);
  });

  // The first bare word names the effect; a board entry is settings the whole way
  var named = false;
  var rightAllowed = CATALOGUE && kind === "board"
                   ? Object.keys(CATALOGUE.board_settings) : null;
  var right = tokens(esc(body.slice(at + 1)), function (word) {
    if (!named && word.indexOf("=") < 0) {
      named = true;
      var marked = mark("s-effect", word);
      if (!CATALOGUE) return marked;
      if (kind === "board") return badWrap(marked);
      var name = word.replace(/,+$/, "").toLowerCase();
      rightAllowed = effectTakes(name, kind);
      if (!rightAllowed) return badWrap(marked);
      // A colour effect has nothing to show on a channel driven as a plain light
      if (mono && CATALOGUE.effects[name].kind === "colour") return badWrap(marked);
      return marked;
    }
    return checkedSetting(word, rightAllowed);
  });

  return left + mark("s-colon", ":") + right + comment;
}

function paint(text) {
  var open = null;
  var inScene = false;
  var painted = text.split("\\n").map(function (line) {
    var body = line.split("#")[0];
    var context = open;
    var at = body.indexOf(":");
    if (body.replace(/^\\s+/, "").slice(0, 1) === "[") inScene = true;
    if (!body.trim() || body.replace(/^\\s+/, "").slice(0, 1) === "[") {
      open = null;
      context = null;
    } else if (at >= 0) {
      var opening = body.slice(0, at).match(/^\\s*([^\\s]+)/);
      var effect = null;
      body.slice(at + 1).split(/\\s+/).forEach(function (word) {
        if (word && word.indexOf("=") < 0 && !effect)
          effect = word.replace(/,+$/, "");
      });
      open = {kind: opening ? targetKind(opening[1]) : "output", effect: effect};
      context = null;
    }
    return highlightLine(line, !!context, context, inScene);
  });
  return painted.join("\\n") + "\\n";
}

// ---- where the caret stands, for offering what fits there ----------------------

function entryBefore(text, caret) {
  // The logical entry up to the caret: this line, plus the lines above it that
  // it continues, since an entry's colon is on its first line
  var lineStart = text.lastIndexOf("\\n", caret - 1) + 1;
  var lines = [text.slice(lineStart, caret)];
  while (lineStart > 0 && lines[0].split("#")[0].indexOf(":") < 0) {
    var previousStart = text.lastIndexOf("\\n", lineStart - 2) + 1;
    var previous = text.slice(previousStart, lineStart - 1).split("#")[0];
    if (!previous.trim() || previous.replace(/^\\s+/, "").slice(0, 1) === "[") break;
    lines.unshift(previous);
    lineStart = previousStart;
    if (previous.indexOf(":") >= 0) break;
  }
  return lines.join(" ");
}

// Which outputs these lines already drive, ranges and components expanded
function outputsUsed(lines) {
  var used = {};
  lines.forEach(function (line) {
    var body = line.split("#")[0];
    var at = body.indexOf(":");
    if (at < 0 || !/^\\s*out[0-9]/i.test(body)) return;
    body.slice(0, at).split(/\\s+/).forEach(function (word) {
      if (word.indexOf("=") >= 0) return;
      word.toLowerCase().split(",").forEach(function (token) {
        token = token.replace(/^out/, "").split(".")[0];
        var range = token.match(/^([0-9]+)-([0-9]+)$/);
        if (range) {
          var from = Math.min(+range[1], +range[2]);
          var to = Math.max(+range[1], +range[2]);
          for (var n = from; n <= to; n++) used[n] = true;
        } else if (/^[0-9]+$/.test(token)) {
          used[+token] = true;
        }
      });
    });
  });
  return used;
}

// The caret's own scene, its line left out, and the always-on section above the
// first heading. Above the first heading the two are one and the same
function sceneScope(text, caret) {
  var lines = text.split("\\n");
  var here = text.slice(0, caret).split("\\n").length - 1;
  function heading(line) {
    return line.split("#")[0].replace(/^\\s+/, "").slice(0, 1) === "[";
  }
  var start = 0;
  for (var up = here; up >= 0; up--)
    if (heading(lines[up])) { start = up + 1; break; }
  var end = lines.length;
  for (var down = here + 1; down < lines.length; down++)
    if (heading(lines[down])) { end = down; break; }
  var first = lines.length;
  for (var scan = 0; scan < lines.length; scan++)
    if (heading(lines[scan])) { first = scan; break; }
  return {
    scene: lines.slice(start, end).filter(function (_, index) {
      return start + index !== here;
    }),
    always: start > 0 ? lines.slice(0, first) : []
  };
}

function contextAt(text, caret) {
  var lineStart = text.lastIndexOf("\\n", caret - 1) + 1;
  var line = text.slice(lineStart, caret);
  if (line.indexOf("#") >= 0) return null;
  if (line.replace(/^\\s+/, "").slice(0, 1) === "[") return null;

  var entry = entryBefore(text, caret);
  var prefix = line.match(/[^\\s:]*$/)[0];
  var found = {prefix: prefix, target: null, kind: "output", effect: null,
               comma: false, used: {}};

  // A comma closes its token, so the caret stands at a fresh word
  if (prefix.slice(-1) === ",") {
    found.comma = true;
    found.prefix = prefix = "";
  }

  var before = entry.slice(0, entry.length - prefix.length);
  var colon = before.indexOf(":");
  found.left = colon < 0;

  var opening = entry.match(/^\\s*([^\\s:]+)/);
  if (opening) {
    found.target = opening[1];
    found.kind = targetKind(opening[1]);
  }

  // A component anywhere in the selector makes the channel a plain light, so a
  // colour effect has nothing there to show itself on
  if (colon >= 0 && found.kind === "output")
    found.mono = entry.slice(0, entry.indexOf(":")).split(/\\s+/).some(function (word) {
      return word.indexOf("=") < 0 && word.indexOf(".") >= 0;
    });

  // What the entry already sets, to the end of the caret's line, so a setting
  // is only ever offered once
  var lineEnd = text.indexOf("\\n", caret);
  var whole = entry + " " +
              text.slice(caret, lineEnd < 0 ? text.length : lineEnd).split("#")[0];
  whole.split(/[\\s,]+/).forEach(function (word) {
    var at = word.indexOf("=");
    if (at > 0) found.used[word.slice(0, at).toLowerCase()] = true;
  });

  if (colon < 0) {
    // A comma before the colon says another output comes next, which is the
    // writer's to number, so nothing is offered and the hint line explains
    found.mode = found.comma ? "more" : before.trim() ? "channel" : "target";
  } else {
    found.mode = found.kind === "board" ? "setting" : "effect";
    before.slice(colon + 1).split(/\\s+/).forEach(function (word) {
      if (word && word.indexOf("=") < 0 && !found.effect) {
        found.effect = word.replace(/,+$/, "");
        found.mode = "setting";
      }
    });
    // The first word of a new line may start a new entry or carry on the one
    // above, so both are offered until the word says which
    if (line.indexOf(":") < 0) {
      if (line.slice(0, line.length - prefix.length).trim() === "") {
        found.mode = "fresh";
      } else {
        // A first word shaped like a selector settles it: the line is a new
        // entry still waiting for its colon, not the one above carrying on
        var starts = line.match(/^\\s*([^\\s:]+)/);
        if (starts && /^(out[0-9]|screen[ab]|strip[lr]|board)/i.test(starts[1])) {
          found.target = starts[1];
          found.kind = targetKind(starts[1]);
          found.effect = null;
          found.mode = "channel";
          found.used = {};
          line.split(/[\\s,]+/).forEach(function (word) {
            var given = word.indexOf("=");
            if (given > 0) found.used[word.slice(0, given).toLowerCase()] = true;
          });
        }
      }
    }
  }

  var at = found.prefix.indexOf("=");
  if (at >= 0) {
    found.mode = "value";
    found.setting = found.prefix.slice(0, at);
    found.prefix = found.prefix.slice(at + 1);
  }

  if (found.mode === "target" || found.mode === "fresh") {
    var scope = sceneScope(text, caret);
    found.sceneUsed = outputsUsed(scope.scene);
    found.alwaysUsed = outputsUsed(scope.always);
  }
  return found;
}

function offers(found) {
  if (!found) return [];
  var out = [];
  var seen = found.prefix.toLowerCase();

  function offer(insert, hint) {
    if (insert.toLowerCase().slice(0, seen.length) === seen && insert !== found.prefix)
      out.push({insert: insert, hint: hint || ""});
  }

  // fade and ease are one setting written two ways, so each rules the other out
  function unused(name) {
    if (found.used[name.toLowerCase()]) return false;
    if (name === "fade" && found.used.ease) return false;
    if (name === "ease" && found.used.fade) return false;
    return true;
  }

  function channelOffers() {
    channelSettings(found.kind).forEach(function (name) {
      if (!unused(name)) return;
      var type = settingType(name, found.kind);
      offer(name + "=", CHANNEL_HINTS[name] || TYPE_HINTS[type] || "");
    });
    offer(": ", "then the effect");
  }

  function settingOffers() {
    var takes = found.kind === "board"
              ? (CATALOGUE ? Object.keys(CATALOGUE.board_settings) : [])
              : found.effect ? effectTakes(found.effect, found.kind) : null;
    (takes || []).forEach(function (name) {
      if (!unused(name)) return;
      var shown = BOARD_CASE[name] || name;
      var hint = found.kind === "board" ? BOARD_HINTS[name]
               : TYPE_HINTS[settingType(name, found.kind)];
      offer(shown + "=", hint || "");
    });
  }

  // A word already naming outputs can take more of them, one colour channel, or
  // go to its effect. Half-written punctuation leaves the numbers to the writer
  function selectorOffers() {
    if (/^out[0-9]/i.test(found.prefix) && found.prefix.slice(-1) === ".") {
      offer(found.prefix + "r", "just the red");
      offer(found.prefix + "g", "just the green");
      offer(found.prefix + "b", "just the blue");
      offer(found.prefix + "*", "all three, each its own light");
      return;
    }
    if (/[-.,]$/.test(found.prefix)) return;
    if (/^out[0-9]/i.test(found.prefix) || /^strip[lr][0-9]/i.test(found.prefix)) {
      var tail = found.prefix.split(",").pop();
      offer(found.prefix + ",", "another output after it: out1,3,5-7");
      if (/^[0-9]+$/.test(tail.replace(/^[a-z]+/i, "")))
        offer(found.prefix + "-", "a range to another output, run either way");
      if (/^out/i.test(found.prefix) && tail.indexOf(".") < 0)
        offer(found.prefix + ".", "one colour channel alone: .r .g .b, or .*");
      offer(found.prefix + ": ", "then the effect");
    } else if (/^(screen[ab]|strip[lr]|board|audio)$/i.test(found.prefix)) {
      offer(found.prefix + ": ", "then the effect");
    }
  }

  // One output by number: the first this scene does not drive yet, and beside it
  // the first held by the always-on section, which a scene may take over
  function dynamicOutput() {
    var free = null;
    var takeover = null;
    for (var n = 1; n <= 7; n++) {
      if (found.sceneUsed[n]) continue;
      if (found.alwaysUsed[n]) {
        if (takeover === null) takeover = n;
      } else if (free === null) {
        free = n;
      }
    }
    if (free !== null)
      offer("out" + free, free === 1 ? "one output" : "the next output not used here");
    if (takeover !== null)
      offer("out" + takeover, "takes over an always-on output while this scene shows");
  }

  function freshStarts() {
    dynamicOutput();
    TARGETS.forEach(function (pair) { offer(pair[0], pair[1]); });
    selectorOffers();
  }

  if (found.mode === "target") {
    freshStarts();

  } else if (found.mode === "channel") {
    channelOffers();

  } else if (found.mode === "effect") {
    effectNames(found.kind).forEach(function (name) {
      var effect = CATALOGUE.effects[name];
      if (found.mono && effect && effect.kind === "colour") return;
      var hint = effect && effect.kind === "colour" ? "brings its own colours" : "";
      offer(name, hint);
    });

  } else if (found.mode === "setting") {
    settingOffers();

  } else if (found.mode === "fresh") {
    // A new line under an entry: carrying it on comes first, a fresh start after
    // a dividing line
    settingOffers();
    var split = out.length;
    freshStarts();
    if (split && out.length > split) out.divider = split;

  } else if (found.mode === "value") {
    (valuesFor(found.setting, found.kind) || []).forEach(function (value) {
      offer(value);
    });
    // A pipe joins the parts of a value that has them; a comma after a value on
    // the left starts the next output group
    if (found.prefix) {
      var name = found.setting.toLowerCase();
      var piped = {fade: "rise|fall, each its own seconds",
                   ease: "rise|fall, each its own seconds",
                   offset: "x|y, * centring that side",
                   tile: "across|down",
                   hold: "one end|the other",
                   args: "the next argument"};
      if (piped[name])
        offer(found.prefix + "|", piped[name]);
      else if (name === "colour" && found.effect &&
               found.effect.toLowerCase() === "rgb_blink")
        offer(found.prefix + "|", "another colour to blink through");
      if (found.left && found.kind !== "screen" && found.kind !== "board")
        offer(found.prefix + ",", name === "colour"
              ? "a colour for each output"
              : "then another output with settings of its own");
    }
  }
  return out;
}

function hintFor(found) {
  if (!found) return "";
  if (!CATALOGUE)
    return "catalogue.js is not beside this page, so nothing can be suggested; " +
           "the copy on the FX drive has it";
  if (found.mode === "more")
    return "another output comes next: a number, or a range such as 5-3, " +
           "then its settings or the colon";
  if ((found.mode === "target" || found.mode === "fresh") &&
      /^out[0-9]/i.test(found.prefix))
    return "outputs join with commas, ranges run either way, and .r .g .b " +
           "or .* takes one colour channel alone";
  if (found.mode === "value" || (found.mode === "setting" && found.prefix)) {
    var name = found.mode === "value" ? found.setting : found.prefix;
    if (found.kind === "board") return BOARD_HINTS[name.toLowerCase()] || "";
    var type = settingType(name, found.kind);
    return type ? name.replace(/,+$/, "") + ": " +
                  (CHANNEL_HINTS[name.toLowerCase()] || TYPE_HINTS[type]) : "";
  }
  if (found.effect) {
    var takes = effectTakes(found.effect, found.kind);
    if (takes) return found.effect + " takes: " + takes.join(", ");
  }
  if (found.kind === "audio")
    return "one sound plays at a time, and its entry sits above every scene heading";
  if (found.mode === "channel")
    return "before the colon: how the " +
           (found.kind === "screen" ? "screen is set" : "lights are set");
  return "";
}

// ---- the page -----------------------------------------------------------------

var entry = document.getElementById("entry");
var painted = document.getElementById("painted");
var paintBox = document.getElementById("paint");
var suggest = document.getElementById("suggest");
var hintLine = document.getElementById("hint");

var STARTER = "# One entry per line: which lights, a colon, then the effect.\\n" +
              "# Settings you leave out take their usual value.\\n\\n" +
              "out1-7: rainbow_wave speed=0.3\\n";

var state = {dirHandle: null, fileHandle: null, offered: [], rows: [], lit: 0};

function repaint() {
  painted.innerHTML = paint(entry.value);
  // The box grows with the file, a spare row deep, so the text never scrolls
  // vertically inside it and the page carries a long file instead
  var rowHeight = parseFloat(getComputedStyle(entry).lineHeight);
  var wanted = (entry.value.split("\\n").length + 1) * rowHeight + 48;
  paintBox.parentNode.style.height = Math.max(384, wanted) + "px";
  paintBox.scrollTop = entry.scrollTop;
  paintBox.scrollLeft = entry.scrollLeft;
}

function banner(text, warn, detail) {
  var box = document.getElementById("banners");
  box.innerHTML = "";
  if (!text) return;
  var note = document.createElement("div");
  note.className = warn ? "banner warn" : "banner";
  note.textContent = text;
  if (detail) {
    var lines = document.createElement("pre");
    lines.textContent = detail;
    note.appendChild(lines);
  }
  box.appendChild(note);
}

// Where the caret's line sits on the screen, found by mirroring the text up to it
function caretPlace() {
  var mirror = document.createElement("div");
  var styles = getComputedStyle(entry);
  ["font", "whiteSpace", "tabSize"].forEach(function (key) {
    mirror.style[key] = styles[key];
  });
  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre";
  var upTo = entry.value.slice(0, entry.selectionStart);
  mirror.textContent = upTo.slice(upTo.lastIndexOf("\\n") + 1);
  document.body.appendChild(mirror);
  var width = mirror.offsetWidth;
  document.body.removeChild(mirror);

  var rect = entry.getBoundingClientRect();
  var rowHeight = parseFloat(styles.lineHeight);
  var lineTop = rect.top + parseFloat(styles.paddingTop) +
                (upTo.split("\\n").length - 1) * rowHeight - entry.scrollTop;
  return {
    left: rect.left + parseFloat(styles.paddingLeft) + width - entry.scrollLeft,
    below: lineTop + rowHeight + 2,
    above: lineTop - 2
  };
}

function showSuggestions() {
  var caret = entry.selectionStart;
  if (caret !== entry.selectionEnd) return hideSuggestions();
  var found = contextAt(entry.value, caret);
  hintLine.textContent = hintFor(found);

  var offered = offers(found);
  if (!offered.length) return hideSuggestions();

  state.offered = offered;
  state.found = found;
  state.lit = 0;
  state.rows = [];
  suggest.innerHTML = "";
  offered.slice(0, 40).forEach(function (one, index) {
    if (index && index === offered.divider) {
      var rule = document.createElement("div");
      rule.className = "rule";
      suggest.appendChild(rule);
    }
    var row = document.createElement("div");
    var name = document.createElement("span");
    name.textContent = one.insert;
    row.appendChild(name);
    if (one.hint) {
      var why = document.createElement("small");
      why.textContent = one.hint;
      row.appendChild(why);
    }
    if (index === 0) row.className = "lit";
    row.onmousedown = function (event) {
      event.preventDefault();
      accept(index);
    };
    suggest.appendChild(row);
    state.rows.push(row);
  });
  // Placed below the caret's line, or above it where the screen runs out
  suggest.style.visibility = "hidden";
  suggest.className = "suggest shown";
  var place = caretPlace();
  var top = place.below;
  if (top + suggest.offsetHeight > window.innerHeight - 8)
    top = Math.max(8, place.above - suggest.offsetHeight);
  suggest.style.top = top + "px";
  suggest.style.left = Math.max(8, Math.min(place.left,
      window.innerWidth - suggest.offsetWidth - 8)) + "px";
  suggest.style.visibility = "";
}

function hideSuggestions() {
  suggest.className = "suggest";
  state.offered = [];
}

function light(index) {
  var count = state.rows.length;
  state.lit = (index + count) % count;
  state.rows.forEach(function (row, i) {
    row.className = i === state.lit ? "lit" : "";
  });
  state.rows[state.lit].scrollIntoView({block: "nearest"});
}

function accept(index) {
  var one = state.offered[index === undefined ? state.lit : index];
  if (!one) return;
  var caret = entry.selectionStart;
  var start = caret - state.found.prefix.length;
  // The colon closes the word before it, so it steps back over the gap
  if (one.insert.slice(0, 1) === ":")
    while (start > 0 && entry.value[start - 1] === " ") start--;
  entry.focus();
  entry.setSelectionRange(start, caret);
  // insertText keeps the undo history; setRangeText is the fallback without it
  if (!document.execCommand("insertText", false, one.insert))
    entry.setRangeText(one.insert, start, caret, "end");
  hideSuggestions();
  changed();
}

function changed() {
  repaint();
  try { localStorage.setItem("fx-editor-draft", entry.value); } catch (e) {}
  showSuggestions();
}

entry.addEventListener("input", changed);
entry.addEventListener("scroll", function () {
  paintBox.scrollTop = entry.scrollTop;
  paintBox.scrollLeft = entry.scrollLeft;
  hideSuggestions();
});
// The dropdown is pinned to the screen, so anything moving under it lets go of it
window.addEventListener("resize", hideSuggestions);
window.addEventListener("scroll", function (event) {
  if (event.target instanceof Node && suggest.contains(event.target)) return;
  hideSuggestions();
}, true);
entry.addEventListener("click", showSuggestions);
entry.addEventListener("blur", function () {
  setTimeout(hideSuggestions, 150);
});
entry.addEventListener("keydown", function (event) {
  if (!state.offered.length) {
    if (event.key === " " && event.ctrlKey) {
      event.preventDefault();
      showSuggestions();
    }
    return;
  }
  if (event.key === "ArrowDown") { event.preventDefault(); light(state.lit + 1); }
  else if (event.key === "ArrowUp") { event.preventDefault(); light(state.lit - 1); }
  else if (event.key === "Tab" || event.key === "Enter") {
    event.preventDefault();
    accept();
  }
  else if (event.key === "Escape") hideSuggestions();
});

// ---- the drive ------------------------------------------------------------------

async function connect() {
  var dir = await window.showDirectoryPicker({mode: "readwrite"});
  state.dirHandle = dir;
  state.fileHandle = await dir.getFileHandle("effects.txt");
  var onBoard = await (await state.fileHandle.getFile()).text();
  var held = entry.value.trim();
  if (onBoard.trim() !== held && (!held || held === STARTER.trim() ||
      confirm("Load effects.txt from the drive and replace what is here?"))) {
    entry.value = onBoard;
    repaint();
  }
  document.getElementById("check").disabled = false;
  document.getElementById("status").textContent = "connected to the drive";
}

document.getElementById("open").onclick = async function () {
  try {
    await connect();
    banner("");
  } catch (e) {
    banner("Could not open the drive: " + e.name + ". Is it showing? " +
           "A double press of the board's button brings it back.", true);
  }
};

document.getElementById("save").onclick = async function () {
  try {
    if (!state.fileHandle) await connect();
    var text = entry.value;
    var writable = await state.fileHandle.createWritable();
    await writable.write(text);
    await writable.close();
    var back = await (await state.fileHandle.getFile()).text();
    if (back !== text) throw new Error("the file read back differently");
    banner("On its way. Eject the FX drive on this computer, and the board plays it. " +
           "Double-press the board's button to bring the drive back, then ask 'Did it work?'.");
  } catch (e) {
    state.fileHandle = null;
    state.dirHandle = null;
    banner("That didn't reach the board: " + e.name + ". Is the FX drive showing? " +
           "A double press of its button brings it back; then try again.", true);
  }
};

document.getElementById("check").onclick = async function () {
  try {
    var handle = await state.dirHandle.getFileHandle("errors.txt");
    var text = await (await handle.getFile()).text();
    banner("The board wasn't happy with some of it:", true, text.trim());
  } catch (e) {
    if (e.name === "NotFoundError")
      banner("All good. The board read the file and found nothing wrong.");
    else
      banner("Couldn't look: " + e.name + ". Is the drive showing?", true);
  }
};

var draft = null;
try { draft = localStorage.getItem("fx-editor-draft"); } catch (e) {}
entry.value = draft || STARTER;
repaint();
</script>
</body>
</html>
"""

CATALOGUE = """\
// Generated from the autofx tables. Do not edit.
var CATALOGUE = {
 "effects": {
  "binary_counter": {
   "kind": "mono",
   "takes": [
    "interval",
    "count",
    "step"
   ]
  },
  "blink": {
   "kind": "mono",
   "takes": [
    "speed",
    "phase",
    "duty"
   ]
  },
  "blink_wave": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "phase",
    "duty"
   ]
  },
  "flash": {
   "kind": "mono",
   "takes": [
    "speed",
    "flashes",
    "window",
    "phase",
    "duty"
   ]
  },
  "flash_sequence": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "flashes",
    "window",
    "phase",
    "duty"
   ]
  },
  "flicker": {
   "kind": "mono",
   "takes": [
    "brightness",
    "dimness",
    "bright_min",
    "bright_max",
    "dim_min",
    "dim_max"
   ]
  },
  "hsv": {
   "kind": "colour",
   "takes": [
    "hue",
    "sat",
    "val"
   ]
  },
  "hue_step": {
   "kind": "colour",
   "takes": [
    "interval",
    "hue",
    "sat",
    "val",
    "steps"
   ]
  },
  "none": {
   "kind": "mono",
   "takes": []
  },
  "pelican_crossing": {
   "kind": "mono",
   "takes": [
    "red_interval",
    "flashing_interval",
    "green_interval",
    "amber_interval"
   ]
  },
  "pulse": {
   "kind": "mono",
   "takes": [
    "speed",
    "phase"
   ]
  },
  "pulse_wave": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "phase"
   ]
  },
  "rainbow": {
   "kind": "colour",
   "takes": [
    "speed",
    "sat",
    "val"
   ]
  },
  "rainbow_wave": {
   "kind": "colour",
   "takes": [
    "speed",
    "length",
    "sat",
    "val"
   ]
  },
  "random": {
   "kind": "mono",
   "takes": [
    "interval",
    "brightness_min",
    "brightness_max"
   ]
  },
  "rgb": {
   "kind": "colour",
   "takes": [
    "red",
    "green",
    "blue"
   ]
  },
  "rgb_blink": {
   "kind": "colour",
   "takes": [
    "colour",
    "speed",
    "phase",
    "duty"
   ]
  },
  "static": {
   "kind": "mono",
   "takes": [
    "brightness"
   ]
  },
  "sweep": {
   "kind": "mono",
   "takes": [
    "speed",
    "length",
    "extent",
    "hold"
   ]
  },
  "traffic_light": {
   "kind": "mono",
   "takes": [
    "red_interval",
    "red_amber_interval",
    "green_interval",
    "amber_interval"
   ]
  }
 },
 "screen_effects": {
  "gif": [
   "file",
   "fps",
   "interval",
   "loop",
   "ping_pong",
   "first_as_last",
   "hold"
  ],
  "image": [
   "file"
  ],
  "sequence": [
   "folder",
   "fps",
   "interval",
   "loop",
   "ping_pong",
   "first_as_last",
   "hold"
  ]
 },
 "audio": "audio",
 "audio_effects": {
  "wav": [
   "file",
   "loop"
  ]
 },
 "settings": {
  "speed": "number",
  "phase": "fraction",
  "duty": "fraction",
  "window": "fraction",
  "length": "count",
  "flashes": "count",
  "steps": "count",
  "extent": "span",
  "brightness": "fraction",
  "brightness_min": "fraction",
  "brightness_max": "fraction",
  "dimness": "fraction",
  "bright_min": "seconds",
  "bright_max": "seconds",
  "dim_min": "seconds",
  "dim_max": "seconds",
  "interval": "seconds",
  "hold": "seconds",
  "count": "whole",
  "step": "whole",
  "red_interval": "seconds",
  "red_amber_interval": "seconds",
  "flashing_interval": "seconds",
  "green_interval": "seconds",
  "amber_interval": "seconds",
  "red": "byte",
  "green": "byte",
  "blue": "byte",
  "hue": "angle",
  "sat": "fraction",
  "val": "fraction",
  "colour": "colour",
  "file": "name",
  "folder": "name",
  "fps": "number",
  "loop": "boolean",
  "ping_pong": "boolean",
  "first_as_last": "boolean"
 },
 "colours": [
  "black",
  "blue",
  "cool",
  "cyan",
  "green",
  "magenta",
  "red",
  "warm",
  "white",
  "yellow"
 ],
 "channel_kinds": {
  "level": "fraction",
  "fade": "seconds",
  "ease": "seconds",
  "backlight": "fraction",
  "rotation": "quarter",
  "mirror": "boolean",
  "pixel_double": "boolean"
 },
 "screen_ports": [
  "screena",
  "screenb"
 ],
 "strips": [
  "stripl",
  "stripr"
 ],
 "output_settings": [
  "level",
  "colour",
  "fade",
  "ease"
 ],
 "screen_settings": [
  "backlight",
  "rotation",
  "mirror",
  "offset",
  "background",
  "pixel_double",
  "tile"
 ],
 "tiling": [
  "off",
  "repeat",
  "mirror"
 ],
 "board_settings": {
  "drive": [
   "manual"
  ],
  "reload": [
   "manual",
   "auto"
  ],
  "program": null,
  "args": null,
  "screena": [
   "2.8",
   "1.54"
  ],
  "screenb": [
   "2.8",
   "1.54"
  ],
  "stripl": null,
  "stripr": null
 }
};
"""
