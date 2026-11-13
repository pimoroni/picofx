import {WORDS, hexOf, hexRgb} from "../01_colours.js";
import {quoted} from "../01_looks.js";
import {boardResidue} from "../03_kept.js";
import {entryParts, unquoted} from "../03_reading.js";
import {allBodies, bodyParts, driveParts, state} from "../04_scenes.js";
import {boardWords, notFittedRead, notFittedSteps, saidNotFitted} from "../07_board.js";
import {isHiddenName, nameShown} from "../18_drive.js";
import {isExampleMedia, mediaHome} from "../26_drive_files.js";
import {openingString} from "../26_drive_programs.js";
import {
  SCREENS, SCREEN_NAMES, freshLook, kindOf, mediaNamed, screenLetter, screenShown
} from "./12_screens.js";
import {
  canvasPixels, drawingArts, drawingSaid, madeDrawing, pairLarger, pairSized, panelPixels,
  pictureOffset, shownBefore, styleWords
} from "./13_screen_art.js";

export function placingTokens(turn, look, light, where) {
  var tokens = [];
  if (Number(turn)) tokens.push("rotation=" + turn);
  if (light < 1) tokens.push("backlight=" + Math.round(light * 100) + "%");
  if (look.mirror) tokens.push("mirror=true");
  if (where.x !== "" || where.y !== "")
    tokens.push("offset=" + (where.x === "" ? "*" : where.x) + "|" +
                (where.y === "" ? "*" : where.y));
  if (look.bg !== "#000000") tokens.push("bg=" + (BG_NAMES[look.bg] || look.bg.slice(1)));
  if (look.double) tokens.push("pixel_double=true");
  var tileDown = look.tileDown || "off";
  if (look.tile !== "off" || tileDown !== "off")
    tokens.push("tile=" + (look.tile === tileDown ? look.tile : look.tile + "|" + tileDown));
  return tokens;
}

export function holdAllowed(playing, look) { return look.loop || playing.pingpong; }

export function secondHoldAllowed(playing, look) { return look.loop && playing.pingpong; }

export function firstAsLastAllowed(playing, look) { return playing.pingpong || !look.loop; }

