
// ---- a Screens tab ------------------------------------------------------------------------
// The two screen boxes, A in blue and B in purple, each with its panel size in the coloured
// band, the module as it is mounted and which way up it is turned, and under them one set of
// pictures, each able to go to A, to B, or to both.
//
// The drawing asks of its page the board's two screens, the pictures on the drive, and each
// scene keeping what its screens show. The size and whether a screen is fitted are the board's,
// so they are changed while the board is set up, the band being the screen's coloured box;
// what a screen shows is the scene's, and chosen at any time.
//
// Which way up a picture is drawn goes with the picture a scene shows, depending on how the
// screen is mounted, how the picture was made, and what the scene wants of it: a picture
// made symmetric can be turned from one scene to the next. So it is the scene's, kept with
// what the screen shows. A picture newly chosen starts at the turn it was last given on
// that screen, which saves setting it again and binds nothing.

var SCREENS = CATALOGUE.screen_ports.map(function (name) {
  return name.slice(-1).toUpperCase();
});

state.screens = {};
SCREENS.forEach(function (letter) {
  state.screens[letter] = {there: true, size: letter === "A" ? "2.8" : "1.54", turn: 0,
                           carried: "", pingpong: false, hold: "", fps: 5, shows: null,
                           kept: null, turns: {}, lastShows: null};
});

// A picture newly chosen on a screen starts as chosenAfresh says. What the screen showed when
// last looked at says whether it is newly chosen, a scene coming round bringing its own turn
function turnForChosen(letter) { chosenAfresh(state.screens[letter]); }
state.media = [];
state.art = {};
state.fileHandle = null;
state.scanned = false;

var BOARD_INK = "#0a0a0a";

var PANEL_INK = "#000000";

var EMPTY_INK = "#2a2f33";

var GROUND_INK = "#0f1113";

var FRAME_INK = "#3d464c";

var FRAME_WIDE = 0.3;

var CHIN_INK = "#131f33";

var HOLE_INK = "#efece6";

var HOLE_EDGE = "#6d7379";

var NAME_INK = "#e8eef2";

var MODULE = {
  "2.8": {board: [48, 88], body: [9.6, 75.2], tab: [4, 44, 88], tabRadius: 4,
          panel: [0.5, 9.4, 47.5, 74.54], lit: [43.2, 57.6]},
  "1.54": {board: [32, 56], body: [9.6, 43.2], tab: [4, 28, 56], tabRadius: 4,
           panel: [0.24, 9.615, 31.76, 43.335], lit: [27.7, 27.7]}
};

var PER_MM = 2.835;

