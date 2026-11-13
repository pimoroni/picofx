import {h, replace} from "./00_dom.js";
import {draw, drawSteps} from "./00_draw.js";
import {
  FAINTEST, WORDS, atBrightness, fieldColour, hexOf, hexRgb, rgbInk, takeApart
} from "./01_colours.js";
import {SIGNAL_TIMINGS, lookNamed, timingOf, withSection} from "./01_looks.js";
import {BLINK, blinkNamed, swatchesFor} from "./02_blink.js";
import {inkOf} from "./02_preview.js";
import {
  forwardTargetFor, runsAWay, sectionLines, takesColour, targetFor, wherePlays
} from "./03_lines.js";
import {widthOf} from "./03_outputs.js";
import {chooseLook, pickingLook, remember} from "./03_runs.js";
import {stretchUnder} from "./04_scenes.js";
import {standingIn} from "./07_board.js";
import {chosenTab} from "./11_tabs.js";
import {renderPreview} from "./18_file_preview.js";
import {figureKey, figureSaid, figureWay, linesAt, placeFor, settingIn} from "./25_figures.js";
import {colourField, swatchRow} from "./30_colour_picker.js";
import {stretchCells, washFor} from "./31_stretch_bar.js";

var FIGURES_KEPT = "fx-picker-figures-open";
var MOST_DETENT_TICKS = 16;
var SIGNAL_INK = {red: "#e8392c", amber: "#f5a623", green: "#20b35c", dark: "#3b3f44"};
var SIGNAL_TINT = {red_interval: SIGNAL_INK.red, red_amber_interval: "#a86600",
                   green_interval: "#16894a", amber_interval: "#a86600",
                   flashing_interval: "#a86600"};
var SIGNAL_STATES = {
  "Traffic light": {red_interval: [1, 0, 0], red_amber_interval: [1, 1, 0],
                    green_interval: [0, 0, 1], amber_interval: [0, 1, 0]},
  "Pelican crossing": {red_interval: [1, 0, 0, 0, 1], flashing_interval: [0, "f", 0, 0, "f"],
                       green_interval: [0, 0, 1, 1, 0], amber_interval: [0, 1, 0, 1, 0]}
};
var SETTING_ICONS = {
  "Brightness": "<circle cx='8' cy='8' r='2.8'/><path d='M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8" +
                "M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3'/>",
  "Speed": "<path d='M2.4 12A6 6 0 1 1 13.6 12'/><path d='M8 10.2L11 5.6'/>" +
           "<circle cx='8' cy='10.4' r='1' fill='currentColor' stroke='none'/>",
  "Fade": "<path d='M5.6 10.4C4 9.3 3.6 7.9 3.6 6.8a4.4 4.4 0 0 1 8.8 0c0 1.1-.4 2.5-2 3.6'/>" +
          "<path d='M6 12.4h4M6.6 14.4h2.8'/><path d='M6.4 6.8c.5-1 1.1-1.5 1.6-1.5'/>",
  "Spread": "<path d='M1.5 8h13M4 5.5L1.5 8 4 10.5M12 5.5L14.5 8 12 10.5'/>",
  "Steps": "<path d='M2 13.5h3v-3h3v-3h3v-3h3'/>",
  "Trail": "<circle cx='12.4' cy='8' r='2.2' fill='currentColor' stroke='none'/><path d='M1.6 8h6.8M3.2 5.2h5.2" +
           "M3.2 10.8h5.2'/>",
  "Flashes": "<path d='M9.2 1.6L4.2 9h3.9l-1.3 5.4L11.8 7H7.9z'/>",
  "On time": "<circle cx='8' cy='8' r='5.8'/><path d='M8 2.2a5.8 5.8 0 0 1 0 11.6z' fill='currentColor' stroke='none'/>",
  "Spacing": "<circle cx='2.6' cy='8' r='1.4' fill='currentColor' stroke='none'/><circle cx='8' cy='8' r='1.4'/>" +
             "<circle cx='13.4' cy='8' r='1.4' fill='currentColor' stroke='none'/>",
  "Saturation": "<path d='M8 1.8C8 1.8 3.6 7.2 3.6 10a4.4 4.4 0 0 0 8.8 0C12.4 7.2 8 1.8 8 1.8z'/>",
  "Intensity": "<path d='M8 1.6c1.5 2.7 4.5 4.3 4.5 7.8a4.5 4.5 0 0 1-9 0c0-2 1.4-3 2-4.4" +
               "c.9 1.4 1.4 1.9 1.9 1.9 0-2 .1-3.5.6-5.3z'/>",
  "Palette": "<path d='M8 1.6a6.4 6.4 0 0 0 0 12.8c1 0 1.6-.6 1.6-1.3 0-.9-.7-1.1-.7-1.8 0-.8.6-1.2" +
             " 1.3-1.2h1.7a2.8 2.8 0 0 0 2.8-2.8C14.7 4 11.8 1.6 8 1.6z'/>" +
             "<circle cx='4.9' cy='7.6' r='.9' fill='currentColor' stroke='none'/><circle cx='6.2' cy='4.7' r='.9' " +
             "class='filled'/><circle cx='9.3' cy='4' r='.9' fill='currentColor' stroke='none'/>"
};
var SETTING_TITLES = {
  "Fade": "how long each light takes to fade on and off, eased so it slows at the end"
};

