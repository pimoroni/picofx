import {h} from "../00_dom.js";
import {draw, drawSteps} from "../00_draw.js";
import {WORDS, rgbInk} from "../01_colours.js";
import {capture, state} from "../04_scenes.js";
import {screenHooks} from "../07_board.js";
import {argumentFrom} from "../26_drive_programs.js";
import {SCREENS, freshLook, kindOf, mediaNamed} from "./12_screens.js";

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

function tabPath(x0, x1, near, far, radius) {
  var edge = far < near ? far + radius : far - radius;
  return "M" + x0 + " " + near +
         " L" + x0 + " " + edge +
         " Q" + x0 + " " + far + " " + (x0 + radius) + " " + far +
         " L" + (x1 - radius) + " " + far +
         " Q" + x1 + " " + far + " " + x1 + " " + edge +
         " L" + x1 + " " + near + " Z";
}

function moduleWords(x, y, ink, words) {
  return h("svg:text", {x: x, y: y, "text-anchor": "middle", fill: ink, "font-size": 4,
                        "font-family": "system-ui"}, words);
}

function moduleSaid(screen, art) {
  var size = (MODULE[screen.size] ? screen.size : "2.8") + " inch screen";
  if (screen.shows === "keep") return size + ", as it is";
  if (art) return size + ", showing a picture";
  if (screen.shows) return size + ", showing a picture on the board";
  if (screen.off) return size + ", off";
  return size + ", no picture";
}

function panelDrawing(screen, under) {
  var made = MODULE[screen.size] || MODULE["2.8"];
  var turn = Number(screen.turn || 0);
  var quarter = turn % 180 === 90;

  var boardW = made.board[0];
  var boardH = made.board[1];
  var extent = Math.max(boardW, boardH);
  var left = (extent - boardW) / 2;
  var bottom = (extent - boardH) / 2;
  function up(y) { return extent - bottom - y; }

  var holes = [];
  [[8, 5], [16, 3.2], [24, 5], [32, 3.2], [40, 5]].forEach(function (hole) {
    if (hole[0] > boardW - 4) return;
    [4, boardH - 4].forEach(function (y) {
      holes.push(h("svg:circle", {cx: left + hole[0], cy: up(y), r: hole[1] / 2, fill: HOLE_INK,
                                  stroke: HOLE_EDGE, "stroke-width": 0.3}));
    });
  });

  var litW = made.lit[0];
  var litH = made.lit[1];
  var litX = left + boardW / 2 - litW / 2;
  var litY = up(boardH / 2) - litH / 2;
  var art = screen.art || (screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows) : null);
  var middleX = litX + litW / 2;
  var middleY = litY + litH / 2 + 1.4;
  var words = screen.shows === "keep" ? moduleWords(middleX, middleY, "#8b959b", "as it is")
            : art ? null
            : screen.shows ? moduleWords(middleX, middleY, "#8b959b", "on the board")
            : screen.off ? moduleWords(middleX, middleY, "#5d666c", "off")
            : moduleWords(middleX, middleY, "#8b959b", "no picture");
  var name = PRINTED[screen.size] || PRINTED["2.8"];

  var drawing = h("svg:svg", {viewBox: "0 0 " + extent + " " + extent, "aria-hidden": "true"},
    h("svg:g", {transform: "rotate(" + turn + " " + (extent / 2) + " " + (extent / 2) + ")"},
      h("svg:rect", {x: left, y: up(made.body[1]), width: boardW, height: made.body[1] - made.body[0],
                     fill: BOARD_INK}),
      h("svg:path", {d: tabPath(left + made.tab[0], left + made.tab[1], up(made.body[1]),
                                up(made.tab[2]), made.tabRadius), fill: BOARD_INK}),
      h("svg:path", {d: tabPath(left + made.tab[0], left + made.tab[1], up(made.body[0]),
                                up(boardH - made.tab[2]), made.tabRadius), fill: BOARD_INK}),
      holes,
      h("svg:rect", {x: left + made.panel[0], y: up(made.panel[3]),
                     width: made.panel[2] - made.panel[0], height: made.panel[3] - made.panel[1],
                     fill: PANEL_INK, stroke: FRAME_INK, "stroke-width": FRAME_WIDE}),
      h("svg:rect", {x: litX, y: litY, width: litW, height: litH,
                     fill: art ? GROUND_INK : screen.off ? "#000000" : EMPTY_INK}),
      h("svg:rect", {x: litX - 0.4, y: litY + litH, width: litW + 0.8,
                     height: Math.max(0, up(made.panel[1]) - (litY + litH) - 0.4), fill: CHIN_INK}),
      words,
      h("svg:g", {transform: "translate(" + (left - name.x / PER_MM) + " " +
                             (extent - bottom - name.y / PER_MM) + ") scale(" + (1 / PER_MM) + ")",
                  fill: NAME_INK},
        h("svg:path", {d: name.d}))));

  var picture = null;
  if (art) {
    var px = PANEL_PX[screen.size] || PANEL_PX["2.8"];
    var windowW = quarter ? litH : litW;
    var windowH = quarter ? litW : litH;
    var perPixel = litW / px[0];
    picture = h("div", {style: {"--left": ((extent - windowW) / 2 / extent * 100) + "%",
                                "--top": ((extent - windowH) / 2 / extent * 100) + "%",
                                "--wide": (windowW / extent * 100) + "%",
                                "--high": (windowH / extent * 100) + "%"}},
      h("img", {src: art.url, alt: "", "data-pixelated": !!art.pixelated,
                style: {"--w": (art.w * perPixel / windowW * 100) + "%",
                        "--h": (art.h * perPixel / windowH * 100) + "%"}}));
  }
  return h("div", {class: "screenmodule", role: "img", "aria-label": moduleSaid(screen, art),
                   "data-under": !!under, title: under || null},
    drawing, picture);
}

