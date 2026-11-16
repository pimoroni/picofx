import {draw} from "./00_draw.js";
import {FAINTEST, WORDS, atBrightness, hexOf, hexRgb, rgbInk, wordFor} from "./01_colours.js";
import {blinkDuty, blinkSpeed, isBanked, lookLines, lookNamed, withSection} from "./01_looks.js";
import {blinkList, blinkWord} from "./02_blink.js";
import {
  CHANNELS, CHANNEL_WORDS, OUTPUTS, colourOutputsSaid, isChannel, joinedItems, nameThese,
  nextOutput, outputSaid, outputsNamed, rangeItem, stripSelector, widthOf
} from "./03_outputs.js";
import {SOLID_COLOUR} from "./05_strips.js";
import {renderPreview} from "./18_file_preview.js";

// ---- what a stretch's lines say -----------------------------------------------------------------
// The effect lines a stretch writes for its look, the colours and the way it runs, and the words
// that head its settings.

// What a stretch plays on, as though it ran from its near end
export function forwardTargetFor(run, section) {
  if (run.strip) {
    // The stretch's lights by number, for the looks that deal them out themselves
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
  // What a stretch plays on, in build order, which a look sharing its lamps out between
  // sets of its own, as Party does, deals from. A colour stretch's are its outputs, and a mono
  // stretch's are its lamps, which are channels, so it names each set itself
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

// A stretch below full brightness says so before the colon of each line it writes, as
// level=, which scales whatever the effect plays. A line playing nothing is left alone
function levelled(lines, level) {
  if (level === undefined || level >= 1) return lines;
  var said = " level=" + Math.round(level * 100) + "%";
  return lines.map(function (line) {
    var at = line.indexOf(":");
    if (at < 0 || /:\s*none\s*$/.test(line)) return line;
    return line.slice(0, at) + said + line.slice(at);
  });
}

// Looks whose colour setting steps through sets of several colours, not one. Party plays
// three at once, and its setting picks which three. They keep their setting and their own
// colours, since one chosen colour in all three places would no longer be Party
var SET_LOOKS = ["Party"];

// Base effects written in one fixed colour, which take a colour beside their own settings
var FIXED_COLOUR_LOOKS = ["Wave", "Blink", "Marquee", "Scanner", "Chase"];

// Whether a look is given its colour here. Solid takes one already, the looks whose second
// slider steps a table of tones take one instead of that slider, and the fixed colour
// ones take one as well
export function takesColour(look) {
  if (!look || SET_LOOKS.indexOf(look.name) >= 0) return false;
  return look.solid || look.mood === "Colour" || FIXED_COLOUR_LOOKS.indexOf(look.name) >= 0;
}

// Each colour a stretch's lines name, in the order they name them, once each. A blink through
// several colours names them all
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

// ---- the colour a look starts with -------------------------------------------------------------
// A look given a stretch starts in its own colour, the one its tone setting gives at the
// stretch's setting, and not whatever colour the stretch was left holding. Solid has no tone
// setting, so it starts in SOLID_COLOUR
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

// The lamps a signal is built from, which a strip's stretch is cut into blocks of
var SIGNAL_LAMPS = {"Traffic light": 3, "Pelican crossing": 5};

// The lines a look writes, a banked look on a run or a strip dealing its banks out along it
function bankedLines(look, target, pace, mood, colour) {
  if (!(target.kind === "run" || target.strip) || !isBanked(look) || target.count === 1)
    return lookLines(look, target, pace, mood, colour);
  return stripLines(look, target, pace, mood);
}

// On a strip, Emergency deals out the stretch's lights as it does outputs. A signal takes a
// set number of lamps, five for a crossing and three for a traffic light, so the stretch is
// cut into that many blocks, the longer ones first, and one entry is written per place
// within a block. Its lights, one from each block, take the signal's parts in order, and a
// block too short for a place drops off the end
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

// A card carries a painter's palette where its look takes a colour, and the stretch being
// worked on can be given one
export function paletteMark() {
  var palette = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  palette.setAttribute("viewBox", "0 0 16 16");
  palette.setAttribute("class", "tint palette");
  palette.innerHTML =
    "<path fill='currentColor' d='M8 1.2a6.8 6.8 0 0 0 0 13.6c1.1 0 1.7-.6 1.7-1.4 " +
    "0-.9-.7-1.1-.7-1.9 0-.8.6-1.3 1.4-1.3h1.8a3 3 0 0 0 3-3C15.2 3.8 12 1.2 8 1.2Z'/>" +
    [[4.6, 8], [5.6, 4.6], [9, 3.6], [12, 5.6]].map(function (at) {
      return "<circle cx='" + at[0] + "' cy='" + at[1] + "' r='1.2' fill='var(--panel)'/>";
    }).join("");
  return palette;
}

export function startColour(run, section, look) {
  if (!takesColour(look)) return;
  var own = look.solid ? SOLID_COLOUR : ownColour(look, run, section);
  if (own) {
    section.colour = own;
    section.custom = false;
  }
}

// Whether this stretch is given a custom colour here, so its brightness goes into the hex
function coloursItself(run, section, look) {
  var first = run.lamps[section.from];
  var custom = section.custom || !wordFor(section.colour || "#ffffff");
  return takesColour(look) && !!first && first.colour && custom;
}

// What one stretch writes, at its brightness and with its typed values. A blink through several
// colours is written as its list, and a custom colour carries its brightness in its hex
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

export function brightnessSlider(tuning, run, where) {
  var section = run.sections[run.picked];
  var ahead = tuning.firstChild;
  var label = document.createElement("label");
  label.textContent = "Brightness";
  tuning.insertBefore(label, ahead);
  var range = document.createElement("input");
  range.type = "range";
  range.min = FAINTEST;
  range.max = 1;
  range.step = 0.01;
  range.value = section.level === undefined ? 1 : section.level;
  range.dataset.focus = where + "-level";
  range.oninput = function () {
    run.sections[run.picked].level = Number(range.value);
    renderPreview();
  };
  // A colour's hex and its preview show the brightness, so they are drawn again once it is set
  range.onchange = function () { draw(); };
  tuning.insertBefore(range, ahead);
}

// The lines a look writes for a target, as the board will play them
export function linesFor(look, target, pace, mood, colour) {
  var lines;
  if (look && look.solid) {
    // Solid is written at full, since its brightness is the stretch's own
    lines = bankedLines(look, target, pace, 1, colour).map(function (line) {
      return line.replace(/ brightness=1(?=\s|$)/, "");
    });
  } else {
    lines = bankedLines(look, target, pace, mood, colour);
  }

  // The colour it was given. Solid already writes it. The looks whose slider steps tones
  // write a tone, so the colour they wrote is replaced with the chosen one, as a word where it
  // is a swatch and as hex from the field
  if (takesColour(look) && target.colour && colour) {
    var said = wordFor(colour) || colour.replace("#", "").toLowerCase();
    lines = lines.map(function (line) { return line.replace(/colour=[^\s:]+/, "colour=" + said); });
  }

  // A wave is written with its speed below zero, so it goes forward as every look does
  lines = lines.map(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    if (WAVES.indexOf(effect) < 0) return line;
    return line.replace(/ speed=(\d)/, " speed=-$1");
  });

  // The values typed for the stretch whose lines are being written
  if (!exactNow) return lines;
  Object.keys(exactNow).forEach(function (slider) {
    var typed = exactNow[slider];
    if (!typed) return;
    // A trail is the fall of a split fade, so a typed one replaces the part after its bar
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

// ---- which way a stretch runs --------------------------------------------------------------
// A stretch can start from its far end, which writes its lamps counting down. Only a look
// that differs from lamp to lamp can show it, so for the rest the toggle is greyed and the
// stretch is written as it runs

// The effects that give each lamp of an entry its place, and a length= does the same
var TRAVELLING = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence", "sweep",
                  "binary_counter", "pelican_crossing", "traffic_light", "clock"];

// picofx's wave effects move their pattern toward the start of the lights they are given as
// time runs, where a sweep, a counter and the signals begin at the start and go on from it.
// So that a stretch goes forward the same way whatever its look, the waves are written
// with their speed below zero, which the manual allows, and Reverse counts the lights down
var WAVES = ["rainbow_wave", "pulse_wave", "blink_wave", "flash_sequence"];

// Whether reversing this stretch would change what it plays, judged from its lines as written
export function runsAWay(look, target, section) {
  if (!look || target.count < 2) return false;
  var lines = linesFor(look, target, section.pace, section.mood, section.colour);
  // A look that deals the stretch out, as Party and Emergency do, deals from the start
  if (lines.length > 1) return true;
  return lines.some(function (line) {
    var effect = (line.split(":")[1] || "").trim().split(/\s+/)[0];
    return TRAVELLING.indexOf(effect) >= 0 || / length=/.test(line);
  });
}

// How many whole outputs from here run counting down with their channels blue, green, red,
// which a descending range with .* writes as one item
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

// Outputs named from the far end, a run counting down written as one range
function nameBackwards(lamps) {
  var items = [];
  var at = 0;
  while (at < lamps.length) {
    // Two or more whole mono outputs counting down, since one alone as .* would run r, g, b
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

// What a stretch plays on, counting its lights down where it starts from its far end and its
// look shows which way it runs
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

// ---- what heads a stretch's settings ------------------------------------------------------------
// The look's name, since the panel is its settings, then where it plays in words, such as
// outputs 1 to 7, LEDs 11 to 20 of the left strip or output 3's red and green. The file's
// selector is the file view's to show, and whether the lights are colour or mono the tab's

// A list said as English does, such as "one, two and three"
export function spoken(items) {
  if (items.length < 2) return items.join("");
  return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
}

// Numbers as English says them. Three or more climbing or falling by one are "a to b", and the
// rest are listed, so 1-7 is "1 to 7" and 5,6 is "5 and 6"
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

// A reversed stretch is said in the order it plays, from its far end, as the file writes it
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
  // Whole outputs and mono ones by number, an output with no number by name, and a broken-out
  // output's channels together, each group in the order they play
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

// The typed values of the stretch whose lines are being written, which linesFor applies
var exactNow = null;

// Write a stretch's lines with its typed values, as both the file and the preview ask for them
export function withExact(exact, write) {
  var had = exactNow;
  exactNow = exact || null;
  try {
    return write();
  } finally {
    exactNow = had;
  }
}
