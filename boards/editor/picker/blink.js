import {SWATCHES, wordFor} from "./colours.js";

// ---- blinking through several colours -----------------------------------------------------
// Blink takes one colour or several. With several it blinks through them in turn, one a beat,
// which is picofx's rgb_blink. The list is the stretch's blinks, {colours, at}, where `at` is the
// one the colour picker is changing. A list is written with the words and hexes at full and the
// stretch's brightness as level=, since rgb_blink takes one level for all of them.

// The swatches a stretch offers. A blink through several colours offers black too, as a turn
// with the light off
export function swatchesFor(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look === BLINK && section.blinks && section.blinks.colours.length > 1 &&
      first && first.colour) return ["black"].concat(SWATCHES);
  return SWATCHES;
}

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
