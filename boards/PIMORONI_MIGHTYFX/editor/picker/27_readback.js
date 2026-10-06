
// ---- reading the board's file back ----------------------------------------------------------
// Opening the drive reads effects.txt into the page. Every line is either read into the page's
// own settings or kept word for word in its scene, so a file comes back without loss (the design
// is in READBACK.md). This first step reads the board line and the scenes, and keeps every
// entry; the steps after it read screens, sound and the lights out of the kept lines.

// The lines this page writes of its own accord, which a file read back does not keep
var PAGE_LINES = HEADER.split("\n").filter(Boolean).concat(["# Nothing is playing yet."]);

// The board settings this page holds itself. Every other token on the board line is kept
var boardResidue = [];
var boardComments = [];

// The kept entries of the scene on show, each its text and the comments written above it, and
// the comments of the lines it read, by the line they sit above
var keptNow = [];
var notesNow = {};

// Where a quote does not hide it, the first colon, which divides an entry's lights from its effect
function unquotedColon(line) {
  var quote = null;
  for (var at = 0; at < line.length; at++) {
    var one = line.charAt(at);
    if (quote) {
      if (one === quote) quote = null;
    } else if (one === "\"" || one === "'") {
      quote = one;
    } else if (one === ":") {
      return at;
    }
  }
  return -1;
}

// A board line's settings, divided at spaces a quote does not hold
function boardTokens(text) {
  var tokens = [];
  var word = "";
  var quote = null;
  text.split("").forEach(function (one) {
    if (quote) {
      word += one;
      if (one === quote) quote = null;
    } else if (one === "\"" || one === "'") {
      word += one;
      quote = one;
    } else if (/\s/.test(one)) {
      if (word) tokens.push(word);
      word = "";
    } else {
      word += one;
    }
  });
  if (word) tokens.push(word);
  return tokens;
}

// A scene heading, as autofx reads one. Where a word is neither a time nor restart, the heading
// is kept as written, since writing it again would lose it
function readHeading(line) {
  var inner = line.slice(1, -1);
  var colon = inner.indexOf(":");
  var name = (colon < 0 ? inner : inner.slice(0, colon)).trim();
  var heading = {name: name, seconds: null, restart: false, written: line};
  var odd = false;
  (colon < 0 ? "" : inner.slice(colon + 1)).split(/\s+/).forEach(function (word) {
    if (!word) return;
    // A time in seconds or in minutes, held as seconds. Minutes are kept as written, the page
    // writing seconds, until the scene's time is changed
    var time = word.match(/^(\d+(?:\.\d+)?)([sm])$/i);
    if (time) {
      heading.seconds = Number(time[1]) * (time[2].toLowerCase() === "m" ? 60 : 1);
      if (time[2].toLowerCase() === "m") odd = true;
    } else if (word.toLowerCase() === "restart") heading.restart = true;
    else odd = true;
  });
  if (!odd) heading.written = null;
  return heading;
}

// The file in parts: the board line's tokens and the comments above it, then each scene's
// kept entries, the always-on section first. A line with no colon after an entry carries it
// on, as autofx reads one, and a comment goes with the entry or heading below it
function readEffects(text) {
  var parsed = {tokens: [], comments: [], slots: [{heading: null, comments: [], kept: []}]};
  var comments = [];
  var entry = null;

  text.replace(/\r/g, "").split("\n").forEach(function (raw) {
    var line = raw.trim();
    var slot = parsed.slots[parsed.slots.length - 1];
    if (!line) return;

    if (line.charAt(0) === "#") {
      if (line.indexOf(WIRED) === 0) parsed.wiring = line.slice(WIRED.length).trim();
      else if (PAGE_LINES.indexOf(line) < 0) comments.push(raw.replace(/\s+$/, ""));
      return;
    }

    if (line.charAt(0) === "[" && line.slice(-1) === "]") {
      parsed.slots.push({heading: readHeading(line), comments: comments, kept: []});
      comments = [];
      entry = null;
      return;
    }

    if (/^board\s*:/i.test(line)) {
      parsed.comments = parsed.comments.concat(comments);
      comments = [];
      parsed.tokens = parsed.tokens.concat(boardTokens(line.replace(/^board\s*:/i, "")));
      entry = {board: true};
      return;
    }

    if (entry && unquotedColon(line) < 0) {
      if (entry.board) parsed.tokens = parsed.tokens.concat(boardTokens(line));
      else entry.text += "\n" + raw.replace(/\s+$/, "");
      return;
    }

    entry = {text: raw.replace(/\s+$/, ""), comments: comments};
    comments = [];
    slot.kept.push(entry);
  });

  // Comments at the very end stay at the end of the last scene
  if (comments.length) {
    parsed.slots[parsed.slots.length - 1].kept.push({text: null, comments: comments});
  }
  return parsed;
}

function copyKept(kept) {
  return (kept || []).map(function (one) {
    return {text: one.text, comments: one.comments.slice()};
  });
}

// The arguments an args= gives, divided at pipes a quote does not hold, their quotes taken off
function argsRead(value) {
  var parts = [], part = "", quoted = false;
  value.split("").forEach(function (one) {
    if (one === "\"") quoted = !quoted;
    else if (one === "|" && !quoted) {
      parts.push(part);
      part = "";
    } else part += one;
  });
  parts.push(part);
  return parts;
}