var figuresOpen = false;
try {
  figuresOpen = window.localStorage.getItem(FIGURES_KEPT) === "1";
} catch (e) {
  figuresOpen = false;
}

var customColours = {};

function keepFigures() {
  try {
    window.localStorage.setItem(FIGURES_KEPT, figuresOpen ? "1" : "0");
  } catch (e) {
    return;
  }
}

export function renderEditor(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  var section = run && run.sections[run.picked];
  if (!section) {
    replace(box);
    return;
  }
  var look = lookNamed(section.look);
  var picking = pickingLook(run);
  var first = run.lamps[section.from];
  var coloured = !picking && takesColour(look) && !!first && first.colour;
  replace(box, h("section", {class: "editor", "data-picking": picking,
                             "aria-label": picking ? "Choose a look" : look.name + " settings"},
    picking ? pickingHeader(run, section, look) : settingsHeader(run, section, look),
    notes(run, section, look, picking),
    coloured ? colourPicker(run) : null,
    picking ? null : sliders(run, section, look, where)));
}

function settingsHeader(run, section, look) {
  var reversed = section.reversed && runsAWay(look, forwardTargetFor(run, section), section);
  return h("header", {title: targetFor(run, section).selector},
    h("h3", {}, look.name, " ", h("small", {}, "on " + wherePlays(run, section, reversed))),
    lookButton("Change look", true),
    reverseToggle(run, section, look));
}

function pickingHeader(run, section, look) {
  return h("header", {title: targetFor(run, section).selector},
    h("h3", {}, "Choose a look", " ", h("small", {}, "for " + wherePlays(run, section, false))),
    look ? lookButton("Keep " + look.name, false) : null);
}

function lookButton(words, choosing) {
  return h("button", {type: "button", onclick: function () {
    chooseLook(choosing);
    draw();
  }}, words);
}

function reverseToggle(run, section, look) {
  var moves = runsAWay(look, forwardTargetFor(run, section), section);
  var on = section.reversed && moves;
  return h("button", {type: "button", "aria-pressed": on ? "true" : "false",
                      disabled: !moves,
                      title: !moves ? (widthOf(section) < 2 ? "One light has no direction"
                                                            : look.name + " looks the same from either end")
                           : section.reversed ? "Travels from the far end" : "Travels from the near end",
                      onclick: function () {
                        remember(run);
                        var live = run.sections[run.picked];
                        live.reversed = !live.reversed;
                        draw();
                      },
                      html: "<svg width='28' height='13' viewBox='0 0 28 13' aria-hidden='true'>" +
                            (section.reversed
                              ? "<rect x='19' y='2.5' width='8' height='8' rx='2'/>" +
                                "<path d='M17 6.5 L11.5 6.5 M14 3.5 L11 6.5 L14 9.5'/>"
                              : "<rect x='1' y='2.5' width='8' height='8' rx='2'/>" +
                                "<path d='M11 6.5 L16.5 6.5 M14 3.5 L17 6.5 L14 9.5'/>") +
                            "</svg> Reverse"});
}

