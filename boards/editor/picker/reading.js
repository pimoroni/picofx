import {CHANNELS, OUTPUTS} from "./outputs.js";

// ---- reading an entry ---------------------------------------------------------------------------
// An entry of the file taken apart: its lights, its effect and settings, and the board line's
// tokens. What the page does with them is the read-back part's.

// Where a quote does not hide it, the first colon, which divides an entry's lights from its effect
export function unquotedColon(line) {
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

// The arguments an args= gives, divided at pipes a quote does not hold, their quotes taken off
export function argsRead(value) {
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

// ---- the parts' own lines out of the kept lines -----------------------------------------------
// Each kept line is tried as a setting of the part it names, and read only where that part's own
// writer then gives back exactly the line. So a setting read wrongly leaves the line kept, never
// changed. A read line's comments are written above it again while it says the same

// An entry's lights and their settings before the colon, and its effect and settings after it
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

// ---- the lights -------------------------------------------------------------------------------
// A line, or the lines a look writes together, is read as a stretch where some look, its sliders
// solved back from the line, writes exactly those lines again for exactly those lights. The
// sliders are solved as the figures drawer solves a typed figure, and a value past a slider's
// end is kept exactly as the line gives it

// The lamps of a run a line's selector names, in the order it names them, or null
export function lampsNamed(run, selector) {
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
export function itemsNamed(selector) {
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
export function placesNamed(selector) {
  var items = itemsNamed(selector);
  if (items.some(function (places) { return !places; })) return null;
  return [].concat.apply([], items);
}

// The ends of a set of lamps with no gap, whichever way it was named, or null where it has one
export function spanOf(lamps) {
  var sorted = lamps.slice().sort(function (a, b) { return a - b; });
  for (var i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return null;
  }
  return {from: sorted[0], to: sorted[sorted.length - 1]};
}