// The program a file runs, opening the program tab with it chosen, where the page knows the
// program and writes its arguments back as the file has them. Otherwise both stay on the board
// line as written, and the page opens on the effects
function readProgram(named, argued) {
  boardSet.program = null;
  onProgramPage = false;
  if (!named) {
    if (argued) boardResidue.push(argued);
    return;
  }
  var path = named.slice("program=".length);
  var given = argued ? argsRead(argued.slice("args=".length)) : [];
  var kept = boardSet.args[path];
  boardSet.args[path] = given;
  if (programNamed(path) && argsWritten(path) === (argued ? argued.slice("args=".length) : "")) {
    boardSet.program = path;
    boardSet.lastProgram = path;
    onProgramPage = true;
    return;
  }
  boardSet.args[path] = kept;
  boardResidue.push(named);
  if (argued) boardResidue.push(argued);
}

// Take a file into the page: the board line, the scenes, and every entry kept in its scene
function absorbFile(text) {
  var parsed = readEffects(text);
  wiringRead = parsed.wiring || null;

  boardSet.reload = false;
  boardSet.driveHidden = false;
  boardResidue = [];
  var named = null, argued = null;
  parsed.tokens.forEach(function (token) {
    var lowered = token.toLowerCase();
    if (lowered === "reload=auto") boardSet.reload = true;
    else if (lowered === "reload=manual") boardSet.reload = false;
    else if (lowered === "drive=manual") boardSet.driveHidden = true;
    else if (/^program=/i.test(token) && !named) named = token;
    else if (/^args=/i.test(token) && !argued) argued = token;
    else boardResidue.push(token);
  });
  readProgram(named, argued);
  boardComments = parsed.comments;

  function bodyKeeping(kept) {
    var body = blankBody();
    body.kept = copyKept(kept);
    return body;
  }

  state.always.body = bodyKeeping(parsed.slots[0].kept);
  state.scenes = parsed.slots.slice(1).map(function (slot) {
    var heading = slot.heading;
    return {name: heading.name, seconds: heading.seconds || 10,
            waits: heading.seconds === null, restart: heading.restart,
            comments: slot.comments, read: heading, body: bodyKeeping(slot.kept)};
  });
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) { return scene.body; }));
  readHubBoard();
  readTabs(bodies);
  readHubLines(bodies);
  readLights(bodies);
  state.at = -1;
  apply(state.always.body);
  draw();
}

// ---- screens and sound out of the kept lines --------------------------------------------------
// Each kept line is tried as a setting of the tab it names, and read only where that tab's own
// writer then gives back exactly the line. So a setting read wrongly leaves the line kept, never
// changed. A hub's lines stay kept for now, their positions going in groups

// An entry's two sides, the lights and their settings before the colon, the effect and its after
function entryParts(text) {
  if (text === null || text.indexOf("\n") >= 0) return null;
  var colon = unquotedColon(text);
  if (colon < 0) return null;
  var left = boardTokens(text.slice(0, colon));
  var right = boardTokens(text.slice(colon + 1));
  if (!left.length || !right.length) return null;
  function settings(tokens) {
    var held = {};
    tokens.forEach(function (token) {
      var equals = token.indexOf("=");
      if (equals < 0) held[""] = token;
      else held[token.slice(0, equals).toLowerCase()] = token.slice(equals + 1);
    });
    return held;
  }
  return {selector: left[0].toLowerCase(), left: settings(left.slice(1)), effect: right[0].toLowerCase(),
          right: settings(right.slice(1))};
}