var pictureQueue = [];

var pictureReading = null;

var shownThisDraw = null;

drawSteps.before.push(function () { shownThisDraw = null; });

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
      probe.onerror = function () { settle(); };
      probe.src = url;
    });
  }, function () {
    if (state.art[next.name]) state.art[next.name].gone = true;
  }).then(function () {
    pictureReading = null;
    draw();
    readNextPicture();
  });
}

export function mediaArt(name, style) {
  var media = mediaNamed(name);
  style = styleNamed(media, style);
  var styled = style && media && media.styleThumbs ? media.styleThumbs[style] : null;
  var key = styled ? name + "#" + style : name;
  var held = state.art[key];
  if (held) return held.ratio ? held : styled ? mediaArt(name) : null;
  var handle = styled || (media && (media.thumbHandle || media.handle));
  if (!handle) return null;
  state.art[key] = {url: null, ratio: 0};
  pictureQueue.push({name: key, handle: handle});
  setTimeout(readNextPicture, 0);
  return styled ? mediaArt(name) : null;
}

export function panelPixels(size, turn) {
  var panel = PANEL_PX[size] || PANEL_PX["2.8"];
  return Number(turn || 0) % 180 === 90 ? [panel[1], panel[0]] : [panel[0], panel[1]];
}

export function canvasPixels(look, size, turn) {
  var panel = panelPixels(size, turn);
  if (look.canvas === "set") return [Number(look.canvasW), Number(look.canvasH)];
  if (look.canvas === "half") return [Math.floor(panel[0] / 2), Math.floor(panel[1] / 2)];
  return panel;
}

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

var DRAWING_LINE = /^\s*(Drawing|Icon|Colour|Section|Defaults|Styles|Firmware):\s*(.+?)\s*$/;

export function drawingSaid(docstring) {
  var said = {title: "", description: "", icon: "", colour: "", section: "", defaults: {},
              styles: []};
  var rest = docstring.split("\n").filter(function (line) {
    var field = line.match(DRAWING_LINE);
    if (!field) return true;
    if (field[1] === "Styles") {
      var choices = field[2].split(",").map(function (style) { return style.trim(); }).filter(Boolean);
      if (choices.length) said.styles.push(choices);
    } else if (field[1] === "Defaults") {
      field[2].split(",").map(argumentFrom).forEach(function (setting) {
        said.defaults[setting.name] = setting;
      });
    } else {
      said[field[1] === "Drawing" ? "title" : field[1].toLowerCase()] = field[2];
    }
    return false;
  }).join(" ").split(/\s+/).join(" ").trim();
  if (!said.title) return null;
  var first = rest.match(/^(.*?\.)(\s|$)/);
  said.description = first ? first[1] : rest;
  return said;
}