var PRINTED = {
  "2.8": {d: 'M72.585,28.824v1.577h-5.307v-1.398l1.25-.952c.793-.605,2.093-1.567,2.093-2.439,0-.388-.258-.665-.635-.665s-.754.277-.754.853h-1.835c.04-1.497,1.131-2.439,2.628-2.439,1.429,0,2.47.883,2.47,2.152,0,1.438-1.428,2.42-2.241,2.976l-.496.337h2.827Z M75.929,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.525-1.181,1.26-1.181,1.259.496,1.259,1.181Z M82.506,28.387c0,1.23-1.121,2.113-2.877,2.113s-2.876-.883-2.876-2.113c0-.783.446-1.339,1.22-1.646-.595-.308-.932-.812-.932-1.478,0-1.131,1.001-1.904,2.588-1.904s2.589.773,2.589,1.904c0,.675-.337,1.181-.942,1.478.784.308,1.23.863,1.23,1.646ZM80.561,28.209c0-.506-.367-.822-.933-.822s-.932.316-.932.822c0,.517.367.844.932.844s.933-.327.933-.844ZM78.767,25.502c0,.456.337.754.862.754s.863-.298.863-.754c0-.477-.337-.773-.863-.773s-.862.297-.862.773Z M85.682,23.459l-1.062,2.886h-1.438l.437-2.886h2.063ZM88.369,23.459l-1.062,2.886h-1.438l.437-2.886h2.062Z M97.318,28.616v1.785h-4.761v-6.942h2.023v5.157h2.737Z M101.258,30.501c-2.133,0-3.67-1.498-3.67-3.571s1.537-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.179-.675-.754-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.219,1.775-1.677,3.016-3.61,3.016Z M112.091,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.768v-6.942h2.768c2.072,0,3.57,1.458,3.57,3.471ZM110.027,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 21.614, y: 249.80300000000003},
  "1.54": {d: 'M44.498,23.459v6.942h-1.904v-5.366h-1.319v-1.576h3.224Z M48.109,29.32c0,.685-.525,1.181-1.259,1.181s-1.26-.496-1.26-1.181.526-1.181,1.26-1.181,1.259.496,1.259,1.181Z M54.24,28.06c0,1.418-1.15,2.44-2.737,2.44-1.448,0-2.559-.942-2.648-2.252h1.904c.089.348.377.605.744.605.426,0,.793-.357.793-.923,0-.525-.328-.883-.793-.883-.327,0-.585.179-.724.546h-1.795l.595-4.136h4.324v1.576h-3.025l-.159,1.27c.327-.356.813-.564,1.438-.564,1.319,0,2.083.972,2.083,2.32Z M60.947,29.053h-1.051v1.349h-1.904v-1.349h-2.985v-1.389l2.608-4.205h2.281v4.017h1.051v1.577ZM56.801,27.475h1.19l.01-1.944-1.2,1.944Z M64.073,23.459l-1.061,2.886h-1.438l.437-2.886h2.063ZM66.761,23.459l-1.062,2.886h-1.438l.437-2.886h2.063Z M75.71,28.616v1.785h-4.761v-6.942h2.023v5.157h2.738Z M79.649,30.501c-2.132,0-3.67-1.498-3.67-3.571s1.538-3.57,3.67-3.57c1.934,0,3.392,1.229,3.61,3.016h-2.073c-.178-.675-.753-1.161-1.537-1.161-.942,0-1.607.715-1.607,1.706,0,1.002.665,1.726,1.607,1.726.773,0,1.349-.485,1.537-1.16h2.073c-.218,1.775-1.676,3.016-3.61,3.016Z M90.482,26.929c0,2.014-1.498,3.472-3.57,3.472h-2.767v-6.942h2.767c2.073,0,3.57,1.458,3.57,3.471ZM88.419,26.92c0-.972-.645-1.676-1.527-1.676h-.724v3.372h.724c.883,0,1.527-.714,1.527-1.696Z', x: 20.48, y: 159.09400000000002}
};

var PANEL_PX = {"2.8": [240, 320], "1.54": [240, 240]};

var DRAWN = 210;

function svgTag(name, attrs, inner) {
  var out = "<" + name;
  Object.keys(attrs).forEach(function (key) { out += " " + key + "='" + attrs[key] + "'"; });
  return inner === undefined ? out + "/>" : out + ">" + inner + "</" + name + ">";
}

function tabPath(x0, x1, near, far, radius) {
  var edge = far < near ? far + radius : far - radius;
  return "M" + x0 + " " + near +
         " L" + x0 + " " + edge +
         " Q" + x0 + " " + far + " " + (x0 + radius) + " " + far +
         " L" + (x1 - radius) + " " + far +
         " Q" + x1 + " " + far + " " + x1 + " " + edge +
         " L" + x1 + " " + near + " Z";
}

// A screen module drawn with the picture it shows as it stands. panelPreview draws the picture
// composed with its look
function panelDrawing(screen) {
  var made = MODULE[screen.size] || MODULE["2.8"];
  var turn = Number(screen.turn || 0);
  var quarter = turn % 180 === 90;

  var boardW = made.board[0];
  var boardH = made.board[1];
  var extent = Math.max(boardW, boardH);
  var left = (extent - boardW) / 2;
  var bottom = (extent - boardH) / 2;
  function up(y) { return extent - bottom - y; }

  var parts = [];

  parts.push(svgTag("rect", {x: left, y: up(made.body[1]), width: boardW,
                             height: made.body[1] - made.body[0], fill: BOARD_INK}));
  parts.push(svgTag("path", {d: tabPath(left + made.tab[0], left + made.tab[1],
                                        up(made.body[1]), up(made.tab[2]), made.tabRadius),
                             fill: BOARD_INK}));
  parts.push(svgTag("path", {d: tabPath(left + made.tab[0], left + made.tab[1],
                                        up(made.body[0]), up(boardH - made.tab[2]),
                                        made.tabRadius), fill: BOARD_INK}));

  [[8, 5], [16, 3.2], [24, 5], [32, 3.2], [40, 5]].forEach(function (hole) {
    if (hole[0] > boardW - 4) return;      // the small panel has three, not five
    [4, boardH - 4].forEach(function (y) {
      parts.push(svgTag("circle", {cx: left + hole[0], cy: up(y), r: hole[1] / 2,
                                   fill: HOLE_INK, stroke: HOLE_EDGE,
                                   "stroke-width": 0.3}));
    });
  });

  parts.push(svgTag("rect", {x: left + made.panel[0], y: up(made.panel[3]),
                             width: made.panel[2] - made.panel[0],
                             height: made.panel[3] - made.panel[1], fill: PANEL_INK,
                             stroke: FRAME_INK, "stroke-width": FRAME_WIDE}));

  var litW = made.lit[0];
  var litH = made.lit[1];
  var litX = left + boardW / 2 - litW / 2;
  var litY = up(boardH / 2) - litH / 2;
  // A screen may be handed its picture outright, as the program page's preview is
  var art = screen.art || (screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows) : null);

  parts.push(svgTag("rect", {x: litX, y: litY, width: litW, height: litH,
                             fill: art ? GROUND_INK : EMPTY_INK}));
  parts.push(svgTag("rect", {x: litX - 0.4, y: litY + litH, width: litW + 0.8,
                             height: Math.max(0, up(made.panel[1]) - (litY + litH) - 0.4),
                             fill: CHIN_INK}));

  if (screen.shows === "keep") {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"}, "as it is"));
  } else if (art) {
    // Drawn over the module as a plain img, since the browser plays every kind of
    // gif properly there where an image inside svg drops delta frames
  } else if (screen.shows) {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"},
                      "on the board"));
  } else {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#8b959b",
                               "font-size": 4, "font-family": "system-ui"}, "no picture"));
  }

  var name = PRINTED[screen.size] || PRINTED["2.8"];
  parts.push("<g transform='translate(" + (left - name.x / PER_MM) + " " +
             (extent - bottom - name.y / PER_MM) + ") scale(" + (1 / PER_MM) + ")' " +
             "fill='" + NAME_INK + "'>" + svgTag("path", {d: name.d}) + "</g>");

  var holder = document.createElement("div");
  holder.className = "holder";
  holder.innerHTML =
    "<svg width='" + DRAWN + "' height='" + DRAWN + "' viewBox='0 0 " + extent + " " + extent +
    "'><g transform='rotate(" + turn + " " + (extent / 2) + " " + (extent / 2) + ")'>" +
    parts.join("") + "</g></svg>";

  // The picture as the board will draw it: its own pixels, centred, cropped by the
  // lit window, black around it. The window sits on the drawing's exact centre, so
  // a turned module swaps its width and height and nothing else moves; the picture
  // itself stays upright, which is what a viewer of a mounted screen sees
  if (art) {
    var px = PANEL_PX[screen.size] || PANEL_PX["2.8"];
    var scale = (DRAWN / extent) * (litW / px[0]);
    var windowW = (quarter ? litH : litW) * (DRAWN / extent);
    var windowH = (quarter ? litW : litH) * (DRAWN / extent);
    var pane = document.createElement("div");
    pane.style.cssText = "position:absolute;overflow:hidden;" +
      "left:" + ((DRAWN - windowW) / 2) + "px;top:" + ((DRAWN - windowH) / 2) + "px;" +
      "width:" + windowW + "px;height:" + windowH + "px;" +
      "display:flex;align-items:center;justify-content:center";
    var img = document.createElement("img");
    img.src = art.url;
    img.style.cssText = "flex:none;width:" + (art.w * scale) + "px;height:" +
                        (art.h * scale) + "px" + (art.pixelated ? ";image-rendering:pixelated" : "");
    pane.appendChild(img);
    holder.style.position = "relative";
    holder.appendChild(pane);
  }
  return holder;
}

