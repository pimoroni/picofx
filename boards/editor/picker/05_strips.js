import {draw, drawSteps, paintAll} from "./00_draw.js";
import {WORDS, detented, hexOf} from "./01_colours.js";
import {BOARD, SIGNAL_TIMINGS, lookNamed, timingOf, withSection} from "./01_looks.js";
import {directionToggle} from "./02_preview.js";
import {boardResidue, keptNow} from "./03_kept.js";
import {
  brightnessSlider, forwardTargetFor, runsAWay, startColour, takesColour, targetFor, wherePlays
} from "./03_lines.js";
import {entryParts, lampsNamed} from "./03_reading.js";
import {Run, active, blank, canEdit, chosenSteps, mono, outs, runs, settle} from "./03_runs.js";
import {renderChosen} from "./04_led_panels.js";
import {allBodies, apply, slotAt, state, store, stretchUnder} from "./04_scenes.js";
import {standingIn} from "./07_board.js";
import {boardBox, renderLeds, small, stripChipChoice} from "./08_setup.js";
import {workOn} from "./10_led_sections.js";
import {renderPreview} from "./18_file_preview.js";
import {barCells, fitBars, renderStripBar, splitTools, washFor} from "./31_stretch_bar.js";
import {renderColourPick, signalFace} from "./32_stretch_editor.js";

// ---- the strips ---------------------------------------------------------------------------
// A strip is a run like the outputs, cut into stretches, each playing its own look, and cut
// per scene as everything else is. It takes the run model without the wiring, since an
// output's three channels are the only thing that breaks out.

// The board's strips. A strip's order is the one it takes its colours in, empty for the board's
// own. It is there as the board describes it until added or removed while the board is edited,
// and one the description says takes other strips takes their terminals. A strip given a
// brightness by the description takes that after its length in place of an order, and the
// description's brightness is the board's own
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

// The strip run a file names, or null where this board has no strip by that name
export function stripNamed(name) {
  var lower = name.toLowerCase();
  return runs.filter(function (run) { return run.strip && run.name === lower; })[0] || null;
}

// The strip's entry, which a fresh run is made from, and the run itself, given the same values
export function stripSet(run, values) {
  var one = STRIPS.filter(function (strip) { return strip.id === run.id; })[0];
  Object.keys(values).forEach(function (key) {
    one[key] = values[key];
    run[key] = values[key];
  });
}

export var GLASS_OUT = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
                "<path d='M5 7.2 L9.4 7.2'/>";

export var GLASS_IN = "<circle cx='7.2' cy='7.2' r='4.9'/><path d='M10.9 10.9 L14.4 14.4'/>" +
               "<path d='M5 7.2 L9.4 7.2 M7.2 5 L7.2 9.4'/>";

// ---- a strip's LEDs, in its stretches' cards -------------------------------------------------
// A strip's LEDs sit in its stretches' cards as beads on a wire. The wire runs the length of the
// bar from a lead block before the first card to a ring after the last, outside the stretches,
// since neither is a light. Between the two ends of a straight scale, the beads close up as an
// LED's room shrinks, from beads apart at full size to one continuous strip.

// The largest a bead is drawn, in pixels, and the height every bead keeps
export var BEAD_MOST = 22;

// The gap in pixels between two full-size beads
export var GAP_MOST = 4.8;

// The room in pixels an LED has where the gaps, corners and edges have closed up to one strip.
// It is what 120 LEDs have on a page 1280 pixels wide
export var BEADS_JOIN_AT = 6.4;

// ---- how many lights are on one ------------------------------------------------------------
// The chip the drawing keeps its count in. A strip's length is a fact about the
// board, so it is the same in every scene and changing it here changes it in all of them

// A strip's length as the chip takes it. One LED is a strip autofx accepts
var STRIP_FEWEST = 1;
var STRIP_MOST = 300;

// The orders a strip can take its colours in, as the file writes them after its length.
// The board's own is written as nothing
export var STRIP_ORDERS = [["", "GRB (most strips)"], ["rgb", "RGB"], ["rbg", "RBG"],
                    ["gbr", "GBR"], ["brg", "BRG"], ["bgr", "BGR"]];

