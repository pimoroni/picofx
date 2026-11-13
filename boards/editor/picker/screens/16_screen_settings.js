import {banner} from "../00_banner.js";
import {h} from "../00_dom.js";
import {draw, drawSteps} from "../00_draw.js";
import {SWATCHES, WORDS, fieldColour, hexOf, hexRgb, rgbInk, takeApart} from "../01_colours.js";
import {spoken} from "../03_lines.js";
import {bodyParts, namesOf, state} from "../04_scenes.js";
import {driveTrouble, nameShown} from "../18_drive.js";
import {copyTile} from "../22_program.js";
import {isExampleMedia, mediaHome, scanMedia} from "../26_drive_files.js";
import {copyToOwn, folderAt} from "../26_drive_programs.js";
import {colourField, swatchRow} from "../30_colour_picker.js";
import {
  SCREENS, freshLook, kindOf, mediaNamed, screenButton, screenUnder, screensPaired
} from "./12_screens.js";
import {
  canvasPixels, mediaArt, pairCanvas, pictureOffset, styleChoices, styleWord
} from "./13_screen_art.js";
import {
  ANCHOR_NAMES, firstAsLastAllowed, groundHex, groundParts, groundSaid, holdAllowed, pictureSaid,
  placementSaid, playbackSaid, secondHoldAllowed
} from "./14_screen_text.js";

SCREENS.forEach(function (letter) { state.screens[letter].look = freshLook(); });

var lookHomes = {};
SCREENS.forEach(function (letter) { lookHomes["screen" + letter] = state.screens[letter].look; });

bodyParts.push({
  capture: function (body) {
    SCREENS.forEach(function (letter) {
      body.screens[letter].look = Object.assign({}, state.screens[letter].look);
    });
  },
  apply: function (body) {
    SCREENS.forEach(function (letter) {
      var home = lookHomes["screen" + letter];
      if (body.screens && body.screens[letter].look) Object.assign(home, body.screens[letter].look);
      state.screens[letter].look = home;
    });
  }
});

var foldOpen = {};
var FOLDS_START_OPEN = {Orientation: true, Placement: false, Background: false, Playback: true,
                        Drawing: true};

function settingFold(key, name, says, ...contents) {
  var id = key + "|" + name;
  var fold = h("details", {open: id in foldOpen ? foldOpen[id] : FOLDS_START_OPEN[name],
                           ontoggle: function () { foldOpen[id] = fold.open; }},
    h("summary", {}, name, h("small", {}, says)),
    contents);
  return fold;
}

function rowName(words, title) {
  return h("span", {"aria-hidden": "true", title: title}, words);
}

function choiceGroup(name, options, chosen, choose, title) {
  return h("span", {role: "group", "aria-label": name, title: title},
    options.map(function (option) {
      return h("button", {type: "button", "aria-pressed": String(option.value === chosen),
                          disabled: !!option.refused, title: option.title,
                          onclick: function () {
                            choose(option.value);
                            draw();
                          }}, option.label);
    }));
}

function numberField(value, placeholder, change, step) {
  var field = h("input", {type: "number", step: step || 1, value: value, placeholder: placeholder,
                          onchange: function () {
                            change(field.value);
                            draw();
                          }});
  return field;
}

function toggleButton(icon, words, on, flip, title, refused) {
  return h("button", {type: "button", "aria-pressed": String(!!on && !refused),
                      disabled: !!refused, title: title,
                      onclick: function () {
                        flip(!on);
                        draw();
                      }},
    h("span", {"aria-hidden": "true"}, icon), " " + words);
}

function percentSetting(words, value, change, title, disabled) {
  var figure = h("output", {}, Math.round(value * 100) + "%");
  var slider = h("input", {type: "range", min: 0, max: 100, step: 5, value: Math.round(value * 100),
                           disabled: disabled,
                           oninput: function () { figure.value = slider.value + "%"; },
                           onchange: function () {
                             change(Number(slider.value) / 100);
                             draw();
                           }});
  return h("label", {title: title}, words, slider, figure);
}

