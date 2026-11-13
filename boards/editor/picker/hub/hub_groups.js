import {drawSteps} from "../draw.js";
import {
  HUB_PLACES, pickPlace, placePicked, placeThere, placeTurnForChosen, placeUnder, placesThere
} from "./hub.js";
import {bodyParts, state} from "../scenes.js";
import {backlightSetting} from "../screens/screen_settings.js";
import {ANCHOR_NAMES, groundSaid, playingTokens} from "../screens/screen_text.js";
import {LOOK_START, freshLook, kindOf} from "../screens/screens.js";

export var GROUP_NUMBERS = ["1", "2", "3"];
export var GROUP_INKS = {"1": "#d98a1a", "2": "#2f9e6a", "3": "#d0508a"};

HUB_PLACES.forEach(function (place) { state.places[place].group = place; });

export function groupOf(place) { return state.places[place].group; }

export function inNumberedGroup(place) { return GROUP_NUMBERS.indexOf(groupOf(place)) >= 0; }

export function membersOf(place) {
  return placesThere().filter(function (other) { return groupOf(other) === groupOf(place); });
}

export function membersOfGroup(number) {
  return placesThere().filter(function (place) { return groupOf(place) === number; });
}

export function sendTargets() {
  var targets = GROUP_NUMBERS.filter(function (number) {
    return membersOfGroup(number).length;
  }).map(function (number) {
    return {name: number, places: membersOfGroup(number), ink: GROUP_INKS[number]};
  });
  placesThere().forEach(function (place) {
    if (!inNumberedGroup(place)) targets.push({name: place, places: [place], ink: null});
  });
  return targets;
}

HUB_PLACES.forEach(function (place) { state.places[place].look = freshLook(); });
state.hubLight = 1;

var placeLookHomes = {};
HUB_PLACES.forEach(function (place) { placeLookHomes[place] = state.places[place].look; });

bodyParts.push({
  capture: function (body) {
    HUB_PLACES.forEach(function (place) {
      body.places[place].look = Object.assign({}, state.places[place].look);
    });
    body.hubLight = state.hubLight;
  },
  apply: function (body) {
    HUB_PLACES.forEach(function (place) {
      var home = placeLookHomes[place];
      if (body.places && body.places[place].look) Object.assign(home, body.places[place].look);
      state.places[place].look = home;
    });
    if (body.hubLight !== undefined) state.hubLight = body.hubLight;
  }
});

bodyParts.push({
  capture: function (body) {
    HUB_PLACES.forEach(function (place) { body.places[place].group = groupOf(place); });
  },
  apply: function (body) {
    HUB_PLACES.forEach(function (place) {
      if (body.places && body.places[place].group)
        state.places[place].group = body.places[place].group;
    });
  }
});

export function sizeFits(place, number) {
  var others = membersOfGroup(number).filter(function (other) { return other !== place; });
  return !others.length || state.hub.sizes[others[0]] === state.hub.sizes[place];
}

export function joinOrLeave(place, number) {
  if (groupOf(place) === number) {
    state.places[place].group = place;
    pickPlace(place);
    return;
  }
  var others = membersOfGroup(number).filter(function (other) { return other !== place; });
  state.places[place].group = number;
  var groupShows = others.length && state.places[others[0]].shows;
  pickPlace(others.length && (groupShows || !state.places[place].shows) ? others[0] : place);
}

function settleGroups() {
  placesThere().forEach(function (place) {
    var first = membersOf(place)[0];
    if (state.hub.sizes[place] !== state.hub.sizes[first]) state.places[place].group = place;
  });
  if (!placeThere(placePicked)) return;
  placeTurnForChosen(placePicked);
  var from = state.places[placePicked];
  membersOf(placePicked).forEach(function (place) {
    if (place === placePicked) return;
    var held = state.places[place];
    held.shows = from.shows;
    held.turn = from.turn;
    held.pingpong = from.pingpong;
    held.hold = from.hold;
    held.off = from.off;
    held.lastShows = from.shows;
    if (from.shows) held.turns[from.shows] = from.turn;
    Object.assign(held.look, from.look);
  });
}

