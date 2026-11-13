import {boardResidue, filterResidue} from "../03_kept.js";
import {entryParts} from "../03_reading.js";
import {bodyParts, state} from "../04_scenes.js";
import {SCREEN_SIZES, boardWords} from "../07_board.js";
import {HUB_PLACES, hubInk, pickPlace, placePicked, placesPart, placesThere} from "./15_hub.js";
import {
  GROUP_NUMBERS, breakingUp, differences, listSaid, plainness, sendTargets
} from "./17_hub_groups.js";
import {LOOK_START, freshLook, kindOf} from "../screens/12_screens.js";
import {pictureOffset} from "../screens/13_screen_art.js";
import {
  lookEntry, offEntry, placingTokens, playingTokens, screenPlaying
} from "../screens/14_screen_text.js";

placesPart.readBoard = readHubBoard;
placesPart.read = readHubLines;

export function placesSaid(places) {
  var said = [];
  var at = 0;
  while (at < places.length) {
    var end = at;
    while (end + 1 < places.length &&
           HUB_PLACES.indexOf(places[end + 1]) === HUB_PLACES.indexOf(places[end]) + 1) end++;
    said.push(end > at ? places[at] + "-" + places[end] : places[at]);
    at = end + 1;
  }
  return said.join(",");
}

function playingKey(playing, place) {
  var look = playing.look || LOOK_START;
  var size = state.hub.sizes[place];
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  var kind = kindOf(playing.shows);
  var alone = kind === "drawing" && GROUP_NUMBERS.indexOf(playing.group) < 0 ? [place] : [];
  return [size, playing.shows].concat(alone, placingTokens(playing.turn, look, 1, where))
    .concat(playingTokens(playing, look, kind, size)).join("|");
}

export function placeGroups(body) {
  var groups = [];
  var byKey = {};
  placesThere().forEach(function (place) {
    var playing = body.places && body.places[place];
    if (!playing || !playing.shows) return;
    var key = playingKey(playing, place);
    if (!byKey[key]) {
      byKey[key] = {playing: playing, places: []};
      groups.push(byKey[key]);
    }
    byKey[key].places.push(place);
  });
  return groups;
}

function hubEntry(group) {
  return lookEntry("hub" + placesSaid(group.places), group.playing,
                   group.playing.look || freshLook(), state.hubLight,
                   state.hub.sizes[group.places[0]]);
}

function offHubEntries(body) {
  var byGroup = {};
  var groups = [];
  placesThere().forEach(function (place) {
    var held = body.places && body.places[place];
    if (!held || !held.off) return;
    var group = held.group || place;
    if (!byGroup[group]) {
      byGroup[group] = [];
      groups.push(group);
    }
    byGroup[group].push(place);
  });
  return groups.map(function (group) {
    return {places: byGroup[group], line: offEntry("hub" + placesSaid(byGroup[group]), state.hubLight)};
  });
}

bodyParts.push({
  writes: "hub",
  entries: function (body, lines) {
    if (!state.hub.on) return lines;
    placeGroups(body).forEach(function (group) { lines.push(hubEntry(group)); });
    offHubEntries(body).forEach(function (one) { lines.push(one.line); });
    return lines;
  }
});

var screensWithoutHub = boardWords.screens;

boardWords.screens = function (written) {
  if (!state.hub.on) return screensWithoutHub(written);
  var tokens = ["screen" + state.hub.port + "=hub"];
  SCREEN_SIZES.forEach(function (inches) {
    var places = placesThere().filter(function (place) {
      return state.hub.sizes[place] === inches;
    });
    if (places.length) tokens.push("hub" + placesSaid(places) + "=" + inches);
  });
  return tokens;
};

function hubPlacesNamed(selector) {
  var match = selector.match(/^hub([a-f](?:-[a-f])?(?:,[a-f](?:-[a-f])?)*)$/i);
  if (!match) return null;
  var places = [];
  match[1].toUpperCase().split(",").forEach(function (part) {
    var ends = part.split("-");
    var from = HUB_PLACES.indexOf(ends[0]);
    var to = HUB_PLACES.indexOf(ends[1] || ends[0]);
    var step = to >= from ? 1 : -1;
    for (var at = from; at !== to + step; at += step) places.push(HUB_PLACES[at]);
  });
  return places;
}

function readHubBoard() {
  var port = null;
  var sizes = {};
  var taken = [];
  boardResidue.forEach(function (token) {
    var wired = token.match(/^screen([ab])=hub$/i);
    var sized = token.match(/^(hub[a-f\-,]+)=(2\.8|1\.54)$/i);
    if (wired) {
      port = wired[1].toUpperCase();
      taken.push(token);
    } else if (sized && hubPlacesNamed(sized[1])) {
      hubPlacesNamed(sized[1]).forEach(function (place) { sizes[place] = sized[2]; });
      taken.push(token);
    }
  });
  state.hub.on = false;
  if (!port) return;

  state.hub.on = true;
  state.hub.port = port;
  HUB_PLACES.forEach(function (place) { state.hub.sizes[place] = sizes[place] || ""; });
  filterResidue(function (token) { return taken.indexOf(token) < 0; });
}

