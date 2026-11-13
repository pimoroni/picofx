import {h} from "./00_dom.js";
import {draw, drawSteps, paintAll} from "./00_draw.js";
import {BOARD, canPlay, keyOf, lookNamed} from "./01_looks.js";
import {wiring} from "./03_outputs.js";
import {
  Run, active, blank, copyBlinks, copyExact, mono, outs, pickOutput, runs, sectionAt, settle
} from "./03_runs.js";
import {startColour, targetFor} from "./04_lines.js";
import {carried} from "./04_scenes.js";
import {renderLeds} from "./08_setup.js";
import {renderStretches} from "./31_stretch_bar.js";
import {renderEditor} from "./32_stretch_editor.js";

var OPENING_LOOK = BOARD.opening.colour;

outs.sections = [blank(0, outs.lamps.length - 1)];
outs.sections[0].look = OPENING_LOOK;
if (mono.lamps.length && BOARD.opening.mono) {
  mono.sections = [blank(0, mono.lamps.length - 1)];
  mono.sections[0].look = BOARD.opening.mono;
}
settle();

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

var STRIP_FEWEST = 1;
var STRIP_MOST = 300;

var STRIP_ORDERS = [["", "GRB (most strips)"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

var STRIP_BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

function stripPercent(brightness) { return Math.round(brightness * 100) + "%"; }

export function stripChipChoice(run) {
  if (run.made === null) {
    return h("select", {title: "The strip's colour order. Change it if red shows as another colour",
                        onchange: function (event) {
                          stripSet(run, {order: event.target.value});
                          draw();
                        }},
      STRIP_ORDERS.map(function (pair) {
        return h("option", {value: pair[0], selected: (run.order || "") === pair[0]}, pair[1]);
      }));
  }
  var offered = STRIP_BRIGHTNESSES.indexOf(run.brightness) < 0
    ? STRIP_BRIGHTNESSES.concat([run.brightness]).sort(function (a, b) { return a - b; })
    : STRIP_BRIGHTNESSES;
  return h("select", {title: "Overall strip brightness, applied on top of each stretch's level",
                      onchange: function (event) {
                        stripSet(run, {brightness: Number(event.target.value)});
                        draw();
                      }},
    offered.map(function (brightness) {
      return h("option", {value: brightness, selected: brightness === run.brightness},
               stripPercent(brightness) + (brightness === run.made ? " (default)" : ""));
    }));
}

export function stripLengthField(run) {
  return h("input", {type: "number", min: STRIP_FEWEST, max: STRIP_MOST, value: run.leds,
                     "aria-label": "LEDs on " + run.label,
                     onchange: function (event) {
                       var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST,
                                           parseInt(event.target.value, 10) || STRIP_FEWEST));
                       if (want === run.leds) return;
                       stripSet(run, {leds: want});
                       settle();
                       draw();
                     }});
}

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

drawSteps.after.push(function () {
  if (active.strip) {
    document.getElementById("outChosen").textContent = "";
  }
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    renderLeds(run.id + "Leds", run);
    renderStretches(run.id + "Bar", run);
    document.getElementById(run.id + "Chosen").textContent = "";
    if (run === active) {
      renderEditor(run.id + "Chosen", run);
    }
  });
  paintAll();
});

function playedBy(out) {
  var lamps = [];
  runs.forEach(function (run) {
    run.lamps.forEach(function (lamp, at) {
      if (lamp.out === out) lamps.push({channel: lamp.channel || 0,
                                        section: run.sections[sectionAt(run, at)]});
    });
  });
  lamps.sort(function (a, b) { return a.channel - b.channel; });
  var counted = [];
  lamps.forEach(function (one) {
    var seen = counted.filter(function (had) { return had.look === one.section.look; })[0];
    if (seen) seen.many++;
    else counted.push({look: one.section.look, section: one.section, many: 1});
  });
  var most = counted[0];
  counted.forEach(function (one) { if (one.many > most.many) most = one; });
  return most ? most.section : null;
}

var STAND_INS = {"Rainbow": "Wave"};

function carriedFrom() { return carried; }

export function standingIn(run, section) {
  var memo = null;
  run.lamps.slice(section.from, section.to + 1).forEach(function (lamp) {
    var had = carriedFrom()[lamp.out];
    if (had && had.as === section.look) memo = had;
  });
  return memo;
}

export function changeWiring(change, toColour) {
  return function (out) {
    if (!!wiring[out].broken !== toColour) return;
    var played = playedBy(out);
    played = played && {look: played.look, pace: played.pace, mood: played.mood,
                        colour: played.colour, level: played.level,
                        blinks: copyBlinks(played.blinks), exact: copyExact(played.exact),
                        timings: copyExact(played.timings)};
    var memo = carriedFrom()[out];
    delete carriedFrom()[out];
    change(out);
    runs.some(function (run) {
      var mine = run.sections.filter(function (section) {
        return run.lamps.slice(section.from, section.to + 1).every(function (lamp) {
          return lamp.out === out;
        });
      })[0];
      if (!mine) return false;
      if (played) {
        var look = lookNamed(played.look);
        var target = targetFor(run, mine);
        var standIn = lookNamed(STAND_INS[played.look]);
        if (toColour && memo && played.look === memo.as) {
          Object.assign(mine, {look: memo.look, pace: played.pace, mood: memo.mood,
                               colour: memo.colour, level: played.level});
        } else if (look && canPlay(look, target)) {
          Object.assign(mine, played);
        } else if (standIn && canPlay(standIn, target)) {
          Object.assign(mine, played, {look: keyOf(standIn)});
          carriedFrom()[out] = {as: keyOf(standIn), look: played.look, mood: played.mood,
                                colour: played.colour};
        }
      }
      return true;
    });
    settle();
    pickOutput(out);
    draw();
  };
}

[outs, mono].forEach(function (run) {
  run.sections.forEach(function (section) {
    var look = lookNamed(section.look);
    if (look) startColour(run, section, look);
  });
});
