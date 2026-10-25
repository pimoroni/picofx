import {drawParts} from "./draw.js";
import {BOARD, rangify} from "./looks.js";

// ---- the board's outputs and their wiring -----------------------------------------------
// A colour output is three PWM channels behind one lamp. Where the board lets an adapter tell
// those three apart, the output is either one colour lamp or three mono ones, and a board is
// a mix. A mono output is one light, always on the mono side.

export var OUTS = BOARD.outputs.length;
export var CHANNELS = ["r", "g", "b"];
export var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

// Each output as the file names it, split into its prefix and number. out3 is out and 3, and
// rgb, which has no number, is rgb alone
export var OUTPUTS = BOARD.outputs.map(function (output) {
  var named = output.name.match(/^([a-z]+)(\d*)$/);
  return {name: output.name, prefix: named[1], number: named[2] ? Number(named[2]) : null,
          mono: output.kind === "mono", breaks: !!output.breaks_out};
});

// Whether the mono side comes first, as on a board whose outputs start with its mono ones. The
// file names the lamps in the same order
export var MONO_FIRST = OUTPUTS.length > 0 && OUTPUTS[0].mono;
document.getElementById("sides").classList.toggle("monofirst", MONO_FIRST);
document.querySelector("#outPanel > summary .says").textContent = BOARD.output_words.panel;

// The colours of the corner cut into a broken-out lamp, which say which channel drives it
export var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

// Every lamp on the page, by the output it belongs to, so pointing at one reaches the
// others without the page being drawn again
export var kinOf = {};

// Empty the lamps by output, which a draw finds afresh
function clearKin() {
  kinOf = {};
}
drawParts.clearKin = clearKin;

// Whether each output is broken out, by place. A colour output is one lamp or three, since the
// adapter brings all three channels out or is not fitted, and a mono output is always broken out.
// Two channels playing the same thing are two lamps in one stretch
export var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: OUTPUTS[n].mono});

// Where each lamp sits in the owner's build, in order. A lamp is placed, not an output, since a
// broken-out output's three channels reach LEDs that can be anywhere in a build
export var order = [];

// Set the wiring and where each lamp sits, which change together
export function setLayout(wired, ordered) {
  wiring = wired;
  order = ordered;
}

// An output's places in the wiring order, which are a mono output's one light, a colour output
// whole, or a colour output broken out as its three channels
export function placesOf(out) {
  if (OUTPUTS[out].mono) return [{out: out, channel: 0}];
  if (!wiring[out].broken) return [{out: out, channel: null}];
  return CHANNELS.map(function (letter, c) { return {out: out, channel: c}; });
}

export function sameLamp(a, b) { return a.out === b.out && a.channel === b.channel; }

export function placeOf(lamp) {
  for (var i = 0; i < order.length; i++) {
    if (sameLamp(order[i], lamp)) return i;
  }
  return -1;
}

export function widthOf(section) { return section.to - section.from + 1; }

// Whether a lamp is a channel of a colour output broken out, which the file names by its channel
export function isChannel(lamp) { return !lamp.colour && !OUTPUTS[lamp.out].mono; }

// What one lamp is called, in the words the file uses
export function selectorFor(lamp) {
  if (lamp.run) return lamp.run.name + (lamp.at + 1);
  var name = OUTPUTS[lamp.out].name;
  return isChannel(lamp) ? name + "." + CHANNELS[lamp.channel] : name;
}

// Whether the output after this one, counting by step, is the next of the same name
export function nextOutput(out, step) {
  var here = OUTPUTS[out], there = OUTPUTS[out + step];
  return !!there && here.number !== null && there.prefix === here.prefix &&
         there.number === here.number + step;
}

// A set of items as the file joins them. An item's prefix carries on to a bare number after it,
// so a numbered item says its prefix only where it differs from the one before, and an output
// with no number always says its name
export function joinedItems(items) {
  var prefix = null;
  return items.map(function (item) {
    var output = OUTPUTS[item.out];
    var said = output.number === null ? output.name + item.rest
             : (output.prefix === prefix ? "" : output.prefix) + item.rest;
    prefix = output.prefix;
    return said;
  }).join(",");
}

// An item naming outputs first to last of one name, with a channel suffix or none
export function rangeItem(first, last, suffix) {
  var from = OUTPUTS[first].number, to = OUTPUTS[last].number;
  return {out: first,
          rest: (from === null ? "" : first === last ? String(from) : from + "-" + to) +
                (suffix ? "." + suffix : "")};
}