function unquoted(value) {
  return value && /^(["']).*\1$/.test(value) ? value.slice(1, -1) : value;
}

// A screen's line as the settings of the screen it names, or null where one is not understood
function screenPlaying(parts, body, letter) {
  var playing = Object.assign({}, body.screens[letter]);
  var look = playing.look = freshLook();
  var source = {gif: "file", image: "file", graphics: "file", sequence: "folder"}[parts.effect];
  if (!source || !parts.right[source]) return null;
  playing.shows = unquoted(parts.right[source]);

  var understood = true;
  Object.keys(parts.left).forEach(function (key) {
    var value = parts.left[key];
    if (key === "rotation") playing.turn = Number(value);
    else if (key === "backlight") look.backlight = /%$/.test(value) ? parseFloat(value) / 100 : Number(value);
    else if (key === "mirror" && value === "true") look.mirror = true;
    else if (key === "pixel_double" && value === "true") look.double = true;
    else if (key === "bg") look.bg = "#" + (WORDS[value] ? hexOf(WORDS[value]) : value);
    else if (key === "offset") {
      var sides = value.split("|");
      look.anchor = null;
      look.x = sides[0] === "*" ? "" : sides[0];
      look.y = sides[1] === "*" ? "" : sides[1];
    } else if (key === "tile") {
      var ways = value.split("|");
      look.tile = ways[0];
      look.tileDown = ways[1] || ways[0];
    } else understood = false;
  });
  Object.keys(parts.right).forEach(function (key) {
    var value = parts.right[key];
    if (key === source) return;
    if (key === "fps" || key === "interval") {
      look.pace = key;
      look.every = Number(value);
    } else if (key === "loop" && value === "false") look.loop = false;
    else if (key === "ping_pong" && value === "true") playing.pingpong = true;
    else if (key === "first_as_last" && value === "true") look.whole = true;
    else if (key === "hold") {
      var ends = value.split("|");
      playing.hold = ends[0];
      look.holdBack = ends[1] || "";
    } else if (key === "width" || key === "height") {
      look.canvas = "set";
      look[key === "width" ? "canvasW" : "canvasH"] = Number(value);
    } else understood = false;
  });
  return understood ? playing : null;
}

// Try each kept line of each body as a screen or a sound, moving those that write back exactly
function readTabs(bodies) {
  var sizes = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^screen([ab])=(2\.8|1\.54)$/i);
    if (named) sizes[named[1].toUpperCase()] = {token: token, size: named[2]};
  });
  var readOn = {};

  bodies.forEach(function (body) {
    body.notes = body.notes || {};
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      if (!parts) return true;
      var read = false;

      var screen = parts.selector.match(/^screen([ab])$/);
      var letter = screen && screen[1].toUpperCase();
      if (letter && sizes[letter] && !body.screens[letter].shows) {
        var playing = screenPlaying(parts, body, letter);
        if (playing) {
          var fitted = state.screens[letter];
          var was = {there: fitted.there, size: fitted.size};
          fitted.there = true;
          fitted.size = sizes[letter].size;
          var trial = {screens: Object.assign({}, body.screens)};
          trial.screens[letter] = playing;
          if (screenEntry(letter, trial) === one.text) {
            body.screens[letter] = playing;
            readOn[letter] = true;
            read = true;
          } else {
            fitted.there = was.there;
            fitted.size = was.size;
          }
        }
      }

      if (!read && parts.selector === "audio" && parts.effect === "wav" && !body.sound &&
          Object.keys(parts.right).every(function (key) { return key === "file" || key === "loop"; })) {
        var sounding = {sound: unquoted(parts.right.file), soundLoop: parts.right.loop === "true",
                        soundKept: null};
        if (sounding.sound && soundLine(sounding) === one.text) {
          body.sound = sounding.sound;
          body.soundLoop = sounding.soundLoop;
          read = true;
        }
      }

      // A read line's comments are written above it again while it says the same
      if (read && one.comments.length) body.notes[one.text] = one.comments;
      return !read;
    });
  });

  // A screen read is fitted at its size, which the page writes itself from here
  Object.keys(readOn).forEach(function (letter) {
    boardResidue.splice(boardResidue.indexOf(sizes[letter].token), 1);
  });
}

// ---- the lights -------------------------------------------------------------------------------
// A line, or the lines a look writes together, is read as a stretch where some look, its sliders
// solved back from the line, writes exactly those lines again for exactly those lights. The
// sliders are solved as the figures drawer solves a typed figure, a value past a slider's end
// held as typed. Whole outputs and strips are read; channels broken out, a signal's own timings
// and a Blink's several colours stay kept for now

// The lamps of a run a line's selector names, in the order it names them, or null
function lampsNamed(run, selector) {
  var match;
  if (run.strip) {
    if (selector.toLowerCase() === run.name) {
      return run.lamps.map(function (lamp, at) { return at; });
    }
    match = selector.match(new RegExp("^" + run.name + "(\\d[\\d,\\-]*)$", "i"));
    if (!match) return null;
    var named = [];
    var pieces = match[1].split(",");
    for (var p = 0; p < pieces.length; p++) {
      var bounds = pieces[p].match(/^(\d+)(?:-(\d+))?$/);
      if (!bounds) return null;
      var first = Number(bounds[1]);
      var last = bounds[2] === undefined ? first : Number(bounds[2]);
      var step = last >= first ? 1 : -1;
      for (var led = first; led !== last + step; led += step) {
        if (led < 1 || led > run.lamps.length) return null;
        named.push(led - 1);
      }
    }
    return named;
  }
  if (run.mono) return channelsNamed(run, selector);
  if (!/^out\d/i.test(selector) || selector.indexOf(".") >= 0) return null;
  var outputs = [];
  var items = selector.slice(3).split(",");
  for (var i = 0; i < items.length; i++) {
    var ends = items[i].match(/^(\d+)(?:-(\d+))?$/);
    if (!ends) return null;
    var from = Number(ends[1]);
    var to = ends[2] === undefined ? from : Number(ends[2]);
    var by = to >= from ? 1 : -1;
    for (var n = from; n !== to + by; n += by) outputs.push(n);
  }
  var lamps = [];
  for (var j = 0; j < outputs.length; j++) {
    var place = -1;
    run.lamps.forEach(function (lamp, at) {
      if (lamp.colour && lamp.out === outputs[j] - 1) place = at;
    });
    if (place < 0) return null;
    lamps.push(place);
  }
  return lamps;
}

