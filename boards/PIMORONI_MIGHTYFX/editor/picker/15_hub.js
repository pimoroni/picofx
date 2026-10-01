
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
state.hub = {on: true, port: "A", sizes: {}, was: {}};
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

// A position shown as a screen of its panel's size, which is what the module drawing asks for
function asScreen(place) {
  var held = state.places[place];
  return {size: state.hub.sizes[place], turn: held.turn, shows: held.shows};
}

// The connector's own colour, A blue and B purple, which the hub takes from the one its
// screens come through
function hubInk() { return state.hub.port === "A" ? "a" : "b"; }

// A picture newly chosen on a position starts at the turn it was last given there
function placeTurnForChosen(place) {
  var held = state.places[place];
  if (held.shows === held.lastShows) return;
  held.turn = (held.shows && held.turns[held.shows]) || 0;
  held.lastShows = held.shows;
}

// ---- each scene keeps what the hub's positions show ------------------------------------------

var oneHubCapture = capture;

capture = function () {
  var body = oneHubCapture();
  body.places = {};
  HUB_PLACES.forEach(function (place) {
    var held = state.places[place];
    body.places[place] = {shows: held.shows, pingpong: held.pingpong, hold: held.hold,
                          fps: held.fps, turn: held.turn};
  });
  return body;
};

var oneHubApply = apply;

apply = function (body) {
  oneHubApply(body);
  if (!body.places) return;
  HUB_PLACES.forEach(function (place) {
    var held = state.places[place];
    Object.assign(held, body.places[place]);
    held.turn = body.places[place].turn || 0;
    held.lastShows = held.shows;
  });
};

var oneHubBlank = blankBody;

blankBody = function () {
  var body = oneHubBlank();
  HUB_PLACES.forEach(function (place) { body.places[place].shows = null; });
  return body;
};

var oneHubContent = hasContent;

