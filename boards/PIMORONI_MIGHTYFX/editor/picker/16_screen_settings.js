
// ---- every setting a screen takes -------------------------------------------------------------
// A screen takes more than its picture and turn: how brightly it is lit, where
// a picture is put and what fills round it, and how a moving picture is paced and looped. All of
// them go with what a screen shows in a scene, as the turn does, so each screen and each hub
// position keeps a look beside its picture and each scene keeps its own.
//
// Under the module is what it shows, then four sections that fold: orientation, placement,
// background, and playback last, being there only for a moving picture, so the three above it
// never move. Labels are the settings' own names, a choice a row of buttons drawn as what it
// does, and anything on or off a toggle. The module drawings show every setting as the board
// would draw it.
//
// The backlight is the screen's, a row across the top of its box. The hub's positions share one
// backlight, so the hub has one for all six, in each scene.

// anchor is which of nine places the picture sits at, left to right and top to bottom, the
// middle being centred, and null where x and y are typed. tile is across and tileDown down, each
// "off", "repeat" or "mirror". customBg is the last custom background, kept while a swatch is
// chosen so custom comes back to it. canvas is a drawing's: "whole", "half" or "set", its size
// then canvasW by canvasH
var LOOK_START = {backlight: 1, mirror: false, anchor: 4, x: "", y: "", bg: "#000000",
                  customBg: "", double: false, tile: "off", tileDown: "off", pace: "saved",
                  every: 5, loop: true, whole: false, holdBack: "", canvas: "whole",
                  canvasW: 120, canvasH: 120};

function freshLook() { return Object.assign({}, LOOK_START); }

SCREENS.forEach(function (letter) { state.screens[letter].look = freshLook(); });
HUB_PLACES.forEach(function (place) { state.places[place].look = freshLook(); });
state.hubLight = 1;

// Colours the file can say by name, the words the board knows, the rest written as hex
var BG_NAMES = {};
Object.keys(WORDS).forEach(function (name) { BG_NAMES["#" + hexOf(WORDS[name])] = name; });

// ---- where a picture sits ---------------------------------------------------------------------
// The nine places are worked out from the picture's size against the panel's, turned and doubled
// as it is drawn, and written as the pixels the file takes. A picture of another size put in the
// same file later sits where those pixels say, not at the edge chosen

var ANCHOR_NAMES = ["top left", "top", "top right", "left", "centred", "right", "bottom left",
                    "bottom", "bottom right"];

function panelPixels(size, turn) {
  var panel = PANEL_PX[size] || PANEL_PX["2.8"];
  return Number(turn || 0) % 180 === 90 ? [panel[1], panel[0]] : [panel[0], panel[1]];
}

// A drawing's canvas in pixels: the screen's as it is turned, half that, or a size set by hand
function canvasPixels(look, size, turn) {
  var panel = panelPixels(size, turn);
  if (look.canvas === "set") return [Number(look.canvasW), Number(look.canvasH)];
  if (look.canvas === "half") return [Math.floor(panel[0] / 2), Math.floor(panel[1] / 2)];
  return panel;
}

// The picture as drawn, in pixels, or null until it has loaded or where it fills the screen
function picturePixels(shows, look, size, turn) {
  var scale = look.double ? 2 : 1;
  if (shows && kindOf(shows) === "drawing") {
    var canvas = canvasPixels(look, size, turn);
    var panel = panelPixels(size, turn);
    var drawn = [canvas[0] * scale, canvas[1] * scale];
    return drawn[0] === panel[0] && drawn[1] === panel[1] ? null : drawn;
  }
  var art = shows && shows !== "keep" ? mediaArt(shows) : null;
  if (!art || !art.w) return null;
  return [art.w * scale, art.h * scale];
}

// The offset a look writes, each side "" where centred
function pictureOffset(look, shows, size, turn) {
  if (look.anchor === null || look.anchor === undefined) return {x: look.x, y: look.y};
  var picture = picturePixels(shows, look, size, turn);
  var panel = panelPixels(size, turn);
  function side(at, axis) {
    if (at === 1 || !picture) return "";
    return at === 0 ? "0" : String(panel[axis] - picture[axis]);
  }
  return {x: side(look.anchor % 3, 0), y: side(Math.floor(look.anchor / 3), 1)};
}

// ---- pictures made for placing ----------------------------------------------------------------
// A small tile and a half-size sprite, which the placing settings are for, and a folder whose
// names each say how long their picture shows

madePicture("bricks.png", "image", 40, 40, function (g, w, h) {
  g.fillStyle = "#8a3b24";
  g.fillRect(0, 0, w, h);
  g.fillStyle = "#c9b8a0";
  g.fillRect(0, 18, w, 3);
  g.fillRect(0, 38, w, 2);
  g.fillRect(18, 0, 3, 18);
  g.fillRect(0, 21, 3, 17);
  g.fillRect(37, 21, 3, 17);
});
madePicture("ghost.png", "image", 96, 96, function (g, w, h) {
  var cells = ["....XXXX....", "..XXXXXXXX..", ".XXXXXXXXXX.", ".XX..XX..XX.",
               ".XX..XX..XX.", "XXXXXXXXXXXX", "XXXXXXXXXXXX", "XXXXXXXXXXXX",
               "XXXXXXXXXXXX", "XXXXXXXXXXXX", "XX.XXX.XXX.X", "X...X...X..."];
  var size = w / 12;
  g.clearRect(0, 0, w, h);
  cells.forEach(function (row, y) {
    row.split("").forEach(function (cell, x) {
      if (cell !== "X") return;
      g.fillStyle = (y === 3 || y === 4) && x % 4 !== 0 && x % 4 !== 3 ? "#1b2a6b" : "#f06aa8";
      g.fillRect(x * size, y * size, size, size);
    });
  });
});
madePicture("clock", "folder", 240, 240, function (g, w, h) {
  g.fillStyle = "#f4efe4";
  g.fillRect(0, 0, w, h);
  g.strokeStyle = "#2b2622";
  g.lineWidth = 8;
  g.beginPath();
  g.arc(w / 2, h / 2, 90, 0, Math.PI * 2);
  g.stroke();
  g.lineWidth = 6;
  g.beginPath();
  g.moveTo(w / 2, h / 2);
  g.lineTo(w / 2, h / 2 - 64);
  g.moveTo(w / 2, h / 2);
  g.lineTo(w / 2 + 44, h / 2);
  g.stroke();
});
// Whether a folder's names each say how long their picture shows: clock_0001_500ms.png
mediaNamed("clock").named = true;

// ---- drawings -------------------------------------------------------------------------------------
// A drawing is a Python file drawn on a screen, graphics file=rings.py. It is listed only where
// its opening string begins "Drawing:", which gives its name, then a line describing it, then
// optionally Icon:, any Unicode character, and Colour:, one of the board's colour words or a hex.
// A Python file without that line is not listed, whether drawing or program. The page cannot run
// one, so a drawing is shown by its icon on its colour, or its initial where it names no icon,
// the colour where it names none coming from its name

