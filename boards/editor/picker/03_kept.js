import {entryParts, lampsNamed} from "./03_reading.js";

// ---- lines kept from the file -------------------------------------------------------------------
// What the file says that the page does not show, kept as written so a save writes it back.

// The tokens on the board line that this page does not hold itself, kept as written
export var boardResidue = [];

// The kept entries of the scene on show, each its text and the comments written above it
export var keptNow = [];

export function copyKept(kept) {
  return (kept || []).map(function (one) {
    return {text: one.text, comments: one.comments.slice()};
  });
}

// The lights of a run the scene's kept lines name, as places in the run, with the lines naming each
export function keptLights(run) {
  var named = {};
  keptNow.forEach(function (one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    (lamps || []).forEach(function (at) { (named[at] = named[at] || []).push(one); });
  });
  return named;
}