// The mono run's lamps a selector names by channel, as autofx reads them: a range counting down
// counts each output's channels down too. Null where an item names a whole output
function channelsNamed(run, selector) {
  if (!/^out\d/i.test(selector)) return null;
  var lamps = [];
  var items = selector.slice(3).toLowerCase().split(",");
  for (var i = 0; i < items.length; i++) {
    var item = items[i].match(/^(\d+)(?:-(\d+))?\.([rgb*])$/);
    if (!item) return null;
    var from = Number(item[1]);
    var to = item[2] === undefined ? from : Number(item[2]);
    var step = to >= from ? 1 : -1;
    var channels = item[3] === "*" ? (step < 0 ? [2, 1, 0] : [0, 1, 2])
                 : [CHANNELS.indexOf(item[3])];
    for (var out = from; out !== to + step; out += step) {
      for (var c = 0; c < channels.length; c++) {
        var place = -1;
        run.lamps.forEach(function (lamp, at) {
          if (!lamp.colour && lamp.out === out - 1 && lamp.channel === channels[c]) place = at;
        });
        if (place < 0) return null;
        lamps.push(place);
      }
    }
  }
  return lamps;
}

// The outputs any kept line names by channel, which the file has broken out
function outputsBrokenOut(bodies) {
  var broken = {};
  bodies.forEach(function (body) {
    body.kept.forEach(function (one) {
      var parts = entryParts(one.text);
      if (!parts || !/^out\d/i.test(parts.selector)) return;
      parts.selector.slice(3).split(",").forEach(function (item) {
        var named = item.match(/^(\d+)(?:-(\d+))?\.[rgb*]$/i);
        if (!named) return;
        var from = Number(named[1]);
        var to = named[2] === undefined ? from : Number(named[2]);
        var step = to >= from ? 1 : -1;
        for (var out = from; out !== to + step; out += step) broken[out - 1] = true;
      });
    });
  });
  return broken;
}

// The wiring the file implies: the outputs it names by channel broken out, in the plain order
function wireAsRead(broken) {
  wiring = wiring.map(function (one, out) { return {broken: !!broken[out]}; });
  order = plainOrder();
}

// Every lamp in number order, an output broken out as its red, green and blue
function plainOrder() {
  var plain = [];
  wiring.forEach(function (one, out) {
    if (one.broken) CHANNELS.forEach(function (letter, c) { plain.push({out: out, channel: c}); });
    else plain.push({out: out, channel: null});
  });
  return plain;
}

// ---- the wiring, in a comment of the page's own -------------------------------------------------
// The file's lines cannot say how the lamps are wired: a range counting down is a stretch reversed
// or lamps wired that way round, and both write the same line. So where the order is not plain
// number order the page says it in a comment of its own, which autofx passes over, and reads it
// back before any stretch

var WIRED = "# Wired in the order ";

// The order the file said it was wired in, as read, or null
var wiringRead = null;

function wiringLine() {
  var plain = plainOrder();
  var same = order.length === plain.length && order.every(function (place, at) {
    return place.out === plain[at].out && place.channel === plain[at].channel;
  });
  if (same) return null;
  return WIRED + "out" + order.map(function (place) {
    return (place.out + 1) + (place.channel === null ? "" : "." + CHANNELS[place.channel]);
  }).join(",");
}

// A wiring said as a file names outputs, as an order the page holds, or null where it does not
// name every output exactly once, whole or as its three channels
function orderSaid(said) {
  var items = said.replace(/^out/i, "").toLowerCase().split(",");
  var placed = [];
  for (var i = 0; i < items.length; i++) {
    var item = items[i].match(/^(\d+)(?:-(\d+))?(?:\.([rgb*]))?$/);
    if (!item) return null;
    var from = Number(item[1]);
    var to = item[2] === undefined ? from : Number(item[2]);
    var step = to >= from ? 1 : -1;
    for (var out = from; out !== to + step; out += step) {
      if (item[3] === undefined) placed.push({out: out - 1, channel: null});
      else if (item[3] === "*") {
        (step < 0 ? [2, 1, 0] : [0, 1, 2]).forEach(function (c) {
          placed.push({out: out - 1, channel: c});
        });
      } else placed.push({out: out - 1, channel: CHANNELS.indexOf(item[3])});
    }
  }
  // Each output once whole, or each of its three channels once
  var seen = {};
  for (var p = 0; p < placed.length; p++) {
    var key = placed[p].out + "." + placed[p].channel;
    if (placed[p].out < 0 || placed[p].out >= wiring.length || seen[key]) return null;
    seen[key] = true;
  }
  for (var o = 0; o < wiring.length; o++) {
    var whole = seen[o + ".null"];
    var channels = [0, 1, 2].filter(function (c) { return seen[o + "." + c]; }).length;
    if (whole ? channels : channels !== 3) return null;
  }
  return placed;
}