// The brightnesses a strip with one of its own can be given, as the file writes them after its
// length. The board's own is written as nothing
export var STRIP_BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

export function stripPercent(brightness) { return Math.round(brightness * 100) + "%"; }

// The same as words, where the chip cannot be changed
export function stripChipShown(run) {
  return run.made === null ? (run.order || "grb").toUpperCase()
                           : stripPercent(run.brightness) + " brightness";
}

// The same as the file writes it after the length, nothing for the board's own
export function stripLengthTail(run) {
  if (run.made === null) return run.order ? "|" + run.order : "";
  return run.brightness === run.made ? "" : "|" + stripPercent(run.brightness);
}

// The same read back from the file, as the values to set, or null for one the page does not
// offer, which stays as written for the board to answer
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

// A strip's chip, its length and its order or brightness to set, shown while the board is set up
export function renderStripChip(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var chip = document.createElement("div");
  chip.className = "chip strip";
  chip.appendChild(document.createTextNode("Strip"));
  var count = document.createElement("input");
  count.type = "number";
  count.min = STRIP_FEWEST;
  count.max = STRIP_MOST;
  count.value = run.leds;
  count.onchange = function () {
    var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST, parseInt(count.value, 10) ||
                                                           STRIP_FEWEST));
    if (want === run.leds) return;
    stripSet(run, {leds: want});
    settle();
    draw();
  };
  chip.appendChild(count);
  var unit = document.createElement("small");
  unit.textContent = "LEDs";
  chip.appendChild(unit);
  chip.appendChild(stripChipChoice(run));
  box.appendChild(chip);
  var says = document.createElement("span");
  says.className = "says";
  says.textContent = "shared by every scene";
  box.appendChild(says);
}

// ---- zooming a strip's bar --------------------------------------------------------------------
// A strip's bar is found by the strip's own id

// The most lights a strip can have and not be zoomed, which the zoom buttons are hidden at
export var ZOOMS_OVER = 12;

// ---- joining them to the page below -----------------------------------------------------

// Each strip has a panel after the outputs', in the board's order, and its board box takes the
// strip's own colour
(function () {
  var colours = document.createElement("style");
  var after = document.getElementById("outPanel");
  BOARD.strips.forEach(function (strip) {
    var id = strip.name;
    var panel = document.createElement("details");
    panel.className = "panel strip";
    panel.id = id + "Panel";
    panel.open = true;
    panel.innerHTML = "<summary>" + strip.label.charAt(0).toUpperCase() + strip.label.slice(1) +
                      "<span class='says'>" + strip.says + "</span></summary>" +
                      "<div class='leds' id='" + id + "Leds'></div>" +
                      "<div class='stripbar' id='" + id + "Bar'></div>" +
                      "<div id='" + id + "Chosen'></div>";
    after.parentNode.insertBefore(panel, after.nextSibling);
    after = panel;
    colours.textContent += ".boardchip." + id + "{background:" + strip.colour + "}\n";
  });
  document.head.appendChild(colours);
}());

// The strips are runs of the page below from here on. Each scene keeps its own cutting of
// them in its body, which captures every run
runs = runs.concat(STRIPS.map(stripRun));
settle();

// ---- drawing the page -------------------------------------------------------------------

drawSteps.after.push(function () {
  // The outputs' settings are for the stretch being worked on, which while a strip is picked is
  // under that strip instead
  if (active.strip) document.getElementById("outChosen").textContent = "";
  runs.filter(function (run) { return run.strip; }).forEach(function (run) {
    // A strip made too short to zoom has no zoom buttons, so it is not left zoomed in
    if (run.lamps.length <= ZOOMS_OVER) {
      run.zoom = 1;
      run.scrolled = 0;
    }
    run.count = run.lamps.length;
    renderLeds(run.id + "Leds", run);
    renderStripBar(run.id + "Bar", run);
    document.getElementById(run.id + "Chosen").textContent = "";
    if (run === active) renderChosen(run.id + "Chosen", run);
  });
  fitBars();
  // The page painted what it drew before these were made, so a fresh bead would hold the
  // default fill until the next frame and show black
  paintAll();
});

