import {BLINK} from "./blink.js";
import {
  BOARD_LINE_AFTER, NOT_FITTED, SCREEN_PORTS, boardLineSteps, notFittedLine, notFittedRead,
  saidNotFitted, setNotFittedRead, stripDescribed
} from "./board.js";
import {
  argsWritten, boardSet, onProgramPage, programNamed, programsReadSteps, setProgramPage
} from "./board_settings.js";
import {WORDS, hexOf, wordFor} from "./colours.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "./draw.js";
import {CONNECT_ORDER, WROTE_KEY, connectSteps, drive} from "./drive.js";
import {programsKnown} from "./drive_programs.js";
import {figureKey, placeFor, settingIn} from "./figures.js";
import {
  boardResidue, clearResidue, copyKept, filterResidue, keptLights, keptNow, setKept
} from "./kept.js";
import {sectionLines, targetFor} from "./lines.js";
import {HEADER, LOOKS, SIGNAL_TIMINGS, canPlay, keyOf} from "./looks.js";
import {CHANNELS, OUTPUTS, joinedItems, order, plainOrder, setLayout, wiring} from "./outputs.js";
import {
  argsRead, boardTokens, entryParts, itemsNamed, lampsNamed, placesNamed, spanOf, unquotedColon
} from "./reading.js";
import {blank, fileHead, outs, runs, settle} from "./runs.js";
import {
  BODY_ORDER, apply, blankBody, bodyParts, capture, hasContent, sceneMark, settleLoneScene, slotAt,
  state
} from "./scenes.js";
import {STRIPS, dropStrip, readStripTail, stripNamed, stripSet} from "./strips.js";
import {NOTHING_PLAYING, currentText} from "./writing.js";

// ---- reading the board's file back ----------------------------------------------------------
// Opening the drive reads effects.txt into the page. Every line is either read into the page's
// own settings or kept word for word in its scene, so a file comes back without loss. This part
// reads the board line, the scenes and the lights. The parts with a share of a scene, such as
// the screens and sound, first read theirs out of the kept lines.

// The lines this page writes of its own accord, which a file read back does not keep
var PAGE_LINES = HEADER.split("\n").filter(Boolean).concat([NOTHING_PLAYING]);
// The comments written above the board line
var boardComments = [];
// The comments of the lines the scene on show read, by the line they sit above
var notesNow = {};