function notes(run, section, look, picking) {
  var said = [];
  var memo = look && standingIn(run, section);
  if (memo && !picking) {
    said.push(look.name + ", replacing " + memo.look + ", which mono lights cannot play. " +
              "Rejoin to restore " + memo.look + ".");
  }
  var under = look ? null : stretchUnder(run, section);
  if (under) said.push(under.tip + " Choose a look to give this scene its own.");
  return said.map(function (words) { return h("p", {}, words); });
}

function colourPicker(run) {
  var section = run.sections[run.picked];
  function live() { return run.sections[run.picked]; }
  var offered = swatchesFor(run, section);
  var chosenHex = (section.colour || "#ffffff").replace("#", "").toLowerCase();
  var chosenWord = offered.filter(function (name) { return hexOf(WORDS[name]) === chosenHex; })[0] || null;
  var custom = !!section.custom || !chosenWord;
  var remembered = run.id + ":" + section.from;
  if (custom) {
    customColours[remembered] = {colour: section.colour || "#ffffff",
                                 level: section.level === undefined ? 1 : section.level};
  }
  var kept = customColours[remembered];
  return h("fieldset", {},
    h("legend", {class: "hidden"}, "Colour"),
    section.look === BLINK ? blinkChips(run) : null,
    swatchRow({label: "Colour", names: offered, chosen: chosenWord, custom: custom,
               picked: kept ? atBrightness(kept.colour, kept.level) : null,
               customTitle: "any hue and saturation, with its own brightness",
               onSwatch: function (name) {
                 live().colour = "#" + hexOf(WORDS[name]);
                 live().custom = false;
                 draw();
               },
               onCustom: function () {
                 live().custom = true;
                 if (kept) {
                   live().colour = kept.colour;
                   live().level = kept.level;
                 }
                 draw();
               }}),
    custom ? customField(live) : null);
}

function blinkChips(run) {
  var section = run.sections[run.picked];
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

  function drop(at) {
    var mine = live();
    mine.blinks.colours.splice(at, 1);
    var left = mine.blinks.colours;
    mine.blinks.at = Math.min(mine.blinks.at, left.length - 1);
    mine.colour = left[mine.blinks.at];
    mine.custom = !blinkNamed(mine.colour);
    if (left.length === 1) mine.blinks = undefined;
    draw();
  }

  function another() {
    var mine = live();
    if (!mine.blinks) mine.blinks = {colours: [mine.colour], at: 0};
    var colours = mine.blinks.colours;
    colours.push(colours[colours.length - 1]);
    choose(colours.length - 1);
  }

  var several = blinks.colours.length > 1;
  return h("div", {},
    h("span", {}, several ? "Blinks through" : "Blinks in"),
    h("ol", {}, blinks.colours.map(function (hex, at) {
      var named = blinkNamed(hex) || hex;
      return h("li", {},
        h("button", {type: "button", "aria-pressed": at === blinks.at ? "true" : "false",
                     style: {"--chip": hex},
                     title: (at === blinks.at ? "the colour being edited below, " : "change ") + named,
                     onclick: function () { choose(at); }}),
        several ? h("button", {type: "button", title: "stop blinking in " + named,
                               onclick: function () { drop(at); }}, "\u00d7") : null);
    })),
    h("button", {type: "button", title: "blink through several colours, one per blink",
                 onclick: another}, "+ another colour"));
}