// A number from a name, the same each time, past the first draws which barely move between
// names of one length
function nameHue(name) {
  var hash = 2166136261;
  for (var at = 0; at < name.length; at++) {
    hash ^= name.charCodeAt(at);
    hash = Math.imul(hash, 16777619);
  }
  for (var mix = 0; mix < 3; mix++) {
    hash = Math.imul(hash ^ (hash >>> 15), 2246822507);
    hash = Math.imul(hash ^ (hash >>> 13), 3266489909);
    hash ^= hash >>> 16;
  }
  return (hash >>> 0) % 360;
}

// The opening strings of the drawings on the drive, as the page would read them from each file
var DRAWING_FILES = [
  ["rings.py", "Drawing: Rings\nRings that grow and fade, in the four colours.\n" +
               "Icon: " + String.fromCodePoint(0x1F3AF) + "\nColour: orange"],
  ["starfield.py", "Drawing: Starfield\nTravel through a field of stars.\n" +
                   "Icon: " + String.fromCodePoint(0x2605) + "\nColour: 5a6cff"],
  ["sketch.py", "Drawing: Sketch\nLines drawn and wiped, over and over."],
  // A program, not a drawing, so it is not listed
  ["departures.py", "Departures from the local stop, on every screen the board has."]
];

// What an opening string says of a drawing, or null for a file that is not one
function drawingSaid(docstring) {
  var lines = docstring.split("\n");
  var named = lines[0].match(/^Drawing:\s*(.+)$/);
  if (!named) return null;
  var said = {title: named[1].trim(), description: "", icon: "", colour: ""};
  lines.slice(1).forEach(function (line) {
    var field = line.match(/^(Icon|Colour):\s*(.+)$/);
    if (field) said[field[1].toLowerCase()] = field[2].trim();
    else if (!said.description) said.description = line.trim();
  });
  return said;
}

// A drawing's colour as a CSS colour: a word the board knows, a hex, or one from its name
function drawingInk(drawing, name) {
  var word = WORDS[drawing.colour.toLowerCase()];
  if (word) return rgbInk(word);
  if (/^#?[0-9a-f]{6}$/i.test(drawing.colour)) return "#" + drawing.colour.replace("#", "");
  return "hsl(" + nameHue(name) + ",60%,45%)";
}

var drawingArts = {};

// A drawing's face at a canvas's size, for where a picture's pixels are drawn: its colour filling
// the canvas and its icon or initial in the middle, the canvas the size the drawing draws at
function drawingArt(name, wide, high) {
  var key = name + "|" + wide + "|" + high;
  if (drawingArts[key]) return drawingArts[key];
  var drawing = mediaNamed(name).drawing;
  var canvas = document.createElement("canvas");
  canvas.width = wide;
  canvas.height = high;
  var g = canvas.getContext("2d");
  g.fillStyle = drawingInk(drawing, name);
  g.fillRect(0, 0, wide, high);
  g.fillStyle = "#fff";
  g.textAlign = "center";
  g.textBaseline = "middle";
  var glyph = Math.round(Math.min(wide, high) * 0.46);
  g.font = drawing.icon ? glyph + "px 'Segoe UI Symbol', system-ui" : "bold " + glyph + "px system-ui";
  g.fillText(drawing.icon || drawing.title[0], wide / 2, high / 2);
  drawingArts[key] = {url: canvas.toDataURL(), w: wide, h: high, ratio: wide / high};
  return drawingArts[key];
}

// Its face as a square, for the tab's swatch
function madeDrawing(name) { state.art[name] = drawingArt(name, 240, 240); }

DRAWING_FILES.forEach(function (file) {
  var drawing = drawingSaid(file[1]);
  if (!drawing) return;
  state.media.push({name: file[0], kind: "drawing", drawing: drawing});
  madeDrawing(file[0]);
});

// ---- drawing a look on the module -------------------------------------------------------------

var loadedArt = {};

// A picture's pixels, loaded once. Until it arrives the drawing waits a frame
function artImage(art) {
  if (loadedArt[art.url]) return loadedArt[art.url].complete ? loadedArt[art.url] : null;
  var image = new Image();
  image.onload = function () { draw(); };
  image.src = art.url;
  loadedArt[art.url] = image;
  return null;
}

var composed = {};

// The panel as the board would draw it: the background, then the picture where the look puts
// it, doubled, flipped or tiled, under the light's dimming. Sized to the panel as it is turned,
// so the module drawing shows it whole
function composedArt(screen, look, art) {
  var panel = PANEL_PX[screen.size] || PANEL_PX["2.8"];
  var quarter = Number(screen.turn || 0) % 180 === 90;
  var wide = quarter ? panel[1] : panel[0];
  var high = quarter ? panel[0] : panel[1];
  var key = [art.url.length, screen.shows, wide, high, JSON.stringify(look)].join("|");
  if (composed[key]) return composed[key];
  var image = artImage(art);
  if (!image) return null;

  var canvas = document.createElement("canvas");
  canvas.width = wide;
  canvas.height = high;
  composeOnto(canvas.getContext("2d"), screen, look, art, image, wide, high);
  var made = {url: canvas.toDataURL(), w: wide, h: high, ratio: wide / high};
  composed[key] = made;
  return made;
}

// The picture placed on a panel's canvas, as the board draws it, from the image's frame now
function composeOnto(g, screen, look, art, image, wide, high) {
  g.imageSmoothingEnabled = false;
  g.fillStyle = look.bg;
  g.fillRect(0, 0, wide, high);

  var scale = look.double ? 2 : 1;
  var pictureW = art.w * scale;
  var pictureH = art.h * scale;
  var where = pictureOffset(look, screen.shows, screen.size, screen.turn);
  var left = where.x === "" ? Math.round((wide - pictureW) / 2) : Number(where.x);
  var top = where.y === "" ? Math.round((high - pictureH) / 2) : Number(where.y);

  function copy(x, y, flipX, flipY) {
    g.save();
    g.translate(x + (flipX ? pictureW : 0), y + (flipY ? pictureH : 0));
    g.scale(flipX ? -1 : 1, flipY ? -1 : 1);
    g.drawImage(image, 0, 0, pictureW, pictureH);
    g.restore();
  }

  // Copies laid out from where the first sits, along each side that tiles, every other one
  // turned round on a side that mirrors
  var tileDown = look.tileDown || "off";
  var firstX = look.tile === "off" ? left : left - Math.ceil(left / pictureW) * pictureW;
  var firstY = tileDown === "off" ? top : top - Math.ceil(top / pictureH) * pictureH;
  var lastX = look.tile === "off" ? left : wide - 1;
  var lastY = tileDown === "off" ? top : high - 1;
  for (var y = firstY; y <= lastY; y += pictureH) {
    for (var x = firstX; x <= lastX; x += pictureW) {
      var across = Math.round((x - left) / pictureW);
      var down = Math.round((y - top) / pictureH);
      copy(x, y, look.mirror !== (look.tile === "mirror" && across % 2 !== 0),
           tileDown === "mirror" && down % 2 !== 0);
    }
  }

  if (look.backlight < 1) {
    g.fillStyle = "rgba(0,0,0," + ((1 - look.backlight) * 0.9) + ")";
    g.fillRect(0, 0, wide, high);
  }
}

// ---- a gif keeps playing on its screen ----------------------------------------------------------
// A canvas given a gif always draws its first frame, so a composed picture of one is a still. Where
// the browser can decode a gif itself (ImageDecoder, in Chrome and Edge), the preview is a canvas
// stepping through the gif's frames at its own timings, each composed as the board draws it.
// Elsewhere the still stays

// Each gif's decoder, shared by every preview showing it, and the frames it has already given
var gifDecoders = {};

function gifDecoder(art) {
  if (!gifDecoders[art.url]) {
    gifDecoders[art.url] = fetch(art.url).then(function (answer) {
      return answer.arrayBuffer();
    }).then(function (bytes) {
      var decoder = new ImageDecoder({data: bytes, type: "image/gif"});
      return decoder.tracks.ready.then(function () {
        return {decoder: decoder, frames: decoder.tracks.selectedTrack.frameCount};
      });
    });
  }
  return gifDecoders[art.url];
}

function liveGif(drawing, still, screen, look, art) {
  if (typeof ImageDecoder === "undefined") return;
  var shown = Array.prototype.filter.call(drawing.querySelectorAll("img"), function (one) {
    return one.getAttribute("src") === still.url;
  })[0];
  if (!shown) return;
  var playing = {screen: Object.assign({}, screen), look: look, art: art, at: 0, canvas: null};

  gifDecoder(art).then(function (gif) {
    if (!shown.isConnected || gif.frames < 2) return;
    var canvas = document.createElement("canvas");
    canvas.width = still.w;
    canvas.height = still.h;
    canvas.className = shown.className;
    canvas.style.cssText = shown.style.cssText;
    shown.parentNode.replaceChild(canvas, shown);
    playing.canvas = canvas;
    nextGifFrame(playing, gif);
  }).catch(function () {});
}

// One frame composed onto the preview, then the next after that frame's own time, until the
// preview leaves the page
function nextGifFrame(playing, gif) {
  if (!playing.canvas.isConnected) return;
  gif.decoder.decode({frameIndex: playing.at}).then(function (decoded) {
    var frame = decoded.image;
    composeOnto(playing.canvas.getContext("2d"), playing.screen, playing.look, playing.art, frame,
                playing.canvas.width, playing.canvas.height);
    // A frame's time is in microseconds, and a gif saying none plays at ten a second
    var wait = frame.duration ? frame.duration / 1000 : 100;
    frame.close();
    playing.at = (playing.at + 1) % gif.frames;
    setTimeout(function () { nextGifFrame(playing, gif); }, Math.max(20, wait));
  }).catch(function () {});
}

var oneLookPreview = panelPreview;

panelPreview = function (screen) {
  var art = screen.look && screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows)
                                                                     : null;
  // A drawing is drawn at its canvas's size, then placed and doubled as a picture is
  if (art && kindOf(screen.shows) === "drawing") {
    var canvas = canvasPixels(screen.look, screen.size, screen.turn);
    art = drawingArt(screen.shows, canvas[0], canvas[1]);
  }
  var made = art ? composedArt(screen, screen.look, art) : null;
  if (!made) return oneLookPreview(screen);
  var name = "~look" + Object.keys(state.art).length;
  state.art[name] = made;
  var drawing = oneLookPreview(Object.assign({}, screen, {shows: name}));
  delete state.art[name];
  if (kindOf(screen.shows) === "gif") liveGif(drawing, made, screen, screen.look, art);
  return drawing;
};

