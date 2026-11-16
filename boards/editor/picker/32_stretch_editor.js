import {draw} from "./00_draw.js";
import {
  FAINTEST, WORDS, atBrightness, detented, fieldColour, hexOf, hexRgb, rgbInk, takeApart
} from "./01_colours.js";
import {SIGNAL_TIMINGS, lookNamed, timingOf, withSection} from "./01_looks.js";
import {BLINK, blinkNamed, swatchesFor} from "./02_blink.js";
import {directionToggle, inkOf} from "./02_preview.js";
import {
  brightnessSlider, forwardTargetFor, runsAWay, sectionLines, takesColour, targetFor, wherePlays
} from "./03_lines.js";
import {chosenSteps} from "./03_runs.js";
import {stretchUnder} from "./04_scenes.js";
import {SETTING_ICONS, SIGNAL_INK, SIGNAL_STATES, SIGNAL_TINT, customColours} from "./05_strips.js";
import {standingIn} from "./07_board.js";
import {renderPreview} from "./18_file_preview.js";
import {
  FIGURES_KEPT, figureKey, figureSaid, figureWay, figuresOpen, linesAt, placeFor, setFiguresOpen,
  settingIn
} from "./25_figures.js";
import {barCells, splitTools, washFor} from "./31_stretch_bar.js";

// ---- the stretch editor -------------------------------------------------------------------------
// The chosen stretch's colour picker, a signal's states and a palette's colours, and the boxes its
// figures are typed in.

// The picker is the one a screen's background has. It is one row of swatches spanning the
// stretch's width, named under them when there is room, and the custom field under the row
// with the hex beside it over the colour itself
function renderColourPick(box, run) {
  var section = run.sections[run.picked];
  // Every draw settles the model and settling makes the stretches afresh, so a handler
  // that kept the stretch it was made with would write onto one the run no longer holds.
  // Each reaches the live one through the run when it fires
  function live() { return run.sections[run.picked]; }
  var remembered = run.id + ":" + section.from;
  var wrap = document.createElement("div");
  wrap.className = "colourpick groundpick";

  var swatches = document.createElement("div");
  swatches.className = "sswatches";
  var offered = swatchesFor(run, section);
  var chosenHex = (section.colour || "#ffffff").replace("#", "").toLowerCase();
  var chosenWord = offered.filter(function (name) {
    return hexOf(WORDS[name]) === chosenHex;
  })[0] || null;
  offered.forEach(function (name) {
    var swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = "swatch" + (chosenWord === name ? " on" : "");
    swatch.style.background = rgbInk(WORDS[name]);
    swatch.title = name;
    var tag = document.createElement("b");
    tag.textContent = name;
    swatch.appendChild(tag);
    swatch.onclick = function () {
      live().colour = "#" + hexOf(WORDS[name]);
      live().custom = false;
      draw();
    };
    swatches.appendChild(swatch);
  });

  // The last one is not a colour but the way to every other one
  var custom = document.createElement("button");
  custom.type = "button";
  custom.className = "swatch custom" + (section.custom || !chosenWord ? " on" : "");
  // Its middle is the custom colour at its own brightness, kept while a swatch is chosen, and
  // empty until there is one
  if (section.custom || !chosenWord) {
    customColours[remembered] = {colour: section.colour || "#ffffff",
                                 level: section.level === undefined ? 1 : section.level};
  }
  var kept = customColours[remembered];
  if (kept) custom.style.setProperty("--picked", atBrightness(kept.colour, kept.level));
  custom.title = "any hue and saturation, with its own brightness";
  var ctag = document.createElement("b");
  ctag.textContent = "custom";
  custom.appendChild(ctag);
  // A swatch keeps the brightness already set, and custom comes back at its own
  custom.onclick = function () {
    live().custom = true;
    if (kept) {
      live().colour = kept.colour;
      live().level = kept.level;
    }
    draw();
  };
  swatches.appendChild(custom);
  wrap.appendChild(swatches);

  // The field, open only while custom is the choice. Hue across and saturation down, at
  // full value throughout, so a colour means the same thing at any brightness
  var holds = document.createElement("div");
  var open = section.custom || !chosenWord;
  holds.className = "customholds scustom";
  holds.style.display = open ? "" : "none";
  var parts = takeApart(hexRgb(section.colour || "#ffffff"));
  var field = document.createElement("div");
  field.className = "field";
  var at = document.createElement("div");
  at.className = "at";
  at.style.left = (parts.hue / 360 * 100) + "%";
  at.style.top = ((1 - parts.sat) * 100) + "%";
  at.style.background = rgbInk(fieldColour(parts.hue, parts.sat));
  field.appendChild(at);

  // Held down and dragged. Only the mark and the box move while the pointer is down, so
  // the field is never rebuilt under it
  function pointingAt(event) {
    var box2 = field.getBoundingClientRect();
    var across = Math.max(0, Math.min(1, (event.clientX - box2.left) / box2.width));
    var down = Math.max(0, Math.min(1, (event.clientY - box2.top) / box2.height));
    var rgb = fieldColour(across * 360, 1 - down);
    live().colour = "#" + hexOf(rgb);
    live().custom = true;
    at.style.left = (across * 100) + "%";
    at.style.top = (down * 100) + "%";
    at.style.background = rgbInk(rgb);
    hex.value = atBrightness(live().colour, live().level);
    preview.style.background = hex.value;
    renderPreview();
  }
  field.onpointerdown = function (event) {
    field.setPointerCapture(event.pointerId);
    pointingAt(event);
  };
  field.onpointermove = function (event) {
    if (field.hasPointerCapture(event.pointerId)) pointingAt(event);
  };
  field.onpointerup = function () { draw(); };
  holds.appendChild(field);

  // A hex is how a colour arrives from somewhere else, so it is typed rather than hunted
  // for. It is the colour as written, at the stretch's brightness, as a screen's background
  // has it, so one typed in sets the colour and the brightness both
  var typed = document.createElement("div");
  typed.className = "hexline";
  var label = document.createElement("label");
  label.textContent = "Hex";
  typed.appendChild(label);
  var hex = document.createElement("input");
  hex.type = "text";
  hex.maxLength = 7;
  hex.spellcheck = false;
  hex.value = atBrightness(section.colour || "#ffffff", section.level);
  hex.title = "the colour as written, at its brightness. Paste a colour " +
              "in to set the hue, saturation and brightness below";
  hex.oninput = function () {
    var said = hex.value.replace("#", "").trim();
    if (!/^[0-9a-fA-F]{6}$/.test(said)) return;
    var typedRgb = hexRgb("#" + said.toLowerCase());
    var got = takeApart(typedRgb);
    var rgb = fieldColour(got.hue, got.sat);
    live().colour = "#" + hexOf(rgb);
    live().level = Math.max(FAINTEST, Math.max.apply(null, typedRgb) / 255);
    live().custom = true;
    at.style.left = (got.hue / 360 * 100) + "%";
    at.style.top = ((1 - got.sat) * 100) + "%";
    at.style.background = rgbInk(rgb);
    preview.style.background = "#" + said.toLowerCase();
    renderPreview();
  };
  hex.onblur = function () { draw(); };
  typed.appendChild(hex);

  // Beside the field, the hex over the colour itself, as large as the room allows, as a
  // screen's custom background has it
  var side = document.createElement("div");
  side.className = "scustomside";
  side.appendChild(typed);
  var preview = document.createElement("div");
  preview.className = "scustompreview";
  preview.style.background = atBrightness(section.colour || "#ffffff", section.level);
  preview.title = "The colour as written, at its brightness";
  side.appendChild(preview);
  holds.appendChild(side);
  wrap.appendChild(holds);

  box.appendChild(wrap);
}

