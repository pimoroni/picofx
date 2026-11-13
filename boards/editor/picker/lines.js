import {blinkList, blinkWord} from "./blink.js";
import {WORDS, atBrightness, hexOf, hexRgb, rgbInk, wordFor} from "./colours.js";
import {blinkDuty, blinkSpeed, isBanked, lookLines, lookNamed, withSection} from "./looks.js";
import {
  CHANNELS, CHANNEL_WORDS, OUTPUTS, colourOutputsSaid, isChannel, joinedItems, nameThese,
  nextOutput, outputSaid, outputsNamed, rangeItem, stripSelector, widthOf
} from "./outputs.js";

var SET_LOOKS = ["Party"];

var FIXED_COLOUR_LOOKS = ["Wave", "Blink", "Marquee", "Scanner", "Chase"];

export function takesColour(look) {
  if (!look || SET_LOOKS.indexOf(look.name) >= 0) return false;
  return look.solid || look.mood === "Colour" || FIXED_COLOUR_LOOKS.indexOf(look.name) >= 0;
}

export function coloursWritten(look, section, run) {
  var colours = blinkList(run, section);
  if (colours) return colours.map(function (hex) { return rgbInk(hexRgb(hex)); });
  var target = targetFor(run, section);
  var found = [];
  linesFor(look, target, section.pace, section.mood, section.colour).forEach(function (line) {
    var said = line.match(/colour=([^\s:]+)/);
    if (!said) return;
    var value = said[1].toLowerCase();
    var ink = WORDS[value] ? rgbInk(WORDS[value])
            : /^[0-9a-f]{6}$/.test(value) ? "#" + value : null;
    if (ink && found.indexOf(ink) < 0) found.push(ink);
  });
  return found;
}

export function ownColourFor(look, target, pace, mood, colour) {
  var lines = target.count === 1 && look.alone
    ? look.alone(target, pace, mood, colour)
    : look.entries(target, pace, mood, colour);
  var said = (lines[0] || "").match(/colour=([^\s:]+)/);
  if (!said) return null;
  var value = said[1].toLowerCase();
  return WORDS[value] ? "#" + hexOf(WORDS[value]) : /^[0-9a-f]{6}$/.test(value) ? "#" + value : null;
}

function ownColour(look, run, section) {
  return ownColourFor(look, targetFor(run, section), section.pace, section.mood,
                      section.colour);
}

export var START_MOODS = {"Solid": 1, "Colour cycle": 1, "Colour steps": 1 / 3,
                   "Pelican crossing": 0.1, "Traffic light": 0.1, "Marquee": 0.25};

export var SOLID_COLOUR = "#" + hexOf(WORDS.yellow);

var SIGNAL_LAMPS = {"Traffic light": 3, "Pelican crossing": 5};

function bankedLines(look, target, pace, mood, colour) {
  if (!(target.kind === "run" || target.strip) || !isBanked(look) || target.count === 1)
    return lookLines(look, target, pace, mood, colour);
  return stripLines(look, target, pace, mood);
}

function stripLines(look, target, pace, mood) {
  function dealt(playing) {
    return Object.assign({}, target, {kind: "outputs", playing: playing});
  }
  var parts = SIGNAL_LAMPS[look.name];
  if (!parts) return look.entries(dealt(target.lights), pace, mood);
  var blocks = [];
  var from = 0;
  for (var part = 0; part < parts; part++) {
    var size = Math.floor(target.lights.length / parts) +
               (part < target.lights.length % parts ? 1 : 0);
    if (size) blocks.push(target.lights.slice(from, from + size));
    from += size;
  }
  var lines = [];
  for (var place = 0; place < blocks[0].length; place++) {
    var lights = blocks.filter(function (block) { return place < block.length; })
                       .map(function (block) { return block[place]; });
    lines.push(look.entries(dealt(lights), pace, mood)[0]);
  }
  return lines;
}

export function startColour(run, section, look) {
  if (!takesColour(look)) return;
  var own = look.solid ? SOLID_COLOUR : ownColour(look, run, section);
  if (own) {
    section.colour = own;
    section.custom = false;
  }
}

function coloursItself(run, section, look) {
  var first = run.lamps[section.from];
  var custom = section.custom || !wordFor(section.colour || "#ffffff");
  return takesColour(look) && !!first && first.colour && custom;
}

