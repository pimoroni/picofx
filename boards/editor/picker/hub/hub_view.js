import {SCREEN_SIZES} from "../board.js";
import {h, replace} from "../dom.js";
import {draw} from "../draw.js";
import {
  HUB_PLACES, asAlwaysScreen, asScreen, hubHeadSteps, hubInk, hubParts, pickPlace, placePicked,
  placeThere, placeUnder, placesThere
} from "./hub.js";
import {inNumberedGroup, placeGroups} from "./hub_groups.js";
import {apartSaid, namesSaid} from "./hub_text.js";
import {allBodies, apply, capture, frozen, slotAt, state, store} from "../scenes.js";
import {panelPreview} from "../screens/screen_art.js";
import {lookSections} from "../screens/screen_settings.js";
import {bandFact, kindOf, pictureSaid} from "../screens/screens.js";
import {BOARD_SETTING_SAYS, boardButton, boardIcon, removeButton} from "../setup.js";

// ---- drawing the hub -------------------------------------------------------------------------

// The choice of two screens or a hub, which takes both connectors. It sits at the top of the
// tab, where the outputs and strips have their board box, and at that box's size
function hubSwitch() {
  return h("div", {className: "hubswitch", title: BOARD_SETTING_SAYS, role: "group",
                   "aria-label": "Screens connected as"},
     h("span", {className: "hublead" + (state.hub.on ? "" : " on")}, boardIcon()),
     [[false, "A screen on each connector"], [true, "A Screen Hub across both"]].map(function (pair) {
       return h("button", {
         type: "button", className: state.hub.on === pair[0] ? "on" : "",
         "aria-pressed": String(state.hub.on === pair[0]),
         onclick: function () {
           state.hub.on = pair[0];
           draw();
         }
       }, pair[1]);
     }));
}

// Take the panel at a hub position off, in every scene, keeping its size to offer back
function takePlaceOff(place) {
  state.hub.was[place] = state.hub.sizes[place];
  state.hub.sizes[place] = "";
  store();
  allBodies().forEach(function (body) { body.places[place].shows = null; });
  apply(slotAt(state.at).body);
  draw();
}

function placeTile(place) {
  var picked = place === placePicked && placeThere(place);
  var name = h("b", {className: "placename"}, place);
  // Check if the position is empty. It offers a panel, at the size it last had
  if (!state.hub.sizes[place]) {
    var add = boardButton("add a panel");
    add.onclick = function (event) {
      event.stopPropagation();
      state.hub.sizes[place] = state.hub.was[place] || SCREEN_SIZES[0];
      draw();
    };
    return h("div", {className: "place" + (picked ? " picked" : "") + " empty", "data-place": place},
             h("div", {className: "placetop"}, name),
             h("span", {className: "placenone"}, add));
  }

  // Which panel is here, beside the board's chip
  var size = h("select", {
    className: "placesize", title: "Panel at " + place + ", shared by every scene",
    name: "placeSize", "aria-label": "Panel at " + place,
    onclick: function (event) { event.stopPropagation(); },
    onchange: function () {
      state.hub.sizes[place] = size.value;
      draw();
    }
  }, SCREEN_SIZES.map(function (inches) {
    return h("option", {value: inches, selected: state.hub.sizes[place] === inches}, inches + "\"");
  }));
  var chip = boardIcon();
  chip.classList.add("placechip");

  // A position the scene leaves to Always on shows Always on's picture in the striped frame
  var held = state.places[place];
  var under = placeUnder(place);
  var drawing = panelPreview(under && under.always ? asAlwaysScreen(place, under.always)
                                                   : asScreen(place));
  if (under && under.always) drawing.classList.add("under");
  return h("div", {
    className: "place" + (picked ? " picked" : ""), "data-place": place,
    onclick: function () {
      pickPlace(place);
      draw();
    }
  }, h("div", {className: "placetop"}, name, chip, size),
     drawing,
     // A position in a scene's own group says Always on's, as the line under it names the group
     h("small", {className: "placesays"},
       held.off ? "off"
       : under && under.always ? (inNumberedGroup(place) ? "Always on's " : "") +
                                 pictureSaid(under.always.shows)
       : under ? "off in this scene" : held.shows || "nothing"),
     // Under the panel, as the size above leaves no room beside the position's letter
     removeButton("panel", function () { takePlaceOff(place); }));
}