// A box for each screen port. A screen's box has the backlight across its top, what it shows
// straight under the module, and its look's sections under that
function renderScreenBoxes() {
  var box = document.getElementById("screensHead");
  box.textContent = "";
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var side = document.createElement("div");
    side.className = "screen-box " + letter.toLowerCase();
    var head = document.createElement("h3");
    head.appendChild(document.createTextNode("Screen " + letter));
    side.appendChild(head);

    var body = document.createElement("div");
    body.className = "body";
    side.appendChild(body);

    if (!screen.there) {
      body.className = "body adding";
      var add = document.createElement("button");
      add.textContent = "add this screen";
      add.onclick = function () {
        screen.there = true;
        screen.shows = null;
        screen.kept = null;
        draw();
      };
      body.appendChild(add);
      box.appendChild(side);
      return;
    }

    // Taking the screen out is the only way to have none: a screen showing
    // nothing says the same thing twice
    var drop = document.createElement("button");
    drop.className = "drop";
    drop.textContent = "\u00d7";
    drop.title = "Take this screen out of every scene";
    drop.onclick = function () {
      screen.there = false;
      // Every scene's choice for it goes too, since nothing is left to show them
      store();
      allBodies().forEach(function (held) {
        held.screens[letter].shows = null;
        held.screens[letter].kept = null;
      });
      apply(slotAt(state.at).body);
      draw();
    };
    head.appendChild(drop);

    var size = document.createElement("select");
    // The sizes a panel can be, the catalogue's hub being no panel size
    var offered = (CATALOGUE.board_settings["screen" + letter.toLowerCase()] || ["2.8", "1.54"])
      .filter(function (inches) { return inches !== "hub"; });
    if (!screen.size) {
      var quiet = document.createElement("option");
      quiet.value = "";
      quiet.textContent = "size as fitted";
      quiet.selected = true;
      size.appendChild(quiet);
    }
    offered.forEach(function (inches) {
      var option = document.createElement("option");
      option.value = inches;
      option.textContent = inches + " inch";
      if (screen.size === inches) option.selected = true;
      size.appendChild(option);
    });
    size.onchange = function () {
      if (size.value) screen.size = size.value;
      draw();
    };
    size.className = "inband";
    size.title = "Which panel is plugged in, which is the same for every scene";
    head.insertBefore(size, drop);

    body.appendChild(panelPreview(screen));

    // The look's sections, what it shows above them, and its backlight across the top
    body.appendChild(lookSections("screen" + letter, screen, screen.size));
    body.insertBefore(showingLine(screen, letter), body.querySelector(".looksettings"));
    body.insertBefore(lightRow(screen.look.backlight, function (value) {
      screen.look.backlight = value;
    }, "backlight", "How brightly screen " + letter + " is lit, in this scene"), body.firstChild);

    // What the file already says for this screen, where the picker did not write it
    // and no picture can stand for it. It is a line of its own under the settings
    if (screen.kept) {
      var keep = document.createElement("button");
      keep.className = "keep" + (screen.shows === "keep" ? " picked" : "");
      keep.title = screen.kept;
      keep.innerHTML = "<b>Leave it as it is</b><code>" + screen.kept + "</code>";
      keep.onclick = function () { screen.shows = "keep"; draw(); };
      side.appendChild(keep);
    }
    box.appendChild(side);
  });
}

