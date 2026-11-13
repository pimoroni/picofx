import {h, replace} from "./00_dom.js";
import {draw, drawSteps} from "./00_draw.js";
import {HEADER, LOOKS, SIGNAL_TIMINGS, canPlay, keyOf} from "./01_looks.js";
import {
  CHANNELS, OUTPUTS, blank, joinedItems, mono, order, outs, placesOf, runs, setLayout, settle,
  wiring
} from "./03_runs.js";
import {
  allBodies, apply, blankBody, bodyParts, capture, fileHead, sceneMark, settleLoneScene, state
} from "./04_scenes.js";
import {
  STRIPS, WORDS, hexOf, readStripTail, sectionLines, stripNamed, stripSet, targetFor, wordFor
} from "./05_effects.js";
import {BLINK} from "./06_blink.js";
import {
  NOT_FITTED, SCREEN_PORTS, boardLineSteps, notFittedLine, notFittedRead, saidNotFitted,
  setNotFittedRead, stripDescribed
} from "./07_board.js";
import {dropStrip} from "./08_setup.js";
import {WROTE_KEY, connectSteps, drive} from "./18_drive.js";
import {argsWritten, boardSet, programNamed} from "./19_board_settings.js";
import {onProgramPage, setProgramPage} from "./22_program.js";
import {figureKey, placeFor, settingIn} from "./25_figures.js";
import {programsKnown} from "./26_drive_programs.js";

var PAGE_LINES = HEADER.split("\n").filter(Boolean).concat(["# Nothing is playing yet."]);

export var boardResidue = [];

export function filterResidue(keep) {
  boardResidue = boardResidue.filter(keep);
}
var boardComments = [];

var keptNow = [];

export function filterKept(keep) {
  keptNow = keptNow.filter(keep);
}
var notesNow = {};

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