// ---- what a stretch is drawn in wherever it is shown in small -------------------------------
// The colours it plays, never only the colour of its look's card. They are read from the
// lines the stretch writes, so they cannot disagree with the file. One colour is drawn
// whole, several across the stretch's width, and a look that writes none, as Rainbow does,
// in its card's colours. A mono stretch is drawn in the warm white its lamps give. The bars
// under the lamps and the Repeat tool's chips all ask here
export var MONO_WASH = "#f3c98b";

// The second setting a look starts at, on its card and on a stretch given it, where middling
// does not suit it. Solid starts at full brightness, Colour cycle at full saturation, Colour
// steps at picofx's six, and the signals' lamps fade in about a tenth of a second, as a real
// signal's do. Marquee starts with every third light lit
export var START_MOODS = {"Solid": 1, "Colour cycle": 1, "Colour steps": 1 / 3,
                   "Pelican crossing": 0.1, "Traffic light": 0.1, "Marquee": 0.25};

// Solid's own colour, which a stretch given it starts in and its card shows, still and at full
// brightness. A card stepping through the swatches would read as Colour steps, and its palette
// mark already says a colour is chosen
export var SOLID_COLOUR = "#" + hexOf(WORDS.yellow);

// The looks the board opens playing start in their own colours too
[outs, mono].forEach(function (run) {
  run.sections.forEach(function (section) {
    var look = lookNamed(section.look);
    if (look) startColour(run, section, look);
  });
});

// The last custom colour of each stretch and its own brightness, by its run and first lamp,
// kept while a swatch is chosen so custom comes back to both, as a screen's background does.
// It is kept here, since the stretches are made afresh on every draw
export var customColours = {};

// The stretch's settings, with the colour choice in place of a slider that steps tones
chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var memo = box && section && standingIn(run, section);
  if (memo) {
    var note = document.createElement("div");
    note.className = "standin";
    note.textContent = look.name + ", replacing " + memo.look + ", " +
                       "which mono lights cannot play. Rejoin to restore " + memo.look + ".";
    box.querySelector(".chosen").appendChild(note);
  }
  // A count of stops may depend on the stretch, as Spread's lengths do on its lights
  if (box && look && look.detents) {
    detented(box, where, typeof look.detents === "function"
      ? look.detents(targetFor(run, section)) : look.detents);
  }
  var wrap = box && box.querySelector(".chosen");
  if (!wrap || !look) return;
  var tuning = wrap.querySelector(".tuning");
  if (!tuning) {
    tuning = document.createElement("div");
    tuning.className = "tuning";
    wrap.appendChild(tuning);
  }
  // Solid's own slider is its brightness, so it gives way to the Brightness slider every look has
  if (look.solid) tuning.textContent = "";
  // A mono lamp has no colour to be given
  var first = run.lamps[section.from];
  var coloured = takesColour(look) && !!first && first.colour;
  // The second slider steps a table of tones for these looks, and the swatches take
  // its place. On mono lights it has nothing to set, since a mono light has no colour
  var mono = !!first && !first.colour;
  var toneless = look.mood === "Colour" || (mono && look.mood === "Palette");
  if ((coloured || mono) && toneless && tuning.children.length >= 4) {
    tuning.removeChild(tuning.children[3]);
    tuning.removeChild(tuning.children[2]);
  }
  brightnessSlider(tuning, run, where);
  // The colour leads and the sliders follow it, brightness the first of them
  if (coloured) {
    renderColourPick(wrap, run);
    wrap.appendChild(tuning);
  }
});

// Party flashes its three sets a third of a beat apart, and the phases it was given, 0, 0.33
// and 0.67, light the first set, then the third, then the second, a step back toward the start
// each time. Swapped, its sets light in order, away from the start as every look goes
(function (party) {
  var partyLines = party.entries;
  party.entries = function (target, pace, mood) {
    return partyLines(target, pace, mood).map(function (line) {
      return line.replace(/ phase=0\.(33|67)\b/, function (all, third) {
        return " phase=0." + (third === "33" ? "67" : "33");
      });
    });
  };
}(lookNamed("Party")));

