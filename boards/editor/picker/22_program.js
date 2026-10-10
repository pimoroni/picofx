
// ---- the effects page, or a program page ------------------------------------------------------
// Only program= and args= reach a program, which takes the whole board, so the page is one of
// two: the effects, as it opens, or a program run in their place. The program page replaces the
// effects view whole, scenes and all, since none of it plays while a program runs. Saving and
// the drive are on the save button's menu.
//
// The programs offered are those that do something the effects cannot and run by themselves:
// the showcase signs, screen pieces, and what a remote, a sensor, a speaker or a motor brings.
// The effects' own demonstrations, walkthroughs of the drawing library and calibrations are left
// out. Each has a small thumbnail at a screen's shape and low resolution: a frame captured off a
// board running it where there is one, drawn here where there is not.

// The board's offered examples by section, each as its path under EXAMPLES_ROOT and how its
// thumbnail is drawn, "shot" being its captured frame. What each uses is read from its source when
// the page is built
var OFFERED = (BOARD.offered || []).map(function (set) { return [set.section, set.examples]; });

// Where the board keeps the examples it offers: what the repository holds under examples/<board>/
// sits at the board's own root
var EXAMPLES_ROOT = BOARD.examples ? BOARD.examples.split("/").slice(2).join("/") + "/" : "";

// What each group's heading says after its name, as the looks' groups do
var GROUP_SAYS = {"On the drive": "your own programs"};
(BOARD.offered || []).forEach(function (set) { GROUP_SAYS[set.section] = set.says; });

// The picture each of the drive's programs names in its opening string, read off the drive, by
// the program's name
var DRIVE_PICTURES = {};

// Round holes cut through a filled shape, one at each point, as a path's own subpaths
function holes(points, radius) {
  return points.map(function (at) {
    return "M" + (at[0] - radius) + " " + at[1] + "a" + radius + " " + radius + " 0 1 0 " +
           radius * 2 + " 0a" + radius + " " + radius + " 0 1 0 " + -radius * 2 + " 0";
  }).join("");
}

// What a program can use beyond the board, each with its name, the shorter one its chip in the
// filter takes, and a drawing on a 24 grid, in the order they are shown. A part classed "f" is
// filled, "fs" filled and outlined, and the rest outlined, so each reads as a silhouette at 18px
var FEATURES = [
  ["outputs", "the outputs", "outputs",
   "<circle class='f' cx='3.8' cy='10' r='3'/><circle class='f' cx='12' cy='10' r='3'/>" +
   "<circle class='f' cx='20.2' cy='10' r='3'/><path d='M1.5 18h21' stroke-width='2.2'/>"],
  // Three lights overlapping, as the three channels of one RGB output
  ["rgb", "the RGB output", "RGB",
   "<circle class='f' cx='12' cy='8' r='5'/><circle cx='8' cy='15' r='5' stroke-width='2'/>" +
   "<circle cx='16' cy='15' r='5' stroke-width='2'/>"],
  // One panel filled, two apart for a pair, the second outlined where it is optional, six for a hub
  ["screen", "a screen", "screen", "<rect class='f' x='3' y='5' width='18' height='14' rx='2'/>"],
  ["either", "one screen or two", "1 or 2 screens",
   "<rect class='f' x='0.5' y='6' width='9.5' height='12' rx='1.6'/>" +
   "<rect x='15' y='7' width='7.5' height='10' rx='1.2' stroke-width='2'/>"],
  ["pair", "two screens", "2 screens",
   "<rect class='f' x='0.5' y='6' width='9.5' height='12' rx='1.6'/>" +
   "<rect class='f' x='14' y='6' width='9.5' height='12' rx='1.6'/>"],
  ["hub", "a screen hub", "hub",
   "<rect class='f' x='1' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect class='f' x='8.85' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect class='f' x='16.7' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect class='f' x='1' y='13' width='6.3' height='7' rx='1.2'/>" +
   "<rect class='f' x='8.85' y='13' width='6.3' height='7' rx='1.2'/>" +
   "<rect class='f' x='16.7' y='13' width='6.3' height='7' rx='1.2'/>"],
  // The strip folded back on itself, along the top, back along the middle and out along the foot,
  // as the effects page draws a strip, its LEDs cut out of it
  ["strip", "an LED strip", "strip",
   "<path class='f' fill-rule='evenodd' d='M1 2.5H17.5A6 6 0 0 1 17.5 14.5H6.5A1 1 0 0 0 6.5 " +
   "16.5H23V21.5H6.5A6 6 0 0 1 6.5 9.5H17.5A1 1 0 0 0 17.5 7.5H1Z" +
   holes([[4.5, 5], [9, 5], [13.5, 5], [9.5, 12], [14, 12], [10.5, 19], [15, 19], [19.5, 19]],
         1.35) + "'/>"],
  ["sound", "a speaker", "speaker",
   "<g transform='scale(1.5)' stroke-width='1.2'><path class='fs' d='M2 6h3l4-3v10l-4-3H2z'/>" +
   "<path d='M11 5.5q2 2.5 0 5M12.8 3.8q3.4 4.2 0 8.4'/></g>"],
  // The handset tilted, pointing, with its signal leaving the tip
  ["remote", "the IR remote", "remote",
   "<g transform='rotate(-35 12 12)'><path class='f' fill-rule='evenodd' d='M9.5 7h5a2.5 2.5 0 " +
   "0 1 2.5 2.5v11a2.5 2.5 0 0 1-2.5 2.5h-5A2.5 2.5 0 0 1 7 20.5v-11A2.5 2.5 0 0 1 9.5 7z" +
   holes([[12, 11]], 1.6) + "'/><path d='M9 4q3-2 6 0M7 1.2q5-3 10 0' stroke-width='2'/></g>"],
  // The connector's plug, its four pins and a short stub of cable
  ["qwst", "a Qw/ST sensor", "Qw/ST",
   "<path class='f' fill-rule='evenodd' d='M5 2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 " +
   "1-2-2V4a2 2 0 0 1 2-2zM5 5.5h2v8H5zM9 5.5h2v8H9zM13 5.5h2v8h-2zM17 5.5h2v8h-2z'/>" +
   "<rect class='f' x='10' y='17' width='4' height='5.5'/>"],
  // A fader, since a gauge reads as the effects' Speed and a wave as sound
  ["analog", "an analog sensor", "analog",
   "<path d='M3 12h18' stroke-width='2.4'/><rect class='f' x='12' y='6' width='5.5' " +
   "height='12' rx='1.4'/>"],
  ["motor", "motors", "motors",
   "<rect class='f' x='1.5' y='5' width='15' height='14' rx='3.5'/>" +
   "<rect class='f' x='16.5' y='10.5' width='6' height='3' rx='1'/>"],
  // A servo from the side, its mounting tabs and its arm, the arm no longer than the body
  ["servo", "servos", "servos",
   "<rect class='f' x='4' y='10' width='16' height='11' rx='1.5'/>" +
   "<rect class='f' x='1' y='13' width='22' height='3' rx='1'/>" +
   "<rect class='f' x='7' y='6.5' width='4' height='4'/><path d='M9 5.5H17.5' stroke-width='3.2'/>"],
  ["wifi", "Wi-Fi", "Wi-Fi",
   "<g transform='scale(1.5)' stroke-width='1.2'><path d='M1.5 6.5a9 9 0 0 1 13 0M4 9a5.5 5.5 0 " +
   "0 1 8 0'/><circle class='fs' cx='8' cy='12' r='1.4'/></g>"],
  ["button", "the Boot button", "Boot button",
   "<rect x='3' y='3' width='18' height='18' rx='3'/><circle class='f' cx='12' cy='12' r='4.5'/>"]
];