export function backlightSetting(value, change, words, title, frozen) {
  var setting = percentSetting(words, value, change,
                               frozen ? "Set on the Always on tab" : title, frozen);
  setting.className = "backlight";
  return setting;
}

function rotationMark(turn) {
  return h("svg:svg", {width: 12, height: 12, viewBox: "0 0 12 12", "aria-hidden": "true"},
    h("svg:g", {transform: "rotate(" + turn + " 6 6)"},
      h("svg:rect", {x: 3, y: 1, width: 6, height: 10, rx: 1, fill: "none", stroke: "currentColor",
                     "stroke-width": 1.3}),
      h("svg:rect", {x: 4.5, y: 8.8, width: 3, height: 1.4, fill: "currentColor"})));
}

function doubleMark() {
  return h("svg:svg", {width: 12, height: 12, viewBox: "0 0 12 12", "aria-hidden": "true"},
    [[1, 1], [6.5, 1], [1, 6.5], [6.5, 6.5]].map(function (at) {
      return h("svg:rect", {x: at[0], y: at[1], width: 4.5, height: 4.5, fill: "currentColor"});
    }));
}

function setTurn(held, turn) {
  held.turn = turn;
  if (held.shows && held.shows !== "keep") held.turns[held.shows] = turn;
}

function orientationFold(key, held) {
  var look = held.look;
  var turn = Number(held.turn || 0);
  return settingFold(key, "Orientation",
                     turn + "\u00b0, " + (look.mirror ? "mirrored" : "not mirrored"),
    h("p", {}, rowName("Rotation"),
      choiceGroup("Rotation", [0, 90, 180, 270].map(function (value) {
        return {value: value, label: [rotationMark(value), value + "\u00b0"]};
      }), turn, function (value) { setTurn(held, value); }, "Screen rotation"),
      toggleButton("\u21c6", "Mirror", look.mirror, function (on) { look.mirror = on; },
                   "Flip the picture left to right")));
}

var TILINGS = [{value: "off", label: "Off"}, {value: "repeat", label: "Repeat"},
               {value: "mirror", label: "Mirror"}];

function placementFold(key, held, size) {
  var look = held.look;
  var where = pictureOffset(look, held.shows, size, held.turn);
  function typed(axis) {
    return function (value) {
      var other = axis === "x" ? "y" : "x";
      look[other] = where[other];
      look[axis] = value;
      look.anchor = null;
    };
  }
  function tiling(down) {
    var side = down ? "tileDown" : "tile";
    return choiceGroup(down ? "Tiling down" : "Tiling across", TILINGS, look[side] || "off",
                       function (value) { look[side] = value; },
                       "Fill the screen " + (down ? "top to bottom" : "left to right") +
                       " with copies. Mirror flips every other copy to join up the edges");
  }
  var anchor = h("span", {class: "anchor", role: "group", "aria-label": "Position",
                          title: "Picture position, calculated from its size and the panel's"},
    ANCHOR_NAMES.map(function (name, at) {
      return h("button", {type: "button", "aria-label": name, title: name,
                          "aria-pressed": String(look.anchor === at),
                          onclick: function () {
                            look.anchor = at;
                            look.x = "";
                            look.y = "";
                            draw();
                          }});
    }));
  return settingFold(key, "Placement", placementSaid(look, where),
    h("div", {class: "columns"},
      h("p", {}, anchor,
        h("label", {title: "Pixels from the left. Leave empty to centre"},
          "x", numberField(where.x, "centre", typed("x"))),
        h("label", {title: "Pixels from the top. Leave empty to centre"},
          "y", numberField(where.y, "centre", typed("y"))),
        toggleButton(doubleMark(), "Pixel double", look.double, function (on) { look.double = on; },
                     "Draw each pixel at double size")),
      h("p", {}, rowName("Tiling"), rowName("\u2194", "Across"), tiling(false),
        rowName("\u2195", "Down"), tiling(true))));
}

