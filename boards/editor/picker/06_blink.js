import {wordFor} from "./05_effects.js";

// ---- blinking through several colours -----------------------------------------------------
// Blink takes one colour or several. With several it blinks through them in turn, one a beat,
// which is picofx's rgb_blink. The list is the stretch's blinks, {colours, at}, at being the
// one the picker above is changing; a stretch with no list has the one colour it always had.
// A list is written with the words and hexes at full and the stretch's brightness as level=,
// rgb_blink taking one level for all of them.

export var BLINK = "Blink";

// The colours a stretch blinks through, where it has more than one and plays them in colour
export function blinkList(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look !== BLINK || !section.blinks || section.blinks.colours.length < 2 ||
      !first || !first.colour) return null;
  return section.blinks.colours;
}

// A colour's word, black included, which a set of colours to blink through may hold
export function blinkNamed(hex) {
  return hex.replace("#", "").toLowerCase() === "000000" ? "black" : wordFor(hex);
}

export function blinkWord(hex) {
  return blinkNamed(hex) || hex.replace("#", "").toLowerCase();
}