export function boardTokens(text) {
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

var programWaiting = null;

export function readWaitingProgram() {
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

function absorbFile(text) {
  var parsed = readEffects(text);
  wiringRead = parsed.wiring || null;
  setNotFittedRead(parsed.notFitted || null);

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
  state.at = -1;
  apply(state.always.body);
  runs.filter(function (run) {
    return run.strip && run.there && runs.some(function (other) {
      return other.strip && other.there && run.takes.indexOf(other.name) >= 0;
    });
  }).forEach(dropStrip);
  draw();
}

export function entryParts(text) {
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

export function unquoted(value) {
  return value && /^(["']).*\1$/.test(value) ? value.slice(1, -1) : value;
}

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

function placesNamed(selector) {
  var items = itemsNamed(selector);
  if (items.some(function (places) { return !places; })) return null;
  return [].concat.apply([], items);
}

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

function wireAsRead(broken) {
  setLayout(wiring.map(function (one, out) {
    return {broken: OUTPUTS[out].mono || !!broken[out]};
  }), plainOrder());
}

function plainOrder() {
  var plain = [];
  wiring.forEach(function (one, out) { plain = plain.concat(placesOf(out)); });
  return plain;
}

var WIRED = "# Wired in the order ";

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

function spanOf(lamps) {
  var sorted = lamps.slice().sort(function (a, b) { return a - b; });
  for (var i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return null;
  }
  return {from: sorted[0], to: sorted[sorted.length - 1]};
}

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
  if (parts.right.colour && parts.right.colour.indexOf("|") >= 0) {
    blinks = {colours: parts.right.colour.split("|").map(hexFor), at: 0};
    colour = blinks.colours[0];
    custom = !wordFor(colour);
  }
  var level = parts.left.level ? parseFloat(parts.left.level) / 100 : 1;

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
    if (sameLines(written, texts)) return section;
    if (sameShape(written, texts) && refineSliders(run, section, look, texts)) return section;
  }
  return null;
}

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

function sameShape(written, texts) {
  function shape(line) { return line.replace(/=[^\s:]+/g, "=#"); }
  return written.length === texts.length && written.every(function (line, at) {
    return shape(line) === shape(texts[at]);
  });
}

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

function solveSliders(run, section, look, texts) {
  ["pace", "mood"].forEach(function (slider) {
    var key = figureKey(run, section, look, slider);
    if (!key) return;
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
  var lengths = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(\w+)=(\d+)(?:\|(\S+))?$/i);
    var run = named && stripNamed(named[1]);
    if (!run) return;
    var values = readStripTail(run, named[3] || "");
    if (!values) return;
    values.leds = Number(named[2]);
    values.there = true;
    lengths[run.name] = {token: token, values: values};
  });
  runs.forEach(function (run) {
    if (run.strip && lengths[run.name]) stripSet(run, lengths[run.name].values);
  });
  if (Object.keys(lengths).length) {
    runs.forEach(function (run) {
      if (run.strip && !lengths[run.name]) stripSet(run, {there: false});
    });
  }
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

bodyParts.push({
  capture: function (body) {
    body.kept = copyKept(keptNow);
    body.notes = JSON.parse(JSON.stringify(notesNow));
  },
  apply: function (body) {
    keptNow = copyKept(body.kept);
    notesNow = JSON.parse(JSON.stringify(body.notes || {}));
  },
  blank: function (body) {
    body.kept = [];
    body.notes = {};
  },
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

function stripOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  return STRIPS.some(function (strip) { return strip.name === name; }) ? name : null;
}

function heldOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  var held = STRIPS.map(function (strip) { return strip.name; })
    .concat(SCREEN_PORTS.map(function (port) { return port.id; }));
  return held.indexOf(name) >= 0 ? name : null;
}

boardLineSteps.after.push(function (line) {
  var lower = (line || "").toLowerCase();
  var kept = boardResidue.filter(function (token) {
    var name = heldOfToken(token);
    return !name || !new RegExp("\\b" + name + "=").test(lower);
  });
  if (kept.length) line = (line || "board:") + " " + kept.join(" ");
  return line;
});

fileHead.under.push(function () {
  var wired = wiringLine();
  return wired ? [wired] : [];
});
fileHead.under.push(function () {
  var off = notFittedLine();
  return off ? [off] : [];
});
fileHead.above.push(function () { return boardComments; });

function renderKept() {
  var box = document.getElementById("keptLines");
  if (!box) {
    box = h("section", {id: "keptLines", "aria-label": "Lines kept as written"});
    var preview = document.getElementById("preview");
    var file = preview.closest("details") || preview;
    file.parentNode.insertBefore(box, file);
  }
  var shown = keptNow.filter(function (one) { return one.text !== null; });
  box.hidden = !shown.length;
  if (!shown.length) {
    replace(box);
    return;
  }
  replace(box,
    h("p", {}, "Lines " + (state.scenes.length ? "in this scene" : "in the file") + " the picker cannot edit:"),
    h("ul", {}, keptNow.map(function (one, at) {
      if (one.text === null) return null;
      return h("li", {}, h("code", {}, one.text),
        h("button", {type: "button", title: "Remove this line from the file",
                     onclick: function () {
                       keptNow.splice(at, 1);
                       draw();
                     }}, "\u00d7"));
    })));
}

export function keptLights(run) {
  var named = {};
  keptNow.forEach(function (one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    (lamps || []).forEach(function (at) { (named[at] = named[at] || []).push(one); });
  });
  return named;
}

function markKeptLights() {
  [outs, mono].forEach(function (run) {
    var named = keptLights(run);
    document.querySelectorAll("#" + (run === outs ? "out" : "mono") + "Run li[data-key]").forEach(function (lamp, at) {
      if (!named[at]) return;
      lamp.dataset.kept = "";
      lamp.title = "used by a line the picker cannot edit: " + named[at][0].text;
    });
  });
}

drawSteps.after.push(function () {
  renderKept();
  markKeptLights();
});

export function forgetKeptFor(run) {
  function elsewhere(one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    return !(lamps && lamps.length);
  }
  filterKept(elsewhere);
  allBodies().forEach(function (held) { held.kept = (held.kept || []).filter(elsewhere); });
  filterResidue(function (token) { return stripOfToken(token) !== run.name; });
}

connectSteps.push(async function () {
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
  rememberRead(text);
});

function rememberRead(text) {
  try { localStorage.setItem(WROTE_KEY, text); } catch (e) {}
}