var groundCustom = {};

function backgroundFold(key, held) {
  var look = held.look;
  var names = ["black"].concat(SWATCHES);
  var parts = groundParts(look.bg);
  var chosen = names.filter(function (name) {
    return hexOf(WORDS[name]) === hexOf(parts.full);
  })[0];
  var open = groundCustom[key] || !chosen;
  if (open) look.customBg = look.bg;
  var swatches = swatchRow({label: "Background colour", names: names, chosen: chosen, custom: open,
                            picked: look.customBg || null,
                            customTitle: "custom: pick a colour or type a hex code",
                            onSwatch: function (name) {
                              look.bg = groundHex(WORDS[name], parts.value);
                              groundCustom[key] = false;
                              draw();
                            },
                            onCustom: function () {
                              groundCustom[key] = true;
                              if (look.customBg) look.bg = look.customBg;
                              draw();
                            }});
  return settingFold(key, "Background", groundSaid(look.bg),
    swatches,
    open ? customGround(look, parts) : null,
    h("p", {}, percentSetting("brightness", parts.value, function (value) {
      look.bg = groundHex(parts.full, value);
    }, chosen === "black" ? "Brightness does not apply to black"
                          : "Background brightness, separate from the backlight",
       chosen === "black")));
}

function customGround(look, parts) {
  var place = takeApart(parts.full);
  return colourField({
    at: {hue: place.hue, sat: place.sat, colour: rgbInk(parts.full), preview: look.bg},
    hex: look.bg,
    hexTitle: "Use the background colour exactly as typed, including dark colours",
    previewTitle: "How the background will look",
    pick: function (hue, sat) {
      look.bg = groundHex(fieldColour(hue, sat), parts.value);
      return {colour: look.bg, preview: look.bg, hex: look.bg};
    },
    typed: function (said) {
      if (!/^[0-9a-f]{6}$/.test(said)) return null;
      look.bg = "#" + said;
      var got = takeApart(hexRgb(look.bg));
      return {hue: got.hue, sat: got.sat, colour: look.bg, preview: look.bg};
    },
    done: function () { draw(); }
  });
}

function paceChoices(look, saved, savedRefused, title) {
  return choiceGroup("Speed", [{value: "fps", label: "fps"}, {value: "interval", label: "interval"},
                               {value: "saved", label: saved, refused: savedRefused}],
                     look.pace, function (value) {
                       var flips = (value === "fps" && look.pace === "interval") ||
                                   (value === "interval" && look.pace === "fps");
                       if (flips) look.every = Math.round(100 / look.every) / 100;
                       look.pace = value;
                     }, title);
}

function speedRow(look, choices) {
  return h("p", {}, rowName("Speed"), choices,
    look.pace === "saved" ? null : h("label", {},
      numberField(look.every, "", function (value) {
        if (Number(value) > 0) look.every = Number(value);
      }, look.pace === "interval" ? 0.05 : 1),
      look.pace === "fps" ? "frames per second" : "seconds per frame"));
}