// Where a file has no wiring comment, a line naming whole outputs out of number order can only have
// been written for lamps wired that way, so the always-on lines, then each scene's, say the order
// in the order they name them, the outputs they leave out following in number order
function orderImplied(bodies) {
  var named = [];
  var needed = false;
  bodies.forEach(function (body) {
    body.kept.forEach(function (one) {
      var parts = entryParts(one.text);
      if (!parts || !/^out\d[\d,\-]*$/i.test(parts.selector)) return;
      var outputs = [];
      parts.selector.slice(3).split(",").forEach(function (item) {
        var ends = item.split("-").map(Number);
        var step = (ends[1] || ends[0]) >= ends[0] ? 1 : -1;
        for (var out = ends[0]; out !== (ends[1] || ends[0]) + step; out += step) outputs.push(out);
      });
      // A look that deals its lights out names gapped sets such as 1,4,7, which say nothing of
      // the wiring, so only a list with no gaps counts, and one going both up and down needs it
      var steps = outputs.slice(1).map(function (out, at) { return out - outputs[at]; });
      if (steps.some(function (step) { return Math.abs(step) !== 1; }) &&
          !(steps.some(function (step) { return step > 0; }) &&
            steps.some(function (step) { return step < 0; }))) return;
      if (steps.some(function (step) { return step > 0; }) &&
          steps.some(function (step) { return step < 0; })) needed = true;
      outputs.forEach(function (out) { if (named.indexOf(out) < 0) named.push(out); });
    });
  });
  if (!needed) return null;
  for (var out = 1; out <= wiring.length; out++) if (named.indexOf(out) < 0) named.push(out);
  return named.map(function (out) { return {out: out - 1, channel: null}; });
}

// Whether a set of lamps is one run from end to end, whichever way it was named
function spanOf(lamps) {
  var sorted = lamps.slice().sort(function (a, b) { return a - b; });
  for (var i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return null;
  }
  return {from: sorted[0], to: sorted[sorted.length - 1]};
}

// A stretch that would write these lines, or null where no look does
function stretchWriting(run, texts, span) {
  var parts = entryParts(texts[0]);
  var colour = null;
  var custom = false;
  var blinks = null;
  function hexFor(word) {
    word = word.toLowerCase();
    return "#" + (word === "black" ? "000000" : WORDS[word] ? hexOf(WORDS[word]) : word);
  }
  if (parts.left.colour) {
    var word = parts.left.colour.toLowerCase();
    colour = hexFor(word);
    custom = !WORDS[word];
  }
  // Several colours after the colon are a Blink's set, blinked through in turn
  if (parts.right.colour && parts.right.colour.indexOf("|") >= 0) {
    blinks = {colours: parts.right.colour.split("|").map(hexFor), at: 0};
    colour = blinks.colours[0];
    custom = !wordFor(colour);
  }
  var level = parts.left.level ? parseFloat(parts.left.level) / 100 : 1;

  // A look with colours of its own, as Party's sets or a tone its slider picks, writes them with
  // no colour chosen, so each look is tried with the line's colour and then with none
  var looks = everyLook();
  var tries = [];
  [{colour: colour, custom: custom}, {colour: null, custom: false}].forEach(function (chosen) {
    [false, true].forEach(function (back) {
      looks.forEach(function (look) { tries.push({look: look, chosen: chosen, back: back}); });
    });
  });
  for (var t = 0; t < tries.length; t++) {
    var look = tries[t].look;
    var section = {from: span.from, to: span.to, look: keyOf(look), pace: 0.5, mood: 0.5,
                   colour: tries[t].chosen.colour, custom: tries[t].chosen.custom,
                   reversed: tries[t].back, level: level,
                   blinks: blinks && look.name === BLINK ? JSON.parse(JSON.stringify(blinks)) : null,
                   exact: null, timings: signalTimings(look, texts)};
    if (!canPlay(look, targetFor(run, section))) continue;
    solveSliders(run, section, look, texts);
    var written = sectionLines(run, section, look);
    if (sameLines(written, texts)) return section;
    if (sameShape(written, texts) && refineSliders(run, section, look, texts)) return section;
  }
  return null;
}

// A signal's timings as its lines give them, each its own setting, or null for any other look
function signalTimings(look, texts) {
  if (!SIGNAL_TIMINGS[look.name]) return null;
  var timings = {};
  SIGNAL_TIMINGS[look.name].forEach(function (part) {
    var said = (texts.join(" ").match(new RegExp("(^|\\s)" + part[0] + "=([\\d.]+)")) || [])[2];
    if (said !== undefined) timings[part[0]] = Number(said);
  });
  return timings;
}

function sameLines(written, texts) {
  return written.length === texts.length && written.every(function (line, at) {
    return line === texts[at];
  });
}

// Whether lines differ only in their values, which a slider placed more finely may close, as a
// palette's colours are closed by its slider
function sameShape(written, texts) {
  function shape(line) { return line.replace(/=[^\s:]+/g, "=#"); }
  return written.length === texts.length && written.every(function (line, at) {
    return shape(line) === shape(texts[at]);
  });
}

// A slider moving two settings rounds each its own way, so the place its figure gives can leave
// the other a step out. Each slider in turn is looked along its whole reach for a place where
// every line matches
function refineSliders(run, section, look, texts) {
  var sliders = ["pace", "mood"];
  for (var pass = 0; pass < 2; pass++) {
    for (var s = 0; s < sliders.length; s++) {
      var slider = sliders[s];
      if (section.exact && section.exact[slider]) continue;
      for (var step = 0; step <= 200; step++) {
        var trial = Object.assign({}, section);
        trial[slider] = step / 200;
        if (sameLines(sectionLines(run, trial, look), texts)) {
          section[slider] = trial[slider];
          return true;
        }
      }
    }
  }
  return false;
}