export function sectionLines(run, section, look) {
  return withExact(section.exact, function () {
    var colours = blinkList(run, section);
    if (colours) {
      var line = targetFor(run, section).selector + ": rgb_blink colour=" +
                 colours.map(blinkWord).join("|") + " speed=" + blinkSpeed(section.pace) +
                 " duty=" + blinkDuty(section.mood);
      return levelled([line], section.level);
    }
    if (coloursItself(run, section, look) && section.level < 1) {
      return linesFor(look, targetFor(run, section), section.pace, section.mood,
                      atBrightness(section.colour || "#ffffff", section.level));
    }
    return withSection(section, function () {
      return levelled(linesFor(look, targetFor(run, section), section.pace, section.mood,
                               section.colour), section.level);
    });
  });
}

export function linesFor(look, target, pace, mood, colour) {
  var lines;
  if (look && look.solid) {
    lines = bankedLines(look, target, pace, 1, colour).map(function (line) {
      return line.replace(/ brightness=1(?=\s|$)/, "");
    });
  } else {
    lines = bankedLines(look, target, pace, mood, colour);
  }

  if (takesColour(look) && target.colour && colour) {
    var said = wordFor(colour) || colour.replace("#", "").toLowerCase();
    lines = lines.map(function (line) { return line.replace(/colour=[^\s:]+/, "colour=" + said); });
  }

  lines = lines.map(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    if (WAVES.indexOf(effect) < 0) return line;
    return line.replace(/ speed=(\d)/, " speed=-$1");
  });

  if (!exactNow) return lines;
  Object.keys(exactNow).forEach(function (slider) {
    var typed = exactNow[slider];
    if (!typed) return;
    if (typed.key === "fade") {
      lines = lines.map(function (line) {
        return line.replace(/(\sfade=[\d.]+\|)[\d.]+/, "$1" + typed.value);
      });
      return;
    }
    var setting = new RegExp("(^|\\s)" + typed.key + "=(-?)[\\d.]+");
    lines = lines.map(function (line) {
      return line.replace(setting, function (all, space, sign) {
        return space + typed.key + "=" + sign + typed.value;
      });
    });
  });
  return lines;
}

var TRAVELLING = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence", "sweep",
                  "binary_counter", "pelican_crossing", "traffic_light", "clock"];

var WAVES = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence"];

export function runsAWay(look, target, section) {
  if (!look || target.count < 2) return false;
  var lines = linesFor(look, target, section.pace, section.mood, section.colour);
  if (lines.length > 1) return true;
  return lines.some(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    return TRAVELLING.indexOf(effect) >= 0 || / length=/.test(line);
  });
}

function wholeOutputsDown(lamps, at) {
  var count = 0;
  while (at + 3 * count + 2 < lamps.length) {
    var three = lamps.slice(at + 3 * count, at + 3 * count + 3);
    var out = lamps[at].out - count;
    var whole = three.every(function (lamp, i) {
      return isChannel(lamp) && lamp.out === out && lamp.channel === 2 - i;
    });
    if (!whole || (count && !nextOutput(out + 1, -1))) break;
    count++;
  }
  return count;
}

function nameBackwards(lamps) {
  var items = [];
  var at = 0;
  while (at < lamps.length) {
    var outputs = wholeOutputsDown(lamps, at);
    if (outputs >= 2) {
      items.push(rangeItem(lamps[at].out, lamps[at].out - outputs + 1, "*"));
      at += 3 * outputs;
      continue;
    }
    var last = at;
    while (!isChannel(lamps[at]) && last + 1 < lamps.length && !isChannel(lamps[last + 1]) &&
           lamps[last + 1].colour === lamps[at].colour &&
           lamps[last + 1].out === lamps[last].out - 1 && nextOutput(lamps[last].out, -1)) last++;
    items.push(rangeItem(lamps[at].out, lamps[last].out,
                         isChannel(lamps[at]) ? CHANNELS[lamps[at].channel] : null));
    at = last + 1;
  }
  return joinedItems(items);
}

export function targetFor(run, section) {
  var target = forwardTargetFor(run, section);
  if (!section.reversed || !runsAWay(lookNamed(section.look), target, section)) return target;
  if (run.strip) {
    var whole = section.from === 0 && section.to === run.lamps.length - 1;
    return Object.assign(target, {
      selector: run.name + (whole ? run.lamps.length + "-1"
                                  : (section.to + 1) + "-" + (section.from + 1)),
      lights: target.lights.slice().reverse(), reversed: true});
  }
  var mine = run.lamps.slice(section.from, section.to + 1).reverse();
  target.selector = nameBackwards(mine);
  target.reversed = true;
  if (target.colour) {
    target.playing = mine.map(function (lamp) { return lamp.out + 1; });
  } else {
    target.nameSet = function (set) {
      return nameBackwards(set.map(function (at) { return mine[at]; }));
    };
  }
  return target;
}