// A hub position is drawn with its look, and the hub's shared light
var oneLookAsScreen = asScreen;

asScreen = function (place) {
  var screen = oneLookAsScreen(place);
  screen.look = Object.assign({}, state.places[place].look, {backlight: state.hubLight});
  return screen;
};

// ---- each scene keeps its screens' looks ------------------------------------------------------

var oneLookCapture = capture;

capture = function () {
  var body = oneLookCapture();
  SCREENS.forEach(function (letter) {
    body.screens[letter].look = Object.assign({}, state.screens[letter].look);
  });
  HUB_PLACES.forEach(function (place) {
    body.places[place].look = Object.assign({}, state.places[place].look);
  });
  body.hubLight = state.hubLight;
  return body;
};

// Each screen and position keeps one look object for good, a scene's values copied into it, so
// a control drawn before a scene is re-applied still changes the look that is written
var lookHomes = {};
SCREENS.forEach(function (letter) { lookHomes["screen" + letter] = state.screens[letter].look; });
HUB_PLACES.forEach(function (place) { lookHomes["place" + place] = state.places[place].look; });

var oneLookApply = apply;

apply = function (body) {
  oneLookApply(body);
  SCREENS.forEach(function (letter) {
    var home = lookHomes["screen" + letter];
    if (body.screens && body.screens[letter].look) Object.assign(home, body.screens[letter].look);
    state.screens[letter].look = home;
  });
  HUB_PLACES.forEach(function (place) {
    var home = lookHomes["place" + place];
    if (body.places && body.places[place].look) Object.assign(home, body.places[place].look);
    state.places[place].look = home;
  });
  if (body.hubLight !== undefined) state.hubLight = body.hubLight;
};

// ---- what the file says -----------------------------------------------------------------------

// The settings before the colon: how the screen is turned and lit, and how its picture is placed
function placingTokens(turn, look, light, where) {
  var tokens = [];
  if (Number(turn)) tokens.push("rotation=" + turn);
  if (light < 1) tokens.push("backlight=" + Math.round(light * 100) + "%");
  if (look.mirror) tokens.push("mirror=true");
  if (where.x !== "" || where.y !== "")
    tokens.push("offset=" + (where.x === "" ? "*" : where.x) + "|" +
                (where.y === "" ? "*" : where.y));
  if (look.bg !== "#000000") tokens.push("bg=" + (BG_NAMES[look.bg] || look.bg.slice(1)));
  if (look.double) tokens.push("pixel_double=true");
  // One word covers both sides, two set them apart, across then down
  var tileDown = look.tileDown || "off";
  if (look.tile !== "off" || tileDown !== "off")
    tokens.push("tile=" + (look.tile === tileDown ? look.tile : look.tile + "|" + tileDown));
  return tokens;
}

