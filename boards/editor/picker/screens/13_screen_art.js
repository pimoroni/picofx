import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps} from "../00_draw.js";
import {WORDS, rgbInk} from "../01_colours.js";
import {capture, state} from "../04_scenes.js";
import {LED_PANELS} from "../10_led_sections.js";
import {FEATURE_TABS, TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches} from "../11_tabs.js";
import {
  BOARD_INK, CHIN_INK, DRAWN, EMPTY_INK, FRAME_INK, FRAME_WIDE, GROUND_INK, HOLE_EDGE, HOLE_INK,
  MODULE, NAME_INK, PANEL_INK, PANEL_PX, PER_MM, PRINTED, SCREENS, drawingArts, freshLook, kindOf,
  mediaNamed, screenParts, screenUnder, shownBefore
} from "./12_screens.js";

// ---- the screens drawn --------------------------------------------------------------------------
// The screen modules and what they show: the tab's head and boxes, pictures read off the drive,
// drawings, and a look drawn on the module with a gif kept playing.

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
                             fill: art ? GROUND_INK : screen.off ? "#000000" : EMPTY_INK}));
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
  } else if (screen.off) {
    parts.push(svgTag("text", {x: litX + litW / 2, y: litY + litH / 2 + 1.4,
                               "text-anchor": "middle", fill: "#5d666c",
                               "font-size": 4, "font-family": "system-ui"}, "off"));
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

  // The picture as the board will draw it, its own pixels centred and cropped by the lit window
  // with black around it. The window sits on the exact centre of the drawn module, so a turned
  // module swaps its width and height and nothing else moves. The picture itself stays upright,
  // which is what a viewer of a mounted screen sees
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

// ---- pictures, read off the drive in turn ------------------------------------------------------
// The drive is slow to read, so pictures come off it one at a time, those a screen or hub position
// shows in any scene first and the rest of the gallery after them

var pictureQueue = [];
var pictureReading = null;

// The pictures any scene puts on a screen or a hub position, calculated once a draw
var shownThisDraw = null;

addStep(drawSteps.before, DRAW_BEFORE, "screenShown", function () { shownThisDraw = null; });

function picturesShown() {
  if (shownThisDraw) return shownThisDraw;
  var shown = shownThisDraw = [];
  var bodies = [capture(), state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  bodies.forEach(function (body) {
    if (!body) return;
    Object.keys(body.screens || {}).forEach(function (letter) {
      if (body.screens[letter].shows) shown.push(body.screens[letter].shows);
    });
    Object.keys(body.places || {}).forEach(function (place) {
      if (body.places[place].shows) shown.push(body.places[place].shows);
    });
  });
  return shown;
}

function readNextPicture() {
  if (pictureReading || !pictureQueue.length) return;
  shownThisDraw = null;
  var shown = picturesShown();
  pictureQueue.sort(function (a, b) {
    return (shown.indexOf(b.name) >= 0) - (shown.indexOf(a.name) >= 0);
  });
  var next = pictureReading = pictureQueue.shift();
  next.handle.getFile().then(function (file) {
    return new Promise(function (settle) {
      var url = URL.createObjectURL(file);
      var probe = new Image();
      probe.onload = function () {
        state.art[next.name] = {url: url, w: probe.naturalWidth, h: probe.naturalHeight,
                                ratio: probe.naturalWidth / probe.naturalHeight};
        settle();
      };
      // One that will not load stays held empty, so it is not asked for again
      probe.onerror = function () { settle(); };
      probe.src = url;
    });
  }, function () {
    // The file is gone, deleted while still listed, so it is asked for again once the drive is
    // next read, where one that would not load is not
    if (state.art[next.name]) state.art[next.name].gone = true;
  }).then(function () {
    pictureReading = null;
    draw();
    readNextPicture();
  });
}

export function mediaArt(name, style) {
  var media = mediaNamed(name);
  // A drawing in a style with a thumbnail of its own is shown by that, held under its name and style
  style = styleNamed(media, style);
  var styled = style && media && media.styleThumbs ? media.styleThumbs[style] : null;
  var key = styled ? name + "#" + style : name;
  var held = state.art[key];
  // The drawing's own thumbnail stands in while a style's loads, so the screen keeps a picture
  if (held) return held.ratio ? held : styled ? mediaArt(name) : null;
  // A slideshow and a drawing are shown by a thumbnail, a picture by itself
  var handle = styled || (media && (media.thumbHandle || media.handle));
  if (!handle) return null;
  // Held empty while it waits, so each is asked for once
  state.art[key] = {url: null, ratio: 0};
  pictureQueue.push({name: key, handle: handle});
  setTimeout(readNextPicture, 0);
  return styled ? mediaArt(name) : null;
}

// The tab's swatch is the two screens, each showing what its screen shows
tabSwatches.screensPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch screenswatch";
  SCREENS.forEach(function (letter) {
    var screen = state.screens[letter];
    var cell = document.createElement("span");
    cell.className = "screencell " + letter.toLowerCase();
    // A screen showing nothing of the scene's own shows Always on's picture where it has one
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var shown = screen.shows || (under && under.always) || null;
    var art = screen.there && shown && shown !== "keep"
              ? mediaArt(shown, screen.look && screen.look.style) : null;
    // Always on's picture wears the stripes of nothing over it
    if (art) cell.style.backgroundImage = (under && under.always ? "var(--through), " : "") +
                                          "url(" + art.url + ")";
    if (!screen.there) cell.classList.add("absent");
    else if (screen.off) cell.classList.add("off");
    // A picture with no thumbnail yet is a white tile, its screen showing something
    else if (!art) cell.classList.add(shown ? "blank"
                                      : under && under.off ? "dark" : "nothing");
    swatch.appendChild(cell);
  });
  swatch.title = SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var said = !screen.there ? "not fitted" : screen.off ? "off"
             : screen.shows || (under && under.always ? "Always on's " + under.always : "nothing");
    return SCREENS.length > 1 ? letter + ": " + said : said;
  }).join(", ");
};