// Each slider set to the place that writes the lines' value for the setting it moves, a value
// past its reach held as typed
function solveSliders(run, section, look, texts) {
  ["pace", "mood"].forEach(function (slider) {
    var key = figureKey(run, section, look, slider);
    if (!key) return;
    // Read as the figures drawer shows it, a wave's speed without its sign
    var value = settingIn(texts, key);
    if (value === null) return;
    var found = placeFor(run, section, look, slider, key, value);
    section[slider] = found.place;
    if (found.off > 1e-6) {
      section.exact = Object.assign({}, section.exact);
      section.exact[slider] = {key: key, value: value};
    }
  });
}

// The groups of kept lines from one place that could be one stretch: consecutive lines naming
// one run's lights, together an unbroken run with no light named twice, clear of the stretches
// already read. The most lines first, so a look that deals its lights out over several lines, or
// writes its spare ones as none, is read whole rather than as its first line alone
function groupsFrom(at, read) {
  var found = [];
  runs.forEach(function (run) {
    var lamps = [];
    for (var k = 1; at + k <= keptNow.length; k++) {
      var parts = entryParts(keptNow[at + k - 1].text);
      var some = parts && lampsNamed(run, parts.selector);
      if (!some) break;
      lamps = lamps.concat(some);
      var span = spanOf(lamps);
      if (!span || span.to - span.from + 1 !== lamps.length) continue;
      var clear = !read[run.name].some(function (one) {
        return one.from <= span.to && span.from <= one.to;
      });
      if (clear) found.push({run: run, k: k, span: span});
    }
  });
  return found.sort(function (a, b) { return b.k - a.k; });
}

function readLights(bodies) {
  // A strip's length is the board's, read from its token, which the page writes itself once
  // a stretch of the strip is read
  var lengths = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(strip[lr])=(\d+)(?:\|([rgb]{3}))?$/i);
    if (!named) return;
    // The board's own order is held as no order, so writing it back changes nothing. One
    // the page does not offer stays as written, for the board to answer
    var order = (named[3] || "").toLowerCase();
    if (order === "grb") order = "";
    var offered = STRIP_ORDERS.some(function (pair) { return pair[0] === order; });
    if (offered) lengths[named[1].toLowerCase()] = {token: token, leds: Number(named[2]), order: order};
  });
  runs.forEach(function (run) {
    if (!run.strip || !lengths[run.name]) return;
    var one = STRIPS.filter(function (strip) { return strip.id === run.id; })[0];
    one.leds = lengths[run.name].leds;
    one.order = lengths[run.name].order;
    run.leds = one.leds;
    run.order = one.order;
    // A file giving the strip a length has it fitted, whatever this page had removed
    one.there = true;
    run.there = true;
  });
  var stripsRead = {};
  var broken = outputsBrokenOut(bodies);
  var said = wiringRead && orderSaid(wiringRead);

  bodies.forEach(function (body) {
    apply(body);
    // The wiring the page said, else the one the lines imply, else number order
    if (said) {
      wiring = wiring.map(function (one, out) {
        return {broken: said.some(function (place) {
          return place.out === out && place.channel !== null;
        })};
      });
      order = said.map(function (place) { return {out: place.out, channel: place.channel}; });
    } else {
      wireAsRead(broken);
      var implied = !Object.keys(broken).length && orderImplied(bodies);
      if (implied) order = implied;
    }
    runs.forEach(function (run) { run.sections = []; });
    settle();
    var read = {};
    runs.forEach(function (run) { read[run.name] = []; });

    var at = 0;
    while (at < keptNow.length) {
      var matched = false;
      var candidates = groupsFrom(at, read);
      for (var c = 0; c < candidates.length && !matched; c++) {
        var one = candidates[c];
        var group = keptNow.slice(at, at + one.k);
        var texts = group.map(function (kept) { return kept.text; });
        var section = stretchWriting(one.run, texts, one.span);
        if (!section) continue;
        read[one.run.name].push(section);
        if (one.run.strip) stripsRead[one.run.name] = true;
        group.forEach(function (kept) {
          if (kept.comments.length) notesNow[kept.text] = kept.comments;
        });
        keptNow.splice(at, one.k);
        matched = true;
      }
      if (!matched) at++;
    }

    // Lights no read stretch covers play nothing, filled in here, since settling would close a
    // gap by stretching the stretch before it
    runs.forEach(function (run) {
      var sorted = read[run.name].sort(function (a, b) { return a.from - b.from; });
      var filled = [];
      var next = 0;
      sorted.forEach(function (section) {
        if (section.from > next) filled.push(blank(next, section.from - 1, run));
        filled.push(section);
        next = section.to + 1;
      });
      if (next < run.lamps.length) filled.push(blank(next, run.lamps.length - 1, run));
      run.sections = filled;
    });
    settle();
    var captured = capture();
    Object.keys(captured).forEach(function (key) { body[key] = captured[key]; });
  });

  Object.keys(stripsRead).forEach(function (name) {
    boardResidue.splice(boardResidue.indexOf(lengths[name].token), 1);
  });
}

// ---- the hub ----------------------------------------------------------------------------------

