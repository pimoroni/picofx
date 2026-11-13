import {h, replace} from "../00_dom.js";
import {draw, drawSteps} from "../03_runs.js";
import {
  allBodies, apply, bodyParts, capture, driveParts, slotAt, state, store
} from "../04_scenes.js";
import {WORDS, hexOf} from "../05_effects.js";
import {
  boardLineSteps, notFittedRead, notFittedSteps, saidNotFitted, screenHooks, screensFitted
} from "../07_board.js";
import {boardIcon, setupOn} from "../08_setup.js";
import {LED_PANELS} from "../10_led_sections.js";
import {TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches, tabUnder} from "../11_tabs.js";
import {OWN_GROUP, foldHead} from "../22_program.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia, isHiddenName,
  mediaHome, nameShown
} from "../26_drive_files.js";
import {openingString} from "../26_drive_programs.js";
import {boardResidue, entryParts, unquoted} from "../27_readback.js";
import {
  backlightSetting, chosenAfresh, drawingArts, drawingCopyTile, drawingInk, drawingSaid, freshLook,
  lookEntry, lookSettings, madeDrawing, panelPreview, pictureSaid, showingLine, shownBefore,
  styleNamed, styleWords
} from "./16_screen_settings.js";
import {pairControl, pairEntry, pairWritten, screenUnder, screensPaired} from "./17_screen_pair.js";

// ---- a Screens tab ------------------------------------------------------------------------
// The tab asks of its page the board's two screens, the pictures on the drive, and each
// scene keeping what its screens show. The size and whether a screen is fitted are the board's,
// so they are changed while the board is set up, the band being the screen's coloured box;
// what a screen shows is the scene's, and chosen at any time.
//
// Which way up a picture is drawn goes with the picture a scene shows, depending on how the
// screen is mounted, how the picture was made, and what the scene wants of it: a picture
// made symmetric can be turned from one scene to the next. So it is the scene's, kept with
// what the screen shows. A picture newly chosen starts at the turn it was last given on
// that screen, which saves setting it again and binds nothing.

// The picker keeps each screen port by a letter, A then B. A file writes it as the board names
// it: screenA and screenB on a board with two, or screen on a board with one
export var SCREEN_NAMES = {};
export var SCREENS = CATALOGUE.screen_ports.map(function (name, index) {
  var letter = "AB".charAt(index);
  SCREEN_NAMES[letter] = "screen" + name.slice("screen".length).toUpperCase();
  return letter;
});

// The letter a screen port is kept by, from the name a file writes it as, or null
export function screenLetter(name) {
  for (var i = 0; i < SCREENS.length; i++) {
    if (SCREEN_NAMES[SCREENS[i]].toLowerCase() === name.toLowerCase()) return SCREENS[i];
  }
  return null;
}

// A screen as the page shows it: by its letter where there are two, and plainly where there is one
export function screenShown(letter) {
  return SCREENS.length > 1 ? "Screen " + letter : "Screen";
}

// The button under a picture that puts it on a screen: which screen where there are two, and with
// one, only whether it is shown
export function screenButton(letter) {
  return SCREENS.length > 1 ? letter : "Show";
}

state.screens = {};
SCREENS.forEach(function (letter) {
  // off= is a scene turning the screen off with `none`, showing black in place of a picture
  state.screens[letter] = {there: true, size: letter === "A" ? "2.8" : "1.54", turn: 0,
                           carried: "", pingpong: false, hold: "", fps: 5, shows: null,
                           kept: null, turns: {}, lastShows: null, off: false, pictureTurn: 0};
});

// A picture newly chosen on a screen starts as chosenAfresh says. What the screen showed when
// last looked at says whether it is newly chosen, a scene coming round bringing its own turn
export function turnForChosen(letter) { chosenAfresh(state.screens[letter]); }
state.media = [];
state.art = {};

// Whether the screens come through a Screen Hub, which none do until one is set up
state.hub = {on: false};

var BOARD_INK = "#0a0a0a";

var PANEL_INK = "#000000";

var EMPTY_INK = "#2a2f33";

var GROUND_INK = "#0f1113";

var FRAME_INK = "#3d464c";

var FRAME_WIDE = 0.3;

var CHIN_INK = "#131f33";

var HOLE_INK = "#efece6";

var HOLE_EDGE = "#6d7379";

var NAME_INK = "#e8eef2";

var MODULE = {
  "2.8": {board: [48, 88], body: [9.6, 75.2], tab: [4, 44, 88], tabRadius: 4,
          panel: [0.5, 9.4, 47.5, 74.54], lit: [43.2, 57.6]},
  "1.54": {board: [32, 56], body: [9.6, 43.2], tab: [4, 28, 56], tabRadius: 4,
           panel: [0.24, 9.615, 31.76, 43.335], lit: [27.7, 27.7]}
};

var PER_MM = 2.835;