export function playingTokens(playing, look, kind, size) {
  if (kind === "image") return [];
  var tokens = [];
  if (look.pace === "fps") tokens.push("fps=" + look.every);
  if (look.pace === "interval") tokens.push("interval=" + look.every);
  if (kind === "drawing") {
    var canvas = canvasPixels(look, size, playing.turn);
    var panel = panelPixels(size, playing.turn);
    var scale = look.double ? 2 : 1;
    if (canvas[0] !== Math.floor(panel[0] / scale) || canvas[1] !== Math.floor(panel[1] / scale))
      tokens.push("width=" + canvas[0], "height=" + canvas[1]);
    if (look.style) tokens.push("style=" + look.style);
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

export function lookEntry(selector, playing, look, light, size) {
  var kind = kindOf(playing.shows);
  var where = pictureOffset(look, playing.shows, size, playing.turn);
  var left = [selector].concat(placingTokens(playing.turn, look, light, where)).join(" ");
  var what = kind === "folder" ? "sequence folder=" : kind === "gif" ? "gif file="
           : kind === "drawing" ? "drawing file=" : "image file=";
  return [left + ":", what + quoted(playing.shows)]
    .concat(playingTokens(playing, look, kind, size)).join(" ");
}

export function placementSaid(look, where) {
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

export function groundSaid(bg) {
  var parts = groundParts(bg);
  var name = BG_NAMES["#" + hexOf(parts.full)];
  if (!name) return bg;
  return parts.value < 1 ? name + " at " + Math.round(parts.value * 100) + "%" : name;
}

export function playbackSaid(held, look) {
  var said = [look.pace === "fps" ? look.every + " fps"
            : look.pace === "interval" ? "frame every " + look.every + " s"
            : kindOf(held.shows) === "folder" ? "timing from file names" : "timing from file"];
  said.push(look.loop ? "loop" : "once");
  if (held.pingpong) said.push("ping pong");
  if (look.whole && firstAsLastAllowed(held, look)) said.push("first frame as last");
  if ((held.hold || look.holdBack) && holdAllowed(held, look))
    said.push("hold " + (held.hold || 0) + " s" +
              (look.holdBack && secondHoldAllowed(held, look) ? " and " + look.holdBack + " s"
                                                              : ""));
  return said.join(", ");
}

export function pictureSaid(name) {
  var media = mediaNamed(name);
  if (media && media.kind === "drawing") return media.drawing.title;
  if (isExampleMedia(name)) return nameShown(name);
  return media && media.kind === "folder" ? "/" + name : name;
}

var PAIR_UNSET = {rotation: "0", backlight: "100%", mirror: "false", offset: "*|*",
                  bg: "black", pixel_double: "false", tile: "off"};

export function picturesMatch(first, second) {
  if (!first.shows || first.shows === "keep" || second.shows !== first.shows) return false;
  var kind = kindOf(first.shows);
  if (kind === "drawing") return false;
  return playingTokens(first, first.look || freshLook(), kind, null).join(" ") ===
         playingTokens(second, second.look || freshLook(), kind, null).join(" ");
}

function pairWritten(body) {
  if (SCREENS.length < 2 || state.hub.on) return false;
  if (!state.screens[SCREENS[0]].there || !state.screens[SCREENS[1]].there) return false;
  var first = body.screens[SCREENS[0]];
  var second = body.screens[SCREENS[1]];
  if (!body.screensPaired) return picturesMatch(first, second);
  return !!first.shows && first.shows !== "keep" && second.shows === first.shows;
}

function pairEntry(body) {
  var said = SCREENS.map(function (letter) {
    var playing = body.screens[letter];
    var look = playing.look || freshLook();
    var size = state.screens[letter].size;
    var where = pictureOffset(look, playing.shows, size, playing.turn);
    var held = {};
    placingTokens(playing.turn, look, look.backlight, where).forEach(function (token) {
      var equals = token.indexOf("=");
      held[token.slice(0, equals)] = token.slice(equals + 1);
    });
    return held;
  });
  var left = [SCREEN_NAMES[SCREENS[0]] + "," + SCREENS[1]];
  Object.keys(PAIR_UNSET).forEach(function (key) {
    if (said[0][key] === undefined && said[1][key] === undefined) return;
    var values = said.map(function (held) {
      return held[key] === undefined ? PAIR_UNSET[key] : held[key];
    });
    left.push(key + "=" + (values[0] === values[1] ? values[0] : values.join(",")));
  });

  var playing = body.screens[SCREENS[0]];
  var look = playing.look || freshLook();
  var size = state.screens[SCREENS[0]].size;
  var kind = kindOf(playing.shows);
  if (kind === "drawing") {
    var sized = pairSized(SCREENS.map(function (letter) { return body.screens[letter]; }));
    playing = sized.playing;
    look = sized.look;
    size = sized.size;
  }
  var what = kind === "folder" ? "sequence folder=" : kind === "gif" ? "gif file="
           : kind === "drawing" ? "drawing file=" : "image file=";
  return [left.join(" ") + ":", what + quoted(playing.shows)]
    .concat(playingTokens(playing, look, kind, size)).join(" ");
}

export function readPairedScreens(bodies) {
  if (SCREENS.length < 2 || state.hub.on) return;
  var selector = (SCREEN_NAMES[SCREENS[0]] + "," + SCREENS[1]).toLowerCase();

  var sizes = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(screen[ab]?)=(2\.8|1\.54)$/i);
    var letter = named && screenLetter(named[1]);
    if (letter) sizes[letter] = {token: token, size: named[2]};
  });
  SCREENS.forEach(function (letter) {
    if (!sizes[letter] && state.screens[letter].there && state.screens[letter].size)
      sizes[letter] = {token: null, size: state.screens[letter].size};
  });
  if (!sizes[SCREENS[0]] || !sizes[SCREENS[1]]) return;
  var readOn = false;

  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      if (!parts || parts.selector !== selector) return true;
      if (body.screens[SCREENS[0]].shows || body.screens[SCREENS[1]].shows) return true;

      var lefts = [{}, {}];
      var understood = true;
      Object.keys(parts.left).forEach(function (key) {
        var values = parts.left[key].split(",");
        if (values.length > 2) understood = false;
        values = values.length === 1 ? [values[0], values[0]] : values;
        values.forEach(function (value, at) {
          if (value !== PAIR_UNSET[key]) lefts[at][key] = value;
        });
      });
      if (!understood) return true;
      var playings = SCREENS.map(function (letter, at) {
        return screenPlaying({selector: SCREEN_NAMES[letter].toLowerCase(), left: lefts[at],
                              effect: parts.effect, right: parts.right}, body, letter);
      });
      if (!playings[0] || !playings[1]) return true;

      var was = SCREENS.map(function (letter) {
        return {there: state.screens[letter].there, size: state.screens[letter].size};
      });
      SCREENS.forEach(function (letter) {
        state.screens[letter].there = true;
        state.screens[letter].size = sizes[letter].size;
      });
      if (parts.effect === "drawing" && !parts.right.width && !parts.right.height) {
        var doubled = playings[pairLarger(playings)].look.double;
        playings.forEach(function (playing) { playing.look.canvas = doubled ? "half" : "whole"; });
      }
      var trial = {screens: {}, screensPaired: true};
      SCREENS.forEach(function (letter, at) { trial.screens[letter] = playings[at]; });
      if (!pairWritten(trial) || pairEntry(trial) !== one.text) {
        SCREENS.forEach(function (letter, at) {
          state.screens[letter].there = was[at].there;
          state.screens[letter].size = was[at].size;
        });
        return true;
      }

      SCREENS.forEach(function (letter, at) { body.screens[letter] = playings[at]; });
      body.screensPaired = kindOf(playings[0].shows) === "drawing";
      readOn = true;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });

  if (readOn) {
    SCREENS.forEach(function (letter) {
      var token = sizes[letter].token;
      if (token && boardResidue.indexOf(token) >= 0) boardResidue.splice(boardResidue.indexOf(token), 1);
    });
  }
}

