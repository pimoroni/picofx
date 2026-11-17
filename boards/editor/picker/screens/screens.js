import {
  NOT_FITTED_ORDER, boardLineSteps, notFittedSteps, screenHooks, screensFitted
} from "../board.js";
import {h} from "../dom.js";
import {addStep} from "../draw.js";
import {isHiddenName, nameShown} from "../drive.js";
import {isExampleMedia, mediaHome} from "../drive_files.js";
import {argumentFrom, openingString} from "../drive_programs.js";
import {setupOn} from "../runs.js";
import {
  BODY_ORDER, DRIVE_ORDER, allBodies, bodyParts, driveParts, otherScenes, state
} from "../scenes.js";
import {boardIcon} from "../setup.js";

// ---- a Screens tab ------------------------------------------------------------------------
// The two screen boxes, A in blue and B in purple, each with its panel size in the coloured
// band, the module as it is mounted and which way up it is turned, and under them one set of
// pictures, each able to go to A, to B, or to both.
//
// The tab asks of its page the board's two screens, the pictures on the drive, and each scene
// keeping what its screens show. The size and whether a screen is fitted are the board's, so
// they are changed while the board is set up, in the band of the screen's coloured box. What a
// screen shows is the scene's, and chosen at any time.
//
// Which way up a picture is drawn goes with the picture a scene shows, depending on how the
// screen is mounted, how the picture was made, and what the scene wants of it. A picture
// made symmetric can be turned from one scene to the next. So it is the scene's, kept with
// what the screen shows. A picture newly chosen starts at the turn it was last given on
// that screen, which saves setting it again and binds nothing.

// The picker keeps each screen port by a letter, A then B. A file writes it as the board names
// it, as screenA and screenB on a board with two, or screen on a board with one
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

// A screen as the page shows it, by its letter where there are two and plainly where there is one
export function screenShown(letter) {
  return SCREENS.length > 1 ? "Screen " + letter : "Screen";
}

// A board setting in a box's coloured band, the board's chip beside its control, which only
// editing the board can change
export function bandFact(control) {
  control.disabled = control.disabled || !setupOn;
  return h("span", {className: "bandfact", title: "Board setup, shared by every scene"},
           boardIcon(), control);
}

// The words on the button under a picture that puts it on a screen, the screen's letter where
// there are two and Show where there is one
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
state.media = [];
state.art = {};

// Whether the screens come through a Screen Hub, which none do until one is set up
state.hub = {on: false};

export var BOARD_INK = "#0a0a0a";

export var PANEL_INK = "#000000";

export var EMPTY_INK = "#2a2f33";

export var GROUND_INK = "#0f1113";

export var FRAME_INK = "#3d464c";

export var FRAME_WIDE = 0.3;

export var CHIN_INK = "#131f33";

export var HOLE_INK = "#efece6";

export var HOLE_EDGE = "#6d7379";

export var NAME_INK = "#e8eef2";

export var MODULE = {
  "2.8": {board: [48, 88], body: [9.6, 75.2], tab: [4, 44, 88], tabRadius: 4,
          panel: [0.5, 9.4, 47.5, 74.54], lit: [43.2, 57.6]},
  "1.54": {board: [32, 56], body: [9.6, 43.2], tab: [4, 28, 56], tabRadius: 4,
           panel: [0.24, 9.615, 31.76, 43.335], lit: [27.7, 27.7]}
};

export var PER_MM = 2.835;