// The picked position's settings, the same sections a screen has. What each position shows is
// said under its module, and the position being set is the one filled, so the settings say neither
function placeSettings() {
  if (!placeThere(placePicked)) return h("div", {className: "hubsettings"});
  var held = state.places[placePicked];
  // A position showing Always on's picture shows Always on's settings, greyed
  var under = placeUnder(placePicked);
  var shown = under && under.always ? Object.assign({}, held, {shows: null, turn: under.always.turn || 0,
                                                               look: under.always.look || held.look})
                                    : held;
  var sections = lookSections("place" + placePicked, shown, state.hub.sizes[placePicked]);
  if (shown !== held) frozen(sections);
  return h("div", {className: "hubsettings"}, sections);
}

// The note on how fast the hub plays what it shows. A still picture is sent once and costs nothing
// after, so only the animations share the hub's speed. One plays as fast as a single screen, sent
// at once to every screen of its group, and several each play slower than they would alone
function hubPace() {
  var sends = placeGroups(capture());
  var moving = sends.filter(function (send) { return kindOf(send.playing.shows) !== "image"; });
  var still = sends.filter(function (send) { return kindOf(send.playing.shows) === "image"; });
  var said = [];
  if (moving.length > 1) {
    said.push(namesSaid(moving) + " share the hub's speed, so " +
              "each animation plays slower than on its own.");
  } else if (moving.length === 1) {
    var together = moving[0].places.length;
    said.push(namesSaid(moving) + (together > 1 ? (together === 2 ? " both" : " all") +
              " play the same animation together, as fast as a single screen."
                                                : " plays its animation at full speed."));
  }
  if (still.length)
    said.push(namesSaid(still) + (still.length > 1 || still[0].places.length > 1 ? " show"
                                                                                  : " shows") +
              " a still picture, sent once" + (moving.length ? ", with no cost to the others."
                                                             : ", so nothing slows down."));
  var apart = apartSaid(sends);
  if (apart) said.push(apart);
  // The sentences name the screens in bold
  return h("p", {className: "hubpace" + (said.length ? "" : " quiet"), html: said.join(" ")});
}

// Draw the hub's box in place of the screens'. How the hub is wired is the board's, so its band
// wears the board's chip beside it
function renderHubHead() {
  var box = document.getElementById("screensHead");
  box.classList.add("hubbed");
  var port = h("select", {
    className: "inband", name: "hubPort", "aria-label": "Hub wiring",
    title: "Which connectors the hub's SPI and Selects are plugged into, as labelled on the hub",
    onchange: function () { state.hub.port = port.value; draw(); }
  }, [["A", "SPI on A, Selects on B"], ["B", "SPI on B, Selects on A"]].map(function (pair) {
    return h("option", {value: pair[0], selected: state.hub.port === pair[0]}, pair[1]);
  }));
  replace(box, h("div", {className: "screen-box " + hubInk() + " hubbox"},
                 h("h3", {title: ""}, "Screen Hub", bandFact(port),
                   h("small", {className: "hubcount"},
                     placesThere().length + " of " + HUB_PLACES.length + " fitted")),
                 h("div", {className: "body"},
                   h("div", {className: "places"}, HUB_PLACES.map(placeTile)),
                   placeSettings(),
                   hubPace())));
  hubHeadSteps.forEach(function (step) { step(); });
}
hubParts.renderHead = renderHubHead;
hubParts.hubSwitch = hubSwitch;