function customField(live) {
  var section = live();
  var parts = takeApart(hexRgb(section.colour || "#ffffff"));
  var shown = atBrightness(section.colour || "#ffffff", section.level);
  return colourField({
    at: {hue: parts.hue, sat: parts.sat, colour: rgbInk(fieldColour(parts.hue, parts.sat)), preview: shown},
    hex: shown,
    hexTitle: "the colour as written, at its brightness. Paste a colour in to set the hue, " +
              "saturation and brightness below",
    previewTitle: "The colour as written, at its brightness",
    pick: function (hue, sat) {
      var rgb = fieldColour(hue, sat);
      live().colour = "#" + hexOf(rgb);
      live().custom = true;
      renderPreview();
      var written = atBrightness(live().colour, live().level);
      return {colour: rgbInk(rgb), preview: written, hex: written};
    },
    typed: function (said) {
      if (!/^[0-9a-f]{6}$/.test(said)) return null;
      var typedRgb = hexRgb("#" + said);
      var got = takeApart(typedRgb);
      var rgb = fieldColour(got.hue, got.sat);
      live().colour = "#" + hexOf(rgb);
      live().level = Math.max(FAINTEST, Math.max.apply(null, typedRgb) / 255);
      live().custom = true;
      renderPreview();
      return {hue: got.hue, sat: got.sat, colour: rgbInk(rgb), preview: "#" + said};
    },
    done: function () { draw(); }
  });
}

function sliderRows(run, section, look, where) {
  var rows = [{slider: "level", label: "Brightness", min: FAINTEST, max: 1, step: 0.01,
               value: section.level === undefined ? 1 : section.level}];
  if (look.solid) return rows;
  var first = run.lamps[section.from];
  var coloured = takesColour(look) && !!first && first.colour;
  var mono = !!first && !first.colour;
  var toneless = look.mood === "Colour" || (mono && look.mood === "Palette");
  var signal = SIGNAL_TIMINGS[look.name];
  if (!signal) rows.push({slider: "pace", label: "Speed", min: 0, max: 1, step: 0.01, value: section.pace});
  if (!((coloured || mono) && toneless)) {
    var count = typeof look.detents === "function" ? look.detents(targetFor(run, section)) : look.detents;
    rows.push({slider: "mood", label: look.mood, min: 0, max: 1, step: count >= 2 ? 1 / (count - 1) : 0.01,
               value: section.mood, detents: count >= 2 && count <= MOST_DETENT_TICKS ? count : 0});
  }
  (signal || []).forEach(function (part) {
    rows.push({timing: part[0], label: part[1], min: part[3], max: part[4], step: 0.5,
               value: withSection(section, function () { return timingOf(look.name, part[0]); }),
               face: signalFace(look.name, part[0]), tint: SIGNAL_TINT[part[0]]});
  });
  rows.forEach(function (row) {
    row.focus = where + "-" + (row.timing ? "timing-" + row.timing : row.slider);
  });
  return rows;
}

function sliders(run, section, look, where) {
  function live() { return run.sections[run.picked]; }
  var rows = sliderRows(run, section, look, where);
  var widest = 3;
  var built = rows.map(function (row) {
    var figure = figureFor(run, section, look, row, live);
    if (figure.chars) widest = Math.max(widest, figure.chars);
    var range = h("input", {type: "range", id: row.focus, min: row.min, max: row.max, step: row.step,
                            value: row.value, "data-focus": row.focus,
                            list: row.detents ? row.focus + "-detents" : null,
                            style: {"accent-color": row.tint || null},
                            title: row.timing ? "seconds, " + row.label.toLowerCase() : null,
                            oninput: function () {
                              moved(run, look, row, Number(range.value));
                              figure.follow();
                            },
                            onchange: function () { draw(); }});
    return [label(row, look), range, figure.cells,
            row.detents ? detentList(row) : null];
  });
  var boxes = built.map(function (cells) { return cells[2][0]; })
    .filter(function (cell) { return cell && cell.tagName === "INPUT"; });
  boxes.forEach(function (box) { box.style.width = (Math.max(widest, box.value.length) + 0.5) + "ch"; });
  return h("div", {role: "group", "aria-label": "Settings", "data-figures": figuresOpen,
                   style: {"--rows": rows.length}},
    built,
    h("button", {type: "button", "aria-expanded": figuresOpen ? "true" : "false",
                 "aria-label": figuresOpen ? "hide values" : "show values",
                 onclick: function () {
                   figuresOpen = !figuresOpen;
                   keepFigures();
                   draw();
                 }}, figuresOpen ? "\u203a" : "\u2039"));
}

