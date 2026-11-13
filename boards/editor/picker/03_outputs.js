import {BOARD, rangify} from "./01_looks.js";

var OUTS = BOARD.outputs.length;

export var CHANNELS = ["r", "g", "b"];

export var CHANNEL_WORDS = {r: "red", g: "green", b: "blue"};

export var OUTPUTS = BOARD.outputs.map(function (output) {
  var named = output.name.match(/^([a-z]+)(\d*)$/);
  return {name: output.name, prefix: named[1], number: named[2] ? Number(named[2]) : null,
          mono: output.kind === "mono", breaks: !!output.breaks_out};
});

export var MONO_FIRST = OUTPUTS.length > 0 && OUTPUTS[0].mono;

export var CHANNEL_INKS = ["#d63a2a", "#23a55a", "#2f76d9"];

export var wiring = [];
for (var n = 0; n < OUTS; n++) wiring.push({broken: OUTPUTS[n].mono});

export var order = [];

for (var m = 0; m < OUTS; m++) order = order.concat(placesOf(m));

export function setLayout(wired, ordered) {
  wiring = wired;
  order = ordered;
}

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

export function isChannel(lamp) { return !lamp.colour && !OUTPUTS[lamp.out].mono; }

export function selectorFor(lamp) {
  if (lamp.run) return lamp.run.name + (lamp.at + 1);
  var name = OUTPUTS[lamp.out].name;
  return isChannel(lamp) ? name + "." + CHANNELS[lamp.channel] : name;
}

export function nextOutput(out, step) {
  var here = OUTPUTS[out], there = OUTPUTS[out + step];
  return !!there && here.number !== null && there.prefix === here.prefix &&
         there.number === here.number + step;
}

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

export function rangeItem(first, last, suffix) {
  var from = OUTPUTS[first].number, to = OUTPUTS[last].number;
  return {out: first,
          rest: (from === null ? "" : first === last ? String(from) : from + "-" + to) +
                (suffix ? "." + suffix : "")};
}

export function nameThese(lamps) {
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

export function shortName(lamp) {
  if (lamp.run) return String(lamp.at + 1);
  var output = OUTPUTS[lamp.out];
  if (output.number === null) {
    return isChannel(lamp) ? CHANNELS[lamp.channel].toUpperCase() : output.name.toUpperCase();
  }
  return isChannel(lamp) ? output.number + CHANNELS[lamp.channel] : String(output.number);
}

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

export function outputSaid(out) {
  var output = OUTPUTS[out];
  return output.number === null ? "the " + output.name.toUpperCase() + " output"
                                : "output " + output.number;
}

export function colourOutputsSaid() {
  var colour = [];
  OUTPUTS.forEach(function (output, out) { if (!output.mono) colour.push(out); });
  return colour.length === 1 ? outputSaid(colour[0]) : "the colour lights";
}

export function placeLamp(move) {
  var moved = order.splice(placeOf(move.from), 1)[0];
  order.splice(placeOf(move.to) + (move.after ? 1 : 0), 0, moved);
}

export function stripSelector(run, section) {
  if (section.from === 0 && section.to === run.lamps.length - 1) return run.name;
  return run.name + (section.from === section.to
    ? String(section.from + 1)
    : (section.from + 1) + "-" + (section.to + 1));
}