function screenEntry(letter, body) {
  if (state.hub.on) return null;
  if (pairWritten(body)) return letter === SCREENS[0] ? pairEntry(body) : null;
  var screen = state.screens[letter];
  var playing = body.screens[letter];
  if (!screen.there) return null;
  if (playing.off) return offEntry(SCREEN_NAMES[letter], (playing.look || freshLook()).backlight);
  if (!playing.shows) return null;
  if (playing.shows === "keep") return playing.kept;
  var look = playing.look || freshLook();
  return lookEntry(SCREEN_NAMES[letter], playing, look, look.backlight, screen.size);
}

export function offEntry(selector, backlight) {
  return selector + (backlight < 1 ? " backlight=" + Math.round(backlight * 100) + "%" : "") +
         ": none";
}

bodyParts.push({
  capture: function (body) {
    body.screens = {};
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      body.screens[letter] = {shows: screen.shows, kept: screen.kept, pingpong: screen.pingpong,
                              hold: screen.hold, fps: screen.fps, turn: screen.turn,
                              off: screen.off};
    });
  },
  apply: function (body) {
    if (!body.screens) return;
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      Object.assign(screen, body.screens[letter]);
      screen.turn = body.screens[letter].turn || 0;
      screen.off = !!body.screens[letter].off;
      screen.lastShows = screen.shows;
    });
  },
  blank: function (body) {
    SCREENS.forEach(function (letter) {
      body.screens[letter].shows = null;
      body.screens[letter].off = false;
    });
  },
  hasContent: function (body) {
    return SCREENS.some(function (letter) {
      return !!(body.screens && (body.screens[letter].shows || body.screens[letter].off));
    });
  },
  sets: function (body) {
    var set = !state.hub.on && SCREENS.some(function (letter) {
      var held = body.screens && body.screens[letter];
      return held && (held.shows || held.off);
    });
    return set ? ["screens", "Screens"] : null;
  },
  named: function (body) {
    return SCREENS.map(function (letter) { return body.screens && body.screens[letter].shows; })
      .filter(function (shows) { return shows && shows !== "keep"; })
      .map(pictureSaid);
  },
  writes: "screens",
  entries: function (body, lines) {
    SCREENS.forEach(function (letter) {
      var entry = body.screens && screenEntry(letter, body);
      if (entry) lines.push(entry);
    });
    return lines;
  },
  read: readScreens
});

