import {draw} from "./00_draw.js";
import {
  FAINTEST, WORDS, atBrightness, fieldColour, hexOf, hexRgb, rgbInk, takeApart
} from "./01_colours.js";
import {swatchesFor} from "./02_blink.js";
import {inkOf} from "./02_preview.js";
import {SIGNAL_INK, SIGNAL_STATES, customColours} from "./05_strips.js";
import {renderPreview} from "./18_file_preview.js";

// ---- the stretch editor -------------------------------------------------------------------------
// The chosen stretch's colour picker, a signal's states and a palette's colours, and the boxes its
// figures are typed in.

// The picker is the one a screen's background has. It is one row of swatches spanning the
// stretch's width, named under them when there is room, and the custom field under the row
// with the hex beside it over the colour itself
export function renderColourPick(box, run) {
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

export function signalFace(name, key) {
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
export function paintPalette(swatches, lines) {
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
export function figureCells(said, unit, title, take) {
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
