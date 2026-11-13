import {BOARD} from "./01_looks.js";
import {Run, runs, settle} from "./03_runs.js";

export var STRIPS = BOARD.strips.map(function (strip) {
  var brightness = strip.brightness === undefined ? null : strip.brightness;
  return {id: strip.name, name: strip.name, label: strip.label, leds: strip.leds, order: "",
          there: strip.fitted, brightness: brightness, made: brightness,
          connector: strip.connector, takes: strip.takes || []};
});

function stripRun(one) {
  var run = Run(one.name, false);
  run.strip = true;
  run.id = one.id;
  run.label = one.label;
  run.leds = one.leds;
  run.order = one.order;
  run.there = one.there;
  run.brightness = one.brightness;
  run.made = one.made;
  run.connector = one.connector;
  run.takes = one.takes;
  return run;
}

export function stripNamed(name) {
  var lower = name.toLowerCase();
  return runs.filter(function (run) { return run.strip && run.name === lower; })[0] || null;
}

export function stripSet(run, values) {
  var one = STRIPS.filter(function (strip) { return strip.id === run.id; })[0];
  Object.keys(values).forEach(function (key) {
    one[key] = values[key];
    run[key] = values[key];
  });
}

export var STRIP_FEWEST = 1;
export var STRIP_MOST = 300;

export var STRIP_ORDERS = [["", "GRB (most strips)"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

export var STRIP_BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

export function stripPercent(brightness) { return Math.round(brightness * 100) + "%"; }

export function stripChipShown(run) {
  return run.made === null ? (run.order || "grb").toUpperCase()
                           : stripPercent(run.brightness) + " brightness";
}

export function stripLengthTail(run) {
  if (run.made === null) return run.order ? "|" + run.order : "";
  return run.brightness === run.made ? "" : "|" + stripPercent(run.brightness);
}

export function readStripTail(run, tail) {
  if (run.made === null) {
    var order = tail.toLowerCase();
    if (order === "grb") order = "";
    var offered = STRIP_ORDERS.some(function (pair) { return pair[0] === order; });
    return offered ? {order: order} : null;
  }
  if (!tail) return {brightness: run.made};
  var percent = tail.match(/^(\d+(?:\.\d+)?)%$/);
  var brightness = percent ? Number(percent[1]) / 100 : Number(tail);
  return brightness >= 0 && brightness <= 1 ? {brightness: brightness} : null;
}

runs.push.apply(runs, STRIPS.map(stripRun));
settle();

