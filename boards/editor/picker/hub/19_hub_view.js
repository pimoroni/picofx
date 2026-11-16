import {draw} from "../00_draw.js";
import {setupOn} from "../03_runs.js";
import {allBodies, apply, capture, frozen, slotAt, state, store} from "../04_scenes.js";
import {SCREEN_SIZES} from "../07_board.js";
import {boardIcon} from "../08_setup.js";
import {
  HUB_PLACES, asAlwaysScreen, asScreen, hubHeadSteps, hubInk, hubParts, pickPlace, placePicked,
  placeThere, placeUnder, placesThere
} from "./15_hub.js";
import {inNumberedGroup, placeGroups} from "./17_hub_groups.js";
import {apartSaid, namesSaid} from "./18_hub_text.js";
import {kindOf, pictureSaid} from "../screens/12_screens.js";
import {panelPreview} from "../screens/13_screen_art.js";
import {lookSections} from "../screens/16_screen_settings.js";

// ---- drawing the hub -------------------------------------------------------------------------

// The choice of two screens or a hub, which takes both connectors. It is always shown, so it can
// be seen to be a choice, and only changed while editing the board. It sits at the top of the
// tab, where the outputs and strips have their board box, and at that box's size
function hubSwitch() {
  var row = document.createElement("div");
  row.className = "hubswitch" + (setupOn ? "" : " locked");
  row.title = setupOn ? "" : "Board setup, shared by every scene. Use Edit board to change it";
  var lead = document.createElement("span");
  lead.className = "hublead" + (state.hub.on ? "" : " on");
  lead.appendChild(boardIcon());
  row.appendChild(lead);
  [[false, "A screen on each connector"], [true, "A Screen Hub across both"]]
    .forEach(function (pair) {
      var choice = document.createElement("button");
      choice.type = "button";
      choice.className = state.hub.on === pair[0] ? "on" : "";
      choice.disabled = !setupOn;
      choice.textContent = pair[1];
      choice.onclick = function () {
        state.hub.on = pair[0];
        draw();
      };
      row.appendChild(choice);
    });
  return row;
}

function placeTile(place) {
  var held = state.places[place];
  var tile = document.createElement("div");
  tile.className = "place" + (place === placePicked && placeThere(place) ? " picked" : "");
  tile.dataset.place = place;
  var top = document.createElement("div");
  top.className = "placetop";
  var letter = document.createElement("b");
  letter.className = "placename";
  letter.textContent = place;
  top.appendChild(letter);
  tile.appendChild(top);

  if (!state.hub.sizes[place]) {
    tile.classList.add("empty");
    var none = document.createElement("span");
    none.className = "placenone";
    none.textContent = "no panel";
    tile.appendChild(none);
    if (setupOn) {
      var fit = document.createElement("button");
      fit.type = "button";
      fit.className = "placefit";
      fit.textContent = "add";
      fit.title = "A panel is fitted at " + place;
      fit.onclick = function (event) {
        event.stopPropagation();
        state.hub.sizes[place] = state.hub.was[place] || "2.8";
        draw();
      };
      tile.appendChild(fit);
    }
    return tile;
  }

  // Which panel is here, shown in every mode and changed only while editing the board
  var size = document.createElement("select");
  size.className = "placesize";
  SCREEN_SIZES.forEach(function (inches) {
    var option = document.createElement("option");
    option.value = inches;
    option.textContent = inches + "\"";
    if (state.hub.sizes[place] === inches) option.selected = true;
    size.appendChild(option);
  });
  size.disabled = !setupOn;
  size.title = "Panel at " + place + ", shared by every scene";
  size.onclick = function (event) { event.stopPropagation(); };
  size.onchange = function () {
    state.hub.sizes[place] = size.value;
    draw();
  };
  top.appendChild(size);

  // A position the scene leaves to Always on shows Always on's picture in the striped frame
  var under = placeUnder(place);
  var drawing = panelPreview(under && under.always ? asAlwaysScreen(place, under.always)
                                                   : asScreen(place));
  if (under && under.always) drawing.classList.add("under");
  tile.appendChild(drawing);
  var says = document.createElement("small");
  says.className = "placesays";
  // A position in a scene's own group says Always on's, as the line under it names the group
  says.textContent = held.off ? "off"
                   : under && under.always ? (inNumberedGroup(place) ? "Always on's " : "") +
                                             pictureSaid(under.always.shows)
                   : under ? "off in this scene" : held.shows || "nothing";
  tile.appendChild(says);
  if (setupOn) {
    var drop = document.createElement("button");
    drop.type = "button";
    drop.className = "placedrop";
    drop.textContent = "\u00d7";
    drop.title = "No panel at " + place + ", in every scene";
    drop.onclick = function (event) {
      event.stopPropagation();
      state.hub.was[place] = state.hub.sizes[place];
      state.hub.sizes[place] = "";
      store();
      allBodies().forEach(function (body) { body.places[place].shows = null; });
      apply(slotAt(state.at).body);
      draw();
    };
    tile.appendChild(drop);
  }
  tile.onclick = function () {
    pickPlace(place);
    draw();
  };
  return tile;
}

