import {BOARD_LINE_AFTER, SCREEN_SIZES, boardLineSteps} from "../board.js";
import {h, replace} from "../dom.js";
import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps} from "../draw.js";
import {
  BODY_ORDER, DRIVE_ORDER, allBodies, apply, bodyParts, driveParts, otherScenes, slotAt, state,
  store
} from "../scenes.js";
import {mediaArt} from "../screens/screen_art.js";
import {chosenAfresh} from "../screens/screen_settings.js";
import {ASSET_ORDER, HEAD_AFTER, assetSteps, screensHeadSteps} from "../screens/screens.js";
import {tabSwatches} from "../tabs.js";

// ---- a Screen Hub in the Screens tab ----------------------------------------------------------
// A hub takes both connectors. One carries the screens' SPI and the other gives its five pins
// up as chip selects, so one hub reaches six panels, lettered A to F as on the hub itself.
// The hub is drawn for its SPI on A and its selects on B, but nothing stops it being wired
// the other way round. Whether the board has two screens or a hub, which way the hub is wired,
// and which panel is at each position are the board's, set while editing the board. What each
// position shows, and which way up, is the scene's, as it is for a screen.
//
// Positions of one size showing the same picture are sent it once, together, so a wall of one
// picture plays as fast as a single screen. Anything else goes to each position in turn, so
// the tab says when moving pictures will slow for it. The positions share one backlight, which
// the board lights for them all.
//
// The file names a position by the hub's own letter, as outputs are named by number, such as hubB,
// or hubA-C,E for several, with the hub and its panels declared on the board line.

export var HUB_PLACES = ["A", "B", "C", "D", "E", "F"];

// A position taken out keeps the size it had, for if it is put back
state.hub = {on: false, port: "A", sizes: {}, was: {}};
state.places = {};
HUB_PLACES.forEach(function (place) {
  state.hub.sizes[place] = "2.8";
  // off= is a scene turning the position off with `none`, as a screen's is
  state.places[place] = {shows: null, turn: 0, pingpong: false, hold: "", fps: 5,
                         turns: {}, lastShows: null, off: false, pictureTurn: 0};
});

// The position whose settings are shown under the hub
export var placePicked = "A";

// Show a position's settings under the hub
export function pickPlace(place) {
  placePicked = place;
}

// What the hub parts after this one lend to it, filled in as they load: placeGroups(body),
// breakingUp(places) and sendTargets() from the groups, hubEntry(group), offHubEntries(body),
// readBoard() and read(bodies) from the text, and renderHead() and hubSwitch() from the view
export var hubParts = {};

// Whether a position has a panel to show on, its size being "" where it has none
export function placeThere(place) { return state.hub.on && !!state.hub.sizes[place]; }

export function placesThere() { return HUB_PLACES.filter(placeThere); }

// A position shown as a screen of its panel's size, which is what the module drawing asks for,
// with its look and the hub's shared light
export function asScreen(place) {
  var held = state.places[place];
  return {size: state.hub.sizes[place], turn: held.turn, shows: held.shows, off: held.off,
          look: Object.assign({}, held.look, {backlight: state.hubLight})};
}

// What the board shows on a position the scene being edited shows nothing on. The result holds
// always=, Always on's settings for the position, which plays on there even where the scene
// takes another position of its group, or off=, every other scene that shows there where Always
// on does not. It is null where nothing shows, and on the Always on tab
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

// A position shown as a screen in Always on's settings and light, for one the scene leaves to it
export function asAlwaysScreen(place, held) {
  return {size: state.hub.sizes[place], turn: held.turn || 0, shows: held.shows,
          look: Object.assign({}, held.look, {backlight: state.always.body.hubLight})};
}

// The connector's own colour, A blue and B purple, which the hub takes from the one its
// screens come through
export function hubInk() { return state.hub.port === "A" ? "a" : "b"; }

// A picture newly chosen on a position starts as chosenAfresh says
export function placeTurnForChosen(place) { chosenAfresh(state.places[place]); }

// ---- each scene keeps what the hub's positions show ------------------------------------------

