import {h} from "../00_dom.js";
import {quoted} from "../01_looks.js";
import {draw, drawSteps} from "../03_runs.js";
import {bodyParts, otherScenes, state} from "../04_scenes.js";
import {boardResidue, entryParts} from "../27_readback.js";
import {
  SCREENS, SCREEN_NAMES, kindOf, screenLetter, screenPlaying, screenShown, turnForChosen
} from "./12_screens.js";
import {
  canvasPixels, freshLook, panelPixels, pictureOffset, placingTokens, playingTokens
} from "./16_screen_settings.js";

// ---- the two screens paired -------------------------------------------------------------------
// Two screens paired in a scene show one picture or drawing, played once and sent to both in
// step, each placed by its own turn and look. Screen B shows what Screen A shows, at A's pace
// and in A's style, so B's box offers only its placing. A pair is the scene's, as what its
// screens show is, so each scene can pair them or not.
//
// The file writes a pair as one entry naming both, screenA,B. A setting the two screens differ
// in is given for each, A's then B's, separated by a comma, and one they agree in is given once.
// Two screens showing the same GIF, slideshow or still played the same way are written as a pair
// too, without being paired, as a hub joins its positions, each screen keeping its own placing.

state.screensPaired = false;

// Whether this scene's two screens are paired, which takes both to be fitted
export function screensPaired() {
  return state.screensPaired && SCREENS.length > 1 && !state.hub.on &&
         state.screens[SCREENS[0]].there && state.screens[SCREENS[1]].there;
}

// What a pair shares of what a screen shows
var PAIR_SHARED = ["pingpong", "hold", "fps"];
// And of its look, everything else being each screen's own placing
var PAIR_SHARED_LOOK = ["pace", "every", "loop", "whole", "holdBack", "canvas", "canvasW",
                        "canvasH", "style"];

// Give Screen B what Screen A shows, before anything is drawn or written. B takes its own
// starting turn for a picture new to it, then A's pace and style over what that start set
function settlePair() {
  if (!screensPaired()) return;
  var from = state.screens[SCREENS[0]];
  var to = state.screens[SCREENS[1]];
  // Does A show a line kept from the file? B cannot show that, so it keeps its own
  if (from.shows === "keep") return;
  to.shows = from.shows;
  turnForChosen(SCREENS[1]);
  PAIR_SHARED.forEach(function (key) { to[key] = from[key]; });
  PAIR_SHARED_LOOK.forEach(function (key) { to.look[key] = from.look[key]; });
}

drawSteps.before.push(settlePair);

// Pair or part the two screens. Pairing gives B what A shows, or gives A what B shows where A
// shows nothing, A taking its own starting turn and then B's pace and style. Parting leaves B
// showing what it shows, now its own
function togglePair() {
  state.screensPaired = !state.screensPaired;
  if (!state.screensPaired) return;
  var first = state.screens[SCREENS[0]];
  var second = state.screens[SCREENS[1]];
  if (!first.shows && second.shows && second.shows !== "keep") {
    first.shows = second.shows;
    turnForChosen(SCREENS[0]);
    PAIR_SHARED.forEach(function (key) { first[key] = second[key]; });
    PAIR_SHARED_LOOK.forEach(function (key) { first.look[key] = second.look[key]; });
  }
}

// ---- each scene keeps whether its screens are paired ------------------------------------------

bodyParts.push({
  capture: function (body) { body.screensPaired = state.screensPaired; },
  apply: function (body) { state.screensPaired = !!body.screensPaired; },
  blank: function (body) { body.screensPaired = false; },
  read: readPairedScreens
});

export function pairControl(letter) {
  if (SCREENS.length < 2 || state.hub.on) return null;
  if (!SCREENS.every(function (one) { return state.screens[one].there; })) return null;
  var fromAlways = SCREENS.filter(function (one) {
    var under = state.screens[one].shows ? null : screenUnder(one);
    return under && under.always;
  });
  var other = SCREENS.filter(function (one) { return one !== letter; })[0];
  var said = fromAlways.indexOf(letter) >= 0 ? "not available"
           : fromAlways.length ? screenShown(fromAlways[0]) + " from Always on"
           : screensPaired() ? "paired with " + screenShown(other)
           : picturesMatch(state.screens[letter], state.screens[other])
             ? "matches " + screenShown(other) : "on its own";
  return h("div", {class: "pairing"},
    h("button", {type: "button", "aria-pressed": String(screensPaired() && !fromAlways.length),
                 disabled: !!fromAlways.length,
                 title: fromAlways.length ? "Pairs this scene's own pictures on both screens"
                                          : "Show Screen A's picture or drawing on both screens in step.",
                 onclick: function () {
                   togglePair();
                   draw();
                 }}, "Paired"),
    h("small", {}, said));
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
function picturesMatch(first, second) {
  if (!first.shows || first.shows === "keep" || second.shows !== first.shows) return false;
  var kind = kindOf(first.shows);
  if (kind === "drawing") return false;
  return playingTokens(first, first.look || freshLook(), kind, null).join(" ") ===
         playingTokens(second, second.look || freshLook(), kind, null).join(" ");
}

// Whether a scene's screens are written as a pair: paired by hand and showing a picture of the
// page's, or showing the same picture played the same way
export function pairWritten(body) {
  if (SCREENS.length < 2 || state.hub.on) return false;
  if (!state.screens[SCREENS[0]].there || !state.screens[SCREENS[1]].there) return false;
  var first = body.screens[SCREENS[0]];
  var second = body.screens[SCREENS[1]];
  if (!body.screensPaired) return picturesMatch(first, second);
  return !!first.shows && first.shows !== "keep" && second.shows === first.shows;
}

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

// Of a pair's two screens, the one whose canvas is larger after its own turn and pixel_double,
// as the board sizes a drawing shown on both, the first screen winning a tie
function pairLarger(playings) {
  var areas = SCREENS.map(function (letter, at) {
    var panel = panelPixels(state.screens[letter].size, playings[at].turn);
    var scale = playings[at].look && playings[at].look.double ? 2 : 1;
    return Math.floor(panel[0] / scale) * Math.floor(panel[1] / scale);
  });
  return areas[1] > areas[0] ? 1 : 0;
}

// A paired drawing as the larger screen sizes its canvas: Screen A's playing, which the pair
// shares, at the larger screen's turn and pixel_double, and that screen's size
function pairSized(playings) {
  var larger = pairLarger(playings);
  var look = Object.assign({}, playings[0].look || freshLook(),
                           {double: !!(playings[larger].look && playings[larger].look.double)});
  return {playing: Object.assign({}, playings[0], {turn: playings[larger].turn}), look: look,
          size: state.screens[SCREENS[larger]].size};
}

// The canvas a paired drawing is drawn on
export function pairCanvas(playings) {
  var sized = pairSized(playings);
  return canvasPixels(sized.look, sized.size, sized.playing.turn);
}

// A pair's one entry: both screens named, each setting given once or once for each screen,
// and what plays as Screen A plays it, a drawing's canvas sized by the larger screen
export function pairEntry(body) {
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
function readPairedScreens(bodies) {
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
      // where that screen is doubled, the screens' sizes being the file's by now
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