drawSteps.settle.push(settleGroups);

function splitsOverAlways(places) {
  var always = state.at >= 0 && state.always.body.places;
  return !!always && places.some(function (place) { return always[place] && always[place].shows; });
}

export function breakingUp(places) {
  return places.filter(function (place) {
    return inNumberedGroup(place) && splitsOverAlways(membersOf(place));
  });
}

export function hubBacklight() {
  var mine = placesThere().some(function (place) {
    return state.places[place].shows || state.places[place].off;
  });
  var always = placesThere().some(function (place) {
    var under = placeUnder(place);
    return under && under.always;
  });
  var fromAlways = always && !mine;
  return backlightSetting(fromAlways ? state.always.body.hubLight : state.hubLight,
                          function (value) { state.hubLight = value; }, "shared backlight",
                          "Backlight brightness for all six hub screens in this scene", fromAlways);
}

export function placeGroupInk(place) {
  return placeThere(place) && inNumberedGroup(place) ? GROUP_INKS[groupOf(place)] : null;
}

export function pickedGroupInk() { return placeThere(placePicked) ? placeGroupInk(placePicked) : null; }

export function pickedPlaces() { return placeThere(placePicked) ? membersOf(placePicked) : []; }

export function differences(send, from) {
  var one = send.playing;
  var other = from.playing;
  var look = one.look || LOOK_START;
  var base = other.look || LOOK_START;
  var words = [];
  if (state.hub.sizes[send.places[0]] !== state.hub.sizes[from.places[0]])
    words.push("a " + state.hub.sizes[send.places[0]] + "\" panel");
  if (Number(one.turn || 0) !== Number(other.turn || 0))
    words.push(Number(one.turn || 0) ? "turned " + one.turn + "\u00b0" : "not turned");
  if (look.mirror !== base.mirror) words.push(look.mirror ? "mirrored" : "not mirrored");
  if (look.anchor !== base.anchor || look.x !== base.x || look.y !== base.y)
    words.push(look.anchor !== null && look.anchor !== undefined
               ? "placed " + ANCHOR_NAMES[look.anchor]
               : "placed at " + (look.x === "" ? "centre" : look.x) + ", " +
                 (look.y === "" ? "centre" : look.y));
  var across = look.tile;
  var down = look.tileDown || "off";
  if (across !== base.tile || down !== (base.tileDown || "off")) {
    var sides = across !== "off" && down !== "off" ? "" : across !== "off" ? " across" : " down";
    var mirrored = across === "mirror" || down === "mirror" ? ", mirrored" : "";
    words.push(across === "off" && down === "off" ? "not tiled" : "tiled" + sides + mirrored);
  }
  if (look.double !== base.double) words.push(look.double ? "pixel doubled" : "not doubled");
  if (look.bg !== base.bg) words.push("on " + groundSaid(look.bg));
  var kind = kindOf(one.shows);
  var played = playingTokens(one, look, kind, state.hub.sizes[send.places[0]]);
  var basePlayed = playingTokens(other, base, kind, state.hub.sizes[from.places[0]]);
  function paced(tokens) { return tokens.filter(function (t) { return /^(fps|interval)=/.test(t); }); }
  function sized(tokens) { return tokens.filter(function (t) { return /^(width|height)=/.test(t); }); }
  function looped(tokens) {
    return tokens.filter(function (t) { return !/^(fps|interval|width|height)=/.test(t); });
  }
  if (paced(played).join() !== paced(basePlayed).join()) words.push("timed differently");
  if (sized(played).join() !== sized(basePlayed).join()) words.push("drawn on another canvas");
  if (looped(played).join() !== looped(basePlayed).join()) words.push("played differently");
  return words;
}

export function listSaid(words) {
  return words.length > 1 ? words.slice(0, -1).join(", ") + " and " + words[words.length - 1]
                          : words[0];
}

export function plainness(send) {
  return differences(send, {places: send.places,
                            playing: {turn: 0, pingpong: false, hold: "", look: LOOK_START}}).length;
}