var PRINTED = {
  "2.8": {d: 'M72.585,28.824v1.577h-5.307v-1.398l1.25-.952c.793-.605,2.093-1.567,2.093-2.439,0-.388-.258-.665-.635-.665s-.754.277-.754.853h-1.835c.04-1.497,1.131-2.439,2.628-2.439,1.429,0,2.47.883,2.47,2.152,0,1.438-1.428,2.42-2.241,2.976l-.496.337h2.827Z M75.929,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.525-1.181,1.26-1.181,1.259.496,1.259,1.181Z M82.506,28.387c0,1.23-1.121,2.113-2.877,2.113s-2.876-.883-2.876-2.113c0-.783.446-1.339,1.22-1.646-.595-.308-.932-.812-.932-1.478,0-1.131,1.001-1.904,2.588-1.904s2.589.773,2.589,1.904c0,.675-.337,1.181-.942,1.478.784.308,1.23.863,1.23,1.646ZM80.561,28.209c0-.506-.367-.822-.933-.822s-.932.316-.932.822c0,.517.367.844.932.844s.933-.327.933-.844ZM78.767,25.502c0,.456.337.754.862.754s.863-.298.863-.754c0-.477-.337-.773-.863-.773s-.862.297-.862.773Z M85.682,23.459l-1.062,2.886h-1.438l.437-2.886h2.063ZM88.369,23.459l-1.062,2.886h-1.438l.437-2.886h2.062Z M97.318,28.616v1.785h-4.761v-6.942h2.023v5.157h2.737Z M101.258,30.501c-2.133,0-3.67-1.498-3.67-3.571s1.537-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.179-.675-.754-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.219,1.775-1.677,3.016-3.61,3.016Z M112.091,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.768v-6.942h2.768c2.072,0,3.57,1.458,3.57,3.471ZM110.027,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 21.614, y: 249.80300000000003},
  "1.54": {d: 'M44.498,23.459v6.942h-1.904v-5.366h-1.319v-1.576h3.224Z M48.109,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.526-1.181,1.26-1.181,1.259.496,1.259,1.181Z M54.24,28.06c0,1.418-1.15,2.44-2.737,2.44-1.448,0-2.559-.942-2.648-2.252h1.904c.089.348.377.605.744.605.426,0,.793-.357.793-.923,0-.525-.328-.883-.793-.883-.327,0-.585.179-.724.546h-1.795l.595-4.136h4.324v1.576h-3.025l-.159,1.27c.327-.356.813-.564,1.438-.564,1.319,0,2.083.972,2.083,2.32Z M60.947,29.053h-1.051v1.349h-1.904v-1.349h-2.985v-1.389l2.608-4.205h2.281v4.017h1.051v1.577ZM56.801,27.475h1.19l.01-1.944-1.2,1.944Z M64.073,23.459l-1.061,2.886h-1.438l.437-2.886h2.063ZM66.761,23.459l-1.062,2.886h-1.438l.437-2.886h2.063Z M75.71,28.616v1.785h-4.761v-6.942h2.023v5.157h2.738Z M79.649,30.501c-2.132,0-3.67-1.498-3.67-3.571s1.538-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.178-.675-.753-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.218,1.775-1.676,3.016-3.61,3.016Z M90.482,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.767v-6.942h2.767c2.073,0,3.57,1.458,3.57,3.471ZM88.419,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 20.48, y: 159.09400000000002}
};

export var PANEL_PX = {"2.8": [240, 320], "1.54": [240, 240]};


function tabPath(x0, x1, near, far, radius) {
  var edge = far < near ? far + radius : far - radius;
  return "M" + x0 + " " + near +
         " L" + x0 + " " + edge +
         " Q" + x0 + " " + far + " " + (x0 + radius) + " " + far +
         " L" + (x1 - radius) + " " + far +
         " Q" + x1 + " " + far + " " + x1 + " " + edge +
         " L" + x1 + " " + near + " Z";
}

function moduleWords(x, y, ink, words) {
  return h("svg:text", {x: x, y: y, "text-anchor": "middle", fill: ink, "font-size": 4,
                        "font-family": "system-ui"}, words);
}

function moduleSaid(screen, art) {
  var size = (MODULE[screen.size] ? screen.size : "2.8") + " inch screen";
  if (screen.shows === "keep") return size + ", as it is";
  if (art) return size + ", showing a picture";
  if (screen.shows) return size + ", showing a picture on the board";
  if (screen.off) return size + ", off";
  return size + ", no picture";
}

export function panelDrawing(screen, under) {
  var made = MODULE[screen.size] || MODULE["2.8"];
  var turn = Number(screen.turn || 0);
  var quarter = turn % 180 === 90;

  var boardW = made.board[0];
  var boardH = made.board[1];
  var extent = Math.max(boardW, boardH);
  var left = (extent - boardW) / 2;
  var bottom = (extent - boardH) / 2;
  function up(y) { return extent - bottom - y; }

  var holes = [];
  [[8, 5], [16, 3.2], [24, 5], [32, 3.2], [40, 5]].forEach(function (hole) {
    if (hole[0] > boardW - 4) return;
    [4, boardH - 4].forEach(function (y) {
      holes.push(h("svg:circle", {cx: left + hole[0], cy: up(y), r: hole[1] / 2, fill: HOLE_INK,
                                  stroke: HOLE_EDGE, "stroke-width": 0.3}));
    });
  });

  var litW = made.lit[0];
  var litH = made.lit[1];
  var litX = left + boardW / 2 - litW / 2;
  var litY = up(boardH / 2) - litH / 2;
  var art = screen.art || (screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows) : null);
  var middleX = litX + litW / 2;
  var middleY = litY + litH / 2 + 1.4;
  var words = screen.shows === "keep" ? moduleWords(middleX, middleY, "#8b959b", "as it is")
            : art ? null
            : screen.shows ? moduleWords(middleX, middleY, "#8b959b", "on the board")
            : screen.off ? moduleWords(middleX, middleY, "#5d666c", "off")
            : moduleWords(middleX, middleY, "#8b959b", "no picture");
  var name = PRINTED[screen.size] || PRINTED["2.8"];

  var drawing = h("svg:svg", {viewBox: "0 0 " + extent + " " + extent, "aria-hidden": "true"},
    h("svg:g", {transform: "rotate(" + turn + " " + (extent / 2) + " " + (extent / 2) + ")"},
      h("svg:rect", {x: left, y: up(made.body[1]), width: boardW, height: made.body[1] - made.body[0],
                     fill: BOARD_INK}),
      h("svg:path", {d: tabPath(left + made.tab[0], left + made.tab[1], up(made.body[1]),
                                up(made.tab[2]), made.tabRadius), fill: BOARD_INK}),
      h("svg:path", {d: tabPath(left + made.tab[0], left + made.tab[1], up(made.body[0]),
                                up(boardH - made.tab[2]), made.tabRadius), fill: BOARD_INK}),
      holes,
      h("svg:rect", {x: left + made.panel[0], y: up(made.panel[3]),
                     width: made.panel[2] - made.panel[0], height: made.panel[3] - made.panel[1],
                     fill: PANEL_INK, stroke: FRAME_INK, "stroke-width": FRAME_WIDE}),
      h("svg:rect", {x: litX, y: litY, width: litW, height: litH,
                     fill: art ? GROUND_INK : screen.off ? "#000000" : EMPTY_INK}),
      h("svg:rect", {x: litX - 0.4, y: litY + litH, width: litW + 0.8,
                     height: Math.max(0, up(made.panel[1]) - (litY + litH) - 0.4), fill: CHIN_INK}),
      words,
      h("svg:g", {transform: "translate(" + (left - name.x / PER_MM) + " " +
                             (extent - bottom - name.y / PER_MM) + ") scale(" + (1 / PER_MM) + ")",
                  fill: NAME_INK},
        h("svg:path", {d: name.d}))));

  var picture = null;
  if (art) {
    var px = PANEL_PX[screen.size] || PANEL_PX["2.8"];
    var windowW = quarter ? litH : litW;
    var windowH = quarter ? litW : litH;
    var perPixel = litW / px[0];
    picture = h("div", {style: {"--left": ((extent - windowW) / 2 / extent * 100) + "%",
                                "--top": ((extent - windowH) / 2 / extent * 100) + "%",
                                "--wide": (windowW / extent * 100) + "%",
                                "--high": (windowH / extent * 100) + "%"}},
      h("img", {src: art.url, alt: "", "data-pixelated": !!art.pixelated,
                style: {"--w": (art.w * perPixel / windowW * 100) + "%",
                        "--h": (art.h * perPixel / windowH * 100) + "%"}}));
  }
  return h("div", {class: "screenmodule", role: "img", "aria-label": moduleSaid(screen, art),
                   "data-under": !!under, title: under || null},
    drawing, picture);
}

var SCREEN_INKS = {A: "var(--screenA)", B: "var(--screenB)"};

export function screenInk(letter) { return SCREEN_INKS[letter]; }

export var screensTabHooks = {above: null, head: null};

function screenBox(letter) {
  var screen = state.screens[letter];
  var named = screenShown(letter);
  var setup = h("label", {title: "Board setup, shared by every scene"}, boardIcon(),
                screen.there ? sizeChoice(letter) : null);
  var box = h("section", {class: "screenbox", "aria-label": named,
                          style: {"--tint": SCREEN_INKS[letter]}});
  if (!screen.there) {
    return replace(box, h("div", {}, h("h3", {}, named), setup),
      h("button", {type: "button", disabled: !setupOn, onclick: function () {
        screen.there = true;
        screen.shows = null;
        screen.kept = null;
        draw();
      }}, "add this screen"));
  }
  var under = screen.shows ? null : screenUnder(letter);
  var held = screen;
  if (under && under.always) {
    var always = state.always.body.screens[letter];
    held = Object.assign({}, screen, {shows: null, turn: always.turn || 0,
                                      look: always.look || screen.look});
  }
  var frozen = held !== screen;
  return replace(box,
    h("div", {}, h("h3", {}, named), setup,
      h("button", {type: "button", "aria-label": "Remove " + named,
                   title: "Remove this screen from every scene", disabled: !setupOn,
                   onclick: function () { dropScreen(letter); }}, "\u00d7")),
    backlightSetting(held.look.backlight, function (value) { screen.look.backlight = value; },
                     "backlight", "Backlight brightness for " +
                     named.replace("Screen", "screen") + " in this scene", frozen),
    previewInScene(screen, letter),
    pairControl(letter),
    showingLine(screen, letter),
    lookSettings("screen" + letter, held, screen.size, frozen),
    screen.kept ? h("button", {type: "button", "aria-pressed": String(screen.shows === "keep"),
                               title: screen.kept,
                               onclick: function () { screen.shows = "keep"; draw(); }},
                    h("b", {}, "Keep as is"), h("code", {}, screen.kept)) : null);
}

function sizeChoice(letter) {
  var screen = state.screens[letter];
  var offered = (CATALOGUE.board_settings[SCREEN_NAMES[letter].toLowerCase()] || ["2.8", "1.54"])
    .filter(function (inches) { return inches !== "hub"; });
  var choice = h("select", {"aria-label": screenShown(letter) + " panel size",
                            title: "Panel fitted, shared by every scene", disabled: !setupOn,
                            onchange: function () {
                              if (choice.value) screen.size = choice.value;
                              draw();
                            }},
    screen.size ? null : h("option", {value: "", selected: true}, "fitted size"),
    offered.map(function (inches) {
      return h("option", {value: inches, selected: screen.size === inches}, inches + " inch");
    }));
  return choice;
}

function dropScreen(letter) {
  state.screens[letter].there = false;
  store();
  allBodies().forEach(function (held) {
    held.screens[letter].shows = null;
    held.screens[letter].kept = null;
  });
  apply(slotAt(state.at).body);
  draw();
}

function previewInScene(screen, letter) {
  var under = screen.shows ? null : screenUnder(letter);
  if (!under || !under.always) return panelPreview(screen);
  var always = state.always.body.screens[letter];
  return panelPreview(Object.assign({}, screen, {shows: always.shows, turn: always.turn || 0,
                                                 look: always.look || screen.look}),
                      "Always on's picture, which shows here in this scene");
}

function mediaGroups() {
  var groups = [[OWN_GROUP, "your own pictures and drawings", state.media.filter(function (media) {
    return !isExampleMedia(media.name);
  }), false]];
  ["drawings", "pictures"].forEach(function (kind) {
    groups = groups.concat(exampleGroups(kind, state.media));
  });
  return groups.filter(function (group, at) { return !at || group[2].length; });
}

function gallerySaid() {
  return !state.fileHandle ? "open the FX drive to see its pictures and drawings"
       : !state.scanned ? "reading the drive..."
       : state.media.length ? "one set of pictures, each shown on A, B or both"
       : "no pictures on the drive yet. Drop a GIF, PNG, JPEG or drawing onto it";
}

export var pictureTargeting = {
  hub: null,
  screens: {
    picture: function (name) {
      return SCREENS.map(function (letter) {
        var screen = state.screens[letter];
        return {label: screenButton(letter), pressed: screen.there && screen.shows === name,
                colour: SCREEN_INKS[letter], disabled: !screen.there, press: function () {
                  var shown = state.screens[screensPaired() ? SCREENS[0] : letter];
                  shown.shows = shown.shows !== name ? name : shown.kept ? "keep" : null;
                  shown.off = false;
                }};
      });
    },
    off: function () {
      return {title: "Turn a screen off in this scene", targets: SCREENS.map(function (letter) {
        var screen = state.screens[letter];
        return {label: screenButton(letter), pressed: screen.off, colour: SCREEN_INKS[letter],
                disabled: !screen.there, press: function () {
                  screen.off = !screen.off;
                  if (screen.off) screen.shows = null;
                }};
      })};
    },
    shown: function (name) {
      var on = SCREENS.filter(function (letter) {
        return state.screens[letter].there && state.screens[letter].shows === name;
      });
      return on.length > 1 ? "var(--accent)" : on.length ? SCREEN_INKS[on[0]] : null;
    }
  }
};

function targeting() {
  return state.hub.on && pictureTargeting.hub ? pictureTargeting.hub : pictureTargeting.screens;
}

export var galleryExamples = {offer: null, addToTile: null};

function targetButton(target) {
  return h("button", {type: "button", "aria-pressed": String(!!target.pressed),
                      disabled: !!target.disabled, title: target.title, "data-all": !!target.all,
                      style: {"--tint": target.colour},
                      onclick: function () {
                        target.press();
                        draw();
                      }}, target.label);
}

function offCard() {
  var off = targeting().off();
  return h("div", {role: "group", "aria-label": "Off", title: off.title, inert: state.at < 0},
    h("span", {"aria-hidden": "true"}, "Off"), off.targets.map(targetButton));
}

function picturesGallery() {
  var grouped = !!state.fileHandle;
  var groups = grouped ? mediaGroups() : [[OWN_GROUP, "", state.media, false]];
  var examples = grouped && galleryExamples.offer
    ? galleryExamples.offer(groups.slice(1).map(function (group) { return group[0]; })) : null;
  var parts = [];
  groups.forEach(function (group, at) {
    var open = groupOpen(group);
    if (examples && at === 1) parts.push(examples.bar);
    if (examples && examples.dividers[group[0]]) parts.push(examples.dividers[group[0]]);
    if (grouped || !at) {
      parts.push(h("div", {class: "grouphead"},
        grouped ? foldHead(group[0], group[1], open, function () { groupsOpen[group[0]] = !open; })
                : null,
        at ? null : offCard()));
    }
    if (grouped && !open) return;
    parts.push(h("ul", {}, group[2].map(pictureTile),
      group[0] === OWN_GROUP && state.fileHandle
        ? h("li", {}, adderTile("add pictures or drawings",
            {description: "Pictures and drawings the board can play",
             accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"], "text/x-python": [".py"]}},
            "pictures", /\.(gif|png|jpe?g|py)$/i))
        : null));
  });
  if (examples && groups.length === 1) parts.push(examples.bar);
  return h("section", {class: "screenpictures", "aria-label": "Pictures"}, parts);
}

function pictureTile(media) {
  var name = media.name;
  var colour = targeting().shown(name);
  var description = media.kind === "drawing" && media.drawing.description;
  var tile = h("li", {title: description || name, "data-shown": !!colour,
                      style: {"--shown": colour}},
    pictureFace(media),
    h("div", {role: "group", "aria-label": "Show " + pictureSaid(name)},
      targeting().picture(name).map(targetButton)),
    isExampleMedia(name) ? null : binButton(name, media.kind),
    media.kind === "drawing" && state.fileHandle ? drawingCopyTile(name) : null);
  if (galleryExamples.addToTile) galleryExamples.addToTile(tile, name);
  return tile;
}

function pictureFace(media) {
  var name = media.name;
  var kind = {gif: "gif", folder: "slideshow", drawing: "drawing"}[media.kind];
  var tag = kind ? h("small", {}, kind) : null;
  if (media.kind === "drawing" && !media.thumbHandle) {
    var drawing = media.drawing;
    return h("figure", {"data-made": true, style: {"--colour": drawingInk(drawing, name)}},
      tag,
      h("span", {"aria-hidden": "true", "data-letter": !drawing.icon},
        drawing.icon || drawing.title[0]),
      h("b", {}, drawing.title),
      h("figcaption", {}, h("b", {}, drawing.title)));
  }
  var art = mediaArt(name);
  if (!art || !art.w) {
    return h("figure", {}, tag, h("span", {}, name.split(".").pop()),
             h("figcaption", {}, nameShown(name)));
  }
  var file = nameShown(name);
  var dot = file.lastIndexOf(".");
  var caption = media.kind === "drawing" ? h("b", {}, media.drawing.title) : [
    h("b", {}, media.kind === "folder" ? pictureSaid(name) : dot > 0 ? file.slice(0, dot) : file),
    h("br"),
    [media.kind === "image" && dot > 0 ? file.slice(dot + 1) : null, art.w + " \u00d7 " + art.h]
      .filter(Boolean).join(" \u00b7 ")
  ];
  return h("figure", {"data-fill": media.kind === "drawing", style: {"--w": art.w, "--h": art.h}},
    tag, h("img", {src: art.url, alt: ""}), h("figcaption", {}, caption));
}


export function mediaNamed(name) {
  return state.media.filter(function (m) { return m.name === name; })[0] || null;
}

// A picture's kind, from the drive or its name
export function kindOf(shows) {
  var media = mediaNamed(shows);
  return media ? media.kind
       : /\.gif$/i.test(shows) ? "gif"
       : /\.(png|jpe?g)$/i.test(shows) ? "image" : "folder";
}

// What a screen's entry says in a scene: its look, or the line kept as the file had it. A hub
// writes its positions' entries in place of the screens', and a pair writes one entry for both
// where the first screen's would go
function screenEntry(letter, body) {
  if (state.hub.on) return null;
  if (pairWritten(body)) return letter === SCREENS[0] ? pairEntry(body) : null;
  var screen = state.screens[letter];
  var playing = body.screens[letter];
  if (!screen.there) return null;
  if (playing.off) return offEntry(SCREEN_NAMES[letter], (playing.look || freshLook()).backlight);
  if (!playing.shows) return null;
  if (playing.shows === "keep") return playing.kept;
  var look = playing.look || freshLook();
  return lookEntry(SCREEN_NAMES[letter], playing, look, look.backlight, screen.size);
}

// The line that turns a screen or hub positions off in a scene, showing black at the backlight given
export function offEntry(selector, backlight) {
  return selector + (backlight < 1 ? " backlight=" + Math.round(backlight * 100) + "%" : "") +
         ": none";
}

// ---- each scene keeps what its screens show ---------------------------------------------------

bodyParts.push({
  capture: function (body) {
    body.screens = {};
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      body.screens[letter] = {shows: screen.shows, kept: screen.kept, pingpong: screen.pingpong,
                              hold: screen.hold, fps: screen.fps, turn: screen.turn,
                              off: screen.off};
    });
  },
  apply: function (body) {
    if (!body.screens) return;
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      Object.assign(screen, body.screens[letter]);
      screen.turn = body.screens[letter].turn || 0;
      screen.off = !!body.screens[letter].off;
      screen.lastShows = screen.shows;
    });
  },
  blank: function (body) {
    SCREENS.forEach(function (letter) {
      body.screens[letter].shows = null;
      body.screens[letter].off = false;
    });
  },
  hasContent: function (body) {
    return SCREENS.some(function (letter) {
      return !!(body.screens && (body.screens[letter].shows || body.screens[letter].off));
    });
  },
  sets: function (body) {
    var set = !state.hub.on && SCREENS.some(function (letter) {
      var held = body.screens && body.screens[letter];
      return held && (held.shows || held.off);
    });
    return set ? ["screens", "Screens"] : null;
  },
  named: function (body) {
    return SCREENS.map(function (letter) { return body.screens && body.screens[letter].shows; })
      .filter(function (shows) { return shows && shows !== "keep"; })
      .map(pictureSaid);
  },
  // A scene's screens are written after its lamps
  entries: function (body, lines) {
    SCREENS.forEach(function (letter) {
      var entry = body.screens && screenEntry(letter, body);
      if (entry) lines.push(entry);
    });
    return lines;
  },
  read: readScreens
});

