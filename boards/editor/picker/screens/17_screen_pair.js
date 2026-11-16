import {DRAW_BEFORE, addStep, draw, drawSteps} from "../00_draw.js";
import {BODY_ORDER, bodyParts, state} from "../04_scenes.js";
import {
  HEAD_AFTER, PAIR_SHARED, PAIR_SHARED_LOOK, SCREENS, screenShown, screenUnder, screensHeadSteps,
  screensPaired
} from "./12_screens.js";
import {picturesMatch, readPairedScreens} from "./14_screen_text.js";
import {turnForChosen} from "./16_screen_settings.js";

// ---- the two screens paired -------------------------------------------------------------------
// Two screens paired in a scene show one picture or drawing, played once and sent to both in
// step, each placed by its own turn and look. Screen B shows what Screen A shows, at A's pace
// and in A's style, so B's box offers only its placing. A pair is the scene's, as what its
// screens show is, so each scene can pair them or not.
//
// The file writes a pair as one entry naming both, screenA,B. A setting the two screens differ
// in is given for each, A's then B's, separated by a comma, and one they agree in is given once.
// Two screens showing the same GIF, slideshow or still played the same way are written as a pair
// too, without being paired, as a hub joins its positions, and each screen keeps its own placing.

state.screensPaired = false;

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

addStep(drawSteps.before, DRAW_BEFORE, "screenPair", settlePair);

// Pair or part the two screens. Pairing gives B what A shows, or gives A what B shows where A
// shows nothing. A takes its own starting turn first, then B's pace and style. Parting leaves B
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

addStep(bodyParts, BODY_ORDER, "screenPair", {
  capture: function (body) { body.screensPaired = state.screensPaired; },
  apply: function (body) { state.screensPaired = !!body.screensPaired; },
  blank: function (body) { body.screensPaired = false; },
  read: readPairedScreens
});

// ---- the toggle, under each screen ---------------------------------------------------------------
// Under each screen's panel, where a hub position has its group's numbers, is a toggle and a line
// saying which screen it is paired with. The two toggles always show the same

addStep(screensHeadSteps.after, HEAD_AFTER, "screenPair", function () {
  if (SCREENS.length < 2 || state.hub.on) return;
  var fitted = SCREENS.every(function (letter) { return state.screens[letter].there; });
  if (!fitted) return;
  // A scene pairs only its own pictures, so while either screen shows Always on's the toggles stay
  // in place but cannot be pressed
  var fromAlways = SCREENS.filter(function (letter) {
    var under = state.screens[letter].shows ? null : screenUnder(letter);
    return under && under.always;
  });
  SCREENS.forEach(function (letter) {
    var body = document.querySelector("#screensHead .screen-box." + letter.toLowerCase() + " .body");
    if (!body) return;
    var other = SCREENS.filter(function (one) { return one !== letter; })[0];
    var place = document.createElement("div");
    place.className = "pairplace";

    var segment = document.createElement("span");
    segment.className = "groupseg";
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Paired";
    button.className = screensPaired() ? "on pairon" : "";
    button.title = "Show Screen A's picture or drawing on both screens in step.";
    button.onclick = function () {
      togglePair();
      draw();
    };
    if (fromAlways.length) {
      button.disabled = true;
      button.className = "";
      button.title = "Pairs this scene's own pictures on both screens";
    }
    segment.appendChild(button);
    place.appendChild(segment);

    // A pair by hand says so, and two screens showing the same picture the same way say they
    // match, since they are sent as a pair until a setting after the file differs
    var said = document.createElement("small");
    said.className = "groupsaid";
    // The screen showing Always on's picture already says so in its own line below
    said.textContent = fromAlways.indexOf(letter) >= 0 ? "not available"
                     : fromAlways.length ? screenShown(fromAlways[0]) + " from Always on"
                     : screensPaired() ? "paired with " + screenShown(other)
                     : picturesMatch(state.screens[letter], state.screens[other])
                       ? "matches " + screenShown(other) : "on its own";
    place.appendChild(said);
    body.insertBefore(place, body.querySelector(".sshowing") || body.querySelector(".looksettings"));
  });
});
