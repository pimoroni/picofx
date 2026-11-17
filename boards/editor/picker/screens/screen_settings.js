import {banner} from "../banner.js";
import {screenHooks} from "../board.js";
import {SWATCHES, WORDS, fieldColour, hexOf, rgbInk, takeApart} from "../colours.js";
import {h, replace} from "../dom.js";
import {addStep, draw} from "../draw.js";
import {driveTrouble, nameShown} from "../drive.js";
import {isExampleMedia, mediaHome, scanMedia} from "../drive_files.js";
import {copyToOwn, folderAt} from "../drive_programs.js";
import {spoken} from "../lines.js";
import {toggle} from "../looks.js";
import {copyTile} from "../program.js";
import {BODY_ORDER, bodyParts, namesOf, state} from "../scenes.js";
import {
  canvasPixels, drawingInk, mediaArt, pairCanvas, panelPreview, pictureOffset, styleChoices,
  styleWord
} from "./screen_art.js";
import {
  ANCHOR_NAMES, BG_NAMES, firstAsLastAllowed, groundHex, groundParts, groundSaid, holdAllowed,
  placementSaid, playbackSaid, secondHoldAllowed
} from "./screen_text.js";
import {
  ASSET_ORDER, SCREENS, assetSteps, freshLook, kindOf, mediaNamed, pictureSaid, screenButton,
  screenParts, screenUnder, screensPaired
} from "./screens.js";

// ---- a screen's settings ------------------------------------------------------------------------
// The chosen screen's settings, its orientation, placement, background, drawing and playback,
// each kept in the scene.

// A picture newly chosen on a screen starts as chosenAfresh says. What the screen showed when
// last looked at says whether it is newly chosen, and a scene coming round brings its own turn
export function turnForChosen(letter) { chosenAfresh(state.screens[letter]); }
screenParts.turnForChosen = turnForChosen;

SCREENS.forEach(function (letter) { state.screens[letter].look = freshLook(); });
Object.keys(WORDS).forEach(function (name) { BG_NAMES["#" + hexOf(WORDS[name])] = name; });
screenHooks.panelPreview = panelPreview;

// ---- each scene keeps its screens' looks ------------------------------------------------------

// Each screen keeps one look object for good, a scene's values copied into it, so a control
// drawn before a scene is re-applied still changes the look that is written
var lookHomes = {};
SCREENS.forEach(function (letter) { lookHomes["screen" + letter] = state.screens[letter].look; });