addStep(bodyParts, BODY_ORDER, "hub", {
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
  // The board line's hub is read before any scene's lines, since screens write none through a hub
  readBoard: function () { return hubParts.readBoard.apply(null, arguments); },
  read: function () { return hubParts.read.apply(null, arguments); }
});

addStep(bodyParts, BODY_ORDER, "hub", {
  entries: function (body, lines) {
    if (!state.hub.on) return lines;
    hubParts.placeGroups(body).forEach(function (group) { lines.push(hubParts.hubEntry(group)); });
    hubParts.offHubEntries(body).forEach(function (one) { lines.push(one.line); });
    return lines;
  }
});

addStep(boardLineSteps.after, BOARD_LINE_AFTER, "hub", function (line) {
  if (!state.hub.on) return line;
  var rest = line.replace(/^board: ?/, "").replace(/\bscreen[ab]=\S+ ?/g, "").trim();
  // The connector the screens come through, then each size fitted and where, such as hubA-D=2.8
  var tokens = ["screen" + state.hub.port + "=hub"];
  SCREEN_SIZES.forEach(function (inches) {
    var places = placesThere().filter(function (place) {
      return state.hub.sizes[place] === inches;
    });
    if (places.length) tokens.push("hub" + placesSaid(places) + "=" + inches);
  });
  return "board: " + tokens.join(" ") + (rest ? " " + rest : "");
});

// ---- a picture deleted from the drive ---------------------------------------------------------