export var PRINTED = {
  "2.8": {d: 'M72.585,28.824v1.577h-5.307v-1.398l1.25-.952c.793-.605,2.093-1.567,2.093-2.439,0-.388-.258-.665-.635-.665s-.754.277-.754.853h-1.835c.04-1.497,1.131-2.439,2.628-2.439,1.429,0,2.47.883,2.47,2.152,0,1.438-1.428,2.42-2.241,2.976l-.496.337h2.827Z M75.929,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.525-1.181,1.26-1.181,1.259.496,1.259,1.181Z M82.506,28.387c0,1.23-1.121,2.113-2.877,2.113s-2.876-.883-2.876-2.113c0-.783.446-1.339,1.22-1.646-.595-.308-.932-.812-.932-1.478,0-1.131,1.001-1.904,2.588-1.904s2.589.773,2.589,1.904c0,.675-.337,1.181-.942,1.478.784.308,1.23.863,1.23,1.646ZM80.561,28.209c0-.506-.367-.822-.933-.822s-.932.316-.932.822c0,.517.367.844.932.844s.933-.327.933-.844ZM78.767,25.502c0,.456.337.754.862.754s.863-.298.863-.754c0-.477-.337-.773-.863-.773s-.862.297-.862.773Z M85.682,23.459l-1.062,2.886h-1.438l.437-2.886h2.063ZM88.369,23.459l-1.062,2.886h-1.438l.437-2.886h2.062Z M97.318,28.616v1.785h-4.761v-6.942h2.023v5.157h2.737Z M101.258,30.501c-2.133,0-3.67-1.498-3.67-3.571s1.537-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.179-.675-.754-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.219,1.775-1.677,3.016-3.61,3.016Z M112.091,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.768v-6.942h2.768c2.072,0,3.57,1.458,3.57,3.471ZM110.027,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 21.614, y: 249.80300000000003},
  "1.54": {d: 'M44.498,23.459v6.942h-1.904v-5.366h-1.319v-1.576h3.224Z M48.109,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.526-1.181,1.26-1.181,1.259.496,1.259,1.181Z M54.24,28.06c0,1.418-1.15,2.44-2.737,2.44-1.448,0-2.559-.942-2.648-2.252h1.904c.089.348.377.605.744.605.426,0,.793-.357.793-.923,0-.525-.328-.883-.793-.883-.327,0-.585.179-.724.546h-1.795l.595-4.136h4.324v1.576h-3.025l-.159,1.27c.327-.356.813-.564,1.438-.564,1.319,0,2.083.972,2.083,2.32Z M60.947,29.053h-1.051v1.349h-1.904v-1.349h-2.985v-1.389l2.608-4.205h2.281v4.017h1.051v1.577ZM56.801,27.475h1.19l.01-1.944-1.2,1.944Z M64.073,23.459l-1.061,2.886h-1.438l.437-2.886h2.063ZM66.761,23.459l-1.062,2.886h-1.438l.437-2.886h2.063Z M75.71,28.616v1.785h-4.761v-6.942h2.023v5.157h2.738Z M79.649,30.501c-2.132,0-3.67-1.498-3.67-3.571s1.538-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.178-.675-.753-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.218,1.775-1.676,3.016-3.61,3.016Z M90.482,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.767v-6.942h2.767c2.073,0,3.57,1.458,3.57,3.471ZM88.419,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 20.48, y: 159.09400000000002}
};

export var PANEL_PX = {"2.8": [240, 320], "1.54": [240, 240]};

export var DRAWN = 210;

// The Screens tab's head, a box for each screen. A part that draws the head another way
// registers on instead, saying whether it did, and one that adds to either on after
export var screensHeadSteps = {instead: [], after: []};
export var HEAD_AFTER = ["hub", "screenPair"];

// What the parts after this one add to the pictures on the drive, each after the one before, such
// as the hub's positions, the whole pictures and the hub's groups
export var assetSteps = [];
export var ASSET_ORDER = ["hub", "screenSettings", "hubGroups", "discover"];

// What the screens parts after this one lend to this one and the art, filled in as they load:
// madeDrawing(name) from the art, screenEntry(letter, body) and readScreens(bodies) from the text,
// turnForChosen(letter) from the settings and renderTab() from the tab
export var screenParts = {};

export function mediaNamed(name) {
  return state.media.filter(function (m) { return m.name === name; })[0] || null;
}
screenHooks.mediaNamed = mediaNamed;

// A picture's kind, from the drive or its name
export function kindOf(shows) {
  var media = mediaNamed(shows);
  return media ? media.kind
       : /\.gif$/i.test(shows) ? "gif"
       : /\.(png|jpe?g)$/i.test(shows) ? "image" : "folder";
}

// ---- each scene keeps what its screens show ---------------------------------------------------

addStep(bodyParts, BODY_ORDER, "screens", {
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
      var entry = body.screens && screenParts.screenEntry(letter, body);
      if (entry) lines.push(entry);
    });
    return lines;
  },
  read: function () { return screenParts.readScreens.apply(null, arguments); }
});

// The board line gives a screen's size only where some scene shows something on it or turns it
// off. The board reserves for a pair wherever two screens are named, which slows the one in use
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
addStep(notFittedSteps, NOT_FITTED_ORDER, "screens", function () {
  if (state.hub.on) return [];
  return SCREENS.filter(function (letter) { return !state.screens[letter].there; }).map(screenShown);
});