function drawingFold(key, held) {
  var look = held.look;
  var media = held.shows ? mediaNamed(held.shows) : null;
  var drawing = media && media.drawing;
  var chosen = drawing ? styleChoices(drawing, look.style) : [];
  var offered = [];
  var styleRows = (drawing ? drawing.styles : []).map(function (line, at) {
    if (line.length < 2) return null;
    offered.push(chosen[at]);
    return choiceGroup("Style", line.map(function (style) { return {value: style, label: style}; }),
                       chosen[at], function (value) {
                         var picked = styleChoices(drawing, look.style);
                         picked[at] = value;
                         look.style = styleWord(drawing, picked);
                       }, "The style this drawing is drawn in");
  }).filter(Boolean);
  var said = offered.concat([
    look.pace === "fps" ? look.every + " fps"
    : look.pace === "interval" ? "frame every " + look.every + " s" : "every frame",
    look.canvas === "set" ? look.canvasW + " \u00d7 " + look.canvasH
    : look.canvas === "half" ? "half size" : "whole screen"]);
  return settingFold(key, "Drawing", said.join(", "),
    madeForLine(held),
    halfSizeLine(),
    styleRows.length ? h("p", {}, rowName("Style"), h("span", {}, styleRows)) : null,
    h("div", {class: "columns"},
      h("div", {}, speedRow(look, paceChoices(look, "every frame", false,
        "Frames per second, seconds per frame, or as fast as the screen allows"))),
      h("div", {},
        h("p", {}, rowName("Canvas"), choiceGroup("Canvas", [
          {value: "whole", label: "Whole screen", title: "As big as the screen"},
          {value: "half", label: "Half size",
           title: "Half the screen's width and height, using a quarter of the memory. With " +
                  "Pixel double it fills the screen"},
          {value: "set", label: "Set size",
           title: "A custom size in pixels, positioned like a small picture"}
        ], look.canvas || "whole", function (value) { look.canvas = value; })),
        look.canvas === "set" ? h("p", {},
          h("label", {}, "Width", numberField(look.canvasW, "", function (value) {
            if (Number(value) > 0) look.canvasW = Math.round(Number(value));
          }), "pixels"),
          h("label", {}, "Height", numberField(look.canvasH, "", function (value) {
            if (Number(value) > 0) look.canvasH = Math.round(Number(value));
          }), "pixels")) : null)));
}

function madeForLine(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || !media.drawing) return null;
  var turns = drawingTurns(media.drawing);
  var turnWrong = !!turns && turns.length > 1 && turns.indexOf(Number(held.turn || 0)) < 0;
  var doubled = drawingDoubled(media.drawing);
  var doubleWrong = doubled === true ? !(held.look.double && held.look.canvas === "half")
                  : doubled === false ? held.look.double || held.look.canvas === "half" : false;
  if (!turnWrong && !doubleWrong) return null;
  var said = [];
  if (turnWrong) said.push(turns.map(function (turn) { return turn + "\u00b0"; }).join(" or "));
  if (doubleWrong) said.push(doubled ? "pixel doubling at half size" : "full resolution");
  return h("p", {}, h("strong", {}, "Made for " + said.join(", ")),
    h("button", {type: "button", title: "Set the rotation and pixel doubling this drawing is made for",
                 onclick: function () {
                   if (turnWrong) setTurn(held, turns[0]);
                   if (doubleWrong) {
                     held.look.double = doubled;
                     held.look.canvas = doubled ? "half" : "whole";
                   }
                   draw();
                 }}, "Apply"));
}

function halfSizeLine() {
  if (SCREENS.length < 2 || state.hub.on || screensPaired()) return null;
  var both = SCREENS.slice(0, 2).map(function (letter) { return state.screens[letter]; });
  var drawings = both.every(function (held) {
    var media = held.there && held.shows ? mediaNamed(held.shows) : null;
    return !!media && !!media.drawing && drawingDoubled(media.drawing) !== false;
  });
  var larger = both.some(function (held) { return !(held.look.double && held.look.canvas === "half"); });
  if (!drawings || !larger) return null;
  return h("p", {title: "Two drawings at full size do not both fit the board's fast memory."},
    h("strong", {}, "Two drawings run faster at half size or paired"),
    h("button", {type: "button", title: "Set both drawings to pixel doubling at half size",
                 onclick: function () {
                   both.forEach(function (held) {
                     held.look.double = true;
                     held.look.canvas = "half";
                   });
                   draw();
                 }}, "Apply"));
}

