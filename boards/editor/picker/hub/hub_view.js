import {SCREEN_SIZES} from "../board.js";
import {h, replace} from "../dom.js";
import {draw} from "../draw.js";
import {
  HUB_PLACES, asAlwaysScreen, asScreen, hubInk, pickPlace, placePicked, placeThere, placeUnder,
  placesThere
} from "./hub.js";
import {
  GROUP_INKS, GROUP_NUMBERS, breakingUp, groupOf, hubBacklight, inNumberedGroup, joinOrLeave,
  membersOf, membersOfGroup, pickedGroupInk, pickedPlaces, placeGroupInk, sendTargets, sizeFits
} from "./hub_groups.js";
import {apartSaid, hubPictureTargets, namesSaid, placeGroups, placesSaid} from "./hub_text.js";
import {spoken} from "../lines.js";
import {setupOn} from "../runs.js";
import {allBodies, apply, capture, namesOf, slotAt, state, store} from "../scenes.js";
import {mediaArt, panelPreview} from "../screens/screen_art.js";
import {lookSettings} from "../screens/screen_settings.js";
import {pictureSaid} from "../screens/screen_text.js";
import {kindOf, pictureTargeting, screensTabHooks} from "../screens/screens.js";
import {swatchCell} from "../screens/screens_tab.js";
import {boardIcon} from "../setup.js";
import {tabSwatches, tabUnder} from "../tabs.js";

function hubSwitch() {
  return h("div", {class: "hubswitch", role: "group", "aria-label": "Screens connected as",
                   title: setupOn ? null
                                  : "Board setup, shared by every scene. Use Edit board to change it"},
    h("span", {}, boardIcon()),
    [[false, "A screen on each connector"], [true, "A Screen Hub across both"]].map(function (choice) {
      return h("button", {type: "button", "aria-pressed": String(state.hub.on === choice[0]),
                          disabled: !setupOn,
                          onclick: function () {
                            state.hub.on = choice[0];
                            draw();
                          }}, choice[1]);
    }));
}

function placeTile(place, sentWith, picked) {
  var size = state.hub.sizes[place];
  if (!size) {
    return h("li", {"data-empty": true},
      h("b", {}, place),
      h("span", {}, "no panel"),
      setupOn ? h("button", {type: "button", "aria-label": "Add a panel at " + place,
                             title: "A panel is fitted at " + place,
                             onclick: function () {
                               state.hub.sizes[place] = state.hub.was[place] || "2.8";
                               draw();
                             }}, "add") : null);
  }
  var held = state.places[place];
  var under = placeUnder(place);
  var always = under && under.always;
  var says = held.shows ? pictureSaid(held.shows)
           : held.off ? "off"
           : always ? (inNumberedGroup(place) ? "Always on's " : "") + pictureSaid(always.shows)
           : under ? "off in this scene" : "nothing";
  var ink = placeGroupInk(place);
  var sizeChosen = h("select", {"aria-label": "Panel at " + place,
                                title: "Panel at " + place + ", shared by every scene",
                                disabled: !setupOn,
                                onchange: function () {
                                  state.hub.sizes[place] = sizeChosen.value;
                                  draw();
                                }},
    SCREEN_SIZES.map(function (inches) {
      return h("option", {value: inches, selected: size === inches}, inches + "\"");
    }));
  return h("li", {"aria-current": picked.indexOf(place) >= 0 ? "true" : null,
                  "data-grouped": !!ink, style: {"--group": ink},
                  onclick: function () {
                    pickPlace(place);
                    draw();
                  }},
    h("button", {type: "button", "aria-label": "Position " + place}, place),
    h("label", {onclick: function (event) { event.stopPropagation(); }}, boardIcon(), sizeChosen),
    setupOn ? h("button", {type: "button", "aria-label": "No panel at " + place,
                           title: "No panel at " + place + ", in every scene",
                           onclick: function (event) {
                             event.stopPropagation();
                             dropPlace(place);
                           }}, "\u00d7") : null,
    panelPreview(always ? asAlwaysScreen(place, always) : asScreen(place),
                 always ? "Always on's picture, which shows here in this scene" : null),
    h("output", {}, says),
    placeGroupControls(place, sentWith));
}

function dropPlace(place) {
  state.hub.was[place] = state.hub.sizes[place];
  state.hub.sizes[place] = "";
  store();
  allBodies().forEach(function (body) { body.places[place].shows = null; });
  apply(slotAt(state.at).body);
  draw();
}

function placeSettings() {
  if (!placeThere(placePicked)) return null;
  var held = state.places[placePicked];
  var under = placeUnder(placePicked);
  var shown = under && under.always ? Object.assign({}, held, {shows: null, turn: under.always.turn || 0,
                                                               look: under.always.look || held.look})
                                    : held;
  return lookSettings("place" + placePicked, shown, state.hub.sizes[placePicked], shown !== held,
                      pickedGroupInk());
}

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
  return h("p", {html: said.join(" ")});
}

function hubSection() {
  var sentWith = {};
  placeGroups(capture()).forEach(function (send) {
    send.places.forEach(function (place) { sentWith[place] = send.places; });
  });
  var picked = pickedPlaces();
  var port = h("select", {"aria-label": "Hub wiring",
                          title: "Which connectors the hub's SPI and Selects are plugged into, " +
                                 "as labelled on the hub",
                          onchange: function () {
                            state.hub.port = port.value;
                            draw();
                          }},
    [["A", "SPI on A, Selects on B"], ["B", "SPI on B, Selects on A"]].map(function (choice) {
      return h("option", {value: choice[0], selected: state.hub.port === choice[0]}, choice[1]);
    }));
  return h("section", {class: "screenhub", "aria-label": "Screen Hub",
                       style: {"--tint": hubInk()}},
    h("div", {},
      h("h3", {}, "Screen Hub"),
      h("label", {title: "Board setup, shared by every scene"}, boardIcon(), port),
      h("small", {}, placesThere().length + " of " + HUB_PLACES.length + " fitted")),
    hubBacklight(),
    h("ol", {}, HUB_PLACES.map(function (place) { return placeTile(place, sentWith, picked); })),
    hubPace(),
    placeSettings());
}