// What playback allows, as the players do: a hold needs somewhere to turn around, which a loop
// or ping pong gives; two holds need both, one for each end; and first as last needs an end to
// play the first frame at, which a forward loop does not have
function holdAllowed(playing, look) { return look.loop || playing.pingpong; }
function secondHoldAllowed(playing, look) { return look.loop && playing.pingpong; }
function firstAsLastAllowed(playing, look) { return playing.pingpong || !look.loop; }

// The settings after the file: how a moving picture is paced, looped and held, leaving out
// whatever playback would refuse
function playingTokens(playing, look, kind, size) {
  if (kind === "image") return [];
  var tokens = [];
  if (look.pace === "fps") tokens.push("fps=" + look.every);
  if (look.pace === "interval") tokens.push("interval=" + look.every);
  // A drawing takes a pace and its canvas's size, and nothing of a picture's loop. The board's
  // own canvas is the screen's, halved by pixel double, so only another size is written
  if (kind === "drawing") {
    var canvas = canvasPixels(look, size, playing.turn);
    var panel = panelPixels(size, playing.turn);
    var scale = look.double ? 2 : 1;
    if (canvas[0] !== Math.floor(panel[0] / scale) || canvas[1] !== Math.floor(panel[1] / scale))
      tokens.push("width=" + canvas[0], "height=" + canvas[1]);
    return tokens;
  }
  if (!look.loop) tokens.push("loop=false");
  if (playing.pingpong) tokens.push("ping_pong=true");
  if (look.whole && firstAsLastAllowed(playing, look)) tokens.push("first_as_last=true");
  if ((playing.hold || look.holdBack) && holdAllowed(playing, look))
    tokens.push("hold=" + (playing.hold || 0) +
                (look.holdBack && secondHoldAllowed(playing, look) ? "|" + look.holdBack : ""));
  return tokens;
}

function lookEntry(selector, playing, look, light, size) {
  var kind = kindOf(playing.shows);
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  var left = [selector].concat(placingTokens(playing.turn, look, light, where)).join(" ");
  var what = kind === "folder" ? "sequence folder=" : kind === "gif" ? "gif file="
           : kind === "drawing" ? "graphics file=" : "image file=";
  return [left + ":", what + quoted(playing.shows)]
    .concat(playingTokens(playing, look, kind, size)).join(" ");
}

var oneLookScreenEntry = screenEntry;

screenEntry = function (letter, body) {
  var playing = body.screens[letter];
  if (state.hub.on || !state.screens[letter].there || !playing.shows || playing.shows === "keep")
    return oneLookScreenEntry(letter, body);
  var look = playing.look || freshLook();
  return lookEntry("screen" + letter, playing, look, look.backlight, state.screens[letter].size);
};

// Positions are one send where the file would say the same for them, so a setting a picture
// does not take, such as a still's pace, or one the page only remembers, such as the last
// custom colour, never splits them
playingKey = function (playing, place) {
  var look = playing.look || LOOK_START;
  var size = state.hub.sizes[place];
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  return [size, playing.shows].concat(placingTokens(playing.turn, look, 1, where))
    .concat(playingTokens(playing, look, kindOf(playing.shows), size)).join("|");
};

// Every position is lit by the hub's one light, so each entry carries it
hubEntry = function (group) {
  return lookEntry("hub" + placesSaid(group.places), group.playing,
                   group.playing.look || freshLook(), state.hubLight,
                   state.hub.sizes[group.places[0]]);
};

// ---- the settings, drawn ----------------------------------------------------------------------
// Each section folds, saying its values beside its name while closed. Orientation and playback
// start open, placement and background folded, a picture made for its screen needing neither

var foldOpen = {};
var FOLDS_START_OPEN = {Orientation: true, Placement: false, Background: false, Playback: true,
                        Drawing: true};

function foldSection(key, name, says, body) {
  var id = key + "|" + name;
  var fold = document.createElement("details");
  fold.className = "sfold";
  fold.dataset.section = name;
  fold.open = foldOpen[id] !== undefined ? foldOpen[id] : FOLDS_START_OPEN[name];
  fold.ontoggle = function () { foldOpen[id] = fold.open; };
  var head = document.createElement("summary");
  head.appendChild(document.createTextNode(name));
  var said = document.createElement("small");
  said.className = "closedonly";
  said.textContent = says;
  head.appendChild(said);
  fold.appendChild(head);
  fold.appendChild(body);
  return fold;
}

function sline() {
  var row = document.createElement("div");
  row.className = "sline";
  for (var at = 0; at < arguments.length; at++) if (arguments[at]) row.appendChild(arguments[at]);
  return row;
}

function named(words) {
  var label = document.createElement("span");
  label.className = "snamed";
  label.textContent = words;
  return label;
}

// One choice of several, as a row of buttons. options are [value, label html, refused]
function segment(options, chosen, choose, title) {
  var seg = document.createElement("span");
  seg.className = "sseg";
  if (title) seg.title = title;
  options.forEach(function (option) {
    var button = document.createElement("button");
    button.type = "button";
    button.dataset.value = option[0];
    button.innerHTML = option[1];
    button.className = option[0] === chosen ? "on" : "";
    button.disabled = !!option[2];
    button.onclick = function () { choose(option[0]); draw(); };
    seg.appendChild(button);
  });
  return seg;
}

// Anything on or off, as a toggle with its icon, greyed where playback would refuse it
function toggle(icon, words, on, flip, title, refused) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "stoggle" + (on && !refused ? " on" : "");
  button.dataset.words = words;
  button.innerHTML = "<span aria-hidden='true'>" + icon + "</span> " + words;
  button.title = title;
  button.disabled = !!refused;
  button.onclick = function () { flip(!on); draw(); };
  return button;
}

function numberBox(value, placeholder, change, step) {
  var box = document.createElement("input");
  box.type = "number";
  box.step = step || 1;
  box.value = value;
  box.placeholder = placeholder;
  box.onchange = function () { change(box.value); draw(); };
  return box;
}

function unit(words) {
  var said = document.createElement("span");
  said.className = "sunit";
  said.textContent = words;
  return said;
}

// How brightly a screen is lit, as a slider with its figure
function lightSlider(value, change, title) {
  var slider = document.createElement("input");
  slider.type = "range";
  slider.min = 0;
  slider.max = 100;
  slider.step = 5;
  slider.value = Math.round(value * 100);
  var figure = document.createElement("span");
  figure.className = "lightfigure";
  figure.textContent = slider.value + "%";
  slider.oninput = function () { figure.textContent = slider.value + "%"; };
  slider.onchange = function () { change(Number(slider.value) / 100); draw(); };
  var label = document.createElement("label");
  label.className = "opt lightopt";
  label.appendChild(document.createTextNode("backlight"));
  label.appendChild(slider);
  label.appendChild(figure);
  label.title = title;
  return label;
}