// The board line gives a screen's size only where some scene shows something on it. The board
// reserves for a pair wherever two screens are named, which
// slows the one in use
boardLineSteps.before.push(function () {
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var used = screen.there && bodies.some(function (body) {
      return body && body.screens && (body.screens[letter].shows || body.screens[letter].off);
    });
    screensFitted[SCREEN_NAMES[letter].toLowerCase()] = used ? screen.size : "";
  });
});

// A screen taken off in Edit board, for the page's comment on what is not fitted. On a Screen Hub
// the ports are the hub's, so neither is listed
notFittedSteps.push(function () {
  if (state.hub.on) return [];
  return SCREENS.filter(function (letter) { return !state.screens[letter].there; }).map(screenShown);
});

// ---- reading the file back ----------------------------------------------------------------------

// A screen's line as the settings of the screen it names, or null where one is not understood
export function screenPlaying(parts, body, letter) {
  var playing = Object.assign({}, body.screens[letter]);
  var look = playing.look = freshLook();
  // A line says all its screen does, so nothing is left from what the screen held before
  playing.turn = 0;
  playing.pingpong = false;
  playing.hold = "";
  playing.off = false;
  // none turns the screen off, taking only a backlight
  if (parts.effect === "none") {
    var known = Object.keys(parts.left).every(function (key) { return key === "backlight"; }) &&
                !Object.keys(parts.right).length;
    if (!known) return null;
    var light = parts.left.backlight;
    if (light !== undefined)
      look.backlight = /%$/.test(light) ? parseFloat(light) / 100 : Number(light);
    playing.shows = null;
    playing.off = true;
    return playing;
  }
  var source = {gif: "file", image: "file", drawing: "file", sequence: "folder"}[parts.effect];
  if (!source || !parts.right[source]) return null;
  playing.shows = unquoted(parts.right[source]);

  var understood = true;
  Object.keys(parts.left).forEach(function (key) {
    var value = parts.left[key];
    if (key === "rotation") playing.turn = Number(value);
    else if (key === "backlight") look.backlight = /%$/.test(value) ? parseFloat(value) / 100 : Number(value);
    else if (key === "mirror" && value === "true") look.mirror = true;
    else if (key === "pixel_double" && value === "true") look.double = true;
    else if (key === "bg") look.bg = "#" + (WORDS[value] ? hexOf(WORDS[value]) : value);
    else if (key === "offset") {
      var sides = value.split("|");
      look.anchor = null;
      look.x = sides[0] === "*" ? "" : sides[0];
      look.y = sides[1] === "*" ? "" : sides[1];
    } else if (key === "tile") {
      var ways = value.split("|");
      look.tile = ways[0];
      look.tileDown = ways[1] || ways[0];
    } else understood = false;
  });
  Object.keys(parts.right).forEach(function (key) {
    var value = parts.right[key];
    if (key === source) return;
    if (key === "fps" || key === "interval") {
      look.pace = key;
      look.every = Number(value);
    } else if (key === "loop" && value === "false") look.loop = false;
    else if (key === "ping_pong" && value === "true") playing.pingpong = true;
    else if (key === "first_as_last" && value === "true") look.whole = true;
    else if (key === "hold") {
      var ends = value.split("|");
      playing.hold = ends[0];
      look.holdBack = ends[1] || "";
    } else if (key === "width" || key === "height") {
      look.canvas = "set";
      look[key === "width" ? "canvasW" : "canvasH"] = Number(value);
    } else if (key === "style") look.style = value;
    else understood = false;
  });
  // A drawing doubled with no size given has the half-size canvas the board gives it
  if (parts.effect === "drawing" && look.double && look.canvas !== "set") look.canvas = "half";
  return understood ? playing : null;
}

