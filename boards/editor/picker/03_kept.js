import {entryParts, lampsNamed} from "./03_reading.js";

export var boardResidue = [];

export function setResidue(tokens) {
  boardResidue = tokens;
}

export function filterResidue(keep) {
  boardResidue = boardResidue.filter(keep);
}

export var keptNow = [];

export function setKept(lines) {
  keptNow = lines;
}

export function filterKept(keep) {
  keptNow = keptNow.filter(keep);
}

export function copyKept(kept) {
  return (kept || []).map(function (one) {
    return {text: one.text, comments: one.comments.slice()};
  });
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