boardWords.screens = function () {
  var bodies = [state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  return SCREENS.filter(function (letter) {
    var screen = state.screens[letter];
    return screen.there && bodies.some(function (body) {
      return body && body.screens && (body.screens[letter].shows || body.screens[letter].off);
    });
  }).map(function (letter) {
    return SCREEN_NAMES[letter].toLowerCase() + "=" + state.screens[letter].size;
  });
};

notFittedSteps.push(function () {
  if (state.hub.on) return [];
  return SCREENS.filter(function (letter) { return !state.screens[letter].there; }).map(screenShown);
});

export function screenPlaying(parts, body, letter) {
  var playing = Object.assign({}, body.screens[letter]);
  var look = playing.look = freshLook();
  playing.turn = 0;
  playing.pingpong = false;
  playing.hold = "";
  playing.off = false;
  if (parts.effect === "none") {
    var known = Object.keys(parts.left).every(function (key) { return key === "backlight"; }) &&
                !Object.keys(parts.right).length;
    if (!known) return null;
    var light = parts.left.backlight;
    if (light !== undefined)
      look.backlight = /%$/.test(light) ? parseFloat(light) / 100 : Number(light);
    playing.shows = null;
    playing.off = true;
    return playing;
  }
  var source = {gif: "file", image: "file", drawing: "file", sequence: "folder"}[parts.effect];
  if (!source || !parts.right[source]) return null;
  playing.shows = unquoted(parts.right[source]);

  var understood = true;
  Object.keys(parts.left).forEach(function (key) {
    var value = parts.left[key];
    if (key === "rotation") playing.turn = Number(value);
    else if (key === "backlight") look.backlight = /%$/.test(value) ? parseFloat(value) / 100 : Number(value);
    else if (key === "mirror" && value === "true") look.mirror = true;
    else if (key === "pixel_double" && value === "true") look.double = true;
    else if (key === "bg") look.bg = "#" + (WORDS[value] ? hexOf(WORDS[value]) : value);
    else if (key === "offset") {
      var sides = value.split("|");
      look.anchor = null;
      look.x = sides[0] === "*" ? "" : sides[0];
      look.y = sides[1] === "*" ? "" : sides[1];
    } else if (key === "tile") {
      var ways = value.split("|");
      look.tile = ways[0];
      look.tileDown = ways[1] || ways[0];
    } else understood = false;
  });
  Object.keys(parts.right).forEach(function (key) {
    var value = parts.right[key];
    if (key === source) return;
    if (key === "fps" || key === "interval") {
      look.pace = key;
      look.every = Number(value);
    } else if (key === "loop" && value === "false") look.loop = false;
    else if (key === "ping_pong" && value === "true") playing.pingpong = true;
    else if (key === "first_as_last" && value === "true") look.whole = true;
    else if (key === "hold") {
      var ends = value.split("|");
      playing.hold = ends[0];
      look.holdBack = ends[1] || "";
    } else if (key === "width" || key === "height") {
      look.canvas = "set";
      look[key === "width" ? "canvasW" : "canvasH"] = Number(value);
    } else if (key === "style") look.style = value;
    else understood = false;
  });
  if (parts.effect === "drawing" && look.double && look.canvas !== "set") look.canvas = "half";
  return understood ? playing : null;
}

function readScreens(bodies) {
  if (notFittedRead) {
    SCREENS.forEach(function (letter) {
      state.screens[letter].there = !saidNotFitted(screenShown(letter));
    });
  }
  var sizes = {};
  boardResidue.forEach(function (token) {
    var named = token.match(/^(screen[ab]?)=(2\.8|1\.54)$/i);
    var letter = named && screenLetter(named[1]);
    if (letter) sizes[letter] = {token: token, size: named[2]};
  });
  var readOn = {};

  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      var letter = parts && screenLetter(parts.selector);
      if (!letter || !sizes[letter] || body.screens[letter].shows || body.screens[letter].off)
        return true;
      var playing = screenPlaying(parts, body, letter);
      if (!playing) return true;

      var fitted = state.screens[letter];
      var was = {there: fitted.there, size: fitted.size};
      fitted.there = true;
      fitted.size = sizes[letter].size;
      var trial = {screens: Object.assign({}, body.screens)};
      trial.screens[letter] = playing;
      if (screenEntry(letter, trial) !== one.text) {
        fitted.there = was.there;
        fitted.size = was.size;
        return true;
      }
      body.screens[letter] = playing;
      readOn[letter] = true;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });

  Object.keys(readOn).forEach(function (letter) {
    boardResidue.splice(boardResidue.indexOf(sizes[letter].token), 1);
  });
}

