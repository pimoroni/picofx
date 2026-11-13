import {draw, drawSteps} from "../00_draw.js";
import {
  allBodies, apply, bodyParts, driveParts, otherScenes, slotAt, state, store
} from "../04_scenes.js";
import {screenInk} from "../screens/12_screens.js";
import {chosenAfresh} from "../screens/16_screen_settings.js";

export var HUB_PLACES = ["A", "B", "C", "D", "E", "F"];

state.hub = {on: false, port: "A", sizes: {}, was: {}};
state.places = {};
HUB_PLACES.forEach(function (place) {
  state.hub.sizes[place] = "2.8";
  state.places[place] = {shows: null, turn: 0, pingpong: false, hold: "", fps: 5,
                         turns: {}, lastShows: null, off: false, pictureTurn: 0};
});

export var placePicked = "A";

export function pickPlace(place) {
  placePicked = place;
}

export function placeThere(place) { return state.hub.on && !!state.hub.sizes[place]; }

export function placesThere() { return HUB_PLACES.filter(placeThere); }

export function asScreen(place) {
  var held = state.places[place];
  return {size: state.hub.sizes[place], turn: held.turn, shows: held.shows, off: held.off,
          look: Object.assign({}, held.look, {backlight: state.hubLight})};
}

export function placeUnder(place) {
  var mine = state.places[place];
  if (state.at < 0 || !state.hub.on || mine.shows || mine.off) return null;
  var always = state.always.body;
  var held = always.places && always.places[place];
  if (held && held.shows) return {always: held};
  var by = otherScenes().filter(function (scene) {
    var theirs = scene.body.places && scene.body.places[place];
    return theirs && (theirs.shows || theirs.off);
  });
  return by.length ? {off: by} : null;
}

export function asAlwaysScreen(place, held) {
  return {size: state.hub.sizes[place], turn: held.turn || 0, shows: held.shows,
          look: Object.assign({}, held.look, {backlight: state.always.body.hubLight})};
}

export function hubInk() { return screenInk(state.hub.port); }

export function placeTurnForChosen(place) { chosenAfresh(state.places[place]); }

driveParts.push({
  gone: function (name) {
    if (state.media.some(function (one) { return one.name === name; })) return;
    store();
    allBodies().forEach(function (body) {
      Object.keys(body.places || {}).forEach(function (place) {
        if (body.places[place].shows === name) body.places[place].shows = null;
      });
    });
    apply(slotAt(state.at).body);
    draw();
  }
});

drawSteps.settle.push(function () { HUB_PLACES.forEach(placeTurnForChosen); });

export var placesPart = {
  capture: function (body) {
    body.places = {};
    HUB_PLACES.forEach(function (place) {
      var held = state.places[place];
      body.places[place] = {shows: held.shows, pingpong: held.pingpong, hold: held.hold,
                            fps: held.fps, turn: held.turn, off: held.off};
    });
  },
  apply: function (body) {
    if (!body.places) return;
    HUB_PLACES.forEach(function (place) {
      var held = state.places[place];
      Object.assign(held, body.places[place]);
      held.turn = body.places[place].turn || 0;
      held.off = !!body.places[place].off;
      held.lastShows = held.shows;
    });
  },
  blank: function (body) {
    HUB_PLACES.forEach(function (place) {
      body.places[place].shows = null;
      body.places[place].off = false;
    });
  },
  hasContent: function (body) {
    return HUB_PLACES.some(function (place) {
      return !!(body.places && (body.places[place].shows || body.places[place].off));
    });
  },
  sets: function (body) {
    var set = state.hub.on && placesThere().some(function (place) {
      var held = body.places && body.places[place];
      return held && (held.shows || held.off);
    });
    return set ? ["hub", "Screen Hub"] : null;
  }
};

bodyParts.push(placesPart);