function label(row, look) {
  if (row.face) return h("label", {for: row.focus, html: row.face}, h("span", {}, row.label));
  var drawn = SETTING_ICONS[row.label];
  return h("label", {for: row.focus, title: SETTING_TITLES[row.label] || null},
    drawn ? h("svg:svg", {viewBox: "0 0 16 16", width: 14, height: 14, fill: "none", stroke: "currentColor",
                          "stroke-width": 1.4, "stroke-linecap": "round", "stroke-linejoin": "round",
                          "aria-hidden": "true", html: drawn}) : null,
    row.label);
}

function detentList(row) {
  var stops = [];
  for (var at = 0; at < row.detents; at++) stops.push(h("option", {value: at / (row.detents - 1)}));
  return h("datalist", {id: row.focus + "-detents"}, stops);
}

function moved(run, look, row, value) {
  var mine = run.sections[run.picked];
  var slider = row.timing || row.slider;
  if (mine.exact && mine.exact[slider]) {
    mine.exact = Object.assign({}, mine.exact);
    delete mine.exact[slider];
  }
  if (row.timing) {
    mine.timings = Object.assign({}, mine.timings);
    mine.timings[row.timing] = value;
  } else {
    mine[row.slider] = value;
  }
  renderPreview();
  var cell = stretchCells(run)[run.picked];
  var band = cell && cell.querySelector(":scope > button > i");
  if (band && look) band.style.setProperty("--wash", washFor(run, mine, look));
}

function figureFor(run, section, look, row, live) {
  function typedBox(said, unit, title, take) {
    var box = h("input", {type: "text", inputMode: "decimal", value: said, title: title,
                          onchange: function () {
                            var typed = parseFloat(box.value.replace(",", "."));
                            if (!(typed > 0)) {
                              box.value = said;
                              return;
                            }
                            take(typed);
                            draw();
                          }});
    return [box, h("span", {}, unit)];
  }
  var none = {cells: [h("span"), h("span")], chars: 0, follow: function () {}};

  if (row.timing) {
    var cells = typedBox(figureSaid(row.value), "s", "seconds, typed exactly, beyond the slider's range if needed",
                         function (typed) {
                           var mine = live();
                           mine.timings = Object.assign({}, mine.timings);
                           mine.timings[row.timing] = Math.round(typed * 100) / 100;
                         });
    return {cells: cells, chars: Math.max(String(row.min).length, String(row.max).length) + 2,
            follow: function () { cells[0].value = figureSaid(Number(document.getElementById(row.focus).value)); }};
  }
  if (row.slider === "level") {
    var level = typedBox(String(Math.round(row.value * 100)), "%", "brightness, typed as a percentage",
                         function (typed) { live().level = Math.max(0.01, Math.min(1, typed / 100)); });
    return {cells: level, chars: 3,
            follow: function () { level[0].value = String(Math.round(live().level * 100)); }};
  }
  if (row.slider === "mood" && look.mood === "Palette") {
    var chips = h("output", {});
    paintPalette(chips, sectionLines(run, section, look));
    return {cells: [chips, null], chars: 0,
            follow: function () { paintPalette(chips, sectionLines(run, live(), look)); }};
  }
  var key = figureKey(run, section, look, row.slider);
  if (!key) return none;
  var way = figureWay(key, look);
  var widest = 3;
  [0, 0.5, 1].forEach(function (place) {
    var reach = figureSaid(way.show(settingIn(linesAt(run, section, look, row.slider, place), key)));
    widest = Math.max(widest, reach.length);
  });
  var typedHere = section.exact && section.exact[row.slider];
  var value = typedHere ? typedHere.value : settingIn(sectionLines(run, section, look), key);
  var figure = typedBox(figureSaid(way.show(value)), way.unit,
                        "the file's " + key + ", typed exactly, beyond the slider's range if needed",
                        function (typed) {
                          var wanted = way.take(typed);
                          var mine = live();
                          var found = placeFor(run, mine, look, row.slider, key, wanted);
                          mine[row.slider] = found.place;
                          mine.exact = Object.assign({}, mine.exact);
                          if (found.off > 1e-6) {
                            mine.exact[row.slider] = {key: key, value: Math.round(wanted * 1000) / 1000};
                          } else {
                            delete mine.exact[row.slider];
                          }
                        });
  return {cells: figure, chars: widest,
          follow: function () {
            figure[0].value = figureSaid(way.show(settingIn(sectionLines(run, live(), look), key)));
          }};
}

