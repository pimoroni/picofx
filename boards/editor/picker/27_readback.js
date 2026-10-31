
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

  boardSet.reload = true;
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
  bodies.forEach(function (body) { body.notes = body.notes || {}; });
  bodyParts.forEach(function (part) { if (part.readBoard) part.readBoard(); });
  bodyParts.forEach(function (part) { if (part.read) part.read(bodies); });
  readLights(bodies);
  state.at = -1;
  apply(state.always.body);
  // A file fitting a strip beside one whose terminals it takes plays the other, as the board
  // does, so this one is taken out with its lines
  runs.filter(function (run) {
    return run.strip && run.there && runs.some(function (other) {
      return other.strip && other.there && run.takes.indexOf(other.name) >= 0;
    });
  }).forEach(dropStrip);
  draw();
}

// ---- the parts' own lines out of the kept lines -----------------------------------------------
// Each kept line is tried as a setting of the part it names, and read only where that part's own
// writer then gives back exactly the line. So a setting read wrongly leaves the line kept, never
// changed. A read line's comments are written above it again while it says the same

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
  var places = placesNamed(selector);
  if (!places) return null;
  var lamps = [];
  for (var j = 0; j < places.length; j++) {
    var place = -1;
    run.lamps.forEach(function (lamp, at) {
      if (lamp.out === places[j].out && lamp.colour === (places[j].channel === null) &&
          (lamp.colour || lamp.channel === places[j].channel)) place = at;
    });
    if (place < 0) return null;
    lamps.push(place);
  }
  return lamps;
}

// Each item of a selector as the places it names on this board, in its order, as autofx reads
// it, or null for an item naming none. An item names an output by name, or a range of one name's
// numbers, whole or with a channel or .* for its three, a range counting down counting the
// channels down too. A mono output is its one light. An item's prefix carries on to a bare
// number after it
function itemsNamed(selector) {
  var prefix = null;
  return selector.toLowerCase().split(",").map(function (text) {
    var item = text.match(/^([a-z]*)(\d+)?(?:-(\d+))?(?:\.([rgb*]))?$/);
    if (!item || (!item[1] && !prefix) || (item[3] !== undefined && item[2] === undefined)) {
      return null;
    }
    prefix = item[1] || prefix;
    var outs = [];
    if (item[2] === undefined) {
      outs = OUTPUTS.map(function (output, out) { return output.name === prefix ? out : -1; })
        .filter(function (out) { return out >= 0; });
    } else {
      var from = Number(item[2]);
      var to = item[3] === undefined ? from : Number(item[3]);
      var step = to >= from ? 1 : -1;
      for (var number = from; number !== to + step; number += step) {
        var found = OUTPUTS.map(function (output, out) {
          return output.prefix === prefix && output.number === number ? out : -1;
        }).filter(function (out) { return out >= 0; });
        if (!found.length) return null;
        outs.push(found[0]);
      }
    }
    if (!outs.length) return null;
    var channels = item[4] === undefined ? [null]
                 : item[4] === "*" ? (step < 0 ? [2, 1, 0] : [0, 1, 2])
                 : [CHANNELS.indexOf(item[4])];
    var places = [];
    for (var at = 0; at < outs.length; at++) {
      var mono = OUTPUTS[outs[at]].mono;
      if (mono && item[4] !== undefined) return null;
      for (var c = 0; c < channels.length; c++) {
        places.push({out: outs[at], channel: mono ? 0 : channels[c]});
      }
    }
    return places;
  });
}

// The places a selector names, or null where any item names none
function placesNamed(selector) {
  var items = itemsNamed(selector);
  if (items.some(function (places) { return !places; })) return null;
  return [].concat.apply([], items);
}

// The outputs any kept line names by channel, which the file has broken out
function outputsBrokenOut(bodies) {
  var broken = {};
  bodies.forEach(function (body) {
    body.kept.forEach(function (one) {
      var parts = entryParts(one.text);
      if (!parts) return;
      itemsNamed(parts.selector).forEach(function (places) {
        (places || []).forEach(function (place) {
          if (place.channel !== null && !OUTPUTS[place.out].mono) broken[place.out] = true;
        });
      });
    });
  });
  return broken;
}