export function drawingCopyTile(name) {
  return copyTile(isExampleMedia(name), nameShown(name), "drawings", async function () {
    try {
      var copy = await copyDrawing(name);
      var held = SCREENS.map(function (letter) { return state.screens[letter]; });
      if (state.places) held = held.concat(Object.keys(state.places).map(function (place) {
        return state.places[place];
      }));
      held.forEach(function (one) {
        if (one.shows !== name) return;
        if (one.turns && name in one.turns) one.turns[copy] = one.turns[name];
        one.shows = copy;
        if ("lastShows" in one) one.lastShows = copy;
      });
      banner("Copied to drawings/" + copy + " on the FX drive. Open it in Thonny or another " +
             "editor to change it.");
    } catch (e) {
      banner("Could not copy " + nameShown(name) + ". " + await driveTrouble(e, name), true);
    }
    draw();
  });
}

export async function copyDrawing(name) {
  var dir = state.dirHandle;
  var example = isExampleMedia(name);
  var from = example ? await folderAt(dir, name.split("/").slice(0, -1)) : mediaHome[name] || dir;
  var into = await dir.getDirectoryHandle("drawings", {create: true});
  var styled = Object.keys((mediaNamed(name) || {}).styleThumbs || {});
  var copy = await copyToOwn(from, nameShown(name), into, !example, [".png"].concat(
    styled.map(function (style) { return "-" + style + ".png"; })));
  for (var tries = 0; tries < 20 && !mediaNamed(copy); tries++) {
    await scanMedia(dir);
    if (!mediaNamed(copy)) await new Promise(function (settle) { setTimeout(settle, 100); });
  }
  return copy;
}

function playbackFold(key, held, media) {
  var look = held.look;
  var folder = media.kind === "folder";
  var holding = holdAllowed(held, look);
  var holdingBoth = secondHoldAllowed(held, look);
  var atEnd = numberField(held.hold, "0", function (value) {
    held.hold = value && Number(value) > 0 ? value : "";
  }, 0.5);
  atEnd.disabled = !holding;
  return settingFold(key, "Playback", playbackSaid(held, look),
    h("div", {class: "columns"},
      h("div", {}, speedRow(look, paceChoices(look, folder ? "from names" : "from file",
        folder && !media.named,
        "Frames per second, seconds per frame, or the delays " +
        (folder ? "written in each picture's file name" : "saved in the file")))),
      h("div", {},
        h("p", {},
          toggleButton("\u21bb", "Loop", look.loop, function (on) { look.loop = on; },
                       "Start again after the last frame"),
          toggleButton("\u21c4", "Ping pong", held.pingpong, function (on) { held.pingpong = on; },
                       "Play forwards then backwards"),
          toggleButton("\u21e4", "First frame as last", look.whole, function (on) { look.whole = on; },
                       firstAsLastAllowed(held, look) ? "Repeat the first frame at the end"
                                                      : "Needs Ping pong, or Loop off",
                       !firstAsLastAllowed(held, look))),
        h("p", {"data-refused": !holding,
                title: holding ? "Pause at each end, in seconds" : "Needs Loop or Ping pong"},
          h("label", {}, "Hold", atEnd, holdingBoth ? "seconds at the end," : "seconds"),
          holdingBoth ? h("label", {}, numberField(look.holdBack, "same", function (value) {
            look.holdBack = value && Number(value) >= 0 ? value : "";
          }, 0.5), "seconds at the start") : null))));
}