function paintPalette(chips, lines) {
  replace(chips, (lines.join(" ").match(/colour=[^\s:]+/g) || []).map(function (said) {
    return h("i", {title: said.slice(7), style: {background: inkOf(said.slice(7))}});
  }));
}

function signalFace(name, key) {
  var lit = SIGNAL_STATES[name][key];
  var blink = "<animate attributeName='opacity' values='1;.2' dur='1s' calcMode='discrete' " +
              "repeatCount='indefinite'/>";
  function lamp(state, ink) { return state ? ink : SIGNAL_INK.dark; }
  function flashing(state) { return state === "f" ? blink : ""; }
  var head = [SIGNAL_INK.red, SIGNAL_INK.amber, SIGNAL_INK.green].map(function (ink, at) {
    return "<circle cx='6' cy='" + (4.5 + at * 6.5) + "' r='2.6' fill='" + lamp(lit[at], ink) + "'>" +
           flashing(lit[at]) + "</circle>";
  }).join("");
  var wide = 12;
  var figures = "";
  if (lit.length > 3) {
    wide = 22;
    var stand = lamp(lit[3], SIGNAL_INK.red), walk = lamp(lit[4], SIGNAL_INK.green);
    figures = "<rect x='12.5' y='1' width='9' height='22' rx='2' fill='#1c1f22'/>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + stand + "'>" + flashing(lit[3]) +
      "<circle cx='17' cy='3.6' r='1.1' fill='" + stand + "' stroke='none'/>" +
      "<path d='M17 5.2 V8.6 M15.6 6.4 H18.4 M16.3 8.6 V11 M17.7 8.6 V11'/></g>" +
      "<g fill='none' stroke-width='1.3' stroke-linecap='round' stroke='" + walk + "'>" + flashing(lit[4]) +
      "<circle cx='17.4' cy='13.6' r='1.1' fill='" + walk + "' stroke='none'/>" +
      "<path d='M17.2 15.2 L16.8 18.3 M15.6 16.8 L18.6 16 M16.8 18.3 L15.4 21 M16.8 18.3 " +
      "L18.6 20.8'/></g>";
  }
  return "<svg viewBox='0 0 " + wide + " 24' width='" + wide * 0.9 +
         "' height='21.6' aria-hidden='true'><rect x='1' y='0' width='10' height='24' rx='3' " +
         "fill='#1c1f22'/>" + head + figures + "</svg>";
}

function parkLooks() {
  var looks = document.getElementById("looks");
  var editor = looks && looks.closest(".editor");
  if (editor) editor.closest(".panel").appendChild(looks);
}

function seatLooks() {
  var looks = document.getElementById("looks");
  if (!looks || looks.hidden || !document.body.hasAttribute("data-looks-below")) return;
  var editor = document.querySelector("#" + chosenTab + " .editor[data-picking]");
  if (editor) editor.appendChild(looks);
}

function notchEditors() {
  document.querySelectorAll(".panel .editor").forEach(function (editor) {
    var cell = editor.closest(".panel").querySelector(".stretches li[aria-current] > button:not([data-says])");
    var outer = editor.getBoundingClientRect();
    var tab = cell && cell.getBoundingClientRect();
    editor.toggleAttribute("data-notch-start", !!tab && tab.left - outer.left < 12);
    editor.toggleAttribute("data-notch-end", !!tab && outer.right - tab.right < 12);
  });
}

drawSteps.before.push(parkLooks);
drawSteps.after.push(function () {
  seatLooks();
  notchEditors();
});
window.addEventListener("resize", notchEditors);