// ---- orientation ----

// The module's driver chip is at its bottom edge, so the mark is there
function rotationMark(turn) {
  return "<svg width='12' height='12' viewBox='0 0 12 12' aria-hidden='true'><g transform='rotate(" +
         turn + " 6 6)'><rect x='3' y='1' width='6' height='10' rx='1' fill='none' " +
         "stroke='currentColor' stroke-width='1.3'/><rect x='4.5' y='8.8' width='3' height='1.4' " +
         "fill='currentColor'/></g></svg>";
}

// A turn goes with the picture showing, remembered for it on this screen, and can be set with
// none showing, for the next one put there
function setTurn(held, turn) {
  held.turn = turn;
  if (held.shows && held.shows !== "keep") held.turns[held.shows] = turn;
}

function orientationFold(key, held) {
  var look = held.look;
  var turn = Number(held.turn || 0);
  var rotation = segment([0, 90, 180, 270].map(function (value) {
    return [value, rotationMark(value) + value + "&deg;"];
  }), turn, function (value) { setTurn(held, value); }, "Which way up the screen is mounted");
  rotation.classList.add("rotationseg");
  var mirror = toggle("&#8646;", "Mirror", look.mirror, function (on) { look.mirror = on; },
                      "Flip the picture left to right");
  return foldSection(key, "Orientation", turn + "\u00b0, " + (look.mirror ? "mirrored"
                                                                          : "not mirrored"),
                     sline(named("Rotation"), rotation, mirror));
}

// ---- placement ----

function placementSaid(look, where) {
  var said = [look.anchor === null ? "at " + (where.x === "" ? "centre" : where.x) + ", " +
                                     (where.y === "" ? "centre" : where.y)
                                   : ANCHOR_NAMES[look.anchor]];
  var tileDown = look.tileDown || "off";
  function tiled(mode) { return mode === "repeat" ? "tiled" : "tiled, mirrored"; }
  if (look.tile === "off" && tileDown === "off") said.push("one picture");
  else if (look.tile === tileDown) said.push(tiled(look.tile));
  else {
    if (look.tile !== "off") said.push(tiled(look.tile) + " across");
    if (tileDown !== "off") said.push(tiled(tileDown) + " down");
  }
  if (look.double) said.push("pixel doubled");
  return said.join(", ");
}


// Pixel doubling as one pixel drawn as four
var DOUBLE_GLYPH = "<svg width='12' height='12' viewBox='0 0 12 12' aria-hidden='true'>" +
                   "<rect x='1' y='1' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='6.5' y='1' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='1' y='6.5' width='4.5' height='4.5' fill='currentColor'/>" +
                   "<rect x='6.5' y='6.5' width='4.5' height='4.5' fill='currentColor'/></svg>";

function placementFold(key, held, size) {
  var look = held.look;
  var where = pictureOffset(look, held.shows, size, held.turn);
  var anchor = document.createElement("span");
  anchor.className = "sanchor";
  anchor.title = "Where the picture sits, worked out from its size and the panel's";
  ANCHOR_NAMES.forEach(function (name, at) {
    var point = document.createElement("button");
    point.type = "button";
    point.className = look.anchor === at ? "on" : "";
    point.title = name;
    point.onclick = function () {
      look.anchor = at;
      look.x = "";
      look.y = "";
      draw();
    };
    anchor.appendChild(point);
  });
  // Typing a figure places the picture by hand, the other side kept where it was
  function typed(axis) {
    return function (value) {
      var other = axis === "x" ? "y" : "x";
      look[other] = where[other];
      look[axis] = value;
      look.anchor = null;
    };
  }
  var x = numberBox(where.x, "centre", typed("x"));
  var y = numberBox(where.y, "centre", typed("y"));
  x.title = "Pixels from the left, empty to centre";
  y.title = "Pixels from the top, empty to centre";
  x.className = y.className = "sxy";
  // Tiling is set for each side, so a picture can be spread across and left alone down. Both
  // sides share one line, each named by its arrow, the choices in words
  function tiling(down) {
    var side = down ? "tileDown" : "tile";
    var seg = segment([["off", "Off"], ["repeat", "Repeat"], ["mirror", "Mirror"]],
                      look[side] || "off",
                      function (value) { look[side] = value; },
                      "Fill the screen " + (down ? "top to bottom" : "left to right") +
                      " with copies; mirror turns every other one round, so any picture joins up");
    seg.classList.add(down ? "tiledown" : "tileacross");
    return seg;
  }
  var double = toggle(DOUBLE_GLYPH, "Pixel double", look.double,
                      function (on) { look.double = on; },
                      "Draw each pixel twice as wide and tall, so a half size picture fills " +
                      "the screen");
  // Where it sits, then how it fills: a line each, or two halves where the section is wide
  var body = document.createElement("div");
  body.className = "ssplit";
  body.appendChild(sline(anchor, named("x"), x, named("y"), y, double));
  var across = named("\u2194");
  across.title = "Across";
  var down = named("\u2195");
  down.title = "Down";
  body.appendChild(sline(named("Tiling"), across, tiling(false), down, tiling(true)));
  return foldSection(key, "Placement", placementSaid(look, where), body);
}

// ---- background ----

// Which background pickers have their custom field open, by screen or position
var groundCustom = {};

// A background as its colour at full brightness and how bright it is, 0 to 1. Black is its
// own colour at any brightness
function groundParts(hex) {
  var rgb = hexRgb(hex);
  var top = Math.max(rgb[0], rgb[1], rgb[2]);
  if (!top) return {full: [0, 0, 0], value: 1};
  return {full: rgb.map(function (v) { return Math.round(v * 255 / top); }), value: top / 255};
}

function groundHex(full, value) {
  return "#" + hexOf(full.map(function (v) { return Math.round(v * value); }));
}

function groundSaid(bg) {
  var parts = groundParts(bg);
  var name = BG_NAMES["#" + hexOf(parts.full)];
  if (!name) return bg;
  return parts.value < 1 ? name + " at " + Math.round(parts.value * 100) + "%" : name;
}

