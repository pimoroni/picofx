import {SWATCHES, wordFor} from "./01_colours.js";

export var BLINK = "Blink";

export function blinkList(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look !== BLINK || !section.blinks || section.blinks.colours.length < 2 ||
      !first || !first.colour) return null;
  return section.blinks.colours;
}

export function blinkNamed(hex) {
  return hex.replace("#", "").toLowerCase() === "000000" ? "black" : wordFor(hex);
}

export function blinkWord(hex) {
  return blinkNamed(hex) || hex.replace("#", "").toLowerCase();
}

export function swatchesFor(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look === BLINK && section.blinks && section.blinks.colours.length > 1 &&
      first && first.colour) return ["black"].concat(SWATCHES);
  return SWATCHES;
}
