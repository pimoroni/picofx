import {notFittedRead, saidNotFitted} from "../board.js";
import {WORDS, hexOf, hexRgb} from "../colours.js";
import {boardResidue} from "../kept.js";
import {quoted} from "../looks.js";
import {entryParts, unquoted} from "../reading.js";
import {state} from "../scenes.js";
import {canvasPixels, pairLarger, pairSized, panelPixels, pictureOffset} from "./screen_art.js";
import {
  SCREENS, SCREEN_NAMES, freshLook, kindOf, screenLetter, screenParts, screenShown
} from "./screens.js";

// ---- what the file says about the screens -------------------------------------------------------
// A screen's entry in a scene, written out and read back, and the words for its placement,
// background and playback.

// What a screen's entry says in a scene, its look or the line kept as the file had it. A hub
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
screenParts.screenEntry = screenEntry;
screenParts.readScreens = readScreens;

// Colours the file can say by name, the words the board knows, the rest written as hex
export var BG_NAMES = {};

// ---- where a picture sits ---------------------------------------------------------------------
// The nine places are calculated from the picture's size against the panel's, turned and doubled
// as it is drawn, and written as the pixels the file takes. A picture of another size put in the
// same file later sits where those pixels say, not at the edge chosen

export var ANCHOR_NAMES = ["top left", "top", "top right", "left", "centred", "right", "bottom left",
                    "bottom", "bottom right"];

// ---- what the file says -----------------------------------------------------------------------

// The settings before the colon, for how the screen is turned and lit and its picture is placed
export function placingTokens(turn, look, light, where) {
  var tokens = [];
  if (Number(turn)) tokens.push("rotation=" + turn);
  if (light < 1) tokens.push("backlight=" + Math.round(light * 100) + "%");
  if (look.mirror) tokens.push("mirror=true");
  if (where.x !== "" || where.y !== "")
    tokens.push("offset=" + (where.x === "" ? "*" : where.x) + "|" +
                (where.y === "" ? "*" : where.y));
  if (look.bg !== "#000000") tokens.push("bg=" + (BG_NAMES[look.bg] || look.bg.slice(1)));
  if (look.double) tokens.push("pixel_double=true");
  // One word covers both sides, two set them apart, across then down
  var tileDown = look.tileDown || "off";
  if (look.tile !== "off" || tileDown !== "off")
    tokens.push("tile=" + (look.tile === tileDown ? look.tile : look.tile + "|" + tileDown));
  return tokens;
}

// What playback allows, as the players do. A hold needs somewhere to turn around, which a loop
// or ping pong gives. Two holds need both, one for each end. First as last needs an end to play
// the first frame at, which a forward loop does not have
export function holdAllowed(playing, look) { return look.loop || playing.pingpong; }
export function secondHoldAllowed(playing, look) { return look.loop && playing.pingpong; }
export function firstAsLastAllowed(playing, look) { return playing.pingpong || !look.loop; }

// The settings after the file, for how a moving picture is paced, looped and held, leaving out
// whatever playback would refuse
export function playingTokens(playing, look, kind, size) {
  if (kind === "image") return [];
  var tokens = [];
  if (look.pace === "fps") tokens.push("fps=" + look.every);
  if (look.pace === "interval") tokens.push("interval=" + look.every);
  // A drawing takes a pace and its canvas's size, and nothing of a picture's loop. The board's
  // own canvas is the screen's, halved by pixel double, so only another size is written
  if (kind === "drawing") {
    var canvas = canvasPixels(look, size, playing.turn);
    var panel = panelPixels(size, playing.turn);
    var scale = look.double ? 2 : 1;
    if (canvas[0] !== Math.floor(panel[0] / scale) || canvas[1] !== Math.floor(panel[1] / scale))
      tokens.push("width=" + canvas[0], "height=" + canvas[1]);
    if (look.style) tokens.push("style=" + look.style);
    return tokens;
  }
  if (!look.loop) tokens.push("loop=false");
  if (playing.pingpong) tokens.push("ping_pong=true");
  if (look.whole && firstAsLastAllowed(playing, look)) tokens.push("first_as_last=true");
  if ((playing.hold || look.holdBack) && holdAllowed(playing, look))
    tokens.push("hold=" + (playing.hold || 0) +
                (look.holdBack && secondHoldAllowed(playing, look) ? "|" + look.holdBack : ""));
  return tokens;
}

export function lookEntry(selector, playing, look, light, size) {
  var kind = kindOf(playing.shows);
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  var left = [selector].concat(placingTokens(playing.turn, look, light, where)).join(" ");
  var what = kind === "folder" ? "sequence folder=" : kind === "gif" ? "gif file="
           : kind === "drawing" ? "drawing file=" : "image file=";
  return [left + ":", what + quoted(playing.shows)]
    .concat(playingTokens(playing, look, kind, size)).join(" ");
}