screensTabHooks.above = hubSwitch;

screensTabHooks.head = function () { return state.hub.on ? hubSection() : null; };

function turnPlaces(places, off) {
  var breaking = off ? [] : breakingUp(places);
  places.forEach(function (place) {
    var held = state.places[place];
    held.off = off;
    if (off) held.shows = null;
  });
  breaking.forEach(function (place) { state.places[place].group = place; });
}

pictureTargeting.hub = {
  picture: hubPictureTargets,
  off: function () {
    var everywhere = placesThere().length && placesThere().every(function (place) {
      return state.places[place].off;
    });
    var targets = sendTargets().map(function (target) {
      var off = target.places.every(function (place) { return state.places[place].off; });
      return {label: target.name, pressed: off, colour: target.ink || hubInk(),
              title: target.ink ? "Group " + target.name + ", " + placesSaid(target.places)
                                : target.name + ", on its own",
              press: function () {
                pickPlace(target.places[0]);
                turnPlaces(target.places, !off);
              }};
    });
    targets.push({label: "all", all: true, pressed: everywhere, colour: hubInk(),
                  disabled: !placesThere().length,
                  title: everywhere ? "Back on at every position"
                                    : "Off at every group and every position on its own, " +
                                      "keeping the groups",
                  press: function () { turnPlaces(placesThere(), !everywhere); }});
    return {title: "Turn a hub position or group off in this scene", targets: targets};
  },
  shown: function (name) {
    return HUB_PLACES.some(function (place) {
      return placeThere(place) && state.places[place].shows === name;
    }) ? hubInk() : null;
  }
};

var screensSwatch = tabSwatches.screensPanel;

tabSwatches.screensPanel = function (swatch) {
  if (!state.hub.on) return screensSwatch(swatch);
  swatch.className = "accswatch screenswatch";
  swatch.dataset.hub = "";
  replace(swatch, HUB_PLACES.map(function (place) {
    var held = state.places[place];
    var under = placeThere(place) ? placeUnder(place) : null;
    var shown = held.shows || (under && under.always ? under.always.shows : null);
    var art = placeThere(place) && shown ? mediaArt(shown) : null;
    var shows = !placeThere(place) ? "absent" : held.off ? "off" : art ? "picture"
              : shown ? "blank" : under && under.off ? "dark" : "nothing";
    return swatchCell(shows, art, under && under.always);
  }));
  swatch.title = HUB_PLACES.map(function (place) {
    var held = state.places[place];
    var under = placeThere(place) ? placeUnder(place) : null;
    return place + ": " + (!placeThere(place) ? "no panel" : held.off ? "off"
                           : held.shows || (under && under.always ? "Always on's " +
                                            under.always.shows : "nothing"));
  }).join(", ");
};

var screensUnder = tabUnder.screensPanel;

tabUnder.screensPanel = function () {
  if (!state.hub.on) return screensUnder();
  var sizes = SCREEN_SIZES.filter(function (inches) {
    return placesThere().some(function (place) { return state.hub.sizes[place] === inches; });
  });
  return !sizes.length ? "hub, empty" : sizes.length > 1 ? "hub, mixed" : "hub, " + sizes[0] + "\"";
};

function placeGroupControls(place, sentWith) {
  var ink = placeGroupInk(place);
  var under = placeUnder(place);
  var frozen = !!(under && under.always) && !ink;
  var others = membersOf(place).filter(function (other) { return other !== place; });
  var matching = (sentWith[place] || []).filter(function (other) { return other !== place; });
  var said = frozen ? "from Always on"
           : under && under.off ? "lit only in " + spoken(namesOf(under.off))
           : ink ? (others.length ? "grouped with " + placesSaid(others)
                                  : "alone in group " + groupOf(place))
           : matching.length ? "matches " + placesSaid(matching) : "on its own";
  return [
    h("span", {role: "group", "aria-label": "Position " + place + " group",
               title: frozen ? "Set on the Always on tab" : null},
      GROUP_NUMBERS.map(function (number) {
        var inIt = groupOf(place) === number;
        var fits = sizeFits(place, number);
        var members = membersOfGroup(number);
        return h("button", {type: "button", "aria-pressed": String(inIt), disabled: !fits || frozen,
                            style: {"--tint": GROUP_INKS[number]},
                            title: !fits ? "Group " + number + " holds " +
                                           state.hub.sizes[members[0]] + "\" panels, and " +
                                           place + " is " + state.hub.sizes[place] + "\""
                                 : inIt ? "Remove " + place + " from group " + number +
                                          ", keeping what it shows"
                                 : "Put " + place + " in group " + number +
                                   (!members.length ? ""
                                    : state.places[members[0]].shows ? ", to show what the group shows"
                                    : state.places[place].shows ? ", taking what " + place + " shows"
                                    : ""),
                            onclick: function (event) {
                              event.stopPropagation();
                              joinOrLeave(place, number);
                              draw();
                            }}, number);
      })),
    h("small", {title: said}, said)
  ];
}
