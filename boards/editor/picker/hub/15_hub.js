import {h, replace} from "../00_dom.js";
import {draw, drawSteps} from "../03_runs.js";
import {
  allBodies, apply, bodyParts, capture, driveParts, otherScenes, slotAt, state, store
} from "../04_scenes.js";
import {SCREEN_SIZES, boardLineSteps} from "../07_board.js";
import {boardIcon, setupOn} from "../08_setup.js";
import {tabSwatches, tabUnder} from "../11_tabs.js";
import {boardResidue, entryParts, filterResidue} from "../27_readback.js";
import {
  GROUP_NUMBERS, apartSaid, breakingUp, hubBacklight, hubPictureTargets, inNumberedGroup,
  namesSaid, pickedGroupInk, pickedPlaces, placeGroupControls, placeGroupInk, sendTargets
} from "./17_hub_groups.js";
import {
  kindOf, mediaArt, offEntry, pictureTargeting, screenInk, screenPlaying, screensTabHooks,
  swatchCell
} from "../screens/12_screens.js";
import {
  LOOK_START, chosenAfresh, freshLook, lookEntry, lookSettings, panelPreview, pictureOffset,
  pictureSaid, placingTokens, playingTokens
} from "../screens/16_screen_settings.js";

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

function asScreen(place) {
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

function asAlwaysScreen(place, held) {
  return {size: state.hub.sizes[place], turn: held.turn || 0, shows: held.shows,
          look: Object.assign({}, held.look, {backlight: state.always.body.hubLight})};
}

export function hubInk() { return screenInk(state.hub.port); }

export function placeTurnForChosen(place) { chosenAfresh(state.places[place]); }

bodyParts.push({
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
  },
  readBoard: readHubBoard,
  read: readHubLines
});

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

function placeGroups(body) {
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
  entries: function (body, lines) {
    if (!state.hub.on) return lines;
    placeGroups(body).forEach(function (group) { lines.push(hubEntry(group)); });
    offHubEntries(body).forEach(function (one) { lines.push(one.line); });
    return lines;
  }
});

boardLineSteps.after.push(function (line) {
  if (!state.hub.on) return line;
  var rest = line.replace(/^board: ?/, "").replace(/\bscreen[ab]=\S+ ?/g, "").trim();
  var tokens = ["screen" + state.hub.port + "=hub"];
  SCREEN_SIZES.forEach(function (inches) {
    var places = placesThere().filter(function (place) {
      return state.hub.sizes[place] === inches;
    });
    if (places.length) tokens.push("hub" + placesSaid(places) + "=" + inches);
  });
  return "board: " + tokens.join(" ") + (rest ? " " + rest : "");
});

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

drawSteps.before.push(function () { HUB_PLACES.forEach(placeTurnForChosen); });

var screensUnder = tabUnder.screensPanel;
tabUnder.screensPanel = function () {
  if (!state.hub.on) return screensUnder();
  var sizes = SCREEN_SIZES.filter(function (inches) {
    return placesThere().some(function (place) { return state.hub.sizes[place] === inches; });
  });
  return !sizes.length ? "hub, empty" : sizes.length > 1 ? "hub, mixed" : "hub, " + sizes[0] + "\"";
};