addStep(bodyParts, BODY_ORDER, "screenSettings", {
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


// ---- the settings, drawn ----------------------------------------------------------------------
// Each section folds, saying its values beside its name while closed. Orientation and playback
// start open, placement and background folded, since a picture made for its screen needs neither

var foldOpen = {};
var FOLDS_START_OPEN = {Orientation: true, Placement: false, Background: false, Playback: true,
                        Drawing: true};

function foldSection(key, name, says, body) {
  var id = key + "|" + name;
  var fold = h("details", {
    className: "sfold", "data-section": name,
    open: foldOpen[id] !== undefined ? foldOpen[id] : FOLDS_START_OPEN[name],
    ontoggle: function () { foldOpen[id] = fold.open; }
  }, h("summary", {}, name, h("small", {className: "closedonly"}, says || null)), body);
  return fold;
}

function sline() {
  return h("div", {className: "sline"}, Array.from(arguments));
}

function named(words) {
  return h("span", {className: "snamed"}, words);
}

// One choice of several, as a row of buttons. options are [value, label html, refused]
function segment(options, chosen, choose, title) {
  return h("span", {className: "sseg", title: title || null}, options.map(function (option) {
    return h("button", {
      type: "button", "data-value": option[0], html: option[1],
      className: option[0] === chosen ? "on" : "", disabled: !!option[2],
      onclick: function () { choose(option[0]); draw(); }
    });
  }));
}

function numberBox(value, placeholder, change, step) {
  var box = h("input", {
    type: "number", step: step || 1, value: value, placeholder: placeholder,
    onchange: function () { change(box.value); draw(); }
  });
  return box;
}

function unit(words) {
  return h("span", {className: "sunit"}, words);
}

// How brightly a screen is lit, as a slider with its figure, named words=
function lightSlider(value, change, title, words) {
  var figure = h("span", {className: "lightfigure"}, Math.round(value * 100) + "%");
  var slider = h("input", {
    type: "range", min: 0, max: 100, step: 5, value: Math.round(value * 100),
    oninput: function () { figure.textContent = slider.value + "%"; },
    onchange: function () { change(Number(slider.value) / 100); draw(); }
  });
  return h("label", {className: "opt lightopt", title: title}, words, slider, figure);
}

// ---- orientation ----

// The module's driver chip is at its bottom edge, so the mark is there
function rotationMark(turn) {
  return "<svg width='12' height='12' viewBox='0 0 12 12' aria-hidden='true'><g transform='rotate(" +
         turn + " 6 6)'><rect x='3' y='1' width='6' height='10' rx='1' fill='none' " +
         "stroke='currentColor' stroke-width='1.3'/><rect x='4.5' y='8.8' width='3' height='1.4' " +
         "fill='currentColor'/></g></svg>";
}

// A turn goes with the picture showing, remembered for it on this screen, and can be set with
// none showing, for the next one put there
function setTurn(held, turn) {
  held.turn = turn;
  if (held.shows && held.shows !== "keep") held.turns[held.shows] = turn;
}

function orientationFold(key, held) {
  var look = held.look;
  var turn = Number(held.turn || 0);
  var rotation = segment([0, 90, 180, 270].map(function (value) {
    return [value, rotationMark(value) + value + "&deg;"];
  }), turn, function (value) { setTurn(held, value); }, "Screen rotation");
  rotation.classList.add("rotationseg");
  var mirror = toggle("&#8646;", "Mirror", look.mirror, function (on) { look.mirror = on; },
                      "Flip the picture left to right");
  return foldSection(key, "Orientation", turn + "\u00b0, " + (look.mirror ? "mirrored"
                                                                          : "not mirrored"),
                     sline(named("Rotation"), rotation, mirror));
}


// Pixel doubling as one pixel drawn as four
var DOUBLE_GLYPH = "<svg width='12' height='12' viewBox='0 0 12 12' aria-hidden='true'>" +
                   "<rect x='1' y='1' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='6.5' y='1' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='1' y='6.5' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='6.5' y='6.5' width='4.5' height='4.5' fill='currentColor'/></svg>";

function placementFold(key, held, size) {
  var look = held.look;
  var where = pictureOffset(look, held.shows, size, held.turn);
  var anchor = h("span", {
    className: "sanchor", title: "Picture position, calculated from its size and the panel's"
  }, ANCHOR_NAMES.map(function (name, at) {
    return h("button", {
      type: "button", className: look.anchor === at ? "on" : "", title: name,
      onclick: function () {
        look.anchor = at;
        look.x = "";
        look.y = "";
        draw();
      }
    });
  }));
  // Typing a figure places the picture by hand, the other side kept where it was
  function typed(axis) {
    return function (value) {
      var other = axis === "x" ? "y" : "x";
      look[other] = where[other];
      look[axis] = value;
      look.anchor = null;
    };
  }
  var x = numberBox(where.x, "centre", typed("x"));
  var y = numberBox(where.y, "centre", typed("y"));
  x.title = "Pixels from the left. Leave empty to centre";
  y.title = "Pixels from the top. Leave empty to centre";
  x.className = y.className = "sxy";
  // Tiling is set for each side, so a picture can be spread across and left alone down. Both
  // sides share one line, each named by its arrow, and the choices are in words
  function tiling(down) {
    var side = down ? "tileDown" : "tile";
    var seg = segment([["off", "Off"], ["repeat", "Repeat"], ["mirror", "Mirror"]],
                      look[side] || "off",
                      function (value) { look[side] = value; },
                      "Fill the screen " + (down ? "top to bottom" : "left to right") +
                      " with copies. Mirror flips every other copy to join up the edges");
    seg.classList.add(down ? "tiledown" : "tileacross");
    return seg;
  }
  var double = toggle(DOUBLE_GLYPH, "Pixel double", look.double,
                      function (on) { look.double = on; },
                      "Draw each pixel at double size");
  // Where it sits, then how it fills, in a line each or two halves where the section is wide
  var body = h("div", {className: "ssplit"},
               sline(anchor, named("x"), x, named("y"), y, double),
               sline(named("Tiling"), h("span", {className: "snamed", title: "Across"}, "\u2194"),
                     tiling(false), h("span", {className: "snamed", title: "Down"}, "\u2195"),
                     tiling(true)));
  return foldSection(key, "Placement", placementSaid(look, where), body);
}

// ---- background ----

// Which background pickers have their custom field open, by screen or position
var groundCustom = {};

// The colour round a picture, chosen from the looks' swatches in one row across the section.
// Black is first, since every screen starts there, and the custom ring is last with the chosen
// colour in its middle. Then comes a brightness of its own, apart from the backlight. A typed hex
// is taken as written, and its brightness is read from it
function backgroundFold(key, held) {
  var look = held.look;
  var names = ["black"].concat(SWATCHES);
  var parts = groundParts(look.bg);
  var chosen = names.filter(function (name) {
    return hexOf(WORDS[name]) === hexOf(parts.full);
  })[0];
  var open = groundCustom[key] || !chosen;
  // A colour that is no swatch's is the custom one, and the ring keeps showing it while a
  // swatch is chosen, so custom comes back to it
  if (open) look.customBg = look.bg;
  var row = h("div", {className: "sswatches"},
    names.map(function (name) {
      // Named under the swatch where the section is wide enough, as the looks' picker names
      // them. A colour keeps the brightness already set
      return h("button", {
        type: "button", className: !open && chosen === name ? "on" : "",
        style: {background: rgbInk(WORDS[name])}, title: name,
        onclick: function () {
          look.bg = groundHex(WORDS[name], parts.value);
          groundCustom[key] = false;
          draw();
        }
      }, h("b", {}, name));
    }),
    h("button", {
      type: "button", className: "custom" + (open ? " on" : ""),
      style: {"--picked": look.customBg || null},
      title: "custom: pick a colour or type a hex code",
      onclick: function () {
        groundCustom[key] = true;
        if (look.customBg) look.bg = look.customBg;
        draw();
      }
    }, h("b", {}, "custom")));

  // How bright the background is, black having none to set
  var figure = h("span", {className: "lightfigure"}, Math.round(parts.value * 100) + "%");
  var slider = h("input", {
    type: "range", min: 0, max: 100, step: 5, value: Math.round(parts.value * 100),
    disabled: chosen === "black",
    oninput: function () { figure.textContent = slider.value + "%"; },
    onchange: function () {
      look.bg = groundHex(parts.full, Number(slider.value) / 100);
      draw();
    }
  });
  var bright = h("label", {
    className: "opt groundbright",
    title: chosen === "black" ? "Brightness does not apply to black"
                              : "Background brightness, separate from the backlight"
  }, "brightness", slider, figure);
  return foldSection(key, "Background", groundSaid(look.bg),
                     h("div", {className: "groundpick"}, row,
                       open ? customGround(look, parts) : null, bright));
}

// The custom colour's field to pick a hue and saturation from, with its hex to type beside the
// colour itself at its brightness, as large as the room beside the field
function customGround(look, parts) {
  var place = takeApart(parts.full);
  var at = h("div", {className: "at", style: {left: place.hue / 360 * 100 + "%",
                                              top: (1 - place.sat) * 100 + "%",
                                              background: rgbInk(parts.full)}});
  var hex = h("input", {
    type: "text", maxLength: 7, value: look.bg,
    title: "Use the background colour exactly as typed, including dark colours",
    onchange: function () {
      var said = hex.value.replace("#", "").trim().toLowerCase();
      if (/^[0-9a-f]{6}$/.test(said)) look.bg = "#" + said;
      draw();
    }
  });
  hex.spellcheck = false;
  var preview = h("div", {className: "scustompreview", style: {background: look.bg},
                          title: "How the background will look"});
  var field = h("div", {
    className: "field",
    onpointerdown: function (event) {
      field.setPointerCapture(event.pointerId);
      pointingAt(event);
    },
    onpointermove: function (event) {
      if (field.hasPointerCapture(event.pointerId)) pointingAt(event);
    },
    onpointerup: function () { draw(); }
  }, at);
  function pointingAt(event) {
    var bounds = field.getBoundingClientRect();
    var across = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    var down = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
    look.bg = groundHex(fieldColour(across * 360, 1 - down), parts.value);
    at.style.left = (across * 100) + "%";
    at.style.top = (down * 100) + "%";
    at.style.background = look.bg;
    hex.value = look.bg;
    preview.style.background = look.bg;
  }
  return h("div", {className: "scustom"}, field,
           h("div", {className: "scustomside"}, h("label", {className: "hexline"}, "Hex", hex),
             preview));
}

// A drawing's own section, in playback's place. It sets how often the drawing draws and its
// canvas, which is the whole screen, half of it, or a size set by hand placed as a small picture is
function drawingFold(key, held) {
  var look = held.look;
  var speed = segment([["fps", "fps"], ["interval", "interval"], ["saved", "every frame"]],
                      look.pace, function (value) {
                        var flips = (value === "fps" && look.pace === "interval") ||
                                    (value === "interval" && look.pace === "fps");
                        if (flips) look.every = Math.round(100 / look.every) / 100;
                        look.pace = value;
                      },
                      "Frames per second, seconds per frame, or as fast as the screen allows");
  var every = look.pace === "saved" ? null : numberBox(look.every, "", function (value) {
    if (Number(value) > 0) look.every = Number(value);
  }, look.pace === "interval" ? 0.05 : 1);
  var canvas = segment([["whole", "Whole screen"], ["half", "Half size"],
                        ["set", "Set size"]], look.canvas || "whole", function (value) {
                          look.canvas = value;
                        });
  canvas.querySelector("[data-value=whole]").title = "As big as the screen";
  canvas.querySelector("[data-value=half]").title =
    "Half the screen's width and height, using a quarter " +
    "of the memory. With Pixel double it fills the screen";
  canvas.querySelector("[data-value=set]").title = "A custom size in pixels, positioned like a small picture";
  // The speed, then the canvas, stacked or in two halves where the section is wide
  var body = h("div", {className: "ssplit"}, speedLine(speed, every, look),
               h("div", {}, sline(named("Canvas"), canvas), look.canvas === "set"
                 ? sline(named("Width"), numberBox(look.canvasW, "", function (value) {
                           if (Number(value) > 0) look.canvasW = Math.round(Number(value));
                         }), unit("pixels"),
                         named("Height"), numberBox(look.canvasH, "", function (value) {
                           if (Number(value) > 0) look.canvasH = Math.round(Number(value));
                         }), unit("pixels"))
                 : null));
  var said = [look.pace === "fps" ? look.every + " fps"
            : look.pace === "interval" ? "frame every " + look.every + " s" : "every frame",
              look.canvas === "set" ? look.canvasW + " \u00d7 " + look.canvasH
            : look.canvas === "half" ? "half size" : "whole screen"];
  // A drawing drawn in styles of its own offers them, a row for each of its Styles: lines stacked
  // beside the one label, a line's first being the one it takes unchosen. A style is the file's own
  // text, so it is escaped for the button's label
  var media = held.shows ? mediaNamed(held.shows) : null;
  var drawing = media && media.drawing;
  var chosen = drawing ? styleChoices(drawing, look.style) : [];
  var offered = [];
  var segments = (drawing ? drawing.styles : []).map(function (line, at) {
    if (line.length < 2) return null;
    offered.push(chosen[at]);
    return segment(line.map(function (style) {
      return [style, style.replace(/&/g, "&amp;").replace(/</g, "&lt;")];
    }), chosen[at], function (value) {
      var picked = styleChoices(drawing, look.style);
      picked[at] = value;
      look.style = styleWord(drawing, picked);
    }, "The style this drawing is drawn in");
  });
  var rows = h("span", {className: "sstylerows"}, segments);
  return foldSection(key, "Drawing", offered.concat(said).join(", "),
                     h("div", {}, madeForLine(held), halfSizeLine(),
                       offered.length ? sline(named("Style"), rows) : null, body));
}

// A line warning that a drawing is turned or doubled otherwise than its Defaults: line says it
// suits, with a button setting it back, or null. A single turn is only where it starts, so only a
// turn outside a list is warned of
function madeForLine(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || !media.drawing) return null;
  var turns = drawingTurns(media.drawing);
  var turnWrong = !!turns && turns.length > 1 && turns.indexOf(Number(held.turn || 0)) < 0;
  // Doubled is right only on the half-size canvas, and full resolution only on the whole screen
  var doubled = drawingDoubled(media.drawing);
  var doubleWrong = doubled === true ? !(held.look.double && held.look.canvas === "half")
                  : doubled === false ? held.look.double || held.look.canvas === "half" : false;
  if (!turnWrong && !doubleWrong) return null;
  var said = [];
  if (turnWrong) said.push(turns.map(function (turn) { return turn + "\u00b0"; }).join(" or "));
  if (doubleWrong) said.push(doubled ? "pixel doubling at half size" : "full resolution");
  var use = h("button", {
    type: "button", className: "stoggle",
    title: "Set the rotation and pixel doubling this drawing is made for",
    onclick: function () {
      if (turnWrong) setTurn(held, turns[0]);
      if (doubleWrong) {
        held.look.double = doubled;
        held.look.canvas = doubled ? "half" : "whole";
      }
      draw();
    }
  }, "Apply");
  var line = sline(named("Made for " + said.join(", ")), use);
  line.classList.add("smadefor");
  return line;
}

// A line suggesting half size or pairing where both screens show a drawing and are not paired,
// unless both are pixel doubled at half size, with a button setting both to that, or null. Two
// larger canvases do not fit the fast memory together, so one draws more slowly. A drawing whose
// Defaults: line asks for full resolution is made for it, so no line is shown
function halfSizeLine() {
  if (SCREENS.length < 2 || state.hub.on || screensPaired()) return null;
  var both = SCREENS.slice(0, 2).map(function (letter) { return state.screens[letter]; });
  var drawings = both.every(function (held) {
    var media = held.there && held.shows ? mediaNamed(held.shows) : null;
    return !!media && !!media.drawing && drawingDoubled(media.drawing) !== false;
  });
  // Is either not doubled at half size? Doubling and half size are judged together, as madeForLine() does
  var larger = both.some(function (held) { return !(held.look.double && held.look.canvas === "half"); });
  if (!drawings || !larger) return null;
  var use = h("button", {
    type: "button", className: "stoggle", title: "Set both drawings to pixel doubling at half size",
    onclick: function () {
      both.forEach(function (held) {
        held.look.double = true;
        held.look.canvas = "half";
      });
      draw();
    }
  }, "Apply");
  var line = sline(named("Two drawings run faster at half size or paired"), use);
  line.classList.add("smadefor");
  line.title = "Two drawings at full size do not both fit the board's fast memory.";
  return line;
}

// A drawing's tile can copy it to the user's own drawings folder, to change in an editor, where it
// takes the original's place on any screen or hub position showing it in this scene. An example is
// customised, and one of the user's own duplicated
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
        // The copy keeps the turn the original was given, so it shows as the original did
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

// Copy a drawing into the drawings folder, its thumbnails with it, and read the drive again so the
// copy is listed. Returns the copy's name
export async function copyDrawing(name) {
  var dir = state.dirHandle;
  var example = isExampleMedia(name);
  var from = example ? await folderAt(dir, name.split("/").slice(0, -1)) : mediaHome[name] || dir;
  var into = await dir.getDirectoryHandle("drawings", {create: true});
  var styled = Object.keys((mediaNamed(name) || {}).styleThumbs || {});
  var copy = await copyToOwn(from, nameShown(name), into, !example, [".png"].concat(
    styled.map(function (style) { return "-" + style + ".png"; })));
  // A walk already under way would miss the copy, so the drive is read until it is listed
  for (var tries = 0; tries < 20 && !mediaNamed(copy); tries++) {
    await scanMedia(dir);
    if (!mediaNamed(copy)) await new Promise(function (settle) { setTimeout(settle, 100); });
  }
  return copy;
}

function playbackFold(key, held, media) {
  var look = held.look;
  // A folder whose names say no delay has nothing to play at its own pace
  var noneSaved = media.kind === "folder" && !media.named;
  var fromWhere = media.kind === "folder" ? "from names" : "from file";
  // Between fps and interval the figure is turned over, so the pace stays the same
  var speed = segment([["fps", "fps"], ["interval", "interval"], ["saved", fromWhere, noneSaved]],
                      look.pace, function (value) {
                        var flips = (value === "fps" && look.pace === "interval") ||
                                    (value === "interval" && look.pace === "fps");
                        if (flips) look.every = Math.round(100 / look.every) / 100;
                        look.pace = value;
                      },
                      "Frames per second, seconds per frame, or the delays " +
                      (media.kind === "folder" ? "written in each picture's file name" : "saved in the file"));
  var every = look.pace === "saved" ? null : numberBox(look.every, "", function (value) {
    // Nothing, zero or less is no pace, so the figure there stays
    if (Number(value) > 0) look.every = Number(value);
  }, look.pace === "interval" ? 0.05 : 1);
  var atEnd = numberBox(held.hold, "0", function (value) {
    held.hold = value && Number(value) > 0 ? value : "";
  }, 0.5);
  atEnd.disabled = !holdAllowed(held, look);
  var second = secondHoldAllowed(held, look);
  var hold = h("span", {
    className: "shold" + (holdAllowed(held, look) ? "" : " off"),
    title: holdAllowed(held, look) ? "Pause at each end, in seconds" : "Needs Loop or Ping pong"
  }, named("Hold"), atEnd, unit(second ? "seconds at the end," : "seconds"),
     second ? [numberBox(look.holdBack, "same", function (value) {
                 look.holdBack = value && Number(value) >= 0 ? value : "";
               }, 0.5), unit("seconds at the start")] : null);
  // The pace, then how it loops and holds, stacked or in two halves where the section is wide
  var body = h("div", {className: "ssplit"}, speedLine(speed, every, look),
    h("div", {},
      sline(toggle("&#8635;", "Loop", look.loop, function (on) { look.loop = on; },
                   "Start again after the last frame"),
            toggle("&#8644;", "Ping pong", held.pingpong, function (on) { held.pingpong = on; },
                   "Play forwards then backwards"),
            toggle("&#8676;", "First frame as last", look.whole, function (on) { look.whole = on; },
                   firstAsLastAllowed(held, look)
                     ? "Repeat the first frame at the end"
                     : "Needs Ping pong, or Loop off",
                   !firstAsLastAllowed(held, look))),
      sline(hold)));
  return foldSection(key, "Playback", playbackSaid(held, look), body);
}

export function showingLine(held, letter) {
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  return h("div", {className: "sshowing" + (picture ? "" : " empty")},
           picture ? showingPicture(picture, held, letter) : showingNothing(held, letter));
}

// What a screen showing nothing of its own says, in the same two lines a picture takes, so nothing
// under it moves when one is chosen
function showingNothing(held, letter) {
  var press = "press " + screenButton(letter) + " under a picture below to show it here";
  var under = held.shows ? null : screenUnder(letter);
  if (held.off) return ["off in this scene", h("small", {}, "black, at the backlight set above")];
  if (under && under.always) {
    return [under.always === "keep" ? "showing the line kept from the file from Always on"
              : ["showing ", h("b", {}, pictureSaid(under.always)), " from Always on"],
            h("small", {}, press + " instead")];
  }
  if (under) {
    return ["backlight off in this scene",
            h("small", {}, "lit only in " + spoken(namesOf(under.off)))];
  }
  return [state.scenes.length ? "nothing chosen for this scene" : "nothing showing",
          h("small", {}, press)];
}

// What a screen showing a picture says, its name and its kind and size, or for a drawing the
// canvas it draws on
function showingPicture(picture, held, letter) {
  var media = mediaNamed(picture);
  var art = mediaArt(picture);
  // A drawing is drawn, not shown, on a canvas
  if (media && media.kind === "drawing") {
    var size = state.hub.on ? state.hub.sizes[letter] : state.screens[letter].size;
    // A pair draws once, on the canvas its larger screen sizes
    var canvas = !state.hub.on && screensPaired()
               ? pairCanvas(SCREENS.map(function (one) { return state.screens[one]; }))
               : canvasPixels(held.look, size, held.turn);
    return ["drawing ", h("b", {}, nameShown(picture)),
            h("small", {}, "canvas, " + canvas[0] + " \u00d7 " + canvas[1])];
  }
  var kind = media ? {image: "picture", gif: "gif", folder: "slideshow"}[media.kind] : null;
  var about = [kind, art && art.w ? art.w + " \u00d7 " + art.h : null].filter(Boolean);
  return ["showing ", h("b", {}, pictureSaid(picture)), media ? null : " (not on the drive)",
          about.length ? h("small", {}, about.join(", ")) : null];
}

// The four sections for a screen or position, with nothing to set until a picture is showing
// but its orientation, which is how the screen is mounted
export function lookSections(key, held, size) {
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  var media = picture ? mediaNamed(picture) : null;
  // Is this a pair's second screen? It plays as the first does, so only its placing is offered
  var second = key === "screen" + SCREENS[SCREENS.length - 1] && screensPaired();
  return h("div", {className: "settings looksettings"},
           orientationFold(key, held),
           picture ? [placementFold(key, held, size), backgroundFold(key, held)] : null,
           !picture || second || !media ? null
             : media.kind === "drawing" ? drawingFold(key, held)
             : media.kind !== "image" ? playbackFold(key, held, media) : null);
}

// A backlight as a row of its own across the top of a screen's or the hub's box
export function lightRow(value, change, words, title) {
  return h("div", {className: "lightrow"}, lightSlider(value, change, title, words));
}

// A picture newly chosen starts at the turn it was last given on this screen, and a picture
// never turned here keeps the turn the screen has for pictures, so a turn can be set on an empty
// screen before anything is put on it. A drawing never turned here starts at the turn its
// Defaults: line gives. A slideshow newly chosen plays at five a second unless its names say
// their own
export function chosenAfresh(held) {
  if (held.shows === held.lastShows) return;
  var wasDrawing = !!held.lastShows && kindOf(held.lastShows) === "drawing";
  // The turn the screen has for pictures, which a drawing's own turn leaves alone. A file gives a
  // turn only on each line, so until a picture shows here it is 0, as for a line with none
  if (!wasDrawing) held.pictureTurn = held.turn;
  paceForChosen(held);
  settingsForChosen(held);
  // Check if a picture takes over from a drawing, whose turn and doubling were its own
  if (wasDrawing && held.shows && held.shows !== "keep" && kindOf(held.shows) !== "drawing") {
    held.turn = held.pictureTurn;
    held.look.double = false;
  }
  if (held.shows && held.turns[held.shows] !== undefined) held.turn = held.turns[held.shows];
  if (held.shows) held.turns[held.shows] = held.turn;
  held.lastShows = held.shows;
}

// ---- the pictures, whole ------------------------------------------------------------------------
// Each picture is drawn whole in its tile, never cropped. The tiles keep the row's fixed width,
// and a picture wider than its tile is scaled down to that width in a tile as tall as its shape
// needs. A narrower one is drawn at its true size, never scaled up, in a square tile at least, so
// a small picture looks as small as it is. The rows line up at the bottom, which keeps the pick
// rows in line. The name, a still's type and the size show over the picture on hover
addStep(assetSteps, ASSET_ORDER, "screenSettings", function () {
  document.getElementById("assets").classList.add("wholeassets");
  document.querySelectorAll("#assets .asset").forEach(function (cell) {
    var media = mediaNamed(cell.dataset.name);
    var art = media && mediaArt(media.name);
    var face = cell.querySelector(".face");
    var img = face && face.querySelector("img");
    // A drawing's description is its tooltip, as a program's is, since it is too long for its tile
    if (media && media.kind === "drawing" && media.drawing.description) {
      cell.title = media.drawing.description;
    }
    // A drawing with no thumbnail shows its icon or initial on its colour, square, named on hover
    if (media && media.kind === "drawing" && !media.thumbHandle && face) {
      var drawing = media.drawing;
      face.className = "face drawingface";
      face.style.height = face.getBoundingClientRect().width + "px";
      face.style.background = drawingInk(drawing, media.name);
      replace(face, h("span", {className: "kind"}, "drawing"),
              drawing.icon ? h("span", {className: "drawingicon"}, drawing.icon)
                           : h("span", {className: "drawingletter"}, drawing.title[0]),
              h("span", {className: "drawingtitle"}, drawing.title),
              h("div", {className: "label"}, h("b", {}, drawing.title)));
      return;
    }
    if (!art || !art.w || !img) return;
    var wide = face.getBoundingClientRect().width;
    // A drawing's thumbnail fills the tile, since it is a stand-in at no size of its own
    var small = art.w < wide && media.kind !== "drawing";
    var high = small ? Math.max(wide, art.h) : wide * art.h / art.w;
    face.classList.add("wholeface");
    face.style.height = high + "px";
    img.style.cssText = small ? "width:" + art.w + "px;height:" + art.h + "px"
                              : "width:100%;height:100%";
    var file = nameShown(media.name);
    var dot = file.lastIndexOf(".");
    var still = media.kind === "image";
    var label = face.querySelector(".label");
    // A slideshow is a folder, so it is named as one
    var shown = media.kind === "folder" ? pictureSaid(media.name)
              : dot > 0 ? file.slice(0, dot) : file;
    // A drawing shown by its thumbnail is named as its opening string says, since the thumbnail's
    // size is not the canvas it draws on
    if (label && media.kind === "drawing") {
      replace(label, h("b", {}, media.drawing.title));
    } else if (label) {
      replace(label, h("b", {}, shown), h("br"),
              [still && dot > 0 ? file.slice(dot + 1) : null, art.w + " \u00d7 " + art.h]
                .filter(Boolean).join(" \u00b7 "));
    }
  });
});

function paceForChosen(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || media.kind !== "folder") return;
  held.look.pace = media.named ? "saved" : "fps";
  held.look.every = 5;
}