// ---- placement ----

export function placementSaid(look, where) {
  var said = [look.anchor === null ? "at " + (where.x === "" ? "centre" : where.x) + ", " +
                                     (where.y === "" ? "centre" : where.y)
                                   : ANCHOR_NAMES[look.anchor]];
  var tileDown = look.tileDown || "off";
  function tiled(mode) { return mode === "repeat" ? "tiled" : "tiled, mirrored"; }
  if (look.tile === "off" && tileDown === "off") said.push("one picture");
  else if (look.tile === tileDown) said.push(tiled(look.tile));
  else {
    if (look.tile !== "off") said.push(tiled(look.tile) + " across");
    if (tileDown !== "off") said.push(tiled(tileDown) + " down");
  }
  if (look.double) said.push("pixel doubled");
  return said.join(", ");
}

// A background as its colour at full brightness and how bright it is, 0 to 1. Black is its
// own colour at any brightness
export function groundParts(hex) {
  var rgb = hexRgb(hex);
  var top = Math.max(rgb[0], rgb[1], rgb[2]);
  if (!top) return {full: [0, 0, 0], value: 1};
  return {full: rgb.map(function (v) { return Math.round(v * 255 / top); }), value: top / 255};
}

export function groundHex(full, value) {
  return "#" + hexOf(full.map(function (v) { return Math.round(v * value); }));
}

export function groundSaid(bg) {
  var parts = groundParts(bg);
  var name = BG_NAMES["#" + hexOf(parts.full)];
  if (!name) return bg;
  return parts.value < 1 ? name + " at " + Math.round(parts.value * 100) + "%" : name;
}

// ---- playback ----

// The folded line is kept short, so a hold still fits it, and the units are written in full on
// the controls themselves
export function playbackSaid(held, look) {
  var said = [look.pace === "fps" ? look.every + " fps"
            : look.pace === "interval" ? "frame every " + look.every + " s"
            : kindOf(held.shows) === "folder" ? "timing from file names" : "timing from file"];
  said.push(look.loop ? "loop" : "once");
  if (held.pingpong) said.push("ping pong");
  if (look.whole && firstAsLastAllowed(held, look)) said.push("first frame as last");
  if ((held.hold || look.holdBack) && holdAllowed(held, look))
    said.push("hold " + (held.hold || 0) + " s" +
              (look.holdBack && secondHoldAllowed(held, look) ? " and " + look.holdBack + " s"
                                                              : ""));
  return said.join(", ");
}

// ---- what the file says ------------------------------------------------------------------------

// Each setting before the colon as a pair writes it, in the order placingTokens() gives them,
// with what a screen that leaves it out has
var PAIR_UNSET = {rotation: "0", backlight: "100%", mirror: "false", offset: "*|*",
                  bg: "black", pixel_double: "false", tile: "off"};

// Whether two screens show the same picture played the same way, a GIF, slideshow or still,
// which looks the same sent as one entry or two. A pair takes each screen's own placing, so only
// the settings after the file have to agree. A drawing can run differently on each screen, so it
// is only ever paired by hand
export function picturesMatch(first, second) {
  if (!first.shows || first.shows === "keep" || second.shows !== first.shows) return false;
  var kind = kindOf(first.shows);
  if (kind === "drawing") return false;
  return playingTokens(first, first.look || freshLook(), kind, null).join(" ") ===
         playingTokens(second, second.look || freshLook(), kind, null).join(" ");
}

// Whether a scene's screens are written as a pair, either paired by hand and showing a picture of
// the page's, or showing the same picture played the same way
function pairWritten(body) {
  if (SCREENS.length < 2 || state.hub.on) return false;
  if (!state.screens[SCREENS[0]].there || !state.screens[SCREENS[1]].there) return false;
  var first = body.screens[SCREENS[0]];
  var second = body.screens[SCREENS[1]];
  if (!body.screensPaired) return picturesMatch(first, second);
  return !!first.shows && first.shows !== "keep" && second.shows === first.shows;
}

