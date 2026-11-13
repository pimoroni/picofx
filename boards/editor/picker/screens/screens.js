import {screenHooks} from "../board.js";
import {otherScenes, state} from "../scenes.js";

export var SCREEN_NAMES = {};
export var SCREENS = CATALOGUE.screen_ports.map(function (name, index) {
  var letter = "AB".charAt(index);
  SCREEN_NAMES[letter] = "screen" + name.slice("screen".length).toUpperCase();
  return letter;
});

export function screenLetter(name) {
  for (var i = 0; i < SCREENS.length; i++) {
    if (SCREEN_NAMES[SCREENS[i]].toLowerCase() === name.toLowerCase()) return SCREENS[i];
  }
  return null;
}

export function screenShown(letter) {
  return SCREENS.length > 1 ? "Screen " + letter : "Screen";
}

export function screenButton(letter) {
  return SCREENS.length > 1 ? letter : "Show";
}

state.screens = {};
SCREENS.forEach(function (letter) {
  state.screens[letter] = {there: true, size: letter === "A" ? "2.8" : "1.54", turn: 0,
                           carried: "", pingpong: false, hold: "", fps: 5, shows: null,
                           kept: null, turns: {}, lastShows: null, off: false, pictureTurn: 0};
});

state.media = [];
state.art = {};

state.hub = {on: false};

export var SCREEN_INKS = {A: "var(--screenA)", B: "var(--screenB)"};

export function screenInk(letter) { return SCREEN_INKS[letter]; }

export var screensTabHooks = {above: null, head: null};

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

export var galleryExamples = {offer: null, addToTile: null};

export function mediaNamed(name) {
  return state.media.filter(function (m) { return m.name === name; })[0] || null;
}

export function kindOf(shows) {
  var media = mediaNamed(shows);
  return media ? media.kind
       : /\.gif$/i.test(shows) ? "gif"
       : /\.(png|jpe?g)$/i.test(shows) ? "image" : "folder";
}

screenHooks.mediaNamed = mediaNamed;
export var LOOK_START = {backlight: 1, mirror: false, anchor: 4, x: "", y: "", bg: "#000000",
                  customBg: "", double: false, tile: "off", tileDown: "off", pace: "saved",
                  every: 5, loop: true, whole: false, holdBack: "", canvas: "whole",
                  canvasW: 120, canvasH: 120, style: ""};

export function freshLook() { return Object.assign({}, LOOK_START); }

export function screensPaired() {
  return state.screensPaired && SCREENS.length > 1 && !state.hub.on &&
         state.screens[SCREENS[0]].there && state.screens[SCREENS[1]].there;
}

export var PAIR_SHARED = ["pingpong", "hold", "fps"];

export var PAIR_SHARED_LOOK = ["pace", "every", "loop", "whole", "holdBack", "canvas", "canvasW",
                        "canvasH", "style"];

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