function readHubLines(bodies) {
  if (!state.hub.on) return;

  bodies.forEach(function (body) {
    var numbered = 0;
    var lightSet = false;
    state.hubLight = 1;
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      var places = parts && hubPlacesNamed(parts.selector);
      if (!places || places.some(function (place) {
        return !state.hub.sizes[place] || body.places[place].shows || body.places[place].off;
      })) return true;

      var playing = screenPlaying(parts, {screens: {X: {}}}, "X");
      if (!playing) return true;
      var light = playing.look.backlight;
      if (lightSet && light !== state.hubLight) return true;

      var trial = {places: JSON.parse(JSON.stringify(body.places))};
      var group = places.length > 1 ? String(numbered + 1) : null;
      places.forEach(function (place) {
        trial.places[place] = Object.assign({}, trial.places[place], {
          shows: playing.shows, turn: playing.turn || 0, pingpong: !!playing.pingpong,
          hold: playing.hold || "", look: Object.assign({}, playing.look),
          group: group || place, off: playing.off});
      });
      var wasLight = state.hubLight;
      state.hubLight = light;
      var named = places.slice().sort(function (a, b) {
        return HUB_PLACES.indexOf(a) - HUB_PLACES.indexOf(b);
      }).join();
      var written = playing.off
        ? offHubEntries(trial).filter(function (one) { return one.places.join() === named; })
            .map(function (one) { return one.line; })[0]
        : placeGroups(trial).filter(function (one) { return one.places.join() === named; })
            .map(hubEntry)[0];
      if (written !== one.text) {
        state.hubLight = wasLight;
        return true;
      }

      body.places = trial.places;
      lightSet = true;
      if (group) numbered++;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
    body.hubLight = state.hubLight;
  });
}

export function hubPictureTargets(name) {
  var targets = sendTargets().map(function (target) {
    var shown = target.places.every(function (place) {
      return state.places[place].shows === name;
    });
    return {label: target.name, pressed: shown, colour: target.ink || hubInk(),
            title: target.ink ? "Group " + target.name + ", " + placesSaid(target.places)
                              : target.name + ", on its own",
            press: function () {
              pickPlace(target.places[0]);
              var breaking = shown ? breakingUp(target.places) : [];
              state.places[placePicked].shows = shown ? null : name;
              state.places[placePicked].off = false;
              breaking.forEach(function (place) {
                state.places[place].shows = null;
                state.places[place].group = place;
              });
            }};
  });
  var everywhere = placesThere().length && placesThere().every(function (place) {
    return state.places[place].shows === name;
  });
  targets.push({label: "all", all: true, pressed: everywhere, colour: hubInk(),
                disabled: !placesThere().length,
                title: everywhere ? "Off every position"
                                  : "On every group and every position on its own, keeping the groups",
                press: function () {
                  var breaking = everywhere ? breakingUp(placesThere()) : [];
                  placesThere().forEach(function (place) {
                    state.places[place].shows = everywhere ? null : name;
                    state.places[place].off = false;
                  });
                  breaking.forEach(function (place) { state.places[place].group = place; });
                }});
  return targets;
}

function screensBold(places) { return "<b>" + placesSaid(places) + "</b>"; }

export function namesSaid(sends) {
  var names = sends.map(function (send) { return screensBold(send.places); });
  return names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1]
                          : names[0];
}

export function apartSaid(sends) {
  var byPicture = {};
  sends.forEach(function (send) {
    (byPicture[send.playing.shows] = byPicture[send.playing.shows] || []).push(send);
  });
  var told = [];
  var bases = [];
  Object.keys(byPicture).forEach(function (picture) {
    var group = byPicture[picture];
    if (group.length < 2) return;
    var base = group.slice().sort(function (a, b) {
      return plainness(a) - plainness(b) || b.places.length - a.places.length;
    })[0];
    group.forEach(function (send) {
      if (send === base) return;
      var words = differences(send, base);
      if (words.length)
        told.push(screensBold(send.places) + (send.places.length > 1 ? " are " : " is ") +
                  listSaid(words));
    });
    bases.push(screensBold(base.places));
  });
  if (!told.length) return "";
  var several = told.length > 1 || sends.some(function (send) {
    return told[0].indexOf(screensBold(send.places) + " are ") === 0;
  });
  return listSaid(told) + ", so " + (told.length > 1 ? "each is" : several ? "they are" : "it is") +
         " sent apart from " + listSaid(bases) + ".";
}