// A scene heading, as autofx reads one. Where a word is neither a time nor restart, the heading
// is kept as written, since writing it again would lose it. "then" ends the settings, and the
// rest of the heading names the scene after, so a scene called "then" or "restart" can follow it
function readHeading(line) {
  var inner = line.slice(1, -1);
  var colon = inner.indexOf(":");
  var name = (colon < 0 ? inner : inner.slice(0, colon)).trim();
  var heading = {name: name, seconds: null, restart: false, after: null, line: line,
                 written: line};
  var odd = false;
  var settings = colon < 0 ? "" : inner.slice(colon + 1);
  var then = settings.match(/(^|\s)then(\s+|$)/i);
  if (then) {
    heading.after = settings.slice(then.index + then[0].length).trim();
    settings = settings.slice(0, then.index);
    if (!heading.after) odd = true;
  }
  settings.split(/\s+/).forEach(function (word) {
    if (!word) return;
    // A time in seconds or in minutes, held as seconds. Minutes are kept as written until the
    // scene's time is changed, as the page writes seconds
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

// The file in parts, as the board line's tokens and the comments above it, then each scene's
// kept entries, Always on's first. A line with no colon after an entry carries it on, as autofx
// reads one, and a comment goes with the entry or heading below it
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
      else if (line.indexOf(NOT_FITTED) === 0) {
        parsed.notFitted = line.slice(NOT_FITTED.length).split(",").map(function (name) {
          return name.trim().toLowerCase();
        }).filter(Boolean);
      } else if (PAGE_LINES.indexOf(line) < 0) comments.push(raw.replace(/\s+$/, ""));
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

// Read the program a file runs. Where the page knows it and writes its arguments back as the file
// has them, the program tab opens with it chosen. Otherwise both stay on the board line as
// written, and the page opens on the effects. A file running no program changes no tab
function readProgram(named, argued) {
  boardSet.program = null;
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
    setProgramPage(true);
    return;
  }
  setProgramPage(false);
  boardSet.args[path] = kept;
  boardResidue.push(named);
  if (argued) boardResidue.push(argued);
}

// A program the file names before the drive's programs are read, as [program=, args=]. It waits on
// the board line as written, so a save in the meantime keeps it
var programWaiting = null;

// Read the waiting program as readProgram() would have, once the programs are known, unless one
// was chosen in the meantime. Still unknown, it stays on the board line and the page where it is
function readWaitingProgram() {
  if (!programWaiting) return;
  var named = programWaiting[0], argued = programWaiting[1];
  programWaiting = null;
  if (boardSet.program) return;
  filterResidue(function (token) {
    return token !== named && token !== argued;
  });
  var page = onProgramPage;
  readProgram(named, argued);
  if (!boardSet.program) setProgramPage(page);
}
programsReadSteps.push(readWaitingProgram);

// Take a file into the page, with its board line, its scenes and every entry kept in its scene
function absorbFile(text) {
  var parsed = readEffects(text);
  wiringRead = parsed.wiring || null;
  setNotFittedRead(parsed.notFitted || null);

  boardSet.reload = true;
  boardSet.driveHidden = false;
  clearResidue();
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
  programWaiting = named && !boardSet.program && !programsKnown ? [named, argued] : null;
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
  // A scene after is named, and taken as the first scene of that name. A name no scene has
  // leaves its heading as written
  state.scenes.forEach(function (scene) {
    if (!scene.read.after) return;
    var named = state.scenes.filter(function (other) { return other.name === scene.read.after; })[0];
    if (named) scene.then = sceneMark(named);
    else scene.read.written = scene.read.line;
  });
  settleLoneScene();
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) { return scene.body; }));
  bodies.forEach(function (body) { body.notes = body.notes || {}; });
  bodyParts.forEach(function (part) { if (part.readBoard) part.readBoard(); });
  bodyParts.forEach(function (part) { if (part.read) part.read(bodies); });
  readLights(bodies);
  // A file whose Always on plays nothing opens on its first scene, where there is something to see
  state.at = state.scenes.length && !hasContent(state.always.body) ? 0 : -1;
  apply(slotAt(state.at).body);
  // A file fitting a strip beside one whose terminals it takes plays the other, as the board
  // does, so this one is taken out with its lines
  runs.filter(function (run) {
    return run.strip && run.there && runs.some(function (other) {
      return other.strip && other.there && run.takes.indexOf(other.name) >= 0;
    });
  }).forEach(dropStrip);
  draw();
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

// Set the wiring the file implies, with the outputs it names by channel broken out, in plain order
function wireAsRead(broken) {
  setLayout(wiring.map(function (one, out) {
    return {broken: OUTPUTS[out].mono || !!broken[out]};
  }), order);
  // The plain order is of the wiring just set
  setLayout(wiring, plainOrder());
}