export function spoken(items) {
  if (items.length < 2) return items.join("");
  return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
}

function numbersSaid(numbers) {
  var said = [];
  var at = 0;
  while (at < numbers.length) {
    var last = at;
    var step = numbers[at + 1] - numbers[at];
    if (step === 1 || step === -1) {
      while (last + 1 < numbers.length && numbers[last + 1] - numbers[last] === step) last++;
    }
    if (last - at >= 2) {
      said.push(numbers[at] + " to " + numbers[last]);
    } else {
      said = said.concat(numbers.slice(at, last + 1).map(String));
    }
    at = last + 1;
  }
  return spoken(said);
}

export function wherePlays(run, section, reversed) {
  var lamps = run.lamps.slice(section.from, section.to + 1);
  if (reversed) lamps.reverse();
  if (run.strip) {
    var from = section.from + 1, to = section.to + 1;
    if (reversed) {
      var swap = from;
      from = to;
      to = swap;
    }
    return (from === to ? "LED " + from : "LEDs " + from + " to " + to) + " of " + run.label;
  }
  var groups = [];
  lamps.forEach(function (lamp) {
    var last = groups[groups.length - 1];
    var numbered = !isChannel(lamp) && OUTPUTS[lamp.out].number !== null;
    if (numbered && last && last.numbers) last.numbers.push(OUTPUTS[lamp.out].number);
    else if (numbered) groups.push({numbers: [OUTPUTS[lamp.out].number]});
    else if (!isChannel(lamp)) groups.push({said: outputSaid(lamp.out)});
    else if (last && last.out === lamp.out) last.channels.push(lamp.channel);
    else groups.push({out: lamp.out, channels: [lamp.channel]});
  });
  return spoken(groups.map(function (group) {
    if (group.numbers) {
      return (group.numbers.length === 1 ? "output " : "outputs ") + numbersSaid(group.numbers);
    }
    if (group.said) return group.said;
    var output = OUTPUTS[group.out];
    var whose = output.number === null ? "the " + output.name.toUpperCase()
                                       : "output " + output.number;
    return whose + "'s " + spoken(group.channels.map(function (channel) {
      return CHANNEL_WORDS[CHANNELS[channel]];
    }));
  }));
}

export function forwardTargetFor(run, section) {
  if (run.strip) {
    var lights = [];
    for (var at = section.from; at <= section.to; at++) lights.push(at + 1);
    return {kind: "run", id: run.id, name: run.name, label: run.label, colour: true,
            selector: stripSelector(run, section), count: widthOf(section), playing: [],
            lights: lights};
  }
  var first = run.lamps[section.from];
  if (!first) return {kind: "outputs", colour: false, selector: "out1", count: 1,
                      label: "nothing", playing: []};
  var mine = [];
  for (var i = section.from; i <= section.to; i++) mine.push(run.lamps[i]);
  var target = {kind: first.colour && widthOf(section) === 1 ? "single" : "outputs",
                name: "out", colour: first.colour, selector: nameThese(mine),
                count: widthOf(section), playing: [],
                label: first.colour ? colourOutputsSaid() : "the mono lights"};
  if (first.colour) {
    target.playing = mine.map(function (lamp) { return lamp.out + 1; });
    target.nameSet = outputsNamed;
  } else {
    target.playing = mine.map(function (lamp, at) { return at; });
    target.nameSet = function (set) {
      return nameThese(set.map(function (at) { return mine[at]; }));
    };
  }
  return target;
}

function levelled(lines, level) {
  if (level === undefined || level >= 1) return lines;
  var said = " level=" + Math.round(level * 100) + "%";
  return lines.map(function (line) {
    var at = line.indexOf(":");
    if (at < 0 || /:\s*none\s*$/.test(line)) return line;
    return line.slice(0, at) + said + line.slice(at);
  });
}

var exactNow = null;

export function withExact(exact, write) {
  var had = exactNow;
  exactNow = exact || null;
  try {
    return write();
  } finally {
    exactNow = had;
  }
}