addStep(driveParts, DRIVE_ORDER, "screens", {
  begin: function () { setMediaFound([]); },
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
    // word added, such as rings-blue-wide.png. This holds only in a drawings folder, since a PNG
    // at the top of the drive is a picture
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
    setMediaFound(mediaFound.filter(function (one) { return !one.taken; }));
    state.media = mediaFound;
    Object.keys(state.art).forEach(function (key) {
      if (state.art[key].gone) delete state.art[key];
    });
    // A drawing given its face before its thumbnail was found, as when a read catches it part
    // way through being copied, takes the thumbnail now
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
      if (one.kind === "drawing" && !one.thumbHandle) screenParts.madeDrawing(one.name);
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

// ---- every setting a screen takes -------------------------------------------------------------
// A screen takes more than its picture and turn. It also takes how brightly it is lit, where a
// picture is put and what fills round it, and how a moving picture is paced and looped. All of
// them go with what a screen shows in a scene, as the turn does, so each screen and each hub
// position keeps a look beside its picture and each scene keeps its own.
//
// Under the module is what it shows, then four sections that fold. They are orientation,
// placement, background, and last playback or a drawing's own section, which is there only for a
// moving picture or a drawing, so the three above it never move. Labels are the settings' own
// names, a choice a row of buttons drawn as what it does, and anything on or off a toggle. The
// module drawings show every setting as the board would draw it.
//
// The backlight is the screen's, a row across the top of its box. The hub's positions share one
// backlight, so the hub has one for all six, in each scene.

// anchor is which of nine places the picture sits at, left to right and top to bottom, the
// middle being centred, and null where x and y are typed. tile is across and tileDown down, each
// "off", "repeat" or "mirror". customBg is the last custom background, kept while a swatch is
// chosen so custom comes back to it. canvas is a drawing's, one of "whole", "half" or "set", and
// its size is then canvasW by canvasH
export var LOOK_START = {backlight: 1, mirror: false, anchor: 4, x: "", y: "", bg: "#000000",
                  customBg: "", double: false, tile: "off", tileDown: "off", pace: "saved",
                  every: 5, loop: true, whole: false, holdBack: "", canvas: "whole",
                  canvasW: 120, canvasH: 120, style: ""};

export function freshLook() { return Object.assign({}, LOOK_START); }

// Whether this scene's two screens are paired, which takes both to be fitted
export function screensPaired() {
  return state.screensPaired && SCREENS.length > 1 && !state.hub.on &&
         state.screens[SCREENS[0]].there && state.screens[SCREENS[1]].there;
}

// What a pair shares of what a screen shows
export var PAIR_SHARED = ["pingpong", "hold", "fps"];
// What a pair shares of a screen's look, since the rest of it is each screen's own placing
export var PAIR_SHARED_LOOK = ["pace", "every", "loop", "whole", "holdBack", "canvas", "canvasW",
                        "canvasH", "style"];

// What the board shows on a screen the scene being edited shows nothing on. The result holds
// always=, Always on's picture, which plays on there even where the scene takes the other screen
// of Always on's pair, or off=, every other scene that shows on it where Always on does not. It
// is null where nothing shows there, on the Always on tab and on a hub
export function screenUnder(letter) {
  if (state.at < 0 || state.hub.on || state.screens[letter].off) return null;
  var always = state.always.body;
  var shown = always.screens && always.screens[letter].shows;
  if (shown) return {always: shown};
  var by = otherScenes().filter(function (scene) {
    return scene.body.screens && (scene.body.screens[letter].shows || scene.body.screens[letter].off);
  });
  return by.length ? {off: by} : null;
}

// A line of a drawing's opening string that says how to show it
var DRAWING_LINE = /^\s*(Drawing|Icon|Colour|Section|Defaults|Styles|Firmware):\s*(.+?)\s*$/;

// What an opening string says of a drawing, or null for a file that is not one. Its defaults are
// the Defaults: line's settings by name, written as a program's Args: line is, such as "Rotation =
// 90 or 270, Pixel double = true"
export function drawingSaid(docstring) {
  var said = {title: "", description: "", icon: "", colour: "", section: "", defaults: {},
              styles: []};
  var rest = docstring.split("\n").filter(function (line) {
    var field = line.match(DRAWING_LINE);
    if (!field) return true;
    if (field[1] === "Styles") {
      // A choice the drawing offers, a line each, the first in a line being the one it takes
      // where none is chosen
      var choices = field[2].split(",").map(function (style) { return style.trim(); }).filter(Boolean);
      if (choices.length) said.styles.push(choices);
    } else if (field[1] === "Defaults") {
      field[2].split(",").map(argumentFrom).forEach(function (setting) {
        said.defaults[setting.name] = setting;
      });
    } else {
      said[field[1] === "Drawing" ? "title" : field[1].toLowerCase()] = field[2];
    }
    return false;
  }).join(" ").split(/\s+/).join(" ").trim();
  if (!said.title) return null;
  var first = rest.match(/^(.*?\.)(\s|$)/);
  said.description = first ? first[1] : rest;
  return said;
}

export var drawingArts = {};

// What each file last showed on a screen, composed with its look, by name
export var shownBefore = {};

// Every style word a drawing could be drawn in but its first, each one a thumbnail can be named for
function styleWords(drawing) {
  var words = [[]];
  drawing.styles.forEach(function (line) {
    var grown = [];
    words.forEach(function (word) {
      line.forEach(function (choice, at) { grown.push(at ? word.concat([choice]) : word); });
    });
    words = grown;
  });
  return words.filter(function (word) { return word.length; }).map(function (word) {
    return word.join("-");
  });
}

// ---- the pictures on the drive ------------------------------------------------------------------
// A screen can show gifs and stills, PNG or JPEG, folders of them, which play as a slideshow,
// and drawings

var mediaFound = [];

// Set the pictures and drawings found on the drive
function setMediaFound(list) {
  mediaFound = list;
}

// ---- what is showing, and every section under it ----

// A picture's name as a person reads it, or a drawing's title
export function pictureSaid(name) {
  var media = mediaNamed(name);
  if (media && media.kind === "drawing") return media.drawing.title;
  // A slideshow of the user's own is a path from the drive's top, an example plainly its name
  if (isExampleMedia(name)) return nameShown(name);
  return media && media.kind === "folder" ? "/" + name : name;
}