// The shortest way to name a set of lamps that the file still reads. Consecutive outputs taken
// whole, and consecutive mono outputs, are a range, and an output's three channels in order
// are named by its `.*`
export function nameThese(lamps) {
  // An output's three channels, in order, starting here
  function allThree(at) {
    return at + 2 < lamps.length && isChannel(lamps[at]) &&
           lamps[at].channel === 0 && lamps[at + 1].channel === 1 &&
           lamps[at + 2].channel === 2 && lamps[at + 1].out === lamps[at].out &&
           lamps[at + 2].out === lamps[at].out;
  }

  var items = [];
  var at = 0;
  while (at < lamps.length) {
    if (!isChannel(lamps[at])) {
      var last = at;
      while (last + 1 < lamps.length && !isChannel(lamps[last + 1]) &&
             lamps[last + 1].colour === lamps[at].colour &&
             lamps[last + 1].out === lamps[last].out + 1 && nextOutput(lamps[last].out, 1)) {
        last++;
      }
      items.push(rangeItem(lamps[at].out, lamps[last].out, null));
      at = last + 1;
    } else if (allThree(at)) {
      var end = at;
      var highest = lamps[at].out;
      while (allThree(end + 3) && lamps[end + 3].out === highest + 1 && nextOutput(highest, 1)) {
        end += 3;
        highest++;
      }
      items.push(rangeItem(lamps[at].out, highest, "*"));
      at = end + 3;
    } else {
      items.push(rangeItem(lamps[at].out, lamps[at].out, CHANNELS[lamps[at].channel]));
      at++;
    }
  }
  return joinedItems(items);
}

// A lamp's label on the page. It is the lamp's number and its channel where it is one, or for an
// output with no number its name or its channel's letter
export function shortName(lamp) {
  if (lamp.run) return String(lamp.at + 1);
  var output = OUTPUTS[lamp.out];
  if (output.number === null) {
    return isChannel(lamp) ? CHANNELS[lamp.channel].toUpperCase() : output.name.toUpperCase();
  }
  return isChannel(lamp) ? output.number + CHANNELS[lamp.channel] : String(output.number);
}

// ---- what the file says ------------------------------------------------------------------

// Some outputs by their place counted from one, as the file names them. Those of one name in a
// row are a set of numbers, and an output with no number is named by its name
export function outputsNamed(places) {
  var items = [];
  var at = 0;
  while (at < places.length) {
    var output = OUTPUTS[places[at] - 1];
    var last = at;
    while (output.number !== null && last + 1 < places.length &&
           OUTPUTS[places[last + 1] - 1].number !== null &&
           OUTPUTS[places[last + 1] - 1].prefix === output.prefix) last++;
    var numbers = places.slice(at, last + 1).map(function (place) {
      return OUTPUTS[place - 1].number;
    });
    items.push({out: places[at] - 1, rest: output.number === null ? "" : rangify(numbers)});
    at = last + 1;
  }
  return joinedItems(items);
}

// An output in words, such as output 3, or the RGB output for one with no number
export function outputSaid(out) {
  var output = OUTPUTS[out];
  return output.number === null ? "the " + output.name.toUpperCase() + " output"
                                : "output " + output.number;
}

// The board's colour outputs in words, as one where there is only one
export function colourOutputsSaid() {
  var colour = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono) colour.push(out); });
  return colour.length === 1 ? outputSaid(colour[0]) : "the colour lights";
}

// Move a lamp to sit beside another, before or after it as move.after says
export function placeLamp(move) {
  var moved = order.splice(placeOf(move.from), 1)[0];
  order.splice(placeOf(move.to) + (move.after ? 1 : 0), 0, moved);
}

// A stretch of a strip is a range of its lights, and the whole of it is the bare name
export function stripSelector(run, section) {
  if (section.from === 0 && section.to === run.lamps.length - 1) return run.name;
  return run.name + (section.from === section.to
    ? String(section.from + 1)
    : (section.from + 1) + "-" + (section.to + 1));
}

// Every lamp in number order, an output broken out as its red, green and blue
export function plainOrder() {
  var plain = [];
  wiring.forEach(function (one, out) { plain = plain.concat(placesOf(out)); });
  return plain;
}