// A pair's one entry, naming both screens and giving each setting once or once for each screen.
// What plays is as Screen A plays it, and a drawing's canvas is sized by the larger screen
function pairEntry(body) {
  var said = SCREENS.map(function (letter) {
    var playing = body.screens[letter];
    var look = playing.look || freshLook();
    var size = state.screens[letter].size;
    var where = pictureOffset(look, playing.shows, size, playing.turn);
    var held = {};
    placingTokens(playing.turn, look, look.backlight, where).forEach(function (token) {
      var equals = token.indexOf("=");
      held[token.slice(0, equals)] = token.slice(equals + 1);
    });
    return held;
  });
  var left = [SCREEN_NAMES[SCREENS[0]] + "," + SCREENS[1]];
  Object.keys(PAIR_UNSET).forEach(function (key) {
    if (said[0][key] === undefined && said[1][key] === undefined) return;
    var values = said.map(function (held) {
      return held[key] === undefined ? PAIR_UNSET[key] : held[key];
    });
    left.push(key + "=" + (values[0] === values[1] ? values[0] : values.join(",")));
  });

  var playing = body.screens[SCREENS[0]];
  var look = playing.look || freshLook();
  var size = state.screens[SCREENS[0]].size;
  var kind = kindOf(playing.shows);
  if (kind === "drawing") {
    var sized = pairSized(SCREENS.map(function (letter) { return body.screens[letter]; }));
    playing = sized.playing;
    look = sized.look;
    size = sized.size;
  }
  var what = kind === "folder" ? "sequence folder=" : kind === "gif" ? "gif file="
           : kind === "drawing" ? "drawing file=" : "image file=";
  return [left.join(" ") + ":", what + quoted(playing.shows)]
    .concat(playingTokens(playing, look, kind, size)).join(" ");
}

// ---- reading the file back ---------------------------------------------------------------------

// Try each kept line naming both screens as a pair, moving those a pair writes back exactly
export function readPairedScreens(bodies) {
  if (SCREENS.length < 2 || state.hub.on) return;
  var selector = (SCREEN_NAMES[SCREENS[0]] + "," + SCREENS[1]).toLowerCase();

  // A screen's size comes from the board line, unless one of its own lines took it already
  var sizes = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(screen[ab]?)=(2\.8|1\.54)$/i);
    var letter = named && screenLetter(named[1]);
    if (letter) sizes[letter] = {token: token, size: named[2]};
  });
  SCREENS.forEach(function (letter) {
    if (!sizes[letter] && state.screens[letter].there && state.screens[letter].size)
      sizes[letter] = {token: null, size: state.screens[letter].size};
  });
  if (!sizes[SCREENS[0]] || !sizes[SCREENS[1]]) return;
  var readOn = false;

  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      if (!parts || parts.selector !== selector) return true;
      if (body.screens[SCREENS[0]].shows || body.screens[SCREENS[1]].shows) return true;

      // Each screen's own settings, leaving out any at the value a screen without it has
      var lefts = [{}, {}];
      var understood = true;
      Object.keys(parts.left).forEach(function (key) {
        var values = parts.left[key].split(",");
        if (values.length > 2) understood = false;
        values = values.length === 1 ? [values[0], values[0]] : values;
        values.forEach(function (value, at) {
          if (value !== PAIR_UNSET[key]) lefts[at][key] = value;
        });
      });
      if (!understood) return true;
      var playings = SCREENS.map(function (letter, at) {
        return screenPlaying({selector: SCREEN_NAMES[letter].toLowerCase(), left: lefts[at],
                              effect: parts.effect, right: parts.right}, body, letter);
      });
      if (!playings[0] || !playings[1]) return true;

      var was = SCREENS.map(function (letter) {
        return {there: state.screens[letter].there, size: state.screens[letter].size};
      });
      SCREENS.forEach(function (letter) {
        state.screens[letter].there = true;
        state.screens[letter].size = sizes[letter].size;
      });
      // Does a drawing give no size of its own? Its canvas is then the larger screen's, halved
      // where that screen is doubled. The screens' sizes are the file's by now
      if (parts.effect === "drawing" && !parts.right.width && !parts.right.height) {
        var doubled = playings[pairLarger(playings)].look.double;
        playings.forEach(function (playing) { playing.look.canvas = doubled ? "half" : "whole"; });
      }
      var trial = {screens: {}, screensPaired: true};
      SCREENS.forEach(function (letter, at) { trial.screens[letter] = playings[at]; });
      if (!pairWritten(trial) || pairEntry(trial) !== one.text) {
        SCREENS.forEach(function (letter, at) {
          state.screens[letter].there = was[at].there;
          state.screens[letter].size = was[at].size;
        });
        return true;
      }

      // A drawing read as a pair was paired by hand, where a picture pairs by matching and so
      // stays free to change on one screen alone
      SCREENS.forEach(function (letter, at) { body.screens[letter] = playings[at]; });
      body.screensPaired = kindOf(playings[0].shows) === "drawing";
      readOn = true;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });

  // A pair read fits both screens at their sizes, which the page writes itself from here
  if (readOn) {
    SCREENS.forEach(function (letter) {
      var token = sizes[letter].token;
      if (token && boardResidue.indexOf(token) >= 0) boardResidue.splice(boardResidue.indexOf(token), 1);
    });
  }
}