// Try each kept line of each body as a screen, moving those that write back exactly
function readScreens(bodies) {
  // A file listing what was taken off has the screens it names off and the others fitted. A line
  // read for a screen below fits it again
  if (notFittedRead) {
    SCREENS.forEach(function (letter) {
      state.screens[letter].there = !saidNotFitted(screenShown(letter));
    });
  }
  var sizes = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(screen[ab]?)=(2\.8|1\.54)$/i);
    var letter = named && screenLetter(named[1]);
    if (letter) sizes[letter] = {token: token, size: named[2]};
  });
  var readOn = {};

  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      var letter = parts && screenLetter(parts.selector);
      if (!letter || !sizes[letter] || body.screens[letter].shows || body.screens[letter].off)
        return true;
      var playing = screenPlaying(parts, body, letter);
      if (!playing) return true;

      var fitted = state.screens[letter];
      var was = {there: fitted.there, size: fitted.size};
      fitted.there = true;
      fitted.size = sizes[letter].size;
      var trial = {screens: Object.assign({}, body.screens)};
      trial.screens[letter] = playing;
      if (screenEntry(letter, trial) !== one.text) {
        fitted.there = was.there;
        fitted.size = was.size;
        return true;
      }
      body.screens[letter] = playing;
      readOn[letter] = true;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });

  // A screen read is fitted at its size, which the page writes itself from here
  Object.keys(readOn).forEach(function (letter) {
    boardResidue.splice(boardResidue.indexOf(sizes[letter].token), 1);
  });
}