export function showingLine(held, letter) {
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  if (!picture) {
    var press = "press " + screenButton(letter) + " under a picture below to show it here";
    var under = held.shows ? null : screenUnder(letter);
    var said = held.off ? ["off in this scene", "black, at the backlight set above"]
      : under && under.always ? [["showing ", under.always === "keep" ? "the line kept from the file"
                                                                      : h("b", {}, pictureSaid(under.always)),
                                  " from Always on"], press + " instead"]
      : under ? ["backlight off in this scene", "lit only in " + spoken(namesOf(under.off))]
      : [state.scenes.length ? "nothing chosen for this scene" : "nothing showing", press];
    return h("output", {"data-empty": true}, said[0], h("small", {}, said[1]));
  }
  var media = mediaNamed(picture);
  if (media && media.kind === "drawing") {
    var size = state.hub.on ? state.hub.sizes[letter] : state.screens[letter].size;
    var canvas = !state.hub.on && screensPaired()
               ? pairCanvas(SCREENS.map(function (one) { return state.screens[one]; }))
               : canvasPixels(held.look, size, held.turn);
    return h("output", {}, "drawing ", h("b", {}, nameShown(picture)),
             h("small", {}, "canvas, " + canvas[0] + " \u00d7 " + canvas[1]));
  }
  var art = mediaArt(picture);
  var kind = media ? {image: "picture", gif: "gif", folder: "slideshow"}[media.kind] : null;
  var about = [kind, art && art.w ? art.w + " \u00d7 " + art.h : null].filter(Boolean);
  return h("output", {}, "showing ", h("b", {}, pictureSaid(picture)),
           media ? null : " (not on the drive)",
           about.length ? h("small", {}, about.join(", ")) : null);
}

export function lookSettings(key, held, size, frozen, ink) {
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  var media = picture ? mediaNamed(picture) : null;
  var pairedSecond = key === "screen" + SCREENS[SCREENS.length - 1] && screensPaired();
  return h("fieldset", {class: "looksettings", disabled: !!frozen,
                        title: frozen ? "Set on the Always on tab" : null, style: {"--tint": ink}},
    orientationFold(key, held),
    picture ? [placementFold(key, held, size), backgroundFold(key, held)] : null,
    !picture || pairedSecond || !media ? null
    : media.kind === "drawing" ? drawingFold(key, held)
    : media.kind !== "image" ? playbackFold(key, held, media) : null);
}

export function chosenAfresh(held) {
  if (held.shows === held.lastShows) return;
  var wasDrawing = !!held.lastShows && kindOf(held.lastShows) === "drawing";
  if (!wasDrawing) held.pictureTurn = held.turn;
  paceForChosen(held);
  settingsForChosen(held);
  if (wasDrawing && held.shows && held.shows !== "keep" && kindOf(held.shows) !== "drawing") {
    held.turn = held.pictureTurn;
    held.look.double = false;
  }
  if (held.shows && held.turns[held.shows] !== undefined) held.turn = held.turns[held.shows];
  if (held.shows) held.turns[held.shows] = held.turn;
  held.lastShows = held.shows;
}

function paceForChosen(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || media.kind !== "folder") return;
  held.look.pace = media.named ? "saved" : "fps";
  held.look.every = 5;
}

function settingsForChosen(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || !media.drawing) return;
  var turns = drawingTurns(media.drawing);
  if (turns && held.turns[held.shows] === undefined) held.turn = turns[0];
  held.look.double = drawingDoubled(media.drawing) === true;
  held.look.canvas = held.look.double ? "half" : "whole";
  held.look.style = "";
}

function drawingTurns(drawing) {
  var rotation = drawing.defaults.Rotation;
  if (!rotation || rotation["default"] === undefined) return null;
  var turns = (rotation.choices || [rotation["default"]]).map(Number).filter(function (turn) {
    return [0, 90, 180, 270].indexOf(turn) >= 0;
  });
  return turns.length ? turns : null;
}

function drawingDoubled(drawing) {
  var doubled = drawing.defaults["Pixel double"];
  if (!doubled || (doubled["default"] !== "true" && doubled["default"] !== "false")) return null;
  return doubled["default"] === "true";
}

export function turnForChosen(letter) { chosenAfresh(state.screens[letter]); }

drawSteps.before.push(function () { SCREENS.forEach(turnForChosen); });