// The wiring the file implies: the outputs it names by channel broken out, in the plain order
function wireAsRead(broken) {
  wiring = wiring.map(function (one, out) {
    return {broken: OUTPUTS[out].mono || !!broken[out]};
  });
  order = plainOrder();
}

// Every lamp in number order, an output broken out as its red, green and blue
function plainOrder() {
  var plain = [];
  wiring.forEach(function (one, out) { plain = plain.concat(placesOf(out)); });
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
  return WIRED + joinedItems(order.map(function (place) {
    var output = OUTPUTS[place.out];
    var channel = place.channel === null || output.mono ? "" : "." + CHANNELS[place.channel];
    return {out: place.out, rest: (output.number === null ? "" : String(output.number)) + channel};
  }));
}

// A wiring said as a file names outputs, as an order the page holds, or null where it does not
// name every output exactly once: a mono output's one light, or a colour output whole or as its
// three channels. One starting with a bare number is of the first output's name
function orderSaid(said) {
  var placed = placesNamed(/^\d/.test(said) ? OUTPUTS[0].prefix + said : said);
  if (!placed) return null;
  var seen = {};
  for (var p = 0; p < placed.length; p++) {
    var key = placed[p].out + "." + placed[p].channel;
    if (seen[key]) return null;
    seen[key] = true;
  }
  for (var o = 0; o < wiring.length; o++) {
    if (OUTPUTS[o].mono) {
      if (!seen[o + ".0"]) return null;
      continue;
    }
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
      var places = parts && placesNamed(parts.selector);
      if (!places || places.some(function (place) {
        return place.channel !== null && !OUTPUTS[place.out].mono;
      })) return;
      var outputs = places.map(function (place) { return place.out + 1; });
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
  return named.map(function (out) {
    return {out: out - 1, channel: OUTPUTS[out - 1].mono ? 0 : null};
  });
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
    var named = token.match(/^(\w+)=(\d+)(?:\|(\S+))?$/i);
    var run = named && stripNamed(named[1]);
    if (!run) return;
    // What follows the length, as the page holds it, the board's own being held as nothing so
    // writing it back changes nothing. One the page does not offer stays as written, for the
    // board to answer
    var values = readStripTail(run, named[3] || "");
    if (!values) return;
    values.leds = Number(named[2]);
    // A file giving the strip a length has it fitted, whatever this page had removed
    values.there = true;
    lengths[run.name] = {token: token, values: values};
  });
  runs.forEach(function (run) {
    if (run.strip && lengths[run.name]) stripSet(run, lengths[run.name].values);
  });
  // A file naming any strip is the board as built, so the strips it names are fitted and no others
  if (Object.keys(lengths).length) {
    runs.forEach(function (run) {
      if (run.strip && !lengths[run.name]) stripSet(run, {there: false});
    });
  }
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

// The strip a board token gives a length, such as stripl for stripl=30, or null
function stripOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  return STRIPS.some(function (strip) { return strip.name === name; }) ? name : null;
}

// The strip or screen port a board token sets, such as stripl for stripl=30 or screena for
// screena=2.8, or null
function heldOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  var held = STRIPS.map(function (strip) { return strip.name; })
    .concat(SCREEN_PORTS.map(function (port) { return port.id; }));
  return held.indexOf(name) >= 0 ? name : null;
}

// The board line's tokens this page does not hold, after its own
boardLineSteps.after.push(function (line) {
  // A strip or screen whose setting the page writes itself leaves out any kept for it, which
  // coming later would be the one the board takes
  var lower = (line || "").toLowerCase();
  var kept = boardResidue.filter(function (token) {
    var name = heldOfToken(token);
    return !name || !new RegExp("\\b" + name + "=").test(lower);
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

// A strip removed takes with it every scene's kept lines that play on it, and its length
// as written, or they would keep its connector on
function forgetKeptFor(run) {
  function elsewhere(one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    return !(lamps && lamps.length);
  }
  keptNow = keptNow.filter(elsewhere);
  allBodies().forEach(function (held) { held.kept = (held.kept || []).filter(elsewhere); });
  boardResidue = boardResidue.filter(function (token) { return stripOfToken(token) !== run.name; });
}

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