// The pictures on the drive, each with what it is on. The parts below add to them, each after the
// one before: the hub's positions, the whole pictures, the hub's groups
var assetSteps = [];

function renderAssets() {
  var box = document.getElementById("assets");
  box.textContent = "";
  document.getElementById("screensSays").textContent = !state.fileHandle
    ? "open the FX drive to see the pictures on it"
    : !state.scanned
      ? "reading the drive..."
      : state.media.length
        ? "one set of pictures, each able to go to A, to B, or to both"
        : "no pictures on the drive yet; drop a gif, png, jpg or drawing onto it";
  state.media.forEach(function (media) {
    var name = media.name;
    var on = {};
    SCREENS.forEach(function (l) {
      on[l] = state.screens[l].there && state.screens[l].shows === name;
    });
    var cell = document.createElement("div");
    cell.className = "asset" + (on.A && on.B ? " onAB" : on.A ? " onA" : on.B ? " onB" : "");
    var face = document.createElement("div");
    face.className = "face";
    var art = mediaArt(name);
    if (art) {
      face.style.background =
        "repeating-conic-gradient(#e8e4dc 0% 25%, #cbc5bb 0% 50%) 0 0/12px 12px";
      var img = document.createElement("img");
      img.src = art.url;
      face.appendChild(img);
    } else {
      // The extension stands in only until the picture arrives
      face.textContent = name.split(".").pop();
    }
    if (media.kind !== "image") {
      var kind = document.createElement("span");
      kind.className = "kind";
      kind.textContent = media.kind === "folder" ? "slideshow"
                       : media.kind === "drawing" ? "drawing" : "gif";
      face.appendChild(kind);
    }
    cell.appendChild(face);
    cell.title = name;
    var label = document.createElement("div");
    label.className = "label";
    label.textContent = name;
    face.appendChild(label);
    var pick = document.createElement("div");
    pick.className = "pick";
    SCREENS.forEach(function (letter) {
      var button = document.createElement("button");
      button.textContent = letter;
      var lit = on[letter];
      button.className = lit ? "lit" + (letter === "B" ? " b" : "") : "";
      button.disabled = !state.screens[letter].there;
      if (button.disabled) button.style.opacity = ".3";
      button.onclick = function () {
        // Tapping the lit one again takes the picture off this scene's screen,
        // falling back to what the file said where there is something to go back
        // to. A scene showing nothing on a screen leaves it as the scene before
        // left it, which the cross in the header cannot say for one scene alone
        var screen = state.screens[letter];
        screen.shows = screen.shows !== name ? name
                     : screen.kept ? "keep" : null;
        draw();
      };
      pick.appendChild(button);
    });
    cell.appendChild(pick);
    cell.appendChild(binButton(name, media.kind));
    box.appendChild(cell);
  });
  if (state.fileHandle)
    box.appendChild(adderTile("add pictures or drawings",
      {description: "Pictures and drawings the board plays",
       accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"], "text/x-python": [".py"]}},
      "pictures", /\.(gif|png|jpe?g|py)$/i));
  assetSteps.forEach(function (step) { step(); });
}

function mediaNamed(name) {
  return state.media.filter(function (m) { return m.name === name; })[0] || null;
}

// What a screen's entry says in a scene: its look, or the line kept as the file had it. A hub
// writes its positions' entries in place of the screens'
function screenEntry(letter, body) {
  if (state.hub.on) return null;
  var screen = state.screens[letter];
  var playing = body.screens[letter];
  if (!screen.there || !playing.shows) return null;
  if (playing.shows === "keep") return playing.kept;
  var look = playing.look || freshLook();
  return lookEntry("screen" + letter, playing, look, look.backlight, screen.size);
}

function allBodies() {
  return [state.always.body].concat(state.scenes.map(function (scene) { return scene.body; }));
}

// ---- each scene keeps what its screens show ---------------------------------------------------

bodyParts.push({
  capture: function (body) {
    body.screens = {};
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      body.screens[letter] = {shows: screen.shows, kept: screen.kept, pingpong: screen.pingpong,
                              hold: screen.hold, fps: screen.fps, turn: screen.turn};
    });
  },
  apply: function (body) {
    if (!body.screens) return;
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      Object.assign(screen, body.screens[letter]);
      screen.turn = body.screens[letter].turn || 0;
      screen.lastShows = screen.shows;
    });
  },
  blank: function (body) {
    SCREENS.forEach(function (letter) { body.screens[letter].shows = null; });
  },
  hasContent: function (body) {
    return SCREENS.some(function (letter) { return !!(body.screens && body.screens[letter].shows); });
  },
  // A scene's screens are written after its lamps
  entries: function (body, lines) {
    SCREENS.forEach(function (letter) {
      var entry = body.screens && screenEntry(letter, body);
      if (entry) lines.push(entry);
    });
    return lines;
  }
});