// ---- the pictures on the drive ------------------------------------------------------------------
// What a screen can show: gifs and stills, PNG or JPEG, folders of them, which play as a
// slideshow, and drawings

var mediaFound = [];

driveParts.push({
  begin: function () { mediaFound = []; },
  file: async function (name, handle) {
    if (/\.gif$/i.test(name)) mediaFound.push({ name: name, kind: "gif", handle: handle });
    else if (/\.(png|jpe?g)$/i.test(name)) mediaFound.push({ name: name, kind: "image", handle: handle });
    else if (/\.py$/i.test(name)) {
      // A Python file is a drawing only where its opening string says so
      var drawing = null;
      try {
        drawing = drawingSaid(openingString(await (await handle.getFile()).text()));
      } catch (e) {
        drawing = null;
      }
      if (drawing) mediaFound.push({name: name, kind: "drawing", drawing: drawing});
    } else return false;
    return true;
  },
  folder: async function (name, handle) {
    for await (var inner of handle.entries()) {
      if (inner[1].kind === "file" && !isHiddenName(inner[0]) &&
          /\.(gif|png|jpe?g)$/i.test(inner[0])) {
        mediaFound.push({ name: name, kind: "folder", thumbHandle: inner[1] });
        return true;
      }
    }
    return false;
  },
  land: function () {
    mediaFound.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
    // A drawing's thumbnail is the PNG of its name beside it, as a program's is, and is no picture
    // of its own. Each of its other styles may have one too, its name with a dash and the style
    // word added, such as rings-blue-wide.png. Only in a drawings folder, a PNG at the top of the
    // drive being a picture
    function inDrawings(one) {
      return isExampleMedia(one.name) || (mediaHome[one.name] || {}).name === "drawings";
    }
    var thumbs = {};
    mediaFound.forEach(function (one) {
      if (one.kind === "image" && inDrawings(one)) thumbs[one.name] = one;
    });
    mediaFound.forEach(function (one) {
      var thumb = one.kind === "drawing" && inDrawings(one) &&
                  thumbs[one.name.replace(/\.py$/i, ".png")];
      if (!thumb) return;
      one.thumbHandle = thumb.handle;
      thumb.taken = true;
      one.styleThumbs = {};
      styleWords(one.drawing).forEach(function (style) {
        var styled = thumbs[one.name.replace(/\.py$/i, "-" + style + ".png")];
        if (!styled) return;
        one.styleThumbs[style] = styled.handle;
        styled.taken = true;
      });
    });
    mediaFound = mediaFound.filter(function (one) { return !one.taken; });
    state.media = mediaFound;
    Object.keys(state.art).forEach(function (key) {
      if (state.art[key].gone) delete state.art[key];
    });
    // A drawing given its face before its thumbnail was found, a read catching it part way
    // through being copied, takes the thumbnail now
    mediaFound.forEach(function (one) {
      if (one.kind !== "drawing" || !one.thumbHandle || !(state.art[one.name] || {}).face) return;
      delete state.art[one.name];
      Object.keys(drawingArts).forEach(function (key) {
        if (key.indexOf(one.name + "|") === 0) delete drawingArts[key];
      });
    });
    // A drawing cannot run in the page, so one without a thumbnail is shown by a face made from
    // its opening string
    mediaFound.forEach(function (one) {
      if (one.kind === "drawing" && !one.thumbHandle) madeDrawing(one.name);
    });
  },
  said: function () {
    return JSON.stringify(state.media.map(function (m) { return m.name + m.kind; }));
  },
  forget: function (name) {
    allBodies().forEach(function (body) {
      SCREENS.forEach(function (letter) {
        if (body.screens[letter].shows === name) body.screens[letter].shows = null;
      });
    });
    // Everything drawn from it goes too, its styles' thumbnails and its previews, so a new file
    // given its name starts afresh
    Object.keys(state.art).forEach(function (key) {
      if (key === name || key.indexOf(name + "#") === 0) delete state.art[key];
    });
    Object.keys(drawingArts).forEach(function (key) {
      if (key.indexOf(name + "|") === 0) delete drawingArts[key];
    });
    delete shownBefore[name];
  }
});

