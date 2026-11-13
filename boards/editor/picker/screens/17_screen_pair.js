import {h} from "../00_dom.js";
import {draw, drawSteps} from "../00_draw.js";
import {quoted} from "../01_looks.js";
import {bodyParts, otherScenes, state} from "../04_scenes.js";
import {boardResidue, entryParts} from "../27_readback.js";
import {
  SCREENS, SCREEN_NAMES, kindOf, screenLetter, screenPlaying, screenShown, turnForChosen
} from "./12_screens.js";
import {
  canvasPixels, freshLook, panelPixels, pictureOffset, placingTokens, playingTokens
} from "./16_screen_settings.js";

state.screensPaired = false;

export function screensPaired() {
  return state.screensPaired && SCREENS.length > 1 && !state.hub.on &&
         state.screens[SCREENS[0]].there && state.screens[SCREENS[1]].there;
}

var PAIR_SHARED = ["pingpong", "hold", "fps"];
var PAIR_SHARED_LOOK = ["pace", "every", "loop", "whole", "holdBack", "canvas", "canvasW",
                        "canvasH", "style"];

function settlePair() {
  if (!screensPaired()) return;
  var from = state.screens[SCREENS[0]];
  var to = state.screens[SCREENS[1]];
  if (from.shows === "keep") return;
  to.shows = from.shows;
  turnForChosen(SCREENS[1]);
  PAIR_SHARED.forEach(function (key) { to[key] = from[key]; });
  PAIR_SHARED_LOOK.forEach(function (key) { to.look[key] = from.look[key]; });
}

drawSteps.before.push(settlePair);

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

var PAIR_UNSET = {rotation: "0", backlight: "100%", mirror: "false", offset: "*|*",
                  bg: "black", pixel_double: "false", tile: "off"};

function picturesMatch(first, second) {
  if (!first.shows || first.shows === "keep" || second.shows !== first.shows) return false;
  var kind = kindOf(first.shows);
  if (kind === "drawing") return false;
  return playingTokens(first, first.look || freshLook(), kind, null).join(" ") ===
         playingTokens(second, second.look || freshLook(), kind, null).join(" ");
}

export function pairWritten(body) {
  if (SCREENS.length < 2 || state.hub.on) return false;
  if (!state.screens[SCREENS[0]].there || !state.screens[SCREENS[1]].there) return false;
  var first = body.screens[SCREENS[0]];
  var second = body.screens[SCREENS[1]];
  if (!body.screensPaired) return picturesMatch(first, second);
  return !!first.shows && first.shows !== "keep" && second.shows === first.shows;
}

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

function pairLarger(playings) {
  var areas = SCREENS.map(function (letter, at) {
    var panel = panelPixels(state.screens[letter].size, playings[at].turn);
    var scale = playings[at].look && playings[at].look.double ? 2 : 1;
    return Math.floor(panel[0] / scale) * Math.floor(panel[1] / scale);
  });
  return areas[1] > areas[0] ? 1 : 0;
}

function pairSized(playings) {
  var larger = pairLarger(playings);
  var look = Object.assign({}, playings[0].look || freshLook(),
                           {double: !!(playings[larger].look && playings[larger].look.double)});
  return {playing: Object.assign({}, playings[0], {turn: playings[larger].turn}), look: look,
          size: state.screens[SCREENS[larger]].size};
}

export function pairCanvas(playings) {
  var sized = pairSized(playings);
  return canvasPixels(sized.look, sized.size, sized.playing.turn);
}

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

function readPairedScreens(bodies) {
  if (SCREENS.length < 2 || state.hub.on) return;
  var selector = (SCREEN_NAMES[SCREENS[0]] + "," + SCREENS[1]).toLowerCase();

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

      SCREENS.forEach(function (letter, at) { body.screens[letter] = playings[at]; });
      body.screensPaired = kindOf(playings[0].shows) === "drawing";
      readOn = true;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });

  if (readOn) {
    SCREENS.forEach(function (letter) {
      var token = sizes[letter].token;
      if (token && boardResidue.indexOf(token) >= 0) boardResidue.splice(boardResidue.indexOf(token), 1);
    });
  }
}