// Hub positions as a file names them, hubA-C,E, or null where the item is not one
function hubPlacesNamed(selector) {
  var match = selector.match(/^hub([a-f](?:-[a-f])?(?:,[a-f](?:-[a-f])?)*)$/i);
  if (!match) return null;
  var places = [];
  match[1].toUpperCase().split(",").forEach(function (part) {
    var ends = part.split("-");
    var from = HUB_PLACES.indexOf(ends[0]);
    var to = HUB_PLACES.indexOf(ends[1] || ends[0]);
    var step = to >= from ? 1 : -1;
    for (var at = from; at !== to + step; at += step) places.push(HUB_PLACES[at]);
  });
  return places;
}

// The hub the board line declares, read into the page, which writes those tokens itself from
// then on. Left alone where the line declares none
function readHubBoard() {
  var port = null;
  var sizes = {};
  var taken = [];
  boardResidue.forEach(function (token) {
    var wired = token.match(/^screen([ab])=hub$/i);
    var sized = token.match(/^(hub[a-f\-,]+)=(2\.8|1\.54)$/i);
    if (wired) {
      port = wired[1].toUpperCase();
      taken.push(token);
    } else if (sized && hubPlacesNamed(sized[1])) {
      hubPlacesNamed(sized[1]).forEach(function (place) { sizes[place] = sized[2]; });
      taken.push(token);
    }
  });
  state.hub.on = false;
  if (!port) return;

  state.hub.on = true;
  state.hub.port = port;
  HUB_PLACES.forEach(function (place) { state.hub.sizes[place] = sizes[place] || ""; });
  boardResidue = boardResidue.filter(function (token) { return taken.indexOf(token) < 0; });
}

// Try each kept line of each body as a hub entry, moving those the hub's own writer gives back
function readHubLines(bodies) {
  if (!state.hub.on) return;

  // Each scene lights the hub its own way, the first of its lines to be read deciding
  bodies.forEach(function (body) {
    var numbered = 0;
    var lightSet = false;
    state.hubLight = 1;
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      var places = parts && hubPlacesNamed(parts.selector);
      if (!places || places.some(function (place) {
        return !state.hub.sizes[place] || body.places[place].shows;
      })) return true;

      var playing = screenPlaying(parts, {screens: {X: {}}}, "X");
      if (!playing) return true;
      var light = playing.look.backlight;
      if (lightSet && light !== state.hubLight) return true;

      var trial = {places: JSON.parse(JSON.stringify(body.places))};
      var group = places.length > 1 ? String(numbered + 1) : places[0];
      places.forEach(function (place) {
        trial.places[place] = Object.assign({}, trial.places[place], {
          shows: playing.shows, turn: playing.turn || 0, pingpong: !!playing.pingpong,
          hold: playing.hold || "", look: Object.assign({}, playing.look), group: group});
      });
      var wasLight = state.hubLight;
      state.hubLight = light;
      var written = placeGroups(trial).filter(function (one) {
        return one.places.join() === places.slice().sort(function (a, b) {
          return HUB_PLACES.indexOf(a) - HUB_PLACES.indexOf(b);
        }).join();
      }).map(hubEntry)[0];
      if (written !== one.text) {
        state.hubLight = wasLight;
        return true;
      }

      body.places = trial.places;
      lightSet = true;
      if (places.length > 1) numbered++;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
    body.hubLight = state.hubLight;
  });
}

// ---- kept entries travel with their scene -----------------------------------------------------

bodyParts.push({
  capture: function (body) {
    body.kept = copyKept(keptNow);
    body.notes = JSON.parse(JSON.stringify(notesNow));
  },
  apply: function (body) {
    keptNow = copyKept(body.kept);
    notesNow = JSON.parse(JSON.stringify(body.notes || {}));
  },
  // A body with nothing in it keeps nothing either, whatever the scene on show kept
  blank: function (body) {
    body.kept = [];
    body.notes = {};
  },
  // Kept entries come last in their scene, each with its comments above it. A line read into
  // the page has its comments above it again while it writes the same
  entries: function (body, written) {
    var notes = body.notes || {};
    var lines = [];
    written.forEach(function (line) {
      lines = lines.concat(notes[line] || []);
      lines.push(line);
    });
    (body.kept || []).forEach(function (one) {
      lines = lines.concat(one.comments);
      if (one.text !== null) lines.push(one.text);
    });
    return lines;
  }
});

// ---- writing them back ------------------------------------------------------------------------

// The board line's tokens this page does not hold, after its own
boardLineSteps.after.push(function (line) {
  // A strip whose length the page writes itself leaves out any kept for it, which coming
  // later would be the one the board takes
  var written = (line || "").toLowerCase().match(/\bstrip[lr](?==)/g) || [];
  var kept = boardResidue.filter(function (token) {
    var named = token.match(/^(strip[lr])=/i);
    return !named || written.indexOf(named[1].toLowerCase()) < 0;
  });
  if (kept.length) line = (line || "board:") + " " + kept.join(" ");
  return line;
});

// Under the header, the wiring where it is not number order, then the comments above the board line
fileHead.under.push(function () {
  var wired = wiringLine();
  return wired ? [wired] : [];
});
fileHead.above.push(function () { return boardComments; });

// ---- showing them -----------------------------------------------------------------------------