// ---- the wiring, in a comment of the page's own -------------------------------------------------
// The file's lines cannot say how the lamps are wired. A range counting down is a stretch reversed
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
// name every output exactly once, as a mono output's one light or a colour output whole or as its
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
// been written for lamps wired that way. So Always on's lines, then each scene's, give the order
// they name them in, and the outputs they leave out follow in number order
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
      // A look that deals its lights out names gapped sets such as 1,4,7, which say nothing of the
      // wiring. A list counts with no gaps or running both ways, and only the second needs an order
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
  var tries = [];
  [{colour: colour, custom: custom}, {colour: null, custom: false}].forEach(function (chosen) {
    [false, true].forEach(function (back) {
      LOOKS.forEach(function (look) { tries.push({look: look, chosen: chosen, back: back}); });
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
    if (sameLines(written, texts) ||
        (sameShape(written, texts) && refineSliders(run, section, look, texts))) {
      roundSliders(run, section, look, texts);
      return section;
    }
  }
  return null;
}

// Move each slider to the roundest of the places that write the same lines, as a person sets a
// slider, so a save reads back where it was saved. Several places can write them once values are
// rounded, such as Campfire's speed at 0.44 and 0.45
function roundSliders(run, section, look, texts) {
  function roundness(step) {
    return step % 20 === 0 ? 3 : step % 10 === 0 ? 2 : step % 2 === 0 ? 1 : 0;
  }
  ["pace", "mood"].forEach(function (slider) {
    if (section.exact && section.exact[slider]) return;
    var writing = [];
    for (var step = 0; step <= 200; step++) {
      var trial = Object.assign({}, section);
      trial[slider] = step / 200;
      if (sameLines(sectionLines(run, trial, look), texts)) writing.push(step);
    }
    if (!writing.length) return;
    // Of the roundest, the one nearest the middle of the places that write the lines
    var middle = (writing[0] + writing[writing.length - 1]) / 2;
    var best = writing.reduce(function (chosen, step) {
      if (roundness(step) !== roundness(chosen))
        return roundness(step) > roundness(chosen) ? step : chosen;
      return Math.abs(step - middle) < Math.abs(chosen - middle) ? step : chosen;
    });
    section[slider] = best / 200;
  });
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

// Whether lines differ only in their values, which a slider placed more finely may close
function sameShape(written, texts) {
  function shape(line) { return line.replace(/=[^\s:]+/g, "=#"); }
  return written.length === texts.length && written.every(function (line, at) {
    return shape(line) === shape(texts[at]);
  });
}

// Look along each slider's whole reach for a place where every line matches. A slider that moves
// two settings rounds each its own way, so the place one gives can leave the other a step out
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

// Set each slider to the place that writes the lines' value for the setting it moves. A value no
// place writes exactly is held as typed
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

// The groups of kept lines starting at kept line `at` that could be one stretch, as consecutive
// lines naming one run's lights, together an unbroken span with no light named twice and clear of
// the stretches already read. The most lines come first, so a look that deals its lights out over
// several lines or writes its spare ones as none is read whole rather than as its first line alone
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
    // What follows the length, as the page holds it. The board's own is held as nothing, so
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
  // A file listing what was taken off says the rest are as the board fits them by default
  if (notFittedRead) {
    runs.forEach(function (run) {
      if (!run.strip || lengths[run.name]) return;
      var strip = stripDescribed(run);
      stripSet(run, {there: strip.fitted && !saidNotFitted(strip.tab)});
    });
  }
  var stripsRead = {};
  var broken = outputsBrokenOut(bodies);
  var said = wiringRead && orderSaid(wiringRead);

  bodies.forEach(function (body) {
    apply(body);
    // Check if the page said the wiring. Otherwise the lines imply it, or it is number order
    if (said) {
      setLayout(wiring.map(function (one, out) {
        return {broken: said.some(function (place) {
          return place.out === out && place.channel !== null;
        })};
      }), said.map(function (place) { return {out: place.out, channel: place.channel}; }));
    } else {
      wireAsRead(broken);
      var implied = !Object.keys(broken).length && orderImplied(bodies);
      if (implied) setLayout(wiring, implied);
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

addStep(bodyParts, BODY_ORDER, "readback", {
  capture: function (body) {
    body.kept = copyKept(keptNow);
    body.notes = JSON.parse(JSON.stringify(notesNow));
  },
  apply: function (body) {
    setKept(copyKept(body.kept));
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

// The strip or screen port a board token sets, such as screena for screena=2.8, or null
function heldOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  var held = STRIPS.map(function (strip) { return strip.name; })
    .concat(SCREEN_PORTS.map(function (port) { return port.id; }));
  return held.indexOf(name) >= 0 ? name : null;
}

// The board line's tokens this page does not hold, after its own
addStep(boardLineSteps.after, BOARD_LINE_AFTER, "readback", function (line) {
  // Leave out a kept token for a strip or screen whose setting the page writes itself, since the
  // later token would be the one the board takes
  var lower = (line || "").toLowerCase();
  var kept = boardResidue.filter(function (token) {
    var name = heldOfToken(token);
    return !name || !new RegExp("\\b" + name + "=").test(lower);
  });
  if (kept.length) line = (line || "board:") + " " + kept.join(" ");
  return line;
});

// Under the header, the wiring where it is not number order and what has been taken off, then the
// comments above the board line
fileHead.under.push(function () {
  var wired = wiringLine();
  return wired ? [wired] : [];
});
fileHead.under.push(function () {
  var off = notFittedLine();
  return off ? [off] : [];
});
fileHead.above.push(function () { return boardComments; });

// ---- showing them -----------------------------------------------------------------------------

function renderKept() {
  var box = document.getElementById("keptLines");
  if (!box) {
    box = h("div", {id: "keptLines", className: "keptlines"});
    // Above the file's own box, so the lines show while the file is folded
    var preview = document.getElementById("preview");
    (preview.closest("details") || preview).before(box);
  }
  var shown = keptNow.filter(function (one) { return one.text !== null; });
  box.hidden = !shown.length;
  if (!shown.length) {
    replace(box);
    return;
  }
  replace(box,
          h("div", {className: "keptsay"},
            "Lines " + (state.scenes.length ? "in this scene" : "in the file") +
            " the picker cannot edit:"),
          keptNow.map(function (one, at) {
            if (one.text === null) return null;
            return h("div", {className: "keptrow"}, h("code", {}, one.text),
                     h("button", {
                       className: "keptdrop", title: "Remove this line from the file",
                       onclick: function () {
                         keptNow.splice(at, 1);
                         draw();
                       }
                     }, "\u00d7"));
          }));
}

// Mark the lights a kept line plays as taken, on the run and on a strip's bar
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
            cell.title = "used by a line the picker cannot edit: " + named[lamp][0].text;
            return;
          }
        }
      });
      return;
    }
    var box = document.getElementById(run === outs ? "outBar" : "monoBar");
    if (!box) return;
    box.querySelectorAll(".cardlamp").forEach(function (lamp, at) {
      if (!named[at]) return;
      lamp.classList.add("keptlamp");
      lamp.title = "used by a line the picker cannot edit: " + named[at][0].text;
    });
  });
}

addStep(drawSteps.after, DRAW_AFTER, "readback", function () {
  renderKept();
  markKeptLights();
});

// ---- when the drive is opened -----------------------------------------------------------------

// A file this page wrote opens straight in. Any other asks first, saying what would be kept
addStep(connectSteps, CONNECT_ORDER, "readback", async function () {
  var text = await (await drive.fileHandle.getFile()).text();
  if (!text.trim()) return;

  var ours = text.indexOf(HEADER) === 0;
  if (!ours) {
    var kept = readEffects(text).slots.reduce(function (count, slot) {
      return count + slot.kept.filter(function (one) { return one.text !== null; }).length;
    }, 0);
    var open = confirm("This file was not written by the picker. Open it anyway? " +
                       (kept === 1 ? "One line" : kept + " lines") + " would be kept " +
                       "unchanged. Cancel to start fresh, replacing the file when you save.");
    if (!open) {
      rememberRead(text);
      return;
    }
  }
  absorbFile(text);
  drive.text = currentText();
  rememberRead(text);
});

// Remember the file, read or passed over by choice, as this page's to save over without asking
function rememberRead(text) {
  try { localStorage.setItem(WROTE_KEY, text); } catch (e) {}
}