// The colour round a picture, chosen from the looks' swatches in one row across the section,
// black first since every screen starts there, the custom ring last with the chosen colour in
// its middle. Then a brightness of its own, apart from the backlight. A typed hex is taken as
// written, its brightness read from it
function backgroundFold(key, held) {
  var look = held.look;
  var body = document.createElement("div");
  body.className = "groundpick";
  var names = ["black"].concat(SWATCHES);
  var parts = groundParts(look.bg);
  var chosen = names.filter(function (name) {
    return hexOf(WORDS[name]) === hexOf(parts.full);
  })[0];
  var open = groundCustom[key] || !chosen;
  var row = document.createElement("div");
  row.className = "sswatches";
  names.forEach(function (name) {
    var swatch = document.createElement("button");
    swatch.type = "button";
    swatch.className = !open && chosen === name ? "on" : "";
    swatch.style.background = rgbInk(WORDS[name]);
    swatch.title = name;
    // Named under the swatch where the section is wide enough, as the looks' picker names them
    var tag = document.createElement("b");
    tag.textContent = name;
    swatch.appendChild(tag);
    // A colour keeps the brightness already set
    swatch.onclick = function () {
      look.bg = groundHex(WORDS[name], parts.value);
      groundCustom[key] = false;
      draw();
    };
    row.appendChild(swatch);
  });
  var custom = document.createElement("button");
  custom.type = "button";
  custom.className = "custom" + (open ? " on" : "");
  // A colour that is no swatch's is the custom one, and the ring keeps showing it while a
  // swatch is chosen, custom coming back to it
  if (open) look.customBg = look.bg;
  if (look.customBg) custom.style.setProperty("--picked", look.customBg);
  custom.title = "custom: any colour, from the field or as a hex";
  var customTag = document.createElement("b");
  customTag.textContent = "custom";
  custom.appendChild(customTag);
  custom.onclick = function () {
    groundCustom[key] = true;
    if (look.customBg) look.bg = look.customBg;
    draw();
  };
  row.appendChild(custom);
  body.appendChild(row);

  if (open) {
    var holds = document.createElement("div");
    holds.className = "scustom";
    var place = takeApart(parts.full);
    var field = document.createElement("div");
    field.className = "field";
    var at = document.createElement("div");
    at.className = "at";
    at.style.left = (place.hue / 360 * 100) + "%";
    at.style.top = ((1 - place.sat) * 100) + "%";
    at.style.background = rgbInk(parts.full);
    field.appendChild(at);
    var hex = document.createElement("input");
    function pointingAt(event) {
      var bounds = field.getBoundingClientRect();
      var across = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
      var down = Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height));
      look.bg = groundHex(fieldColour(across * 360, 1 - down), parts.value);
      at.style.left = (across * 100) + "%";
      at.style.top = (down * 100) + "%";
      at.style.background = look.bg;
      hex.value = look.bg;
      preview.style.background = look.bg;
    }
    field.onpointerdown = function (event) {
      field.setPointerCapture(event.pointerId);
      pointingAt(event);
    };
    field.onpointermove = function (event) {
      if (field.hasPointerCapture(event.pointerId)) pointingAt(event);
    };
    field.onpointerup = function () { draw(); };
    holds.appendChild(field);
    var typed = document.createElement("label");
    typed.className = "hexline";
    typed.appendChild(document.createTextNode("Hex"));
    hex.type = "text";
    hex.maxLength = 7;
    hex.spellcheck = false;
    hex.value = look.bg;
    hex.title = "The background exactly as typed, dark colours included";
    hex.onchange = function () {
      var said = hex.value.replace("#", "").trim().toLowerCase();
      if (/^[0-9a-f]{6}$/.test(said)) look.bg = "#" + said;
      draw();
    };
    typed.appendChild(hex);
    // The hex over the colour itself at its brightness, as large as the room beside the field
    var side = document.createElement("div");
    side.className = "scustomside";
    side.appendChild(typed);
    var preview = document.createElement("div");
    preview.className = "scustompreview";
    preview.style.background = look.bg;
    preview.title = "The background as it will be drawn";
    side.appendChild(preview);
    holds.appendChild(side);
    body.appendChild(holds);
  }

  // How bright the background is, black having none to set
  var slider = document.createElement("input");
  slider.type = "range";
  slider.min = 0;
  slider.max = 100;
  slider.step = 5;
  slider.value = Math.round(parts.value * 100);
  slider.disabled = chosen === "black";
  var figure = document.createElement("span");
  figure.className = "lightfigure";
  figure.textContent = slider.value + "%";
  slider.oninput = function () { figure.textContent = slider.value + "%"; };
  slider.onchange = function () {
    look.bg = groundHex(parts.full, Number(slider.value) / 100);
    draw();
  };
  var bright = document.createElement("label");
  bright.className = "opt groundbright";
  bright.appendChild(document.createTextNode("brightness"));
  bright.appendChild(slider);
  bright.appendChild(figure);
  bright.title = chosen === "black" ? "Black has no brightness to set"
                                    : "How bright the background is, apart from the backlight";
  body.appendChild(bright);
  return foldSection(key, "Background", groundSaid(look.bg), body);
}

// ---- playback ----

// The folded line is kept short, so a hold still fits it, the units written in full on the
// controls themselves
function playbackSaid(held, look) {
  var said = [look.pace === "fps" ? look.every + " fps"
            : look.pace === "interval" ? "frame every " + look.every + " s"
            : kindOf(held.shows) === "folder" ? "pace from names" : "pace from file"];
  said.push(look.loop ? "loop" : "once");
  if (held.pingpong) said.push("ping pong");
  if (look.whole && firstAsLastAllowed(held, look)) said.push("first as last");
  if ((held.hold || look.holdBack) && holdAllowed(held, look))
    said.push("hold " + (held.hold || 0) + " s" +
              (look.holdBack && secondHoldAllowed(held, look) ? " and " + look.holdBack + " s"
                                                              : ""));
  return said.join(", ");
}

// The speed's line, kept to one line: its choices, the figure, and what the figure counts
function speedLine(speed, every, look) {
  var line = sline(named("Speed"), speed, every,
                   every ? unit(look.pace === "fps" ? "frames per second" : "seconds per frame")
                         : null);
  line.classList.add("speedline");
  return line;
}

// A drawing's own section, in playback's place: how often it draws, and its canvas, the whole
// screen, half of it, or a size set by hand, placed as a small picture is
function drawingFold(key, held) {
  var look = held.look;
  var speed = segment([["fps", "fps"], ["interval", "interval"], ["saved", "every frame"]],
                      look.pace, function (value) {
                        var flips = (value === "fps" && look.pace === "interval") ||
                                    (value === "interval" && look.pace === "fps");
                        if (flips) look.every = Math.round(100 / look.every) / 100;
                        look.pace = value;
                      },
                      "Frames a second, seconds between frames, or as often as the screen takes " +
                      "a frame");
  var every = look.pace === "saved" ? null : numberBox(look.every, "", function (value) {
    if (Number(value) > 0) look.every = Number(value);
  }, look.pace === "interval" ? 0.05 : 1);
  var canvas = segment([["whole", "Whole screen"], ["half", "Half size"],
                        ["set", "Set size"]], look.canvas || "whole", function (value) {
                          look.canvas = value;
                        });
  canvas.querySelector("[data-value=whole]").title = "As big as the screen";
  canvas.querySelector("[data-value=half]").title =
    "Half as wide and tall as the screen, a quarter of the memory. With pixel double it " +
    "fills the screen";
  canvas.querySelector("[data-value=set]").title = "A size in pixels, placed as a small picture is";
  // The speed, then the canvas: stacked, or two halves where the section is wide
  var body = document.createElement("div");
  body.className = "ssplit";
  body.appendChild(speedLine(speed, every, look));
  var sized = document.createElement("div");
  body.appendChild(sized);
  sized.appendChild(sline(named("Canvas"), canvas));
  if (look.canvas === "set") {
    var wide = numberBox(look.canvasW, "", function (value) {
      if (Number(value) > 0) look.canvasW = Math.round(Number(value));
    });
    var high = numberBox(look.canvasH, "", function (value) {
      if (Number(value) > 0) look.canvasH = Math.round(Number(value));
    });
    sized.appendChild(sline(named("Width"), wide, unit("pixels"), named("Height"), high,
                           unit("pixels")));
  }
  var said = [look.pace === "fps" ? look.every + " fps"
            : look.pace === "interval" ? "frame every " + look.every + " s" : "every frame",
              look.canvas === "set" ? look.canvasW + " \u00d7 " + look.canvasH
            : look.canvas === "half" ? "half size" : "whole screen"];
  return foldSection(key, "Drawing", said.join(", "), body);
}