// The board line gives a screen's size only where some scene shows something on it. The board
// reserves for a pair wherever two screens are named, which
// slows the one in use
boardLineSteps.before.push(function () {
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var used = screen.there && bodies.some(function (body) {
      return body && body.screens && body.screens[letter].shows;
    });
    screensFitted["screen" + letter.toLowerCase()] = used ? screen.size : "";
  });
});

// ---- drawing the tab -------------------------------------------------------------------------

// The tab's head and its pictures. renderScreensTab puts the board's chips beside what is the
// board's
function renderScreensParts() {
  renderScreensHead();
  renderAssets();
  var head = document.getElementById("screensHead");
  // The band is the screen's coloured box, so it wears the board's chip like the others
  head.querySelectorAll(".screen-box h3").forEach(function (band) {
    band.insertBefore(boardIcon(), band.firstChild);
    band.title = "How the board is built, which is the same in every scene";
  });
  // Whether a screen is fitted and its size are the board's
  if (!setupOn) {
    head.querySelectorAll(".screen-box h3 select, .screen-box h3 .drop, .body.adding button")
      .forEach(function (control) { control.disabled = true; });
  }
}

// The tab's swatch is the two screens, each showing what its screen shows
tabSwatches.screensPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch screenswatch";
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var cell = document.createElement("span");
    cell.className = "screencell " + letter.toLowerCase();
    var art = screen.there && screen.shows ? mediaArt(screen.shows) : null;
    if (art) cell.style.backgroundImage = "url(" + art.url + ")";
    if (!screen.there) cell.classList.add("absent");
    else if (!art) cell.classList.add("blank");
    swatch.appendChild(cell);
  });
  swatch.title = SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    return letter + ": " + (!screen.there ? "not fitted" : screen.shows || "nothing");
  }).join(", ");
};