function signalFace(name, key) {
  var lit = SIGNAL_STATES[name][key];
  function lamp(state, ink) {
    if (!state) return SIGNAL_INK.dark;
    return ink;
  }
  function flashing(state) { return state === "f" ? " class='flashing'" : ""; }
  var head = [SIGNAL_INK.red, SIGNAL_INK.amber, SIGNAL_INK.green].map(function (ink, at) {
    return "<circle cx='6' cy='" + (4.5 + at * 6.5) + "' r='2.6' fill='" + lamp(lit[at], ink) +
           "'" + flashing(lit[at]) + "/>";
  }).join("");
  var wide = 12;
  var figures = "";
  // A crossing's pedestrian lights are drawn as its figures, the red one standing and the
  // green one walking, so they read as figures and not as a second head of lamps
  if (lit.length > 3) {
    wide = 22;
    var stand = lamp(lit[3], SIGNAL_INK.red), walk = lamp(lit[4], SIGNAL_INK.green);
    figures = "<rect x='12.5' y='1' width='9' height='22' rx='2' fill='#1c1f22'/>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + stand + "'" +
      flashing(lit[3]) + "><circle cx='17' cy='3.6' r='1.1' fill='" + stand + "' stroke='none'/>" +
      "<path d='M17 5.2 V8.6 M15.6 6.4 H18.4 M16.3 8.6 V11 M17.7 8.6 V11'/></g>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + walk + "'" +
      flashing(lit[4]) + "><circle cx='17.4' cy='13.6' r='1.1' fill='" + walk + "' stroke='none'/>" +
      "<path d='M17.2 15.2 L16.8 18.3 M15.6 16.8 L18.6 16 M16.8 18.3 L15.4 21 M16.8 18.3 " +
      "L18.6 20.8'/></g>";
  }
  return "<svg class='signalface' viewBox='0 0 " + wide + " 24' width='" + wide * 0.9 +
         "' height='21.6' aria-hidden='true'><rect x='1' y='0' width='10' height='24' rx='3' " +
         "fill='#1c1f22'/>" + head + figures + "</svg>";
}