function featureNamed(key) {
  return FEATURES.filter(function (one) { return one[0] === key; })[0];
}

function featureIcon(key) {
  var feature = featureNamed(key);
  var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("class", "featureicon");
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = feature[3];
  return icon;
}

// What an example uses, read from its source. A program on the drive says nothing of it
function usesOf(path) {
  var example = BOARD_EXAMPLES.filter(function (one) { return one.path === path; })[0];
  return example ? example.uses : [];
}

// Frames captured off a board running each example, composed to what its panel showed and scaled
// to the thumbnail's size, by the example's file name, carried in the page as data URLs. Where one
// exists it is the thumbnail, the drawn one standing in only for what has not been captured
var THUMBS = __THUMBS__;

function offeredAt(path) {
  for (var g = 0; g < OFFERED.length; g++) {
    for (var i = 0; i < OFFERED[g][1].length; i++) {
      if (EXAMPLES_ROOT + OFFERED[g][1][i][0] === path) return OFFERED[g][1][i];
    }
  }
  return null;
}

// Words a file name spells for the code, said as a reader would
var TITLE_WORDS = {crt: "CRT", led: "LED", color: "colour"};

// A program's name to show: its own where it gives one, else its file's, in words
function programTitle(path) {
  var program = programNamed(path);
  if (program && program.name) return program.name;
  var words = path.split("/").pop().replace(/\.py$/, "").split("_").map(function (word) {
    return TITLE_WORDS[word] || word;
  }).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---- thumbnails ----------------------------------------------------------------------------------
// A screen's shape at a fifth of a 2.8" panel's pixels, drawn blocky on purpose, which is also what
// a captured frame scaled down this far would look like

var THUMB_W = 64, THUMB_H = 48;
var thumbImages = {};

function thumbCanvas(kind, seed, uses) {
  var canvas = document.createElement("canvas");
  canvas.width = THUMB_W;
  canvas.height = THUMB_H;
  canvas.className = "progthumb";
  paintThumb(canvas.getContext("2d"), kind, seed || 1, canvas, uses || []);
  return canvas;
}

// The outputs a program's lamps are drawn for: all of them, but a colour output among mono ones
// only where the program uses it
function lampsDrawn(uses) {
  var mixed = BOARD.outputs.some(function (output) { return output.kind === "mono"; });
  return BOARD.outputs.filter(function (output) {
    return !mixed || output.kind === "mono" || uses.indexOf("rgb") >= 0;
  });
}

// A lamp's colour on a mono output, a warm white as bright as the colour, an unlit lamp unchanged
function monoInk(ink) {
  if (ink === "#3a3f44") return ink;
  var level = (parseInt(ink.slice(1, 3), 16) * 0.2126 + parseInt(ink.slice(3, 5), 16) * 0.7152 +
               parseInt(ink.slice(5, 7), 16) * 0.0722) / 255;
  level = Math.max(0.3, level);
  return "rgb(" + Math.round(255 * level) + "," + Math.round(217 * level) + "," +
         Math.round(160 * level) + ")";
}

// A repeatable scatter, so a thumbnail is the same every time it is drawn
function scatter(seed) {
  var state = seed * 9301 + 49297;
  return function () {
    state = (state * 9301 + 49297) % 233280;
    return state / 233280;
  };
}

function paintThumb(g, kind, seed, canvas, uses) {
  var W = THUMB_W, H = THUMB_H, x, y, i;
  var chance = scatter(seed);
  function fill(ink) { g.fillStyle = ink; g.fillRect(0, 0, W, H); }
  function dotRow(ink, top, count, size, gap) {
    g.fillStyle = ink;
    for (i = 0; i < count; i++) g.fillRect(3 + i * (size + gap), top, size, size);
  }
  // A pair's two captured frames side by side, each whole in its half, as the two panels stand
  if (kind.indexOf("pair:") === 0) {
    fill("#111");
    [THUMBS[kind.slice(5)], THUMBS[kind.slice(5) + "-2"]].forEach(function (src, side) {
      var panel = thumbImages[src];
      if (!panel) {
        panel = thumbImages[src] = new Image();
        panel.src = src;
      }
      var placed = function () {
        var half = W / 2 - 1;
        var fit = Math.min(half / panel.width, H / panel.height);
        g.imageSmoothingEnabled = true;
        g.drawImage(panel, side * (half + 2) + (half - panel.width * fit) / 2,
                    (H - panel.height * fit) / 2, panel.width * fit, panel.height * fit);
      };
      if (panel.complete && panel.width) placed();
      else panel.addEventListener("load", placed);
    });
    return;
  }
  // A captured frame carried in the page, or the picture a program on the drive names
  if (kind.indexOf("shot:") === 0 || kind.indexOf("picture:") === 0) {
    fill("#111");
    var src = kind.indexOf("shot:") === 0 ? THUMBS[kind.slice(5)] : DRIVE_PICTURES[kind.slice(8)];
    var image = thumbImages[src];
    if (!image) {
      image = thumbImages[src] = new Image();
      image.src = src;
    }
    var drawn = function () {
      var scale = Math.max(W / image.width, H / image.height);
      g.imageSmoothingEnabled = true;
      g.drawImage(image, (W - image.width * scale) / 2, (H - image.height * scale) / 2,
                  image.width * scale, image.height * scale);
    };
    if (image.complete && image.width) drawn();
    else image.addEventListener("load", drawn);
    return;
  }
  if (kind.indexOf("lamps:") === 0) {
    // What the outputs do, as a lamp for each on the board's dark, spread across seven lamps' width
    fill("#1c1f22");
    var inks = {rainbow: ["#ff2d1a", "#ff9022", "#ffd21f", "#22c65a", "#28e0e0", "#2b5cff", "#9a46ff"],
                warm: ["#ffb060", "#ffc27a", "#ff9022", "#ffb060", "#ffc27a", "#ff9022", "#ffb060"],
                mono: ["#ffd9a0", "#3a3f44", "#ffd9a0", "#ffd9a0", "#3a3f44", "#ffd9a0", "#3a3f44"],
                pulse: ["#ffd9a0", "#c9aa7c", "#8a765a", "#4d4336", "#8a765a", "#c9aa7c", "#ffd9a0"],
                dusk: ["#ffe6b0", "#ffe6b0", "#ffe6b0", "#c9aa7c", "#8a765a", "#4d4336", "#3a3f44"],
                level: ["#3a3f44", "#3a3f44", "#22c65a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"],
                bar: ["#2b5cff", "#28e0e0", "#22c65a", "#ffd21f", "#3a3f44", "#3a3f44", "#3a3f44"],
                melody: ["#9a46ff", "#3a3f44", "#ff36c8", "#9a46ff", "#3a3f44", "#2b5cff", "#ff36c8"],
                countdown: ["#ff2d1a", "#ff2d1a", "#ff2d1a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"],
                off: ["#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44"]};
    var row = inks[kind.slice(6)] || inks.mono;
    var lamps = lampsDrawn(uses);
    lamps.forEach(function (output, at) {
      var ink = row[Math.min(at, row.length - 1)];
      g.fillStyle = output.kind === "mono" ? monoInk(ink) : ink;
      g.beginPath();
      g.arc(lamps.length > 1 ? 6 + at * 8.6 * 6 / (lamps.length - 1) : W / 2, H / 2, 3.2, 0,
            Math.PI * 2);
      g.fill();
    });
    return;
  }
  switch (kind) {
  case "flipdot":
    fill("#101010");
    for (y = 0; y < 7; y++) for (x = 0; x < 20; x++) {
      g.fillStyle = chance() < 0.42 ? "#f5d400" : "#262626";
      g.fillRect(2 + x * 3, 13 + y * 3, 2, 2);
    }
    break;
  case "flap":
    fill("#161616");
    for (i = 0; i < 4; i++) {
      g.fillStyle = "#2c2c2c";
      g.fillRect(4 + i * 14 + (i > 1 ? 4 : 0), 12, 12, 24);
      g.fillStyle = "#0c0c0c";
      g.fillRect(4 + i * 14 + (i > 1 ? 4 : 0), 23, 12, 1);
      g.fillStyle = "#eee";
      g.font = "bold 16px monospace";
      g.fillText("1942".charAt(i), 6 + i * 14 + (i > 1 ? 4 : 0), 30);
    }
    break;
  case "flapboard":
    fill("#161616");
    for (y = 0; y < 5; y++) for (x = 0; x < 9; x++) {
      g.fillStyle = "#2a2a2a";
      g.fillRect(2 + x * 6.8, 5 + y * 8, 6, 7);
      g.fillStyle = chance() < 0.7 ? "#e8e8e8" : "#f5c400";
      g.fillRect(3.5 + x * 6.8, 7 + y * 8, 3, 3);
    }
    break;
  case "nixie":
  case "lixie":
    fill(kind === "nixie" ? "#140a06" : "#06080f");
    g.font = "bold 30px serif";
    g.shadowColor = kind === "nixie" ? "#ff7a1a" : "#6ab0ff";
    g.shadowBlur = 8;
    g.fillStyle = kind === "nixie" ? "#ffb060" : "#bfe0ff";
    g.fillText("7", 23, 36);
    g.shadowBlur = 0;
    break;
  case "board":
  case "bus":
    fill(kind === "bus" ? "#0b1a33" : "#0a0a0a");
    for (y = 0; y < 5; y++) {
      g.fillStyle = kind === "bus" ? "#ffffff" : "#ffb000";
      g.fillRect(4, 6 + y * 8, 8 + chance() * 10, 3);
      g.fillRect(28, 6 + y * 8, 14 + chance() * 12, 3);
      g.fillStyle = kind === "bus" ? "#ffd21f" : "#ffb000";
      g.fillRect(W - 12, 6 + y * 8, 8, 3);
    }
    break;
  case "amber":
  case "roadworks":
    fill("#0d0c0a");
    for (y = 0; y < 8; y++) for (x = 0; x < 21; x++) {
      var on = kind === "roadworks" ? (y === 3 || y === 4 || (x > 8 && x < 12))
                                    : chance() < 0.3;
      g.fillStyle = on ? "#ffa51a" : "#2a2218";
      g.fillRect(2 + x * 3, 12 + y * 3, 2, 2);
    }
    break;
  case "gantry":
    fill("#0a0a0a");
    for (i = 0; i < 3; i++) {
      g.fillStyle = "#1e1e1e";
      g.fillRect(3 + i * 21, 10, 18, 28);
      g.strokeStyle = i === 0 ? "#ff2d1a" : "#ffffff";
      g.lineWidth = 2;
      g.beginPath();
      if (i === 0) {
        g.moveTo(7, 16); g.lineTo(17, 32); g.moveTo(17, 16); g.lineTo(7, 32);
      } else {
        g.moveTo(12 + i * 21 - 9, 14); g.lineTo(12 + i * 21 - 9, 33);
        g.moveTo(12 + i * 21 - 14, 28); g.lineTo(12 + i * 21 - 9, 34);
        g.lineTo(12 + i * 21 - 4, 28);
      }
      g.stroke();
    }
    break;
  case "crt":
    fill("#031a06");
    g.fillStyle = "#39ff6a";
    for (y = 0; y < 6; y++) g.fillRect(4, 5 + y * 7, 10 + chance() * 40, 3);
    g.fillRect(4 + 22, 5 + 6 * 7 - 7, 3, 4);
    break;
  case "trivision":
    fill("#222");
    for (i = 0; i < 10; i++) {
      g.fillStyle = ["#ff5a36", "#ffd21f", "#2b5cff"][i % 3 === 0 ? 0 : i < 5 ? 1 : 2];
      g.fillRect(i * 6.4, 4, 5.6, 40);
    }
    break;
  case "iso":
    fill("#8fd0ff");
    for (y = 0; y < 6; y++) for (x = 0; x < 6; x++) {
      g.fillStyle = (x + y) % 3 ? "#4caf50" : "#2e7d32";
      g.beginPath();
      var cx = 32 + (x - y) * 6, cy = 8 + (x + y) * 3.4;
      g.moveTo(cx, cy); g.lineTo(cx + 6, cy + 3.4); g.lineTo(cx, cy + 6.8); g.lineTo(cx - 6, cy + 3.4);
      g.fill();
    }
    break;
  case "stars":
    fill("#02030a");
    for (i = 0; i < 60; i++) {
      var far = chance();
      g.fillStyle = far < 0.8 ? "#8a93b8" : "#ffffff";
      g.fillRect(Math.floor(chance() * W), Math.floor(chance() * H), far < 0.9 ? 1 : 2, 1);
    }
    break;
  case "wheel":
    fill("#000");
    for (i = 0; i < 24; i++) {
      g.fillStyle = "hsl(" + i * 15 + ",100%,55%)";
      g.beginPath();
      g.moveTo(32, 24);
      g.arc(32, 24, 19, i / 24 * Math.PI * 2, (i + 1) / 24 * Math.PI * 2 + 0.02);
      g.fill();
    }
    break;
  case "matrix":
    fill("#080808");
    for (y = 0; y < 10; y++) for (x = 0; x < 14; x++) {
      var lit = Math.hypot(x - 6.5, (y - 4.5) * 1.3) < 4.2;
      g.fillStyle = lit ? "#ff3a2a" : "#2a0d0a";
      g.beginPath();
      g.arc(5 + x * 4.2, 5 + y * 4.2, 1.5, 0, Math.PI * 2);
      g.fill();
    }
    break;
  case "kaleido":
    fill("#10061a");
    for (i = 0; i < 12; i++) {
      g.fillStyle = ["#ff36c8", "#28e0e0", "#ffd21f", "#9a46ff"][i % 4];
      g.beginPath();
      g.moveTo(32, 24);
      g.arc(32, 24, 21, i / 12 * Math.PI * 2, (i + 0.55) / 12 * Math.PI * 2);
      g.fill();
    }
    break;
  case "logo":
    fill("#15233a");
    g.fillStyle = "#ff36c8";
    g.fillRect(34, 10, 20, 12);
    g.fillStyle = "#15233a";
    g.fillRect(38, 13, 12, 6);
    break;
  case "carpet":
    fill("#6b1f2a");
    for (y = 0; y < 6; y++) for (x = 0; x < 8; x++) {
      g.fillStyle = (x + y) % 2 ? "#d9a441" : "#1f4d6b";
      g.beginPath();
      g.arc(4 + x * 8, 4 + y * 8, 2.4, 0, Math.PI * 2);
      g.fill();
    }
    break;
  case "drive":
    // A program of the user's own that names no picture, shown as a prompt waiting for code
    fill("#1c1f22");
    g.fillStyle = "#8a93a0";
    g.font = "bold 16px monospace";
    g.fillText(">_", 22, 30);
    break;
  case "servo":
  case "motor":
    fill("#e9e6e0");
    g.strokeStyle = "#56708f";
    g.fillStyle = "#56708f";
    g.lineWidth = 3;
    if (kind === "servo") {
      g.fillRect(18, 22, 28, 16);
      g.beginPath(); g.moveTo(32, 22); g.lineTo(44, 8); g.stroke();
    } else {
      g.beginPath(); g.arc(32, 24, 13, 0, Math.PI * 2); g.stroke();
      for (i = 0; i < 6; i++) {
        g.beginPath(); g.moveTo(32, 24);
        g.lineTo(32 + Math.cos(i) * 13, 24 + Math.sin(i) * 13); g.stroke();
      }
    }
    break;
  default:
    fill("#ddd");
  }
}

function programThumb(path) {
  var offered = offeredAt(path);
  var file = path.split("/").pop().replace(/\.py$/, "");
  var kind = offered && THUMBS[file + "-2"] ? "pair:" + file
           : offered && THUMBS[file] ? "shot:" + file
           : offered ? offered[1] : DRIVE_PICTURES[path] ? "picture:" + path : "drive";
  return thumbCanvas(kind, path.length, usesOf(path));
}

// ---- the program page ------------------------------------------------------------------------

var programView = null;

// Whether the program tab is open. A program is chosen only by picking one, so the tab can be open
// with none chosen, and the file says program= only once one is
var onProgramPage = false;

// A program as a card, as the looks are, its thumbnail over its name, and what it uses as a row
// of small drawings along the foot of the thumbnail
function programCard(path) {
  var card = document.createElement("button");
  card.type = "button";
  card.className = "progcard" + (boardSet.program === path ? " picked" : "");
  card.dataset.path = path;
  card.appendChild(programThumb(path));
  var uses = usesOf(path);
  if (uses.length) {
    var row = document.createElement("span");
    row.className = "proguses";
    uses.forEach(function (key) { row.appendChild(featureIcon(key)); });
    card.appendChild(row);
  }
  var name = document.createElement("span");
  name.className = "progname";
  name.textContent = programTitle(path);
  card.appendChild(name);
  card.title = ((programNamed(path) || {}).does || "") + (uses.length ? "\nUses " +
    uses.map(function (key) { return featureNamed(key)[1]; }).join(", ") : "");
  // Picked again, the program is put back, leaving none chosen
  card.onclick = function () {
    boardSet.program = boardSet.program === path ? null : path;
    if (boardSet.program) boardSet.lastProgram = path;
    draw();
  };
  return card;
}

// The screen size a program is shown on: the one it is given, else screen A's, else a 2.8"
function sizeShown(path) {
  var program = programNamed(path) || {};
  var at = (program.onDrive ? [] : program.args || []).map(function (argument) {
    return argument.kind;
  }).indexOf("size");
  var given = at >= 0 ? (boardSet.args[path] || [])[at] : null;
  var screen = state.screens && state.screens.A;
  return given || (screen && screen.there && screen.size) || "2.8";
}

// One captured frame on a module at the program's screen size, turned as the program turns it
function framedPanel(path, url) {
  var image = thumbImages[url];
  var upright = image && image.height > image.width;
  return panelPreview({size: sizeShown(path), turn: upright ? 0 : 90,
                       art: {url: url, w: upright ? 240 : 320, h: upright ? 320 : 240,
                             pixelated: true}});
}

// The picked program's picture: a screen program's captured frame on the panel it would play on,
// as the Screens tab draws one, turned as the program turns it, and anything else its thumbnail
// large. A frame taller than wide was taken from a panel upright
function programPicture(path) {
  var file = path.split("/").pop().replace(/\.py$/, "");
  var onScreen = usesOf(path).some(function (key) {
    return ["screen", "either", "pair", "hub"].indexOf(key) >= 0;
  });
  if (onScreen && THUMBS[file]) {
    // A pair's second frame goes on a second panel, the two drawn smaller to stand side by side
    if (!THUMBS[file + "-2"]) return framedPanel(path, THUMBS[file]);
    var both = document.createElement("div");
    both.className = "twopanels";
    both.appendChild(framedPanel(path, THUMBS[file]));
    both.appendChild(framedPanel(path, THUMBS[file + "-2"]));
    return both;
  }
  var big = programThumb(path);
  big.classList.add("big");
  return big;
}

// The picture before a program is chosen: an empty panel upright, so its words read across, or on
// a board without screens its lamps unlit
function emptyPicture() {
  if (SCREEN_PORTS.length) return panelPreview({size: "2.8", turn: 0});
  var big = thumbCanvas("lamps:off", 1);
  big.classList.add("big");
  return big;
}

// The line along the preview's top, saying what the board runs, with the way to choose none
function heroNote(path) {
  var note = document.createElement("div");
  note.className = "programnote";
  note.appendChild(boardIcon());
  var said = document.createElement("span");
  said.textContent = path
    ? "The board runs " + path.split("/").pop() + " in place of the effects. They are kept, and " +
      "play if it is missing or stops, when errors.txt says why."
    : "No program chosen, so the board plays the effects. Pick one below to run it in their place.";
  note.appendChild(said);
  if (path) {
    var none = document.createElement("button");
    none.type = "button";
    none.className = "progchoosenone";
    none.textContent = "Choose none";
    none.onclick = function () {
      boardSet.program = null;
      draw();
    };
    note.appendChild(none);
  }
  return note;
}

// The picked program large, with what it does, what it needs and what it takes. With none picked
// the box keeps its size, an empty panel in the picture's place, so choosing one moves nothing
function programHero(path) {
  var hero = document.createElement("div");
  hero.className = "proghero" + (path ? "" : " unchosen");
  hero.appendChild(heroNote(path));
  var body = document.createElement("div");
  body.className = "herobody";
  hero.appendChild(body);
  var picture = document.createElement("div");
  picture.className = "progpicture";
  picture.appendChild(path ? programPicture(path) : emptyPicture());
  body.appendChild(picture);
  if (!path) {
    var waiting = document.createElement("div");
    waiting.className = "progwords";
    var taken = ["outputs"];
    if (SCREEN_PORTS.length) taken.push(SCREEN_PORTS.length > 1 ? "screens" : "screen");
    if (BOARD.sound) taken.push("sound");
    waiting.innerHTML = "<h3>Choose a program</h3><p>Each takes the whole board, its " +
                        spoken(taken) + ", while it runs.</p>";
    body.appendChild(waiting);
    return hero;
  }
  var words = document.createElement("div");
  words.className = "progwords";
  var program = programNamed(path) || {};
  words.innerHTML = "<h3>" + escapeHtml(programTitle(path)) + "</h3>" +
                    "<p>" + escapeHtml(program.does || "Says nothing about itself.") + "</p>" +
                    "<p class='progwhere'>" + escapeHtml(path) +
                    (program.onDrive ? ", on the drive" : ", comes with the board") + "</p>";
  // What it uses, each drawn and named, as the filter below names them
  var uses = document.createElement("div");
  uses.className = "herouses";
  usesOf(path).forEach(function (key) {
    var one = document.createElement("span");
    one.appendChild(featureIcon(key));
    one.appendChild(document.createTextNode(featureNamed(key)[1]));
    uses.appendChild(one);
  });
  if (uses.children.length) words.appendChild(uses);
  words.appendChild(argsFor(path, false));
  body.appendChild(words);
  return hero;
}

function renderProgramView() {
  programView.textContent = "";
  if (!onProgramPage) return;
  programView.appendChild(programHero(boardSet.program));
  programView.appendChild(featureFilter());
  var shown = 0;
  function group(title, paths) {
    var kept = paths.filter(passesFilter);
    if (!kept.length) return;
    shown += kept.length;
    var heading = document.createElement("div");
    heading.className = "gallery-head";
    heading.appendChild(document.createTextNode(title));
    if (GROUP_SAYS[title]) {
      var says = document.createElement("span");
      says.className = "says";
      says.textContent = GROUP_SAYS[title];
      heading.appendChild(says);
    }
    programView.appendChild(heading);
    var grid = document.createElement("div");
    grid.className = "proggrid";
    kept.forEach(function (path) { grid.appendChild(programCard(path)); });
    programView.appendChild(grid);
  }
  group("On the drive", DRIVE_PROGRAMS.map(function (one) { return one[0]; }));
  OFFERED.forEach(function (set) {
    group(set[0], set[1].map(function (entry) { return EXAMPLES_ROOT + entry[0]; }));
  });
  if (!shown) {
    var none = document.createElement("p");
    none.className = "prognone";
    none.textContent = "Every program here needs something not ticked.";
    programView.appendChild(none);
  }
}

// ---- choosing by what is to hand ----------------------------------------------------------------
// A chip for each thing an offered program can use, all on to begin with. A chip turned off is
// something not to hand, so every program needing it goes, and a program stays only while all it
// uses is on. One screen or two is had with either a screen or two, so it has no chip of its own,
// and every board has its outputs and its Boot button, and an RGB output where it has one, so
// none of those has one

var CHIPLESS = ["either", "outputs", "rgb", "button"];

var unhad = [];

function had(key) { return unhad.indexOf(key) < 0; }

function passesFilter(path) {
  return usesOf(path).every(function (key) {
    return key === "either" ? had("screen") || had("pair") : had(key);
  });
}

// The things there is a chip for, those some offered program uses
function chipFeatures() {
  var offered = offeredPaths();
  return FEATURES.filter(function (feature) {
    return CHIPLESS.indexOf(feature[0]) < 0 && offered.some(function (path) {
      return usesOf(path).indexOf(feature[0]) >= 0;
    });
  });
}

function offeredPaths() {
  var offered = DRIVE_PROGRAMS.map(function (one) { return one[0]; });
  OFFERED.forEach(function (set) {
    set[1].forEach(function (entry) { offered.push(EXAMPLES_ROOT + entry[0]); });
  });
  return offered;
}

function featureFilter() {
  var row = document.createElement("div");
  row.className = "featurefilter";
  var said = document.createElement("span");
  said.textContent = "Plugged in:";
  row.appendChild(said);
  var chips = chipFeatures();
  chips.forEach(function (feature) {
    var chip = document.createElement("button");
    chip.type = "button";
    chip.className = "featurechip" + (had(feature[0]) ? " on" : "");
    chip.dataset.feature = feature[0];
    chip.title = had(feature[0]) ? "Showing programs that use " + feature[1]
                                 : "Hiding programs that need " + feature[1];
    chip.appendChild(featureIcon(feature[0]));
    chip.appendChild(document.createTextNode(feature[2]));
    chip.onclick = function () {
      var at = unhad.indexOf(feature[0]);
      if (at >= 0) unhad.splice(at, 1);
      else unhad.push(feature[0]);
      draw();
    };
    row.appendChild(chip);
  });
  // Every chip on, or every chip off for ticking what is to hand
  [["all", function () { return []; }],
   ["none", function () { return chips.map(function (feature) { return feature[0]; }); }]]
    .forEach(function (one) {
      var choice = document.createElement("button");
      choice.type = "button";
      choice.className = "featureclear";
      choice.textContent = one[0];
      choice.onclick = function () {
        unhad = one[1]();
        draw();
      };
      row.appendChild(choice);
    });
  return row;
}

// ---- moving between the two pages ---------------------------------------------------------------
// Two tabs split under the header, the effects tab holding the way into scenes until there are some

// Back to the effects, the file running them again
function toEffects() {
  onProgramPage = false;
  boardSet.program = null;
  draw();
}

// Over to the programs with none chosen, until one is picked
function toProgram() {
  onProgramPage = true;
  draw();
}

// The effects summed up small: a live swatch of the outputs, as their own tab's is, painted every
// frame from what the lamps play, so it never stops on whichever frame a redraw caught
function effectsFace() {
  var face = document.createElement("span");
  face.className = "effectsface";
  var swatch = document.createElement("span");
  swatch.className = "accswatch";
  tabSwatch(swatch, "outPanel");
  face.appendChild(swatch);
  return face;
}

function renderPageSwitch() {
  var inHeader = document.getElementById("headSwitch");
  inHeader.textContent = "";
  var program = boardSet.program || boardSet.lastProgram;
  // Split under the header, the tabs are drawn as the tabs off its foot are
  inHeader.className = "headswitch headsplit headtabs";
  // Two tabs, what runs picked, each showing what it would run, small in the header where the
  // page's name is, taking no room from the page
  [["effects", "The effects"],
   ["program", "A program", program ? programTitle(program) : ""]].forEach(function (one) {
    // A tab holds the scenes' button, and a button cannot hold another, so a tab is a plain
    // element taking the click and the keyboard
    var cover = document.createElement("div");
    cover.setAttribute("role", "button");
    cover.tabIndex = 0;
    cover.onkeydown = function (event) {
      if (event.key === "Enter" || event.key === " ") cover.onclick();
    };
    cover.className = "cover" + ((one[0] === "program") === onProgramPage ? " on" : "");
    cover.dataset.page = one[0];
    // With no program chosen its tab shows a starfield, or the lamps lit on a board without screens
    var face = one[0] === "effects" ? effectsFace()
             : program ? programThumb(program)
             : thumbCanvas(SCREEN_PORTS.length ? "stars" : "lamps:rainbow", 3);
    face.classList.add("coverface");
    cover.appendChild(face);
    var words = document.createElement("span");
    // Only a program's name is said under its tab
    words.innerHTML = "<b>" + one[1] + "</b>" +
                      (one[2] ? "<small>" + escapeHtml(one[2]) + "</small>" : "");
    cover.appendChild(words);
    cover.onclick = one[0] === "effects" ? toEffects : toProgram;
    inHeader.appendChild(cover);
  });
}

(function () {
  // In the header after the page's name. What follows the name is gathered into one group, so a
  // wide header can set name, tabs and group on a single line
  var headSwitch = document.createElement("span");
  headSwitch.id = "headSwitch";
  headSwitch.className = "headswitch";
  var named = document.querySelector("header h1");
  var actions = document.createElement("span");
  actions.id = "headActions";
  actions.className = "headactions";
  while (named.nextSibling) actions.appendChild(named.nextSibling);
  named.parentNode.appendChild(headSwitch);
  named.parentNode.appendChild(actions);
  programView = document.createElement("div");
  programView.id = "programView";
  programView.className = "programview";
  var body = document.getElementById("sceneBody");
  body.parentNode.insertBefore(programView, body.nextSibling);
}());

drawSteps.after.push(function () {
  document.body.classList.toggle("programpage", onProgramPage);
  document.body.dataset.pageway = "headsplit";
  renderPageSwitch();
  renderProgramView();
  scenesAsCards();
  scenesInTheTab();
  headerOnOneLine();
  // The effects' live swatch in the tabs is made after the page painted, so it is painted now
  paintAll();
});

// Pictures for thumbnails, decoded ahead of being shown, so a thumbnail is drawn whole the first
// time and never fills in late. Once all are in, the page is drawn again for any already showing
function loadThumbs(sources) {
  var waiting = 0;
  sources.forEach(function (src) {
    if (thumbImages[src]) return;
    var image = thumbImages[src] = new Image();
    waiting++;
    image.onload = image.onerror = function () {
      waiting--;
      if (!waiting) draw();
    };
    image.src = src;
  });
}

loadThumbs(Object.keys(THUMBS).map(function (name) { return THUMBS[name]; }));

// The scenes are always a grid of cards, the way into another one the grid's last tile
function scenesAsCards() {
  var bar = document.getElementById("tabs");
  bar.classList.add("wrapped");
  if (state.scenes.length) document.getElementById("sceneBody").classList.add("loose");
}

// Split under the header, the tabs stand over the page's column. Where the window is wide
// enough for the name to fit left of that column and the rest right of it, all three share one
// line, measured, since what fits depends on the name and on which buttons show
var COLUMN_REM = 57.2;

function headerOnOneLine() {
  var header = document.querySelector("header");
  header.classList.remove("oneline");
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  var style = getComputedStyle(header);
  var inner = header.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  var gap = rem;
  var side = (inner - COLUMN_REM * rem) / 2 - gap;
  var name = document.querySelector("header h1").scrollWidth;
  // The group's width as it sits, first shown to last, so a button joined to another counts once.
  // What is laid over the page, such as an open menu, takes no room in the line
  var shown = Array.prototype.filter.call(document.getElementById("headActions").children,
    function (one) {
      return one.offsetWidth && getComputedStyle(one).position !== "absolute";
    });
  var rest = shown.length ? shown[shown.length - 1].getBoundingClientRect().right -
                            shown[0].getBoundingClientRect().left : 0;
  // The space below the buttons matches the header's top padding, measured to its outer edge so
  // its bottom border counts, and the tabs reach from the buttons' top to that edge. The tabs
  // keep that height on two rows too, so moving between one and two changes nothing
  var above = parseFloat(style.paddingTop);
  var border = parseFloat(style.borderBottomWidth) || 0;
  // Its exact height, a whole-pixel one leaving the spacing half a pixel out
  var button = document.getElementById("open").getBoundingClientRect().height;
  header.style.setProperty("--headgap", (above - border) + "px");
  header.style.setProperty("--buttonheight", button + "px");
  header.style.setProperty("--tabheight", (button + above) + "px");
  // A little to spare, as the group's borders and the arrow's join round up
  if (name <= side && rest + 8 <= side) header.classList.add("oneline");
}

window.addEventListener("resize", headerOnOneLine);

// Before there are scenes, the way into them is the effects tab's own, at its end, so no row is
// kept above the gallery for it. Once there are scenes their tabs are that row, as they were
function scenesInTheTab() {
  var into = !state.scenes.length && !onProgramPage &&
             document.querySelector("#headSwitch .cover[data-page=effects]");
  document.body.classList.toggle("scenesintab", !!into);
  if (!into) return;
  var plus = document.querySelector("#tabs .plus");
  if (!plus) return;
  plus.addEventListener("click", function (event) { event.stopPropagation(); });
  into.appendChild(plus);
}