hasContent = function (body) {
  return oneHubContent(body) || HUB_PLACES.some(function (place) {
    return !!(body.places && body.places[place].shows);
  });
};

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
// Panels of different sizes are sent apart, so the size is part of it
function playingKey(playing, place) {
  var kind = kindOf(playing.shows);
  return [state.hub.sizes[place], playing.shows, Number(playing.turn) || 0,
          kind !== "image" && playing.pingpong, kind !== "image" && playing.hold,
          kind === "folder" && playing.fps].join("|");
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

function hubEntry(group) {
  var playing = group.playing;
  var kind = kindOf(playing.shows);
  var selector = "hub" + placesSaid(group.places);
  if (Number(playing.turn)) selector += " rotation=" + playing.turn;
  var extras = "";
  if (kind !== "image") {
    if (playing.pingpong) extras += " ping_pong=true";
    if (playing.hold) extras += " hold=" + playing.hold;
  }
  if (kind === "folder")
    return selector + ": sequence folder=" + quoted(playing.shows) + " fps=" + playing.fps +
           extras;
  if (kind === "gif") return selector + ": gif file=" + quoted(playing.shows) + extras;
  return selector + ": image file=" + quoted(playing.shows);
}

// With a hub fitted its positions are written in place of the two screens
var oneHubEntryFor = screenEntry;

screenEntry = function (letter, body) {
  return state.hub.on ? null : oneHubEntryFor(letter, body);
};

var oneHubEntries = entriesOf;

entriesOf = function (body) {
  var lines = oneHubEntries(body);
  if (state.hub.on) placeGroups(body).forEach(function (group) { lines.push(hubEntry(group)); });
  return lines;
};

var oneHubBoardLine = boardLine;

boardLine = function () {
  var line = oneHubBoardLine();
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
};

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

// The picked position's settings, as a screen's are under it
function placeSettings() {
  var settings = document.createElement("div");
  settings.className = "hubsettings";
  if (!placeThere(placePicked)) return settings;
  var held = state.places[placePicked];
  var picture = held.shows;

  var named = document.createElement("b");
  named.className = "placeat";
  named.textContent = "At " + placePicked;
  settings.appendChild(named);

  var turn = document.createElement("select");
  [[0, "not turned"], [90, "quarter"], [180, "half"], [270, "three quarters"]]
    .forEach(function (pair) {
      var option = document.createElement("option");
      option.value = pair[0];
      option.textContent = pair[1];
      if (Number(held.turn || 0) === pair[0]) option.selected = true;
      turn.appendChild(option);
    });
  turn.disabled = !picture;
  turn.title = picture ? "Which way up " + picture + " is drawn at " + placePicked +
                         ", in this scene"
                       : "Which way up a picture is drawn, once one is showing";
  turn.onchange = function () {
    held.turn = Number(turn.value);
    held.turns[picture] = held.turn;
    draw();
  };
  settings.appendChild(turn);

  var media = picture ? mediaNamed(picture) : null;
  if (media && media.kind !== "image") {
    var back = document.createElement("label");
    back.className = "opt";
    var tick = document.createElement("input");
    tick.type = "checkbox";
    tick.checked = held.pingpong;
    tick.onchange = function () { held.pingpong = tick.checked; draw(); };
    back.appendChild(tick);
    back.appendChild(document.createTextNode("back and forth"));
    settings.appendChild(back);

    var holdWrap = document.createElement("label");
    holdWrap.className = "opt";
    holdWrap.appendChild(document.createTextNode("hold"));
    var hold = document.createElement("input");
    hold.type = "number";
    hold.min = 0;
    hold.step = 0.5;
    hold.value = held.hold || "";
    hold.placeholder = "0";
    hold.onchange = function () {
      held.hold = hold.value && Number(hold.value) > 0 ? hold.value : "";
      draw();
    };
    holdWrap.appendChild(hold);
    settings.appendChild(holdWrap);

    if (media.kind === "folder") {
      var fpsWrap = document.createElement("label");
      fpsWrap.className = "opt";
      fpsWrap.appendChild(document.createTextNode("fps"));
      var fps = document.createElement("input");
      fps.type = "number";
      fps.min = 1;
      fps.value = held.fps;
      fps.onchange = function () {
        held.fps = Math.max(1, Number(fps.value) || 5);
        draw();
      };
      fpsWrap.appendChild(fps);
      settings.appendChild(fpsWrap);
    }
  }

  var showing = document.createElement("span");
  showing.className = "showing";
  showing.innerHTML = picture
    ? "showing <b>" + picture + "</b>"
    : state.scenes.length ? "showing nothing here; tap " + placePicked + " under a picture below"
                          : "tap " + placePicked + " under a picture below";
  settings.appendChild(showing);
  return settings;
}

// Whether moving pictures slow here, each different one being sent in turn
function hubPace() {
  var groups = placeGroups(capture());
  var moving = groups.some(function (group) { return kindOf(group.playing.shows) !== "image"; });
  var pace = document.createElement("p");
  pace.className = "hubpace";
  var pictures = groups.map(function (group) { return group.playing.shows; })
    .filter(function (shows, at, all) { return all.indexOf(shows) === at; });
  if (groups.length > 1 && moving && pictures.length === groups.length) {
    pace.textContent = groups.length + " different pictures, each sent in turn, so moving " +
                       "pictures play slower than one picture on several positions.";
  } else if (groups.length > 1 && moving) {
    pace.textContent = "Sent in " + groups.length + " goes, panels of different sizes or " +
                       "turns taking a picture apart, so moving pictures play slower.";
  } else if (groups.length === 1 && groups[0].places.length > 1) {
    pace.textContent = "One picture, sent once to " + placesSaid(groups[0].places) +
                       " together.";
  }
  return pace;
}

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
}

var oneHubHead = renderScreensHead;

renderScreensHead = function () {
  var box = document.getElementById("screensHead");
  if (!state.hub.on) {
    box.classList.remove("hubbed");
    oneHubHead();
  } else {
    renderHubHead();
  }
  var facts = document.getElementById("hubFacts");
  facts.textContent = "";
  facts.appendChild(hubSwitch());
};

// A picture's own row of positions, each tapped to show it there or tapped again to take it off
var oneHubAssets = renderAssets;

renderAssets = function () {
  oneHubAssets();
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
};

// ---- the tab --------------------------------------------------------------------------------

// The tab's swatch is the hub's six positions, each showing what it shows
var oneHubSwatch = tabSwatch;

tabSwatch = function (swatch, panel) {
  if (panel !== "screensPanel" || !state.hub.on) return oneHubSwatch(swatch, panel);
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

var oneHubDraw = draw;

draw = function () {
  HUB_PLACES.forEach(placeTurnForChosen);
  oneHubDraw();
  // Under the tab's name, the hub and the size of its panels, in no more room than the name's
  var under = document.querySelector("#ledTabs .ledtab[data-panel=screensPanel] .tabunder");
  if (!under || !state.hub.on) return;
  var sizes = SCREEN_SIZES.filter(function (inches) {
    return placesThere().some(function (place) { return state.hub.sizes[place] === inches; });
  });
  under.textContent = !sizes.length ? "hub, empty"
                    : sizes.length > 1 ? "hub, mixed" : "hub, " + sizes[0] + "\"";
};

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

// A page can open on the Screens tab, to be looked at
if (/[?&]screens\b/.test(location.search)) chosenTab = "screensPanel";

state.always.body = capture();
showChosen();
draw();