// Put the size fitted to each screen, A then B, under the tab's name
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
addStep(drawSteps.before, DRAW_BEFORE, "screenTurns", function () {
  SCREENS.forEach(function (letter) { screenParts.turnForChosen(letter); });
});

addStep(drawSteps.after, DRAW_AFTER, "screens", function () {
  sizesUnderName();
  screenParts.renderTab();
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
  var after = document.getElementById(LED_PANELS[LED_PANELS.length - 1]);
  after.parentNode.insertBefore(panel, after.nextSibling);
}());

// A board with no screen ports keeps the panel out of sight, for the parts that draw into it
if (SCREENS.length) {
  TAB_NAMES.screensPanel = "Screens";
  addStep(TAB_PANELS, FEATURE_TABS, "screens", "screensPanel");
  keptOpen("screensPanel");
} else {
  document.getElementById("screensPanel").hidden = true;
}

export function panelPixels(size, turn) {
  var panel = PANEL_PX[size] || PANEL_PX["2.8"];
  return Number(turn || 0) % 180 === 90 ? [panel[1], panel[0]] : [panel[0], panel[1]];
}

// A drawing's canvas in pixels, the screen's as it is turned, half that, or a size set by hand
export function canvasPixels(look, size, turn) {
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
export function pictureOffset(look, shows, size, turn) {
  if (look.anchor === null || look.anchor === undefined) return {x: look.x, y: look.y};
  var picture = picturePixels(shows, look, size, turn);
  var panel = panelPixels(size, turn);
  function side(at, axis) {
    if (at === 1 || !picture) return "";
    return at === 0 ? "0" : String(panel[axis] - picture[axis]);
  }
  return {x: side(look.anchor % 3, 0), y: side(Math.floor(look.anchor / 3), 1)};
}

// ---- drawings -------------------------------------------------------------------------------------
// A drawing is a Python file drawn on a screen, drawing file=rings.py. It is listed only where
// its opening string has a "Drawing:" line giving its name, read as a program's lines are. Other
// lines may give Icon:, any Unicode character, Colour:, one of the board's colour words or a hex,
// and Section:, the gallery section an example drawing is listed in. The first sentence of the
// rest describes it. A Python file without a Drawing: line is not listed, whether drawing or
// program. The page cannot run one, so a drawing is shown by its icon on its colour, or its
// initial where it names no icon. A drawing that names no colour takes one from its name

// A hue from a name, the same each time. The hash is mixed again after its first pass, which
// barely moves between names of one length
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

// A drawing's colour as a CSS colour, from a word the board knows, a hex, or its name
export function drawingInk(drawing, name) {
  var word = WORDS[drawing.colour.toLowerCase()];
  if (word) return rgbInk(word);
  if (/^#?[0-9a-f]{6}$/i.test(drawing.colour)) return "#" + drawing.colour.replace("#", "");
  return "hsl(" + nameHue(name) + ",60%,45%)";
}

// A drawing at a canvas's size, for where a picture's pixels are drawn. Its thumbnail covers the
// canvas, or where it has none its colour fills the canvas with its icon or initial in the middle
function drawingArt(name, wide, high, style) {
  // Kept by the thumbnail it is made from, so a style's found on a later read of the drive
  // replaces the drawing's that stood in for it. One still loading is stood in for, and not kept
  style = styleNamed(mediaNamed(name), style);
  var styleThumbs = (mediaNamed(name) || {}).styleThumbs || {};
  var styled = !!style && !!styleThumbs[style];
  var key = name + "|" + wide + "|" + high + "|" + (styled ? style : "");
  var waiting = styled && !(state.art[name + "#" + style] || {}).ratio;
  if (drawingArts[key]) return drawingArts[key];
  var media = mediaNamed(name);
  var drawing = media.drawing;
  var canvas = document.createElement("canvas");
  canvas.width = wide;
  canvas.height = high;
  var g = canvas.getContext("2d");
  // A thumbnail covers the canvas once it has loaded. Until then there is nothing to show, so a
  // screen keeps what it showed before, and only a drawing with no thumbnail shows its face
  var thumb = media.thumbHandle ? mediaArt(name, style) : null;
  var loaded = thumb ? artImage(thumb) : null;
  if (media.thumbHandle && !loaded) return null;
  if (loaded) {
    var scale = Math.max(wide / loaded.naturalWidth, high / loaded.naturalHeight);
    var drawnWide = loaded.naturalWidth * scale;
    var drawnHigh = loaded.naturalHeight * scale;
    g.drawImage(loaded, (wide - drawnWide) / 2, (high - drawnHigh) / 2, drawnWide, drawnHigh);
    var made = {url: canvas.toDataURL(), w: wide, h: high, ratio: wide / high};
    if (!waiting) drawingArts[key] = made;
    return made;
  }
  g.fillStyle = drawingInk(drawing, name);
  g.fillRect(0, 0, wide, high);
  g.fillStyle = "#fff";
  g.textAlign = "center";
  g.textBaseline = "middle";
  var glyph = Math.round(Math.min(wide, high) * 0.46);
  g.font = drawing.icon ? glyph + "px 'Segoe UI Symbol', system-ui" : "bold " + glyph + "px system-ui";
  g.fillText(drawing.icon || drawing.title[0], wide / 2, high / 2);
  var face = {url: canvas.toDataURL(), w: wide, h: high, ratio: wide / high};
  if (!media.thumbHandle) drawingArts[key] = face;
  return face;
}

// Make a drawing's face as a square, for the gallery and the tab's swatch. It is made afresh each
// time the drive is read, since the opening string it comes from may have changed
function madeDrawing(name) {
  Object.keys(drawingArts).forEach(function (key) {
    if (key.indexOf(name + "|") === 0) delete drawingArts[key];
  });
  state.art[name] = drawingArt(name, 240, 240);
  state.art[name].face = true;
}
screenParts.madeDrawing = madeDrawing;

// ---- drawing a look on the module -------------------------------------------------------------

var loadedArt = {};

// A picture's pixels, loaded once. Until they arrive this is null, and the page draws again then
function artImage(art) {
  if (loadedArt[art.url]) return loadedArt[art.url].complete ? loadedArt[art.url] : null;
  var image = new Image();
  image.onload = function () { draw(); };
  image.src = art.url;
  loadedArt[art.url] = image;
  return null;
}

var composed = {};

// The panel as the board would draw it, with the background, then the picture where the look puts
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

  // Lay copies out from where the first sits along each side that tiles, and turn every other one
  // round on a side that mirrors
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
// Any other browser keeps showing the still

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

// A screen module drawn showing its picture composed with its look, and a gif playing in it
export function panelPreview(screen) {
  var style = screen.look ? screen.look.style : "";
  var art = screen.look && screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows, style)
                                                                     : null;
  // A drawing is drawn at its canvas's size, then placed and doubled as a picture is
  if (art && kindOf(screen.shows) === "drawing") {
    var canvas = canvasPixels(screen.look, screen.size, screen.turn);
    art = drawingArt(screen.shows, canvas[0], canvas[1], style);
  }
  var made = art ? composedArt(screen, screen.look, art) : null;
  // A picture still loading leaves the screen showing what it last showed of that file, so a new
  // style or setting does not blank it for a moment
  if (made) shownBefore[screen.shows] = made;
  else if (screen.shows && shownBefore[screen.shows]) made = shownBefore[screen.shows];
  if (!made) return panelDrawing(screen);
  var name = "~look" + Object.keys(state.art).length;
  state.art[name] = made;
  var drawing = panelDrawing(Object.assign({}, screen, {shows: name}));
  delete state.art[name];
  if (kindOf(screen.shows) === "gif") liveGif(drawing, made, screen, screen.look, art);
  return drawing;
}

// The choices a style word makes, one from each of the drawing's Styles: lines, a line's first
// where the word names none of its. The word joins its choices with dashes, in any order
export function styleChoices(drawing, style) {
  var words = style ? style.split("-") : [];
  return drawing.styles.map(function (line) {
    return words.filter(function (word) { return line.indexOf(word) >= 0; })[0] || line[0];
  });
}

// The style word for these choices, in the lines' order. A line's first choice is left out, so a
// drawing drawn as it is unchosen writes no style
export function styleWord(drawing, choices) {
  return choices.filter(function (choice, at) { return choice !== drawing.styles[at][0]; }).join("-");
}

// The style word of the thumbnail nearest a style, whatever order its choices were written in. A
// style without a thumbnail of its own drops its last choice until one has, so ember-bare-oval
// is shown by ember-bare's or ember's, and by the drawing's own where none has one
function styleNamed(media, style) {
  if (!style || !media || !media.drawing) return style;
  var choices = styleWord(media.drawing, styleChoices(media.drawing, style)).split("-");
  var thumbs = media.styleThumbs || {};
  while (choices.length && !thumbs[choices.join("-")]) choices.pop();
  return choices.join("-");
}

// Of a pair's two screens, the one whose canvas is larger after its own turn and pixel_double,
// as the board sizes a drawing shown on both. The first screen wins a tie
export function pairLarger(playings) {
  var areas = SCREENS.map(function (letter, at) {
    var panel = panelPixels(state.screens[letter].size, playings[at].turn);
    var scale = playings[at].look && playings[at].look.double ? 2 : 1;
    return Math.floor(panel[0] / scale) * Math.floor(panel[1] / scale);
  });
  return areas[1] > areas[0] ? 1 : 0;
}

// A paired drawing as the larger screen sizes its canvas. It is Screen A's playing, which the pair
// shares, at the larger screen's turn and pixel_double, and that screen's size
export function pairSized(playings) {
  var larger = pairLarger(playings);
  var look = Object.assign({}, playings[0].look || freshLook(),
                           {double: !!(playings[larger].look && playings[larger].look.double)});
  return {playing: Object.assign({}, playings[0], {turn: playings[larger].turn}), look: look,
          size: state.screens[SCREENS[larger]].size};
}

// The canvas a paired drawing is drawn on
export function pairCanvas(playings) {
  var sized = pairSized(playings);
  return canvasPixels(sized.look, sized.size, sized.playing.turn);
}