// A palette's colours, a swatch for each its lines name, drawn afresh as its slider moves
function paintPalette(swatches, lines) {
  swatches.textContent = "";
  (lines.join(" ").match(/colour=[^\s:]+/g) || []).forEach(function (said) {
    var chip = document.createElement("span");
    chip.className = "palettechip";
    chip.style.background = inkOf(said.slice(7));
    chip.title = said.slice(7);
    swatches.appendChild(chip);
  });
}

// The box a figure is typed in and its unit, each a cell of the sliders' grid
function figureCells(said, unit, title, take) {
  var box = document.createElement("input");
  box.type = "text";
  box.inputMode = "decimal";
  box.className = "figurebox";
  box.value = said;
  box.title = title;
  box.onchange = function () {
    var typed = parseFloat(box.value.replace(",", "."));
    if (!(typed > 0)) {
      box.value = said;
      return;
    }
    take(typed);
    draw();
  };
  var units = document.createElement("span");
  units.className = "figureunit";
  units.textContent = unit;
  return [box, units];
}

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

// ---- blinking through several colours, on the chosen stretch ------------------------------------
// The chips of the colours Blink steps through, drawn among the chosen stretch's settings.

// Above the swatches, the colours it blinks through, each a chip that the picker changes
// while it is chosen, with a way to add another and to take one away
chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var pick = box && box.querySelector(".chosen .colourpick");
  var first = section && run.lamps[section.from];
  if (!pick || section.look !== BLINK || !first || !first.colour) return;
  function live() { return run.sections[run.picked]; }
  var blinks = section.blinks || {colours: [section.colour || "#ff0000"], at: 0};
  blinks.colours[blinks.at] = section.colour;
  section.blinks = blinks;

  function choose(at) {
    var mine = live();
    mine.blinks.at = at;
    mine.colour = mine.blinks.colours[at];
    mine.custom = !blinkNamed(mine.colour);
    draw();
  }

  var row = document.createElement("div");
  row.className = "blinklist";
  var said = document.createElement("span");
  said.className = "blinksay";
  said.textContent = blinks.colours.length > 1 ? "Blinks through" : "Blinks in";
  row.appendChild(said);
  blinks.colours.forEach(function (hex, at) {
    var chip = document.createElement("button");
    chip.type = "button";
    chip.className = "blinkchip" + (at === blinks.at ? " on" : "");
    chip.style.setProperty("--chip", hex);
    chip.title = (at === blinks.at ? "the colour being edited below, " : "change ") +
                 (blinkNamed(hex) || hex);
    chip.onclick = function () { choose(at); };
    row.appendChild(chip);
    if (blinks.colours.length > 1) {
      var drop = document.createElement("button");
      drop.type = "button";
      drop.className = "blinkdrop";
      drop.textContent = "\u00d7";
      drop.title = "stop blinking in " + (blinkNamed(hex) || hex);
      drop.onclick = function () {
        var mine = live();
        mine.blinks.colours.splice(at, 1);
        var left = mine.blinks.colours;
        mine.blinks.at = Math.min(mine.blinks.at, left.length - 1);
        mine.colour = left[mine.blinks.at];
        mine.custom = !blinkNamed(mine.colour);
        if (left.length === 1) mine.blinks = undefined;
        draw();
      };
      row.appendChild(drop);
    }
  });
  var more = document.createElement("button");
  more.type = "button";
  more.className = "blinkmore";
  more.textContent = "+ another colour";
  more.title = "blink through several colours, one per blink";
  // The colour added is a copy of the last, a custom one included, to be changed from there
  more.onclick = function () {
    var mine = live();
    if (!mine.blinks) mine.blinks = {colours: [mine.colour], at: 0};
    var colours = mine.blinks.colours;
    colours.push(colours[colours.length - 1]);
    choose(colours.length - 1);
  };
  row.appendChild(more);
  pick.insertBefore(row, pick.firstChild);
});

chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning || !look) return;
  function live() { return run.sections[run.picked]; }
  tuning.classList.toggle("figuresopen", figuresOpen);

  var ranges = Array.prototype.slice.call(tuning.querySelectorAll("input[type=range]"));
  var boxes = [];
  ranges.forEach(function (range) {
    var slider = (range.dataset.focus || "").split("-").pop();
    var cells, way = null, key = null, widest = 3;
    var timing = range.dataset.timing;
    if (timing) {
      // A signal's timing is its seconds already, typed past the slider's ends as it is
      widest = Math.max(String(range.min).length, String(range.max).length) + 2;
      cells = figureCells(figureSaid(Number(range.value)), "s",
                          "seconds, typed exactly, beyond the slider's range if needed", function (typed) {
        var mine = live();
        mine.timings = Object.assign({}, mine.timings);
        mine.timings[timing] = Math.round(typed * 100) / 100;
      });
    } else if (slider === "mood" && look.mood === "Palette") {
      // A palette is its colours, not a number, so its slot shows them
      var swatches = document.createElement("span");
      swatches.className = "figurebox paletteswatches";
      paintPalette(swatches, sectionLines(run, section, look));
      // Across the box and unit columns, from where the boxes start, being wider than a box
      swatches.style.gridColumn = "span 2";
      cells = [swatches, null];
    } else if (slider === "level") {
      var bright = section.level === undefined ? 1 : section.level;
      cells = figureCells(String(Math.round(bright * 100)), "%",
                          "brightness, typed as a percentage", function (typed) {
        live().level = Math.max(0.01, Math.min(1, typed / 100));
      });
    } else if (slider === "pace" || slider === "mood") {
      key = figureKey(run, section, look, slider);
      if (key) {
        way = figureWay(key, look);
        // As wide as the widest figure the slider can reach, so dragging it never resizes its
        // column and with it the slider
        [0, 0.5, 1].forEach(function (place) {
          var reach = figureSaid(way.show(settingIn(linesAt(run, section, look, slider, place),
                                                   key)));
          widest = Math.max(widest, reach.length);
        });
        var typedHere = section.exact && section.exact[slider];
        var value = typedHere ? typedHere.value : settingIn(sectionLines(run, section, look), key);
        cells = figureCells(figureSaid(way.show(value)), way.unit,
                            "the file's " + key + ", typed exactly, beyond the slider's range if needed",
                            function (typed) {
          var wanted = way.take(typed);
          var mine = live();
          var found = placeFor(run, mine, look, slider, key, wanted);
          mine[slider] = found.place;
          mine.exact = Object.assign({}, mine.exact);
          if (found.off > 1e-6) {
            mine.exact[slider] = {key: key, value: Math.round(wanted * 1000) / 1000};
          } else {
            delete mine.exact[slider];
          }
        });
      }
    } else {
      return;
    }
    // Check if the slider has no one figure
    if (!cells) {
      // Keep the row's cells, empty, so the columns stay whole
      cells = [document.createElement("span"), document.createElement("span")];
      cells[0].className = "figurebox";
      cells[1].className = "figureunit";
    }
    if (cells[0].tagName === "INPUT") {
      // A figure typed past the slider's end, wider than any it reaches, widens the box to fit
      boxes.push({box: cells[0], chars: Math.max(widest, String(cells[0].value || "").length)});
    }
    if (cells[1]) range.parentNode.insertBefore(cells[1], range.nextSibling);
    range.parentNode.insertBefore(cells[0], range.nextSibling);

    // Moved, the slider is the setting again, and its figure follows it
    var moved = range.oninput;
    range.oninput = function () {
      var mine = live();
      if (mine.exact && mine.exact[slider]) {
        mine.exact = Object.assign({}, mine.exact);
        delete mine.exact[slider];
      }
      if (moved) moved.call(range);
      if (cells[0].classList.contains("paletteswatches")) {
        paintPalette(cells[0], sectionLines(run, mine, look));
        return;
      }
      if (cells[0].tagName !== "INPUT") return;
      if (timing) cells[0].value = figureSaid(Number(range.value));
      else if (slider === "level") cells[0].value = String(Math.round(Number(range.value) * 100));
      else cells[0].value = figureSaid(way.show(settingIn(sectionLines(run, mine, look), key)));
    };
  });

  // Every box in the panel as wide as the widest, so they line up and none moves as it changes
  var chars = boxes.reduce(function (most, one) { return Math.max(most, one.chars); }, 3);
  boxes.forEach(function (one) { one.box.style.width = (chars + 0.5) + "ch"; });

  // The drawer's handle, down the right of the sliders, which opens and shuts every figure
  var handle = document.createElement("button");
  handle.type = "button";
  handle.className = "figurehandle";
  handle.textContent = figuresOpen ? "\u203a" : "\u2039";
  handle.title = figuresOpen ? "hide values" : "show values";
  handle.setAttribute("aria-expanded", figuresOpen ? "true" : "false");
  handle.style.gridRow = "1 / span " + ranges.length;
  handle.onclick = function () {
    setFiguresOpen(!figuresOpen);
    try {
      window.localStorage.setItem(FIGURES_KEPT, figuresOpen ? "1" : "0");
    } catch (e) {
      // Kept only for this visit where the page may not keep anything
    }
    draw();
  };
  tuning.appendChild(handle);
});