function playbackFold(key, held, media) {
  var look = held.look;
  // A folder whose names say no delay has nothing to play at its own pace
  var noneSaved = media.kind === "folder" && !media.named;
  var fromWhere = media.kind === "folder" ? "from names" : "from file";
  // Between fps and interval the figure is turned over, so the pace stays the same
  var speed = segment([["fps", "fps"], ["interval", "interval"], ["saved", fromWhere, noneSaved]],
                      look.pace, function (value) {
                        var flips = (value === "fps" && look.pace === "interval") ||
                                    (value === "interval" && look.pace === "fps");
                        if (flips) look.every = Math.round(100 / look.every) / 100;
                        look.pace = value;
                      },
                      "Frames a second, seconds between frames, or the delays " +
                      (media.kind === "folder" ? "the pictures' names give" : "the file was saved with"));
  var every = look.pace === "saved" ? null : numberBox(look.every, "", function (value) {
    // Nothing, zero or less is no pace, so the figure there stays
    if (Number(value) > 0) look.every = Number(value);
  }, look.pace === "interval" ? 0.05 : 1);
  // The pace, then how it loops and holds: stacked, or two halves where the section is wide
  var body = document.createElement("div");
  body.className = "ssplit";
  body.appendChild(speedLine(speed, every, look));
  var looping = document.createElement("div");
  body.appendChild(looping);
  looping.appendChild(sline(
    toggle("&#8635;", "Loop", look.loop, function (on) { look.loop = on; },
           "Start again after the last frame"),
    toggle("&#8644;", "Ping pong", held.pingpong, function (on) { held.pingpong = on; },
           "Play forwards then backwards"),
    toggle("&#8676;", "First as last", look.whole, function (on) { look.whole = on; },
           firstAsLastAllowed(held, look)
             ? "Play the first frame again at the end, for an animation drawn to loop"
             : "Needs ping pong, or loop off: a forward loop has no end to play it at",
           !firstAsLastAllowed(held, look))));

  var hold = document.createElement("span");
  hold.className = "shold" + (holdAllowed(held, look) ? "" : " off");
  hold.title = holdAllowed(held, look) ? "Seconds to wait where it turns around"
                                       : "Needs loop or ping pong, somewhere to turn around";
  hold.appendChild(named("Hold"));
  var atEnd = numberBox(held.hold, "0", function (value) {
    held.hold = value && Number(value) > 0 ? value : "";
  }, 0.5);
  atEnd.disabled = !holdAllowed(held, look);
  hold.appendChild(atEnd);
  hold.appendChild(unit(secondHoldAllowed(held, look) ? "seconds at the end," : "seconds"));
  if (secondHoldAllowed(held, look)) {
    hold.appendChild(numberBox(look.holdBack, "same", function (value) {
      look.holdBack = value && Number(value) >= 0 ? value : "";
    }, 0.5));
    hold.appendChild(unit("seconds at the start"));
  }
  looping.appendChild(sline(hold));
  return foldSection(key, "Playback", playbackSaid(held, look), body);
}

// ---- what is showing, and every section under it ----

// A picture's name as a person reads it, a slideshow being a folder named as a path from the
// drive's top
function pictureSaid(name) {
  var media = mediaNamed(name);
  if (media && media.kind === "drawing") return media.drawing.title;
  return media && media.kind === "folder" ? "/" + name : name;
}

function showingLine(held, letter) {
  var line = document.createElement("div");
  line.className = "sshowing";
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  // Nothing showing takes the same two lines a picture does, so nothing under it moves when one
  // is chosen
  if (!picture) {
    line.classList.add("empty");
    line.innerHTML = (state.scenes.length ? "nothing chosen for this scene" : "nothing showing") +
                     "<small>press " + letter + " under a picture below to show it here</small>";
    return line;
  }
  var media = mediaNamed(picture);
  var art = mediaArt(picture);
  // A drawing is drawn, not shown, on a canvas
  if (media && media.kind === "drawing") {
    var size = state.hub.on ? state.hub.sizes[letter] : state.screens[letter].size;
    var canvas = canvasPixels(held.look, size, held.turn);
    line.innerHTML = "drawing <b>" + picture + "</b><small>canvas, " + canvas[0] + " \u00d7 " +
                     canvas[1] + "</small>";
    return line;
  }
  var kind = media ? {image: "picture", gif: "gif", folder: "slideshow"}[media.kind] : null;
  line.innerHTML = "showing <b>" + pictureSaid(picture) + "</b>" +
                   (media ? "" : " (not on the drive)");
  var about = [kind, art && art.w ? art.w + " \u00d7 " + art.h : null].filter(Boolean);
  if (about.length) {
    var small = document.createElement("small");
    small.textContent = about.join(", ");
    line.appendChild(small);
  }
  return line;
}

// The four sections for a screen or position, with nothing to set until a picture is showing
// but its orientation, which is how the screen is mounted
function lookSections(key, held, size) {
  var sections = document.createElement("div");
  sections.className = "settings looksettings";
  sections.appendChild(orientationFold(key, held));
  var picture = held.shows && held.shows !== "keep" ? held.shows : null;
  if (!picture) return sections;
  sections.appendChild(placementFold(key, held, size));
  sections.appendChild(backgroundFold(key, held));
  var media = mediaNamed(picture);
  if (media && media.kind === "drawing") sections.appendChild(drawingFold(key, held));
  else if (media && media.kind !== "image") sections.appendChild(playbackFold(key, held, media));
  return sections;
}

// A screen's box has the backlight across its top, what it shows
// straight under the module, and the sections under that
var oneLookHead = renderScreensHead;

