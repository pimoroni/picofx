import {h} from "../00_dom.js";
import {draw, drawSteps} from "../00_draw.js";
import {bodyParts, state} from "../04_scenes.js";
import {
  PAIR_SHARED, PAIR_SHARED_LOOK, SCREENS, screenShown, screenUnder, screensPaired
} from "./12_screens.js";
import {picturesMatch, readPairedScreens} from "./14_screen_text.js";
import {turnForChosen} from "./16_screen_settings.js";

state.screensPaired = false;

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

drawSteps.settle.push(settlePair);

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