addStep(driveParts, DRIVE_ORDER, "hub", {
  // A picture still listed was not deleted. One that was comes off every hub position showing it
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

// What the parts after this one add to the hub's box, each after the one before, which are the
// hub's light and then its groups
export var hubHeadSteps = [];

// The hub's box in the Screens tab's head where there is a hub, with the switch between it and
// the screens' boxes above
screensHeadSteps.instead.push(function () {
  if (!state.hub.on) return false;
  hubParts.renderHead();
  return true;
});

addStep(screensHeadSteps.after, HEAD_AFTER, "hub", function () {
  replace(document.getElementById("hubFacts"), hubParts.hubSwitch());
});

// A picture's own row of positions, each tapped to show it there or tapped again to take it off
addStep(assetSteps, ASSET_ORDER, "hub", function () {
  var box = document.getElementById("assets");
  box.classList.toggle("hubbed", state.hub.on);
  if (!state.hub.on) return;
  box.querySelectorAll(".asset:not(.offasset)").forEach(function (cell) {
    var name = cell.dataset.name;
    var on = HUB_PLACES.filter(function (place) {
      return placeThere(place) && state.places[place].shows === name;
    });
    cell.className = "asset" + (on.length ? " on" + state.hub.port : "");
    cell.classList.toggle("hubb", state.hub.port === "B");
    replace(cell.querySelector(".pick"), HUB_PLACES.map(function (place) {
      return h("button", {
        className: on.indexOf(place) >= 0 ? "lit" : "", disabled: !placeThere(place),
        "aria-pressed": String(on.indexOf(place) >= 0),
        onclick: function () {
          var held = state.places[place];
          held.shows = held.shows !== name ? name : null;
          placePicked = place;
          draw();
        }
      }, place);
    }),
    // Every position at once, or off every one where it shows on all
    h("button", {
      className: "all" + (on.length && on.length === placesThere().length ? " lit" : ""),
      "aria-pressed": String(!!on.length && on.length === placesThere().length),
      disabled: !placesThere().length,
      onclick: function () {
        var everywhere = on.length === placesThere().length;
        placesThere().forEach(function (place) {
          state.places[place].shows = everywhere ? null : name;
        });
        draw();
      }
    }, "all"));
  });
});

// ---- the tab --------------------------------------------------------------------------------

// The Off card's buttons are the hub's groups and positions on their own where a hub is on, then
// all, as a picture's are. A group turns off as one, and turning it back on empties it, breaking it
// up where splitsOverAlways() says, as taking a group's picture off does
addStep(assetSteps, ASSET_ORDER, "hub", function () {
  var cell = document.querySelector("#assets .offasset");
  if (!cell || !state.hub.on) return;
  cell.title = "Turn a hub position or group off in this scene";

  function turn(places, off) {
    var breaking = off ? [] : hubParts.breakingUp(places);
    places.forEach(function (place) {
      var held = state.places[place];
      held.off = off;
      if (off) held.shows = null;
    });
    breaking.forEach(function (place) { state.places[place].group = place; });
  }

  // Every position at once, keeping the groups, or back on everywhere where all are off
  var everywhere = placesThere().length && placesThere().every(function (place) {
    return state.places[place].off;
  });
  replace(cell.querySelector(".pick"), hubParts.sendTargets().map(function (target) {
    var off = target.places.every(function (place) { return state.places[place].off; });
    return h("button", {
      type: "button", className: off ? "lit" : "", "aria-pressed": String(off),
      style: {background: off && target.ink ? target.ink : null},
      title: target.ink ? "Group " + target.name + ", " + placesSaid(target.places)
                        : target.name + ", on its own",
      onclick: function () {
        placePicked = target.places[0];
        turn(target.places, !off);
        draw();
      }
    }, target.name);
  }), h("button", {
    type: "button", className: everywhere ? "lit" : "", "aria-pressed": String(!!everywhere),
    title: everywhere ? "Back on at every position"
                      : "Off at every group and every position on its own, keeping the groups",
    disabled: !placesThere().length,
    onclick: function () {
      turn(placesThere(), !everywhere);
      draw();
    }
  }, "all"));
});

var screensSwatch = tabSwatches.screensPanel;

// The tab's swatch is the hub's six positions, each showing what it shows, where a hub is on
tabSwatches.screensPanel = function (swatch) {
  if (!state.hub.on) return screensSwatch(swatch);
  swatch.className = "accswatch screenswatch hubswatch";
  replace(swatch, HUB_PLACES.map(function (place) {
    var held = state.places[place];
    // Off is black, and Always on's picture wears the stripes of nothing, as on two screens
    var under = placeThere(place) ? placeUnder(place) : null;
    var shown = held.shows || (under && under.always ? under.always.shows : null);
    var art = placeThere(place) && shown ? mediaArt(shown) : null;
    // A picture with no thumbnail yet is a white tile, its position showing something
    var marked = !placeThere(place) ? "absent" : held.off ? "off" : art ? ""
               : shown ? "blank" : under && under.off ? "dark" : "nothing";
    return h("span", {
      className: "screencell " + hubInk() + (marked ? " " + marked : ""),
      style: {"background-image": art ? (under && under.always ? "var(--through), " : "") +
                                        "url(" + art.url + ")" : null}
    });
  }));
  swatch.title = HUB_PLACES.map(function (place) {
    var held = state.places[place];
    var under = placeThere(place) ? placeUnder(place) : null;
    return place + ": " + (!placeThere(place) ? "no panel" : held.off ? "off"
                           : held.shows || (under && under.always ? "Always on's " +
                                            under.always.shows : "nothing"));
  }).join(", ");
};

addStep(drawSteps.before, DRAW_BEFORE, "hubTurns", function () {
  HUB_PLACES.forEach(placeTurnForChosen);
});

addStep(drawSteps.after, DRAW_AFTER, "hub", function () {
  // Under the tab's name, the hub and the size of its panels, in no more room than the name's
  var under = document.querySelector("#ledTabs .ledtab[data-panel=screensPanel] .tabunder");
  if (!under || !state.hub.on) return;
  var sizes = SCREEN_SIZES.filter(function (inches) {
    return placesThere().some(function (place) { return state.hub.sizes[place] === inches; });
  });
  under.textContent = !sizes.length ? "hub, empty"
                    : sizes.length > 1 ? "hub, mixed" : "hub, " + sizes[0] + "\"";
});

// The switch takes the place of the line the tab opened with, at the top where the other
// tabs have their board box
document.getElementById("screensSays").before(h("div", {className: "facts", id: "hubFacts"}));
document.getElementById("screensSays").hidden = true;

// ---- what the file says ----------------------------------------------------------------------

// Positions as the file names them, a run of neighbours as a range, such as "A-C,E"
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