var mediaFound = [];

driveParts.push({
  begin: function () { mediaFound = []; },
  file: async function (name, handle) {
    if (/\.gif$/i.test(name)) mediaFound.push({ name: name, kind: "gif", handle: handle });
    else if (/\.(png|jpe?g)$/i.test(name)) mediaFound.push({ name: name, kind: "image", handle: handle });
    else if (/\.py$/i.test(name)) {
      var drawing = null;
      try {
        drawing = drawingSaid(openingString(await (await handle.getFile()).text()));
      } catch (e) {
        drawing = null;
      }
      if (drawing) mediaFound.push({name: name, kind: "drawing", drawing: drawing});
    } else return false;
    return true;
  },
  folder: async function (name, handle) {
    for await (var inner of handle.entries()) {
      if (inner[1].kind === "file" && !isHiddenName(inner[0]) &&
          /\.(gif|png|jpe?g)$/i.test(inner[0])) {
        mediaFound.push({ name: name, kind: "folder", thumbHandle: inner[1] });
        return true;
      }
    }
    return false;
  },
  land: function () {
    mediaFound.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
    function inDrawings(one) {
      return isExampleMedia(one.name) || (mediaHome[one.name] || {}).name === "drawings";
    }
    var thumbs = {};
    mediaFound.forEach(function (one) {
      if (one.kind === "image" && inDrawings(one)) thumbs[one.name] = one;
    });
    mediaFound.forEach(function (one) {
      var thumb = one.kind === "drawing" && inDrawings(one) &&
                  thumbs[one.name.replace(/\.py$/i, ".png")];
      if (!thumb) return;
      one.thumbHandle = thumb.handle;
      thumb.taken = true;
      one.styleThumbs = {};
      styleWords(one.drawing).forEach(function (style) {
        var styled = thumbs[one.name.replace(/\.py$/i, "-" + style + ".png")];
        if (!styled) return;
        one.styleThumbs[style] = styled.handle;
        styled.taken = true;
      });
    });
    mediaFound = mediaFound.filter(function (one) { return !one.taken; });
    state.media = mediaFound;
    Object.keys(state.art).forEach(function (key) {
      if (state.art[key].gone) delete state.art[key];
    });
    mediaFound.forEach(function (one) {
      if (one.kind !== "drawing" || !one.thumbHandle || !(state.art[one.name] || {}).face) return;
      delete state.art[one.name];
      Object.keys(drawingArts).forEach(function (key) {
        if (key.indexOf(one.name + "|") === 0) delete drawingArts[key];
      });
    });
    mediaFound.forEach(function (one) {
      if (one.kind === "drawing" && !one.thumbHandle) madeDrawing(one.name);
    });
  },
  said: function () {
    return JSON.stringify(state.media.map(function (m) { return m.name + m.kind; }));
  },
  forget: function (name) {
    allBodies().forEach(function (body) {
      SCREENS.forEach(function (letter) {
        if (body.screens[letter].shows === name) body.screens[letter].shows = null;
      });
    });
    Object.keys(state.art).forEach(function (key) {
      if (key === name || key.indexOf(name + "#") === 0) delete state.art[key];
    });
    Object.keys(drawingArts).forEach(function (key) {
      if (key.indexOf(name + "|") === 0) delete drawingArts[key];
    });
    delete shownBefore[name];
  }
});

var BG_NAMES = {};

Object.keys(WORDS).forEach(function (name) { BG_NAMES["#" + hexOf(WORDS[name])] = name; });

export var ANCHOR_NAMES = ["top left", "top", "top right", "left", "centred", "right", "bottom left",
                    "bottom", "bottom right"];

export function groundParts(hex) {
  var rgb = hexRgb(hex);
  var top = Math.max(rgb[0], rgb[1], rgb[2]);
  if (!top) return {full: [0, 0, 0], value: 1};
  return {full: rgb.map(function (v) { return Math.round(v * 255 / top); }), value: top / 255};
}

export function groundHex(full, value) {
  return "#" + hexOf(full.map(function (v) { return Math.round(v * value); }));
}