// ---- a signal's states, drawn ----------------------------------------------------------------
// Each timing is named by the state it holds, drawn as the signal shows it, as a head of three
// lamps, red, amber and green top to bottom, with those lit in their colour, and for a
// crossing the two figures beside it, the red one standing and the green one walking. Its
// slider takes the state's colour. The word stays beside the drawing
export var SIGNAL_INK = {red: "#e8392c", amber: "#f5a623", green: "#20b35c", dark: "#3b3f44"};

// The lamps each state lights, 1 for lit, 0 for dark and "f" for flashing
export var SIGNAL_STATES = {
  "Traffic light": {red_interval: [1, 0, 0], red_amber_interval: [1, 1, 0],
                    green_interval: [0, 0, 1], amber_interval: [0, 1, 0]},
  "Pelican crossing": {red_interval: [1, 0, 0, 0, 1], flashing_interval: [0, "f", 0, 0, "f"],
                       green_interval: [0, 0, 1, 1, 0], amber_interval: [0, 1, 0, 1, 0]}
};

// A slider's tint, amber and green a shade deeper than the lamps. A browser gives a light
// accent a dark track, which reads as a slider filled to its end
var SIGNAL_TINT = {red_interval: SIGNAL_INK.red, red_amber_interval: "#a86600",
                   green_interval: "#16894a", amber_interval: "#a86600",
                   flashing_interval: "#a86600"};

// A signal's timings take Speed's place, each a slider in seconds under its own name
chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning || !look || !SIGNAL_TIMINGS[look.name]) return;
  var speed = tuning.querySelector("input[data-focus='" + where + "-pace']");
  var after = speed ? speed.nextSibling : null;
  if (speed) {
    tuning.removeChild(speed.previousElementSibling);
    tuning.removeChild(speed);
  }
  // Ease is about every state, so it comes before them, after Brightness
  var ease = tuning.querySelector("input[data-focus='" + where + "-mood']");
  if (ease) {
    var easeLabel = ease.previousElementSibling;
    if (after === easeLabel) after = ease.nextSibling;
    tuning.insertBefore(easeLabel, after);
    tuning.insertBefore(ease, after);
    after = ease.nextSibling;
  }
  SIGNAL_TIMINGS[look.name].forEach(function (part) {
    var label = document.createElement("label");
    label.className = "signalstate";
    label.innerHTML = signalFace(look.name, part[0]) + "<span>" + part[1] + "</span>";
    var range = document.createElement("input");
    range.style.accentColor = SIGNAL_TINT[part[0]];
    range.type = "range";
    range.min = part[3];
    range.max = part[4];
    range.step = 0.5;
    range.value = withSection(section, function () { return timingOf(look.name, part[0]); });
    range.dataset.focus = where + "-timing-" + part[0];
    range.dataset.timing = part[0];
    range.title = "seconds, " + part[1].toLowerCase();
    range.oninput = function () {
      var mine = run.sections[run.picked];
      mine.timings = Object.assign({}, mine.timings);
      mine.timings[part[0]] = Number(range.value);
      renderPreview();
    };
    tuning.insertBefore(label, after);
    tuning.insertBefore(range, after);
  });
});