export function drawingInk(drawing, name) {
  var word = WORDS[drawing.colour.toLowerCase()];
  if (word) return rgbInk(word);
  if (/^#?[0-9a-f]{6}$/i.test(drawing.colour)) return "#" + drawing.colour.replace("#", "");
  return "hsl(" + nameHue(name) + ",60%,45%)";
}

export var drawingArts = {};

function drawingArt(name, wide, high, style) {
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

export function madeDrawing(name) {
  Object.keys(drawingArts).forEach(function (key) {
    if (key.indexOf(name + "|") === 0) delete drawingArts[key];
  });
  state.art[name] = drawingArt(name, 240, 240);
  state.art[name].face = true;
}

var loadedArt = {};

function artImage(art) {
  if (loadedArt[art.url]) return loadedArt[art.url].complete ? loadedArt[art.url] : null;
  var image = new Image();
  image.onload = function () { draw(); };
  image.src = art.url;
  loadedArt[art.url] = image;
  return null;
}

var composed = {};

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
    var canvas = h("canvas", {width: still.w, height: still.h});
    canvas.style.cssText = shown.style.cssText;
    shown.replaceWith(canvas);
    playing.canvas = canvas;
    nextGifFrame(playing, gif);
  }).catch(function () {});
}

function nextGifFrame(playing, gif) {
  if (!playing.canvas.isConnected) return;
  gif.decoder.decode({frameIndex: playing.at}).then(function (decoded) {
    var frame = decoded.image;
    composeOnto(playing.canvas.getContext("2d"), playing.screen, playing.look, playing.art, frame,
                playing.canvas.width, playing.canvas.height);
    var wait = frame.duration ? frame.duration / 1000 : 100;
    frame.close();
    playing.at = (playing.at + 1) % gif.frames;
    setTimeout(function () { nextGifFrame(playing, gif); }, Math.max(20, wait));
  }).catch(function () {});
}

export var shownBefore = {};

export function panelPreview(screen, under) {
  var style = screen.look ? screen.look.style : "";
  var art = screen.look && screen.shows && screen.shows !== "keep" ? mediaArt(screen.shows, style)
                                                                     : null;
  if (art && kindOf(screen.shows) === "drawing") {
    var canvas = canvasPixels(screen.look, screen.size, screen.turn);
    art = drawingArt(screen.shows, canvas[0], canvas[1], style);
  }
  var made = art ? composedArt(screen, screen.look, art) : null;
  if (made) shownBefore[screen.shows] = made;
  else if (screen.shows && shownBefore[screen.shows]) made = shownBefore[screen.shows];
  if (!made) return panelDrawing(screen, under);
  var drawing = panelDrawing(Object.assign({}, screen, {art: made}), under);
  if (kindOf(screen.shows) === "gif") liveGif(drawing, made, screen, screen.look, art);
  return drawing;
}

export function styleChoices(drawing, style) {
  var words = style ? style.split("-") : [];
  return drawing.styles.map(function (line) {
    return words.filter(function (word) { return line.indexOf(word) >= 0; })[0] || line[0];
  });
}

export function styleWord(drawing, choices) {
  return choices.filter(function (choice, at) { return choice !== drawing.styles[at][0]; }).join("-");
}

export function styleWords(drawing) {
  var words = [[]];
  drawing.styles.forEach(function (line) {
    var grown = [];
    words.forEach(function (word) {
      line.forEach(function (choice, at) { grown.push(at ? word.concat([choice]) : word); });
    });
    words = grown;
  });
  return words.filter(function (word) { return word.length; }).map(function (word) {
    return word.join("-");
  });
}

function styleNamed(media, style) {
  if (!style || !media || !media.drawing) return style;
  var choices = styleWord(media.drawing, styleChoices(media.drawing, style)).split("-");
  var thumbs = media.styleThumbs || {};
  while (choices.length && !thumbs[choices.join("-")]) choices.pop();
  return choices.join("-");
}

export function pairLarger(playings) {
  var areas = SCREENS.map(function (letter, at) {
    var panel = panelPixels(state.screens[letter].size, playings[at].turn);
    var scale = playings[at].look && playings[at].look.double ? 2 : 1;
    return Math.floor(panel[0] / scale) * Math.floor(panel[1] / scale);
  });
  return areas[1] > areas[0] ? 1 : 0;
}

export function pairSized(playings) {
  var larger = pairLarger(playings);
  var look = Object.assign({}, playings[0].look || freshLook(),
                           {double: !!(playings[larger].look && playings[larger].look.double)});
  return {playing: Object.assign({}, playings[0], {turn: playings[larger].turn}), look: look,
          size: state.screens[SCREENS[larger]].size};
}

export function pairCanvas(playings) {
  var sized = pairSized(playings);
  return canvasPixels(sized.look, sized.size, sized.playing.turn);
}

screenHooks.panelPreview = panelPreview;