// Under the tab's name, where the others have their swatch, the size fitted to each screen,
// A then B, the pictures beside it no longer saying which is which
function sizesUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=screensPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  var named = document.createElement("span");
  named.className = "tabname";
  named.appendChild(tab.querySelector("b"));
  var sizes = document.createElement("small");
  sizes.className = "tabunder";
  var fitted = SCREENS.map(function (letter) {
    return state.screens[letter].there ? state.screens[letter].size : "";
  });
  sizes.textContent = fitted.some(Boolean)
    ? fitted.map(function (size) { return size ? size + "\"" : "none"; }).join(", ")
    : "no screens";
  named.appendChild(sizes);
  tab.insertBefore(named, tab.firstChild);
}

// A picture newly chosen is given its starting turn before anything else is drawn, since
// writing the file applies every scene in turn and would take it as already chosen
drawSteps.before.push(function () { SCREENS.forEach(turnForChosen); });

drawSteps.after.push(function () {
  sizesUnderName();
  renderScreensTab();
});

(function () {
  var panel = document.createElement("details");
  panel.className = "panel";
  panel.id = "screensPanel";
  panel.open = true;
  panel.innerHTML = "<summary>Screens</summary>" +
                    "<p class='says screenssays' id='screensSays'></p>" +
                    "<div class='screens-head' id='screensHead'></div>" +
                    "<div class='assets' id='assets'></div>";
  var after = document.getElementById("striprPanel");
  after.parentNode.insertBefore(panel, after.nextSibling);
}());

TAB_NAMES.screensPanel = "Screens";
TAB_PANELS.push("screensPanel");
keptOpen("screensPanel");