function renderKept() {
  var box = document.getElementById("keptLines");
  if (!box) {
    box = document.createElement("div");
    box.id = "keptLines";
    box.className = "keptlines";
    // Above the file's own box, so the lines show while the file is folded
    var preview = document.getElementById("preview");
    var file = preview.closest("details") || preview;
    file.parentNode.insertBefore(box, file);
  }
  var shown = keptNow.filter(function (one) { return one.text !== null; });
  box.hidden = !shown.length;
  box.textContent = "";
  if (!shown.length) return;

  var head = document.createElement("div");
  head.className = "keptsay";
  head.textContent = "Also " + (state.scenes.length ? "in this scene" : "in the file") +
                     ", kept as written:";
  box.appendChild(head);
  keptNow.forEach(function (one, at) {
    if (one.text === null) return;
    var row = document.createElement("div");
    row.className = "keptrow";
    var code = document.createElement("code");
    code.textContent = one.text;
    row.appendChild(code);
    var drop = document.createElement("button");
    drop.className = "keptdrop";
    drop.textContent = "\u00d7";
    drop.title = "Take this line out of the file";
    drop.onclick = function () {
      keptNow.splice(at, 1);
      draw();
    };
    row.appendChild(drop);
    box.appendChild(row);
  });
}

// The lights of a run the scene's kept lines name, as places in the run, with the lines naming each
function keptLights(run) {
  var named = {};
  keptNow.forEach(function (one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    (lamps || []).forEach(function (at) { (named[at] = named[at] || []).push(one); });
  });
  return named;
}

// Lights a kept line plays are taken, marked on the run and on a strip's bar
function markKeptLights() {
  runs.forEach(function (run) {
    var named = keptLights(run);
    if (run.strip) {
      var bar = document.getElementById(run.id + "Bar");
      if (!bar) return;
      bar.querySelectorAll(".sec").forEach(function (cell, at) {
        var section = run.sections[at];
        if (!section) return;
        for (var lamp = section.from; lamp <= section.to; lamp++) {
          if (named[lamp]) {
            cell.classList.add("keptlamp");
            cell.title = "played by a line kept as written: " + named[lamp][0].text;
            return;
          }
        }
      });
      return;
    }
    var box = document.getElementById(run === outs ? "outRun" : "monoRun");
    if (!box) return;
    box.querySelectorAll(".lamp").forEach(function (lamp, at) {
      if (!named[at]) return;
      lamp.classList.add("keptlamp");
      lamp.title = "played by a line kept as written: " + named[at][0].text;
    });
  });
}

drawSteps.after.push(function () {
  renderKept();
  markKeptLights();
});

// A look chosen for lights a kept line plays asks first, since the board refuses a light set
// twice: agreed, the kept lines go and the look plays; declined, nothing changes
var oneReadLandLook = landLook;

landLook = function (run, at, name) {
  var section = run.sections[at];
  if (section && name) {
    var named = keptLights(run);
    var clashing = [];
    for (var lamp = section.from; lamp <= section.to; lamp++) {
      (named[lamp] || []).forEach(function (one) {
        if (clashing.indexOf(one) < 0) clashing.push(one);
      });
    }
    if (clashing.length) {
      var lines = clashing.map(function (one) { return one.text; }).join("\n");
      if (!confirm((clashing.length === 1 ? "A line kept as written already plays some of " +
                    "these lights:" : "Lines kept as written already play some of these " +
                    "lights:") + "\n\n" + lines + "\n\nTake " +
                   (clashing.length === 1 ? "it" : "them") + " out of the file and play " +
                   name + " instead?")) return;
      keptNow = keptNow.filter(function (one) { return clashing.indexOf(one) < 0; });
    }
  }
  oneReadLandLook(run, at, name);
};

// A strip removed takes with it every scene's kept lines that play on it, and its length
// as written, or they would keep its connector on
var oneReadDropStrip = dropStrip;

dropStrip = function (run) {
  function elsewhere(one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    return !(lamps && lamps.length);
  }
  keptNow = keptNow.filter(elsewhere);
  allBodies().forEach(function (held) { held.kept = (held.kept || []).filter(elsewhere); });
  boardResidue = boardResidue.filter(function (token) {
    var named = token.match(/^(strip[lr])=/i);
    return !named || named[1].toLowerCase() !== run.name;
  });
  oneReadDropStrip(run);
};

// ---- when the drive is opened -----------------------------------------------------------------

// A file this page wrote opens straight in. Any other asks first, saying what would be kept
connectSteps.push(async function () {
  var text = await (await drive.fileHandle.getFile()).text();
  if (!text.trim()) return;

  var ours = text.indexOf(HEADER) === 0;
  if (!ours) {
    var kept = readEffects(text).slots.reduce(function (count, slot) {
      return count + slot.kept.filter(function (one) { return one.text !== null; }).length;
    }, 0);
    var open = confirm("This file was not written by this page. Open what's on the board? " +
                       (kept === 1 ? "One line" : kept + " lines") + " would be kept as " +
                       "written. Cancel starts fresh, and saving then replaces the file.");
    if (!open) {
      rememberRead(text);
      return;
    }
  }
  absorbFile(text);
  rememberRead(text);
});

// Read or passed over by choice, the file is this page's to save over without asking again
function rememberRead(text) {
  try { localStorage.setItem(WROTE_KEY, text); } catch (e) {}
}

overwriteQuestion = function () {
  return "The file on the board has changed since this page read it, so saving replaces " +
         "those changes. Save over it?";
};