// ---- an icon for each setting ------------------------------------------------------------------
// Each slider's name has a small line drawing before it, in the name's own grey, as the toggles
// have theirs, so a panel reads at a glance. A signal's states keep their coloured
// drawings, since colour is what they are about. The word stays, and the icon only hints
var SETTING_ICONS = {
  "Brightness": "<circle cx='8' cy='8' r='2.8'/><path d='M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8" +
                "M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3'/>",
  "Speed": "<path d='M2.4 12A6 6 0 1 1 13.6 12'/><path d='M8 10.2L11 5.6'/>" +
           "<circle cx='8' cy='10.4' r='1' class='filled'/>",
  "Fade": "<path d='M5.6 10.4C4 9.3 3.6 7.9 3.6 6.8a4.4 4.4 0 0 1 8.8 0c0 1.1-.4 2.5-2 3.6'/>" +
          "<path d='M6 12.4h4M6.6 14.4h2.8'/><path d='M6.4 6.8c.5-1 1.1-1.5 1.6-1.5'/>",
  "Spread": "<path d='M1.5 8h13M4 5.5L1.5 8 4 10.5M12 5.5L14.5 8 12 10.5'/>",
  "Steps": "<path d='M2 13.5h3v-3h3v-3h3v-3h3'/>",
  "Trail": "<circle cx='12.4' cy='8' r='2.2' class='filled'/><path d='M1.6 8h6.8M3.2 5.2h5.2" +
           "M3.2 10.8h5.2'/>",
  "Flashes": "<path d='M9.2 1.6L4.2 9h3.9l-1.3 5.4L11.8 7H7.9z'/>",
  "On time": "<circle cx='8' cy='8' r='5.8'/><path d='M8 2.2a5.8 5.8 0 0 1 0 11.6z' class='filled'/>",
  "Spacing": "<circle cx='2.6' cy='8' r='1.4' class='filled'/><circle cx='8' cy='8' r='1.4'/>" +
             "<circle cx='13.4' cy='8' r='1.4' class='filled'/>",
  "Saturation": "<path d='M8 1.8C8 1.8 3.6 7.2 3.6 10a4.4 4.4 0 0 0 8.8 0C12.4 7.2 8 1.8 8 1.8z'/>",
  "Intensity": "<path d='M8 1.6c1.5 2.7 4.5 4.3 4.5 7.8a4.5 4.5 0 0 1-9 0c0-2 1.4-3 2-4.4" +
               "c.9 1.4 1.4 1.9 1.9 1.9 0-2 .1-3.5.6-5.3z'/>",
  "Palette": "<path d='M8 1.6a6.4 6.4 0 0 0 0 12.8c1 0 1.6-.6 1.6-1.3 0-.9-.7-1.1-.7-1.8 0-.8.6-1.2" +
             " 1.3-1.2h1.7a2.8 2.8 0 0 0 2.8-2.8C14.7 4 11.8 1.6 8 1.6z'/>" +
             "<circle cx='4.9' cy='7.6' r='.9' class='filled'/><circle cx='6.2' cy='4.7' r='.9' " +
             "class='filled'/><circle cx='9.3' cy='4' r='.9' class='filled'/>"
};

chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning) return;
  // Every slider keeps the picked stretch's colours on the bar in step as it moves, since one
  // such as Palette changes them, and redraws the panel once let go. A slider's own handler
  // plays only the preview, which would leave the bar showing the colours from before
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  Array.prototype.forEach.call(tuning.querySelectorAll("input[type=range]"), function (range) {
    var moved = range.oninput;
    range.oninput = function () {
      if (moved) moved.call(range);
      var live = run.sections[run.picked];
      var cell = barCells(run)[run.picked];
      var wash = cell && cell.querySelector(".lit");
      if (wash && look) wash.style.background = washFor(run, live, look);
    };
    if (!range.onchange) range.onchange = function () { draw(); };
  });
  Array.prototype.forEach.call(tuning.querySelectorAll(":scope > label"), function (label) {
    var drawn = SETTING_ICONS[label.textContent];
    if (!drawn || label.querySelector(".settingicon")) return;
    if (label.textContent === "Fade") {
      label.title = "how long each light takes to fade on and off, eased so it slows at the end";
    }
    label.classList.add("withicon");
    label.insertAdjacentHTML("afterbegin", "<svg class='settingicon' viewBox='0 0 16 16' " +
                                           "aria-hidden='true'>" + drawn + "</svg>");
  });
});

chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var who = box && box.querySelector(".chosen .who");
  var section = run && run.sections[run.picked];
  if (!who || !section) return;
  var look = lookNamed(section.look);
  var under = look ? null : stretchUnder(run, section);
  who.innerHTML = "";
  var named = document.createElement("b");
  named.textContent = look ? look.name : "Nothing";
  who.appendChild(named);
  var reversed = section.reversed && runsAWay(look, forwardTargetFor(run, section), section);
  who.appendChild(document.createTextNode(" on " + wherePlays(run, section, reversed)));
  who.title = targetFor(run, section).selector;
  // A stretch the scene leaves empty says what the board plays there, and how to change it
  if (under) {
    var hint = document.createElement("div");
    hint.className = "underhint";
    hint.textContent = under.tip + " Choose a look to give this scene its own.";
    who.parentNode.insertBefore(hint, who.nextSibling);
  }
});

chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var who = box && box.querySelector(".chosen .who");
  if (!section || !who) return;
  // The name and its count stay one piece of text, the toggle set apart at the end
  var named = document.createElement("span");
  while (who.firstChild) named.appendChild(who.firstChild);
  who.appendChild(named);
  who.classList.add("withway");
  if (run.strip) who.appendChild(splitTools(where, run));
  who.appendChild(directionToggle(run, section));
});

// Whether a strip is there, on the run and on the entry a fresh run is made from
function stripThere(run, there) { stripSet(run, {there: there}); }

function capitalised(text) { return text.charAt(0).toUpperCase() + text.slice(1); }

// Why a strip cannot be fitted just now, or nothing where it can. A strip taking other strips'
// terminals cannot be fitted beside them, nor they beside it
export function stripBlockedBy(run) {
  if (run.there) return "";
  var fitted = runs.filter(function (one) {
    return one.strip && one.there && run.takes.indexOf(one.name) >= 0;
  });
  if (fitted.length) {
    return capitalised(run.label) + " takes " + run.connector + ", so it cannot be fitted beside " +
           fitted.map(function (one) { return one.label; }).join(" and ") + ". Remove " +
           (fitted.length > 1 ? "them" : "it") + " to fit one here.";
  }
  var taking = runs.filter(function (one) {
    return one.strip && one.there && one.takes.indexOf(run.name) >= 0;
  })[0];
  return taking ? capitalised(taking.label) + " uses " + taking.connector +
                  ". Remove it to fit a strip here." : "";
}

// Taking a strip out clears what it plays in every scene, the lines kept from a file
// included, which leaves its length unwritten and its connector off
export function dropStrip(run) {
  forgetKeptFor(run);
  store();
  allBodies().forEach(function (held) {
    var kept = held.runs[run.name];
    if (!kept) return;
    kept.sections = [blank(0, run.leds - 1, run)];
    kept.picked = 0;
    kept.was = [];
    kept.undone = [];
  });
  stripThere(run, false);
  apply(slotAt(state.at).body);
  draw();
}

// The cross on a strip's chip while the board is edited, as a screen has on its own
export function stripDrop(run) {
  var drop = document.createElement("button");
  drop.type = "button";
  drop.className = "drop";
  drop.textContent = "\u00d7";
  drop.title = "Remove this strip from every scene";
  drop.onclick = function () { dropStrip(run); };
  return drop;
}

// A strip not fitted offers to be added, which only editing the board can take up, or says
// why it cannot be
export function renderStripOut(box, run, panel) {
  box.textContent = "";
  box.appendChild(boardBox(panel, ["Strip", small("not fitted")]));
  var blocked = stripBlockedBy(run);
  if (blocked) {
    var why = document.createElement("span");
    why.className = "stripblocked says";
    why.textContent = blocked;
    box.appendChild(why);
    return;
  }
  var add = document.createElement("button");
  add.type = "button";
  add.className = "addstrip";
  add.textContent = "add this strip";
  add.disabled = !canEdit(panel);
  add.onclick = function () {
    stripThere(run, true);
    workOn(panel);
    draw();
  };
  box.appendChild(add);
}

// ---- writing them back ------------------------------------------------------------------------

// The strip a board token gives a length, such as stripl for stripl=30, or null
function stripOfToken(token) {
  var named = token.match(/^(\w+)=/);
  var name = named && named[1].toLowerCase();
  return STRIPS.some(function (strip) { return strip.name === name; }) ? name : null;
}

// A strip removed takes with it every scene's kept lines that play on it, and its length
// as written, or they would keep its connector on
function forgetKeptFor(run) {
  function elsewhere(one) {
    var parts = entryParts(one.text);
    var lamps = parts && lampsNamed(run, parts.selector);
    return !(lamps && lamps.length);
  }
  keptNow = keptNow.filter(elsewhere);
  allBodies().forEach(function (held) { held.kept = (held.kept || []).filter(elsewhere); });
  boardResidue = boardResidue.filter(function (token) { return stripOfToken(token) !== run.name; });
}