renderScreensHead = function () {
  oneLookHead();
  if (state.hub.on) return;
  var boxes = document.querySelectorAll("#screensHead .screen-box");
  SCREENS.forEach(function (letter, at) {
    var screen = state.screens[letter];
    var old = boxes[at] && boxes[at].querySelector(".settings");
    if (!old) return;
    var body = old.parentNode;
    body.replaceChild(lookSections("screen" + letter, screen, screen.size), old);
    body.insertBefore(showingLine(screen, letter), body.querySelector(".looksettings"));
    body.insertBefore(lightRow(screen.look.backlight, function (value) {
      screen.look.backlight = value;
    }, "backlight", "How brightly screen " + letter + " is lit, in this scene"), body.firstChild);
  });
};

// A backlight as a row of its own across the top of a screen's or the hub's box
function lightRow(value, change, words, title) {
  var row = document.createElement("div");
  row.className = "lightrow";
  var light = lightSlider(value, change, title);
  light.firstChild.textContent = words;
  row.appendChild(light);
  return row;
}

// The picked position's settings, the same sections a screen has. What each position shows is
// said under its module, and the position being set is the one filled, so the strip says neither
placeSettings = function () {
  var settings = document.createElement("div");
  settings.className = "hubsettings";
  if (!placeThere(placePicked)) return settings;
  var held = state.places[placePicked];
  settings.appendChild(lookSections("place" + placePicked, held, state.hub.sizes[placePicked]));
  return settings;
};

// The hub's one backlight is a row of its own across the top of the box, over all six
// positions and apart from whatever group is being set, since it lights every screen
var oneLookHubHead = renderHubHead;

renderHubHead = function () {
  oneLookHubHead();
  var body = document.querySelector("#screensHead .hubbox .body");
  if (!body) return;
  // What each position shows, a slideshow named as its folder
  body.querySelectorAll(".place").forEach(function (tile) {
    var says = tile.querySelector(".placesays");
    var held = state.places[tile.dataset.place];
    if (says && held && held.shows) says.textContent = pictureSaid(held.shows);
  });
  var row = lightRow(state.hubLight, function (value) { state.hubLight = value; },
                     "backlight, every screen on the hub",
                     "How brightly the hub's screens are lit, all six together, in this scene");
  row.classList.add("hublightrow");
  row.querySelector(".lightopt").classList.add("hublight");
  body.insertBefore(row, body.firstChild);
};

// The chip goes beside what is the board's and not before a box's name: a screen's panel size in
// its band, and on the hub which way it is wired, in its band, and each position's panel size
var oneLookScreensTab = renderScreensTab;

renderScreensTab = function () {
  oneLookScreensTab();
  if (state.hub.on) {
    document.querySelectorAll("#screensHead .hubbox .place .placesize").forEach(function (size) {
      var chip = boardIcon();
      chip.classList.add("placechip");
      size.parentNode.insertBefore(chip, size);
    });
  }
  document.querySelectorAll("#screensHead .screen-box h3").forEach(function (band) {
    var chip = band.querySelector(".boardicon");
    var size = band.querySelector("select.inband");
    if (!chip || !size) return;
    var fact = document.createElement("span");
    fact.className = "bandfact";
    fact.title = "How the board is built, which is the same in every scene";
    band.insertBefore(fact, size);
    fact.appendChild(chip);
    fact.appendChild(size);
    band.title = "";
  });
};

// A picture newly chosen starts at the turn it was last given on this screen, and a picture
// never turned here keeps the turn the screen already has, so a turn can be set on an empty
// screen before anything is put on it. A slideshow newly chosen plays at five a second
// unless its names say their own
function chosenAfresh(held) {
  if (held.shows === held.lastShows) return;
  paceForChosen(held);
  if (held.shows && held.turns[held.shows] !== undefined) held.turn = held.turns[held.shows];
  if (held.shows) held.turns[held.shows] = held.turn;
  held.lastShows = held.shows;
}

turnForChosen = function (letter) { chosenAfresh(state.screens[letter]); };

placeTurnForChosen = function (place) { chosenAfresh(state.places[place]); };

// ---- the pictures, whole ------------------------------------------------------------------------
// Each picture is drawn whole in its tile, never cropped: the tiles keep the row's fixed width,
// and a picture wider than its tile is scaled down to that width, the tile as tall as its shape
// needs; a narrower one is drawn at its true size, never scaled up, in a square tile at least,
// so a small picture looks as small as it is. The rows line up at the bottom, keeping the pick
// rows in line. The name, a still's type and the size show over the picture on hover
var oneWholeAssets = renderAssets;

renderAssets = function () {
  oneWholeAssets();
  document.getElementById("assets").classList.add("wholeassets");
  document.querySelectorAll("#assets .asset").forEach(function (cell, at) {
    var media = state.media[at];
    var art = media && mediaArt(media.name);
    var face = cell.querySelector(".face");
    var img = face && face.querySelector("img");
    // A drawing is its icon on its colour, or its initial, square, tagged as a drawing, its name
    // and description on hover
    if (media && media.kind === "drawing" && face) {
      var drawing = media.drawing;
      face.className = "face drawingface";
      face.style.height = face.getBoundingClientRect().width + "px";
      face.style.background = drawingInk(drawing, media.name);
      face.innerHTML = "<span class='kind'>drawing</span>" +
        (drawing.icon ? "<span class='drawingicon'>" + drawing.icon + "</span>"
                      : "<span class='drawingletter'>" + drawing.title[0] + "</span>") +
        "<span class='drawingtitle'>" + drawing.title + "</span>" +
        "<div class='label'><b>" + drawing.title + "</b><br>" + drawing.description + "</div>";
      return;
    }
    if (!art || !art.w || !img) return;
    var wide = face.getBoundingClientRect().width;
    var small = art.w < wide;
    var high = small ? Math.max(wide, art.h) : wide * art.h / art.w;
    face.classList.add("wholeface");
    face.style.height = high + "px";
    img.style.cssText = small ? "width:" + art.w + "px;height:" + art.h + "px"
                              : "width:100%;height:100%";
    var dot = media.name.lastIndexOf(".");
    var still = media.kind === "image";
    var label = face.querySelector(".label");
    // A slideshow is a folder, so it is named as one, a path from the drive's top
    var shown = media.kind === "folder" ? pictureSaid(media.name)
              : dot > 0 ? media.name.slice(0, dot) : media.name;
    if (label) {
      label.innerHTML = "<b>" + shown + "</b><br>" +
        [still && dot > 0 ? media.name.slice(dot + 1) : null, art.w + " \u00d7 " + art.h]
          .filter(Boolean).join(" \u00b7 ");
    }
  });
};

function paceForChosen(held) {
  var media = held.shows ? mediaNamed(held.shows) : null;
  if (!media || media.kind !== "folder") return;
  held.look.pace = media.named ? "saved" : "fps";
  held.look.every = 5;
}

state.always.body = capture();
draw();