// ---- pictures, read off the drive in turn ------------------------------------------------------
// The drive is slow to read, so pictures come off it one at a time, those a screen or hub position
// shows in any scene first and the rest of the gallery after them

var pictureQueue = [];
var pictureReading = null;

// The pictures any scene puts on a screen or a hub position, worked out once a draw
var shownThisDraw = null;

drawSteps.before.push(function () { shownThisDraw = null; });

function picturesShown() {
  if (shownThisDraw) return shownThisDraw;
  var shown = shownThisDraw = [];
  var bodies = [capture(), state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  bodies.forEach(function (body) {
    if (!body) return;
    Object.keys(body.screens || {}).forEach(function (letter) {
      if (body.screens[letter].shows) shown.push(body.screens[letter].shows);
    });
    Object.keys(body.places || {}).forEach(function (place) {
      if (body.places[place].shows) shown.push(body.places[place].shows);
    });
  });
  return shown;
}

function readNextPicture() {
  if (pictureReading || !pictureQueue.length) return;
  shownThisDraw = null;
  var shown = picturesShown();
  pictureQueue.sort(function (a, b) {
    return (shown.indexOf(b.name) >= 0) - (shown.indexOf(a.name) >= 0);
  });
  var next = pictureReading = pictureQueue.shift();
  next.handle.getFile().then(function (file) {
    return new Promise(function (settle) {
      var url = URL.createObjectURL(file);
      var probe = new Image();
      probe.onload = function () {
        state.art[next.name] = {url: url, w: probe.naturalWidth, h: probe.naturalHeight,
                                ratio: probe.naturalWidth / probe.naturalHeight};
        settle();
      };
      // One that will not load stays held empty, so it is not asked for again
      probe.onerror = function () { settle(); };
      probe.src = url;
    });
  }, function () {
    // The file is gone, deleted while still listed, so it is asked for again once the drive is
    // next read, where one that would not load is not
    if (state.art[next.name]) state.art[next.name].gone = true;
  }).then(function () {
    pictureReading = null;
    draw();
    readNextPicture();
  });
}

export function mediaArt(name, style) {
  var media = mediaNamed(name);
  // A drawing in a style with a thumbnail of its own is shown by that, held under its name and style
  style = styleNamed(media, style);
  var styled = style && media && media.styleThumbs ? media.styleThumbs[style] : null;
  var key = styled ? name + "#" + style : name;
  var held = state.art[key];
  // The drawing's own thumbnail stands in while a style's loads, so the screen keeps a picture
  if (held) return held.ratio ? held : styled ? mediaArt(name) : null;
  // A slideshow and a drawing are shown by a thumbnail, a picture by itself
  var handle = styled || (media && (media.thumbHandle || media.handle));
  if (!handle) return null;
  // Held empty while it waits, so each is asked for once
  state.art[key] = {url: null, ratio: 0};
  pictureQueue.push({name: key, handle: handle});
  setTimeout(readNextPicture, 0);
  return styled ? mediaArt(name) : null;
}

var screensTab = h("div", {class: "screenstab"});

function renderScreensTab() {
  var above = screensTabHooks.above ? screensTabHooks.above() : h("p", {}, gallerySaid());
  var hubbed = screensTabHooks.head ? screensTabHooks.head() : null;
  replace(screensTab, above, hubbed || SCREENS.map(screenBox), picturesGallery());
  screensTab.toggleAttribute("data-setup", setupOn);
}

export function swatchCell(shows, art, under) {
  return h("span", {"data-shows": shows,
                    style: {"--picture": art ? (under ? "var(--through), " : "") +
                                               "url(" + art.url + ")" : null}});
}

tabSwatches.screensPanel = function (swatch) {
  swatch.className = "accswatch screenswatch";
  replace(swatch, SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var shown = screen.shows || (under && under.always) || null;
    var art = screen.there && shown && shown !== "keep"
              ? mediaArt(shown, screen.look && screen.look.style) : null;
    var shows = !screen.there ? "absent" : screen.off ? "off" : art ? "picture"
              : shown ? "blank" : under && under.off ? "dark" : "nothing";
    return swatchCell(shows, art, under && under.always);
  }));
  swatch.title = SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var said = !screen.there ? "not fitted" : screen.off ? "off"
             : screen.shows || (under && under.always ? "Always on's " + under.always : "nothing");
    return SCREENS.length > 1 ? letter + ": " + said : said;
  }).join(", ");
};

tabUnder.screensPanel = function () {
  var fitted = SCREENS.map(function (letter) {
    return state.screens[letter].there ? state.screens[letter].size : "";
  });
  return fitted.some(Boolean)
    ? fitted.map(function (size) { return size ? size + "\"" : "none"; }).join(", ")
    : "no screens";
};

drawSteps.before.push(function () { SCREENS.forEach(turnForChosen); });

drawSteps.after.push(function () {
  renderScreensTab();
});

(function () {
  var after = document.getElementById(LED_PANELS[LED_PANELS.length - 1]);
  after.after(h("details", {class: "panel", id: "screensPanel", open: true},
    h("summary", {}, "Screens"), screensTab));
}());

if (SCREENS.length) {
  TAB_NAMES.screensPanel = "Screens";
  TAB_PANELS.push("screensPanel");
  keptOpen("screensPanel");
} else {
  document.getElementById("screensPanel").hidden = true;
}

screenHooks.mediaNamed = mediaNamed;
screenHooks.panelPreview = panelPreview;
