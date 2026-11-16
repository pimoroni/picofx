import {boardResidue, filterResidue} from "../03_kept.js";
import {entryParts} from "../03_reading.js";
import {state} from "../04_scenes.js";
import {HUB_PLACES, hubParts, placesSaid, placesThere} from "./15_hub.js";
import {differences, listSaid, placeGroups, plainness} from "./17_hub_groups.js";
import {freshLook} from "../screens/12_screens.js";
import {lookEntry, offEntry, screenPlaying} from "../screens/14_screen_text.js";

// A group's entry. Every position is lit by the hub's one light, so each entry carries it
function hubEntry(group) {
  return lookEntry("hub" + placesSaid(group.places), group.playing,
                   group.playing.look || freshLook(), state.hubLight,
                   state.hub.sizes[group.places[0]]);
}

// The lines turning hub positions off in a scene, one for each group and one for each position on
// its own, so the groups read back as they were written
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

// ---- reading the file back --------------------------------------------------------------------

// Hub positions as a file names them, hubA-C,E, or null where the item is not one
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

// Read the hub the board line declares into the page, which writes those tokens itself from then
// on. The hub is off where the line declares none
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

// Try each kept line of each body as a hub entry, moving those the hub's own writer gives back
function readHubLines(bodies) {
  if (!state.hub.on) return;

  // Each scene lights the hub its own way, and the first of its lines to be read decides how
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
hubParts.hubEntry = hubEntry;
hubParts.offHubEntries = offHubEntries;
hubParts.readBoard = readHubBoard;
hubParts.read = readHubLines;

// Screens named in the note are bold, so "A plays" reads as the screen and not as a word. The
// letters and their commas and dashes are all the markup holds
function screensBold(places) { return "<b>" + placesSaid(places) + "</b>"; }

export function namesSaid(sends) {
  var names = sends.map(function (send) { return screensBold(send.places); });
  return names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1]
                          : names[0];
}

// Where one picture goes out in several sends, which happens when some of its screens are set
// differently, a sentence naming how against the plainest of them. The plainest is the one least
// changed from how a screen starts, or the one on most screens where that is a tie
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