// Set a drawing newly chosen to the turn and doubling its Defaults: line asks for. Doubling is off
// where it does not ask, as a drawing sizes itself to its canvas and doubled draws at half size.
// A doubled drawing takes the half-size canvas, which doubles to fill the screen
function settingsForChosen(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || !media.drawing) return;
  var turns = drawingTurns(media.drawing);
  if (turns && held.turns[held.shows] === undefined) held.turn = turns[0];
  held.look.double = drawingDoubled(media.drawing) === true;
  held.look.canvas = held.look.double ? "half" : "whole";
  held.look.style = "";
}

// The turns a drawing's Defaults: line gives, the one it starts at first, or null where it gives
// none. One turn alone is only where it starts, as a program's single Rotation is, and a list is
// the only turns it suits
function drawingTurns(drawing) {
  var rotation = drawing.defaults.Rotation;
  if (!rotation || rotation["default"] === undefined) return null;
  var turns = (rotation.choices || [rotation["default"]]).map(Number).filter(function (turn) {
    return [0, 90, 180, 270].indexOf(turn) >= 0;
  });
  return turns.length ? turns : null;
}

// Whether a drawing's Defaults: line asks for pixel doubling, true or false, or null where it says
// neither and suits both
function drawingDoubled(drawing) {
  var doubled = drawing.defaults["Pixel double"];
  if (!doubled || (doubled["default"] !== "true" && doubled["default"] !== "false")) return null;
  return doubled["default"] === "true";
}

// The speed's line, kept to one line, with its choices, the figure and what the figure counts
function speedLine(speed, every, look) {
  var line = sline(named("Speed"), speed, every,
                   every ? unit(look.pace === "fps" ? "frames per second" : "seconds per frame")
                         : null);
  line.classList.add("speedline");
  return line;
}
