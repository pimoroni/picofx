
// ---- a Screen Hub in the Screens tab ----------------------------------------------------------
// A hub takes both connectors: one carries the screens' SPI and the other gives its five pins
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
// The file names a position by the hub's own letter, as outputs are named by number: hubB, or
// hubA-C,E for several, with the hub and its panels declared on the board line.

var HUB_PLACES = ["A", "B", "C", "D", "E", "F"];

// A position taken out keeps the size it had, for if it is put back
state.hub = {on: false, port: "A", sizes: {}, was: {}};
state.places = {};
HUB_PLACES.forEach(function (place) {
  state.hub.sizes[place] = "2.8";
  state.places[place] = {shows: null, turn: 0, pingpong: false, hold: "", fps: 5,
                         turns: {}, lastShows: null};
});

// The position whose settings are shown under the hub
var placePicked = "A";

// Whether a position has a panel to show on, its size being "" where it has none
function placeThere(place) { return state.hub.on && !!state.hub.sizes[place]; }

function placesThere() { return HUB_PLACES.filter(placeThere); }

// A position shown as a screen of its panel's size, which is what the module drawing asks for,
// with its look and the hub's shared light
function asScreen(place) {
  var held = state.places[place];
  return {size: state.hub.sizes[place], turn: held.turn, shows: held.shows,
          look: Object.assign({}, held.look, {backlight: state.hubLight})};
}

// The connector's own colour, A blue and B purple, which the hub takes from the one its
// screens come through
function hubInk() { return state.hub.port === "A" ? "a" : "b"; }

// A picture newly chosen on a position starts as chosenAfresh says
function placeTurnForChosen(place) { chosenAfresh(state.places[place]); }

// ---- each scene keeps what the hub's positions show ------------------------------------------

bodyParts.push({
  capture: function (body) {
    body.places = {};
    HUB_PLACES.forEach(function (place) {
      var held = state.places[place];
      body.places[place] = {shows: held.shows, pingpong: held.pingpong, hold: held.hold,
                            fps: held.fps, turn: held.turn};
    });
  },
  apply: function (body) {
    if (!body.places) return;
    HUB_PLACES.forEach(function (place) {
      var held = state.places[place];
      Object.assign(held, body.places[place]);
      held.turn = body.places[place].turn || 0;
      held.lastShows = held.shows;
    });
  },
  blank: function (body) {
    HUB_PLACES.forEach(function (place) { body.places[place].shows = null; });
  },
  hasContent: function (body) {
    return HUB_PLACES.some(function (place) { return !!(body.places && body.places[place].shows); });
  }
});

// ---- what the file says ----------------------------------------------------------------------