// The picked position's settings, the same sections a screen has. What each position shows is
// said under its module, and the position being set is the one filled, so the strip says neither
function placeSettings() {
  var settings = document.createElement("div");
  settings.className = "hubsettings";
  if (!placeThere(placePicked)) return settings;
  var held = state.places[placePicked];
  // A position showing Always on's picture shows Always on's settings, greyed
  var under = placeUnder(placePicked);
  var shown = under && under.always ? Object.assign({}, held, {shows: null, turn: under.always.turn || 0,
                                                               look: under.always.look || held.look})
                                    : held;
  var sections = lookSections("place" + placePicked, shown, state.hub.sizes[placePicked]);
  if (shown !== held) frozen(sections);
  settings.appendChild(sections);
  return settings;
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
  var pace = document.createElement("p");
  pace.className = "hubpace" + (said.length ? "" : " quiet");
  pace.innerHTML = said.join(" ");
  return pace;
}

// Draw the hub's box in place of the screens'
function renderHubHead() {
  var box = document.getElementById("screensHead");
  box.textContent = "";
  box.classList.add("hubbed");

  var side = document.createElement("div");
  side.className = "screen-box " + hubInk() + " hubbox";
  var head = document.createElement("h3");
  head.appendChild(document.createTextNode("Screen Hub"));
  // The hub is drawn for its screens through A, but may be wired the other way round
  var port = document.createElement("select");
  [["A", "SPI on A, Selects on B"], ["B", "SPI on B, Selects on A"]]
    .forEach(function (pair) {
      var option = document.createElement("option");
      option.value = pair[0];
      option.textContent = pair[1];
      if (state.hub.port === pair[0]) option.selected = true;
      port.appendChild(option);
    });
  port.className = "inband";
  port.title = "Which connectors the hub's SPI and Selects " +
               "are plugged into, as labelled on the hub";
  port.onchange = function () { state.hub.port = port.value; draw(); };
  head.appendChild(port);
  var fitted = document.createElement("small");
  fitted.className = "hubcount";
  fitted.textContent = placesThere().length + " of " + HUB_PLACES.length + " fitted";
  head.appendChild(fitted);
  side.appendChild(head);

  var body = document.createElement("div");
  body.className = "body";
  var row = document.createElement("div");
  row.className = "places";
  HUB_PLACES.forEach(function (place) { row.appendChild(placeTile(place)); });
  body.appendChild(row);
  body.appendChild(placeSettings());
  body.appendChild(hubPace());
  side.appendChild(body);
  box.appendChild(side);
  hubHeadSteps.forEach(function (step) { step(); });
}
hubParts.renderHead = renderHubHead;
hubParts.hubSwitch = hubSwitch;