// Positions as the file names them, a run of neighbours as a range: "A-C,E"
function placesSaid(places) {
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

// A picture's kind, from the drive or its name
function kindOf(shows) {
  var media = mediaNamed(shows);
  return media ? media.kind
       : /\.gif$/i.test(shows) ? "gif"
       : /\.(png|jpe?g)$/i.test(shows) ? "image" : "folder";
}

// What a position plays, as a key: positions with the same key are one entry, and one stream.
// Panels of different sizes are sent apart, so the size is part of it. They are one send where
// the file would say the same for them, so a setting a picture does not take, such as a still's
// pace, or one the page only remembers, such as the last custom colour, never splits them
function playingKey(playing, place) {
  var look = playing.look || LOOK_START;
  var size = state.hub.sizes[place];
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  return [size, playing.shows].concat(placingTokens(playing.turn, look, 1, where))
    .concat(playingTokens(playing, look, kindOf(playing.shows), size)).join("|");
}

// The positions of one scene, gathered into what each different picture is sent to
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

// A group's entry. Every position is lit by the hub's one light, so each entry carries it
function hubEntry(group) {
  return lookEntry("hub" + placesSaid(group.places), group.playing,
                   group.playing.look || freshLook(), state.hubLight,
                   state.hub.sizes[group.places[0]]);
}

bodyParts.push({
  entries: function (body, lines) {
    if (state.hub.on) placeGroups(body).forEach(function (group) { lines.push(hubEntry(group)); });
    return lines;
  }
});

boardLineSteps.after.push(function (line) {
  if (!state.hub.on) return line;
  var rest = line.replace(/^board: ?/, "").replace(/\bscreen[ab]=\S+ ?/g, "").trim();
  // The connector the screens come through, then each size fitted and where: hubA-D=2.8
  var tokens = ["screen" + state.hub.port + "=hub"];
  SCREEN_SIZES.forEach(function (inches) {
    var places = placesThere().filter(function (place) {
      return state.hub.sizes[place] === inches;
    });
    if (places.length) tokens.push("hub" + placesSaid(places) + "=" + inches);
  });
  return "board: " + tokens.join(" ") + (rest ? " " + rest : "");
});

// ---- drawing the hub -------------------------------------------------------------------------

// Two screens or a hub, the hub taking both connectors. It is always shown, so it can be seen
// to be a choice, and only changed while editing the board. It sits at the top of the tab,
// where the outputs and strips have their board box, and at that box's size
function hubSwitch() {
  var row = document.createElement("div");
  row.className = "hubswitch" + (setupOn ? "" : " locked");
  row.title = setupOn ? "" : "How the board is built, the same in every scene. Edit board to " +
                             "change it";
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
  size.title = "Which panel is at " + place + ", which is the same for every scene";
  size.onclick = function (event) { event.stopPropagation(); };
  size.onchange = function () {
    state.hub.sizes[place] = size.value;
    draw();
  };
  top.appendChild(size);

  var drawing = panelPreview(asScreen(place));
  tile.appendChild(drawing);
  var says = document.createElement("small");
  says.className = "placesays";
  says.textContent = held.shows || "nothing";
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
    placePicked = place;
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
  settings.appendChild(lookSections("place" + placePicked, held, state.hub.sizes[placePicked]));
  return settings;
}

// Whether moving pictures slow here: the sends share the hub's speed, a still picture sent once
// costing the rest nothing
function hubPace() {
  var sends = placeGroups(capture());
  var moving = sends.filter(function (send) { return kindOf(send.playing.shows) !== "image"; });
  var still = sends.filter(function (send) { return kindOf(send.playing.shows) === "image"; });
  var said = [];
  if (moving.length > 1) {
    said.push(namesSaid(moving) + " share the hub's speed, so each animation plays slower " +
              "than it would alone.");
  } else if (moving.length === 1) {
    var together = moving[0].places.length;
    said.push(namesSaid(moving) + (together > 1 ? (together === 2 ? " both" : " all") +
              " play their animation at once, as fast as a single screen."
                                                : " plays its animation at full speed."));
  }
  if (still.length)
    said.push(namesSaid(still) + (still.length > 1 || still[0].places.length > 1 ? " show"
                                                                                  : " shows") +
              " a still picture, sent once" + (moving.length ? ", costing the rest nothing."
                                                             : ", so nothing slows."));
  var apart = apartSaid(sends);
  if (apart) said.push(apart);
  var pace = document.createElement("p");
  pace.className = "hubpace" + (said.length ? "" : " quiet");
  pace.innerHTML = said.join(" ");
  return pace;
}

// The hub's box, in place of the screens'. The parts below add to it, each after the one before:
// the hub's light, its groups
var hubHeadSteps = [];

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
  port.title = "Which connector the hub's SPI is plugged into, and which its Selects, as " +
               "printed on the hub";
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

// The Screens tab's head: a box for each screen, or the hub's box where there is one, with the
// switch between them above
function renderScreensHead() {
  var box = document.getElementById("screensHead");
  if (!state.hub.on) {
    box.classList.remove("hubbed");
    renderScreenBoxes();
  } else {
    renderHubHead();
  }
  var facts = document.getElementById("hubFacts");
  facts.textContent = "";
  facts.appendChild(hubSwitch());
}

// A picture's own row of positions, each tapped to show it there or tapped again to take it off
assetSteps.push(function () {
  var box = document.getElementById("assets");
  box.classList.toggle("hubbed", state.hub.on);
  if (!state.hub.on) return;
  box.querySelectorAll(".asset").forEach(function (cell, at) {
    var name = state.media[at].name;
    var on = HUB_PLACES.filter(function (place) {
      return placeThere(place) && state.places[place].shows === name;
    });
    cell.className = "asset" + (on.length ? " on" + state.hub.port : "");
    cell.classList.toggle("hubb", state.hub.port === "B");
    var pick = cell.querySelector(".pick");
    pick.textContent = "";
    HUB_PLACES.forEach(function (place) {
      var button = document.createElement("button");
      button.textContent = place;
      button.className = on.indexOf(place) >= 0 ? "lit" : "";
      button.disabled = !placeThere(place);
      button.onclick = function () {
        var held = state.places[place];
        held.shows = held.shows !== name ? name : null;
        placePicked = place;
        draw();
      };
      pick.appendChild(button);
    });
    // Every position at once, or off every one where it shows on all
    var all = document.createElement("button");
    all.className = "all" + (on.length && on.length === placesThere().length ? " lit" : "");
    all.textContent = "all";
    all.disabled = !placesThere().length;
    all.onclick = function () {
      var everywhere = on.length === placesThere().length;
      placesThere().forEach(function (place) {
        state.places[place].shows = everywhere ? null : name;
      });
      draw();
    };
    pick.appendChild(all);
  });
});

// ---- the tab --------------------------------------------------------------------------------

// The tab's swatch is the hub's six positions, each showing what it shows, where a hub is on
var screensSwatch = tabSwatches.screensPanel;

tabSwatches.screensPanel = function (swatch) {
  if (!state.hub.on) return screensSwatch(swatch);
  swatch.textContent = "";
  swatch.className = "accswatch screenswatch hubswatch";
  HUB_PLACES.forEach(function (place) {
    var held = state.places[place];
    var cell = document.createElement("span");
    cell.className = "screencell " + hubInk();
    var art = placeThere(place) && held.shows ? mediaArt(held.shows) : null;
    if (art) cell.style.backgroundImage = "url(" + art.url + ")";
    if (!placeThere(place)) cell.classList.add("absent");
    else if (!art) cell.classList.add("blank");
    swatch.appendChild(cell);
  });
  swatch.title = HUB_PLACES.map(function (place) {
    return place + ": " + (!placeThere(place) ? "no panel" : state.places[place].shows ||
                                                              "nothing");
  }).join(", ");
};

drawSteps.before.push(function () { HUB_PLACES.forEach(placeTurnForChosen); });

drawSteps.after.push(function () {
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
(function () {
  var says = document.getElementById("screensSays");
  var facts = document.createElement("div");
  facts.className = "facts";
  facts.id = "hubFacts";
  says.parentNode.insertBefore(facts, says);
  says.hidden = true;
}());
