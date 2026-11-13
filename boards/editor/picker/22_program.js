import {h, replace} from "./00_dom.js";
import {draw, drawSteps, paintAll} from "./00_draw.js";
import {BOARD} from "./01_looks.js";
import {state} from "./04_scenes.js";
import {spoken} from "./05_effects.js";
import {SCREEN_PORTS, screenHooks} from "./07_board.js";
import {tabSwatch} from "./11_tabs.js";
import {CAN_REACH_A_DRIVE, banner, drive, driveTrouble} from "./18_drive.js";
import {
  PROGRAMS, boardSet, programArguments, programNamed, programNote, setPrograms
} from "./19_board_settings.js";
import {
  OWN_FOLDER, PICTURES, SECTIONS, copyProgram, driveHasCredentials, drivePrograms, programsKnown,
  programsReading, removeProgram
} from "./26_drive_programs.js";

export var OWN_GROUP = "On the drive";

function offeredGroups() {
  var runnable = PROGRAMS.filter(function (one) {
    return driveHasCredentials || one.uses.indexOf("wifi") < 0;
  });
  var named = SECTIONS.map(function (one) { return one[0]; });
  runnable.forEach(function (one) {
    if (one.section && named.indexOf(one.section) < 0) named.push(one.section);
  });
  var own = runnable.filter(function (one) { return !one.example && !one.section; });
  var groups = [[OWN_GROUP, own]].concat(named.map(function (name) {
    return [name, runnable.filter(function (one) { return one.section === name; })];
  }));
  return groups.map(function (group) {
    var paths = group[1].map(function (one) { return one.path; });
    paths.sort(function (a, b) {
      return programTitle(a).localeCompare(programTitle(b), undefined, {numeric: true});
    });
    return [group[0], paths];
  }).filter(function (group, at) { return !at || group[1].length; });
}

function groupSays(title) {
  if (title === OWN_GROUP) return "your own programs";
  var listed = SECTIONS.filter(function (one) { return one[0] === title; })[0];
  return listed ? listed[1] : "";
}

var programsFolded = {};

function programGroupFolded(title) {
  if (title in programsFolded) return programsFolded[title];
  var listed = SECTIONS.filter(function (one) { return one[0] === title; })[0];
  return !!(listed && listed[2]);
}

export function foldHead(title, says, open, toggle) {
  return h("button", {type: "button", class: "gallery-head foldhead" + (open ? " open" : ""),
                      "aria-expanded": String(open),
                      onclick: function () {
                        toggle();
                        draw();
                      }},
    title, says ? h("span", {class: "says"}, says) : null);
}

function holes(points, radius) {
  return points.map(function (at) {
    return "M" + (at[0] - radius) + " " + at[1] + "a" + radius + " " + radius + " 0 1 0 " +
           radius * 2 + " 0a" + radius + " " + radius + " 0 1 0 " + -radius * 2 + " 0";
  }).join("");
}

export var FEATURES = [
  ["outputs", "the outputs", "outputs",
   "<circle fill='currentColor' stroke='none' cx='3.8' cy='10' r='3'/><circle fill='currentColor' stroke='none' cx='12' cy='10' r='3'/>" +
   "<circle fill='currentColor' stroke='none' cx='20.2' cy='10' r='3'/><path d='M1.5 18h21' stroke-width='2.2'/>"],
  ["rgb", "the RGB output", "RGB",
   "<circle fill='currentColor' stroke='none' cx='12' cy='8' r='5'/><circle cx='8' cy='15' r='5' stroke-width='2'/>" +
   "<circle cx='16' cy='15' r='5' stroke-width='2'/>"],
  ["screen", "a screen", "screen", "<rect fill='currentColor' stroke='none' x='3' y='5' width='18' height='14' rx='2'/>"],
  ["either", "one screen or two", "1 or 2 screens",
   "<rect fill='currentColor' stroke='none' x='0.5' y='6' width='9.5' height='12' rx='1.6'/>" +
   "<rect x='15' y='7' width='7.5' height='10' rx='1.2' stroke-width='2'/>"],
  ["pair", "two screens", "2 screens",
   "<rect fill='currentColor' stroke='none' x='0.5' y='6' width='9.5' height='12' rx='1.6'/>" +
   "<rect fill='currentColor' stroke='none' x='14' y='6' width='9.5' height='12' rx='1.6'/>"],
  ["hub", "a screen hub", "hub",
   "<rect fill='currentColor' stroke='none' x='1' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect fill='currentColor' stroke='none' x='8.85' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect fill='currentColor' stroke='none' x='16.7' y='4' width='6.3' height='7' rx='1.2'/>" +
   "<rect fill='currentColor' stroke='none' x='1' y='13' width='6.3' height='7' rx='1.2'/>" +
   "<rect fill='currentColor' stroke='none' x='8.85' y='13' width='6.3' height='7' rx='1.2'/>" +
   "<rect fill='currentColor' stroke='none' x='16.7' y='13' width='6.3' height='7' rx='1.2'/>"],
  ["strip", "an LED strip", "strip",
   "<path fill='currentColor' stroke='none' fill-rule='evenodd' d='M1 2.5H17.5A6 6 0 0 1 17.5 14.5H6.5A1 1 0 0 0 6.5 " +
   "16.5H23V21.5H6.5A6 6 0 0 1 6.5 9.5H17.5A1 1 0 0 0 17.5 7.5H1Z" +
   holes([[4.5, 5], [9, 5], [13.5, 5], [9.5, 12], [14, 12], [10.5, 19], [15, 19], [19.5, 19]],
         1.35) + "'/>"],
  ["sound", "a speaker", "speaker",
   "<g transform='scale(1.5)' stroke-width='1.2'><path fill='currentColor' d='M2 6h3l4-3v10l-4-3H2z'/>" +
   "<path d='M11 5.5q2 2.5 0 5M12.8 3.8q3.4 4.2 0 8.4'/></g>"],
  ["remote", "the IR remote", "remote",
   "<g transform='rotate(-35 12 12)'><path fill='currentColor' stroke='none' fill-rule='evenodd' d='M9.5 7h5a2.5 2.5 0 " +
   "0 1 2.5 2.5v11a2.5 2.5 0 0 1-2.5 2.5h-5A2.5 2.5 0 0 1 7 20.5v-11A2.5 2.5 0 0 1 9.5 7z" +
   holes([[12, 11]], 1.6) + "'/><path d='M9 4q3-2 6 0M7 1.2q5-3 10 0' stroke-width='2'/></g>"],
  ["qwst", "a Qw/ST sensor", "Qw/ST",
   "<path fill='currentColor' stroke='none' fill-rule='evenodd' d='M5 2h14a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 " +
   "1-2-2V4a2 2 0 0 1 2-2zM5 5.5h2v8H5zM9 5.5h2v8H9zM13 5.5h2v8h-2zM17 5.5h2v8h-2z'/>" +
   "<rect fill='currentColor' stroke='none' x='10' y='17' width='4' height='5.5'/>"],
  ["analog", "an analog sensor", "analog",
   "<path d='M3 12h18' stroke-width='2.4'/><rect fill='currentColor' stroke='none' x='12' y='6' width='5.5' " +
   "height='12' rx='1.4'/>"],
  ["motor", "motors", "motors",
   "<rect fill='currentColor' stroke='none' x='1.5' y='5' width='15' height='14' rx='3.5'/>" +
   "<rect fill='currentColor' stroke='none' x='16.5' y='10.5' width='6' height='3' rx='1'/>"],
  ["servo", "servos", "servos",
   "<rect fill='currentColor' stroke='none' x='4' y='10' width='16' height='11' rx='1.5'/>" +
   "<rect fill='currentColor' stroke='none' x='1' y='13' width='22' height='3' rx='1'/>" +
   "<rect fill='currentColor' stroke='none' x='7' y='6.5' width='4' height='4'/><path d='M9 5.5H17.5' stroke-width='3.2'/>"],
  ["wifi", "Wi-Fi", "Wi-Fi",
   "<g transform='scale(1.5)' stroke-width='1.2'><path d='M1.5 6.5a9 9 0 0 1 13 0M4 9a5.5 5.5 0 " +
   "0 1 8 0'/><circle fill='currentColor' cx='8' cy='12' r='1.4'/></g>"],
  ["button", "the Boot button", "Boot button",
   "<rect x='3' y='3' width='18' height='18' rx='3'/><circle fill='currentColor' stroke='none' cx='12' cy='12' r='4.5'/>"]
];

function featureNamed(key) {
  return FEATURES.filter(function (one) { return one[0] === key; })[0];
}

export function featureIcon(key) {
  return h("svg:svg", {viewBox: "0 0 24 24", width: 18, height: 18, fill: "none", stroke: "currentColor",
                       "stroke-width": 1.8, "stroke-linecap": "round", "stroke-linejoin": "round",
                       "aria-hidden": "true",
                       html: featureNamed(key)[3]});
}

export function usesOf(path) {
  var program = programNamed(path);
  return program ? program.uses : [];
}

export function programTitle(path) {
  var program = programNamed(path);
  if (program && program.name) return program.name;
  var words = path.split("/").pop().replace(/\.py$/, "").split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

var THUMB_W = 160, THUMB_H = 120;
var thumbImages = {};

function thumbCanvas(kind, seed, uses) {
  var canvas = h("canvas", {width: THUMB_W, height: THUMB_H});
  paintThumb(canvas.getContext("2d"), kind, seed || 1, canvas, uses || []);
  return canvas;
}

function monoInk(ink) {
  if (ink === "#3a3f44") return ink;
  var level = (parseInt(ink.slice(1, 3), 16) * 0.2126 + parseInt(ink.slice(3, 5), 16) * 0.7152 +
               parseInt(ink.slice(5, 7), 16) * 0.0722) / 255;
  level = Math.max(0.3, level);
  return "rgb(" + Math.round(255 * level) + "," + Math.round(217 * level) + "," +
         Math.round(160 * level) + ")";
}

function fillRounded(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
  g.fill();
}

var MOTION = "#ffd21f";

function drawTurn(g, x, y, rx, ry, from, to, backwards) {
  g.strokeStyle = MOTION;
  g.lineWidth = 2.5;
  g.lineCap = "round";
  g.beginPath(); g.ellipse(x, y, rx, ry, 0, from, to, backwards); g.stroke();
  var way = backwards ? -1 : 1;
  var tipX = x + rx * Math.cos(to), tipY = y + ry * Math.sin(to);
  var alongX = -rx * Math.sin(to) * way, alongY = ry * Math.cos(to) * way;
  var length = Math.sqrt(alongX * alongX + alongY * alongY);
  alongX /= length;
  alongY /= length;
  g.fillStyle = MOTION;
  g.beginPath();
  g.moveTo(tipX + alongX * 6, tipY + alongY * 6);
  g.lineTo(tipX - alongY * 4.5 - alongX * 2, tipY + alongX * 4.5 - alongY * 2);
  g.lineTo(tipX + alongY * 4.5 - alongX * 2, tipY - alongX * 4.5 - alongY * 2);
  g.fill();
}

function drawWheel(g, x, y) {
  g.fillStyle = "#62666e";
  fillRounded(g, x - 7.5, y - 42, 15, 84, 7.5);
  g.fillStyle = "#7c8089";
  for (var tread = -35; tread < 37; tread += 5) g.fillRect(x - 5.5, y + tread, 11, 2);
  drawTurn(g, x + 17.5, y, 6, 24, Math.PI * 0.34, Math.PI * 2.1, false);
}

var BLUE = "#2f62d6", BLUE_DARK = "#1d43a6", BLUE_LIGHT = "#5d8bef", WHITE = "#eef1f5";

function drawServo(g, x, y, horn) {
  g.lineWidth = 3;
  g.lineCap = "round";
  [["#f2a33a", -4], ["#d0352b", 0], ["#6b4228", 4]].forEach(function (wire) {
    g.strokeStyle = wire[0];
    g.beginPath();
    g.moveTo(x + 4, y + 36 + wire[1]);
    g.bezierCurveTo(x - 14, y + 36 + wire[1], x - 22, y + 44 + wire[1], x - 30, y + 58);
    g.stroke();
  });
  g.fillStyle = BLUE_DARK;
  g.fillRect(x - 15, y + 6, 98, 9);
  g.fillStyle = BLUE;
  g.fillRect(x - 15, y + 6, 98, 6);
  g.fillStyle = BLUE_LIGHT;
  fillRounded(g, x + 4, y - 22, 26, 14, 4);
  g.fillStyle = "#4677e3";
  fillRounded(g, x + 2, y - 14, 50, 14, 2);
  g.fillStyle = "#7aa0f2";
  g.fillRect(x + 4, y - 14, 46, 2);
  g.fillStyle = BLUE_DARK;
  fillRounded(g, x, y - 4, 68, 54, 3);
  g.fillStyle = BLUE;
  fillRounded(g, x, y - 4, 68, 50, 3);
  g.fillStyle = WHITE;
  g.fillRect(x + 12.5, y - 30, 9, 9);
  if (horn) {
    g.fillRect(x + 11.5, y - 33, 11, 6);
    g.fillRect(x + 9.5, y - 38, 42, 5);
  }
}

function drawSweep(g, x, y) {
  drawTurn(g, x + 17, y - 36, 36, 8, Math.PI * 0.95, Math.PI * 0.12, true);
}

var SILVER = "#c3cad3", SILVER_LIGHT = "#dfe4ea", BRASS = "#d9a93a", BRASS_DARK = "#a77d1f",
    PLASTIC = "#4b5058";

function drawMotor(g, y) {
  g.fillStyle = SILVER;
  g.fillRect(12, y - 13, 10, 3);
  g.fillRect(12, y + 10, 10, 3);
  g.fillStyle = PLASTIC;
  fillRounded(g, 19, y - 20, 13, 40, 3);
  g.fillStyle = SILVER;
  fillRounded(g, 28, y - 22, 56, 44, 5);
  g.fillStyle = SILVER_LIGHT;
  fillRounded(g, 28, y - 22, 56, 12, 5);
  g.fillStyle = SILVER;
  g.fillRect(28, y - 14, 56, 4);
  g.strokeStyle = "#8d96a1";
  g.lineWidth = 3;
  g.lineCap = "round";
  g.beginPath(); g.moveTo(46, y - 4); g.lineTo(64, y - 4); g.moveTo(46, y + 9); g.lineTo(64, y + 9);
  g.stroke();
  g.fillStyle = "#6f757e";
  g.fillRect(86, y - 15, 28, 30);
  g.fillStyle = "#a3a9b1";
  for (var tooth = 87; tooth < 113; tooth += 3) g.fillRect(tooth, y - 13, 1.4, 26);
  g.fillStyle = BRASS_DARK;
  g.fillRect(84, y - 21, 34, 4);
  g.fillRect(84, y + 17, 34, 4);
  [[83, 7], [98, 5], [113, 7]].forEach(function (plate) {
    g.fillStyle = BRASS_DARK;
    g.fillRect(plate[0], y - 24, plate[1], 48);
    g.fillStyle = BRASS;
    g.fillRect(plate[0], y - 24, plate[1] - 2, 46);
  });
  g.fillStyle = SILVER;
  g.fillRect(120, y - 4, 28, 8);
  g.fillStyle = SILVER_LIGHT;
  g.fillRect(121, y - 3, 25, 2);
}

function scatter(seed) {
  var state = seed * 9301 + 49297;
  return function () {
    state = (state * 9301 + 49297) % 233280;
    return state / 233280;
  };
}

var OUTPUT_INKS = {
  rainbow: ["#ff2d1a", "#ff9022", "#ffd21f", "#22c65a", "#28e0e0", "#2b5cff", "#9a46ff"],
  warm: ["#ffb060", "#ffc27a", "#ff9022", "#ffb060", "#ffc27a", "#ff9022", "#ffb060"],
  mono: ["#ffd9a0", "#3a3f44", "#ffd9a0", "#ffd9a0", "#3a3f44", "#ffd9a0", "#3a3f44"],
  pulse: ["#ffd9a0", "#c9aa7c", "#8a765a", "#4d4336", "#8a765a", "#c9aa7c", "#ffd9a0"],
  dusk: ["#ffe6b0", "#ffe6b0", "#ffe6b0", "#c9aa7c", "#8a765a", "#4d4336", "#3a3f44"],
  level: ["#3a3f44", "#3a3f44", "#22c65a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"],
  bar: ["#2b5cff", "#28e0e0", "#22c65a", "#ffd21f", "#3a3f44", "#3a3f44", "#3a3f44"],
  temperature: ["#2b5cff", "#6a45ff", "#a63cff", "#e036e0", "#3a3f44", "#3a3f44", "#3a3f44"],
  melody: ["#9a46ff", "#3a3f44", "#ff36c8", "#9a46ff", "#3a3f44", "#2b5cff", "#ff36c8"],
  countdown: ["#ff2d1a", "#ff2d1a", "#ff2d1a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"],
  solid: ["#ff36c8", "#ff36c8", "#ff36c8", "#ff36c8", "#ff36c8", "#ff36c8", "#ff36c8"],
  random: ["#e67e22", "#1abc9c", "#9b59b6", "#f1c40f", "#3498db", "#e74c3c", "#2ecc71"],
  off: ["#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44"]
};

function thumbImage(src) {
  var image = thumbImages[src];
  if (!image) {
    image = thumbImages[src] = new Image();
    image.src = src;
  }
  return image;
}

function whenLoaded(image, paint) {
  if (image.complete && image.width) paint();
  else image.addEventListener("load", paint);
}

function paintPair(g, path, W, H) {
  g.fillStyle = "#111";
  g.fillRect(0, 0, W, H);
  PICTURES[path].forEach(function (src, side) {
    var panel = thumbImage(src);
    whenLoaded(panel, function () {
      var half = W / 2 - 1;
      var fit = Math.min(half / panel.width, H / panel.height);
      g.imageSmoothingEnabled = true;
      g.drawImage(panel, side * (half + 2) + (half - panel.width * fit) / 2,
                  (H - panel.height * fit) / 2, panel.width * fit, panel.height * fit);
    });
  });
}

function paintShot(g, path, W, H) {
  g.fillStyle = "#111";
  g.fillRect(0, 0, W, H);
  var image = thumbImage(PICTURES[path][0]);
  whenLoaded(image, function () {
    var upright = image.height > image.width;
    var scale = (upright ? Math.min : Math.max)(W / image.width, H / image.height);
    g.imageSmoothingEnabled = true;
    g.drawImage(image, (W - image.width * scale) / 2, (H - image.height * scale) / 2,
                image.width * scale, image.height * scale);
  });
}

function paintOutputs(g, pattern, uses, W, H) {
  g.fillStyle = "#16181b";
  g.fillRect(0, 0, W, H);
  var row = OUTPUT_INKS[pattern] || OUTPUT_INKS.mono;
  var lamps = BOARD.outputs;
  var mixed = lamps.some(function (output) { return output.kind === "mono"; }) &&
              lamps.some(function (output) { return output.kind !== "mono"; });
  var usesMono = !mixed || uses.indexOf("outputs") >= 0;
  var usesColour = !mixed || uses.indexOf("rgb") >= 0;
  lamps.forEach(function (output, at) {
    var isMono = output.kind === "mono";
    var ink = row[Math.min(at, row.length - 1)];
    if (!(isMono ? usesMono : usesColour)) ink = "#3a3f44";
    else if (!isMono && !usesMono) ink = row[0];
    g.fillStyle = isMono ? monoInk(ink) : ink;
    g.beginPath();
    g.arc(lamps.length > 1 ? 17 + at * 21 * 6 / (lamps.length - 1) : W / 2,
          H / 2 + (mixed ? (isMono ? -21 : 21) : 0), 7.5, 0, Math.PI * 2);
    g.fill();
  });
}

function paintServo(g, kind, W, H) {
  g.fillStyle = "#16181b";
  g.fillRect(0, 0, W, H);
  if (kind === "servo:pair") {
    [1, -1].forEach(function (side) {
      g.save();
      g.translate(side > 0 ? 2 : 158, 24);
      g.scale(0.66 * side, 0.66);
      drawServo(g, 30, 52, true);
      drawSweep(g, 30, 52);
      g.restore();
    });
  } else if (kind === "servo:wheel") {
    g.save();
    g.translate(82, 67);
    g.scale(0.86, 0.86);
    g.translate(0, -17);
    g.save();
    g.scale(1, -1);
    g.rotate(Math.PI / 2);
    drawServo(g, -34, 6, false);
    g.restore();
    drawWheel(g, 31.5, 17);
    g.restore();
  } else {
    drawServo(g, 46, 58, true);
    if (kind === "servo:sweep") drawSweep(g, 46, 58);
  }
}

function paintMotor(g, kind, W, H) {
  g.fillStyle = "#16181b";
  g.fillRect(0, 0, W, H);
  if (kind === "motor:song") {
    drawMotor(g, 72);
    g.fillStyle = MOTION;
    g.strokeStyle = MOTION;
    g.lineWidth = 2;
    [[40, 26], [60, 18], [80, 28]].forEach(function (note) {
      g.beginPath(); g.ellipse(note[0], note[1], 5, 3.6, -0.4, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.moveTo(note[0] + 4.4, note[1] - 1); g.lineTo(note[0] + 4.4, note[1] - 16);
      g.stroke();
    });
    return;
  }
  g.save();
  g.translate(72, 60);
  g.scale(0.94, 0.94);
  g.translate(-80, -60);
  drawMotor(g, 60);
  drawWheel(g, 142, 60);
  g.restore();
}

function paintStars(g, seed, W, H) {
  var chance = scatter(seed);
  g.fillStyle = "#02030a";
  g.fillRect(0, 0, W, H);
  var cell = W / 64;
  for (var star = 0; star < 60; star++) {
    var far = chance();
    g.fillStyle = far < 0.8 ? "#8a93b8" : "#ffffff";
    g.fillRect(Math.floor(chance() * 64) * cell, Math.floor(chance() * 48) * cell,
               (far < 0.9 ? 1 : 2) * cell, cell);
  }
}

function paintPrompt(g, W, H) {
  g.fillStyle = "#1c1f22";
  g.fillRect(0, 0, W, H);
  g.fillStyle = "#8a93a0";
  g.font = "bold 40px monospace";
  g.fillText(">_", 55, 75);
}

function paintThumb(g, kind, seed, canvas, uses) {
  var W = canvas.width, H = canvas.height;
  if (kind.indexOf("pair:") === 0) return paintPair(g, kind.slice("pair:".length), W, H);
  if (kind.indexOf("shot:") === 0) return paintShot(g, kind.slice("shot:".length), W, H);
  if (kind.indexOf("outputs:") === 0) return paintOutputs(g, kind.slice("outputs:".length), uses, W, H);
  if (/^servo(:|$)/.test(kind)) return paintServo(g, kind, W, H);
  if (/^motor(:|$)/.test(kind)) return paintMotor(g, kind, W, H);
  if (kind === "stars") return paintStars(g, seed, W, H);
  if (kind === "drive") return paintPrompt(g, W, H);
  g.fillStyle = kind === "shot" ? "#111" : "#ddd";
  g.fillRect(0, 0, W, H);
}

function programThumb(path) {
  var program = programNamed(path) || {};
  var shown = PICTURES[path] || [];
  var kind = shown.length > 1 ? "pair:" + path : shown.length ? "shot:" + path
           : program.thumbnail || (program.example ? "shot" : "drive");
  return thumbCanvas(kind, path.length, usesOf(path));
}

var programView = null;

export var onProgramPage = false;

export function setProgramPage(on) {
  onProgramPage = on;
}

export function copyTile(example, file, folder, copy) {
  return h("span", {class: "bin", "data-copy": example ? "alone" : "",
                    title: (example ? "Customise a copy of " : "Duplicate ") + file + " in the " +
                           folder + " folder",
                    onclick: function (event) {
                      event.stopPropagation();
                      copy();
                    }}, "\u29c9");
}

export var programHooks = {examples: null, extras: []};

export function programUsesSaid(path) {
  var uses = usesOf(path);
  return ((programNamed(path) || {}).does || "") + (uses.length ? "\nUses " +
    uses.map(function (key) { return featureNamed(key)[1]; }).join(", ") : "");
}

export function programCardFace(path) {
  var uses = usesOf(path);
  return [h("span", {}, programThumb(path),
            uses.length ? h("span", {}, uses.map(featureIcon)) : null),
          h("strong", {}, programTitle(path))];
}

function programCard(path) {
  var program = programNamed(path) || {};
  var extras = programHooks.extras.map(function (extra) { return extra(path); }).filter(Boolean);
  var remove = program.example
    ? extras.map(function (extra) { return extra.remove; }).filter(Boolean)[0]
    : function () { removeProgram(path); };
  return h("li", {"data-busy": extras.some(function (extra) { return extra.busy; })},
    h("button", {type: "button", class: "programcard", "aria-pressed": String(boardSet.program === path),
                 title: programUsesSaid(path),
                 onclick: function () {
                   boardSet.program = boardSet.program === path ? null : path;
                   draw();
                 }},
      programCardFace(path)),
    programCardActions(path, program, remove),
    extras.map(function (extra) { return extra.badge; }));
}

function programCardActions(path, program, remove) {
  if (!drive.dirHandle && !remove) return null;
  var file = path.split("/").pop();
  var copySaid = (program.example ? "Customise a copy of " : "Duplicate ") + file + " in the " +
                 OWN_FOLDER + " folder";
  var removeSaid = "Delete " + file + " from the FX drive";
  return h("span", {},
    drive.dirHandle ? h("button", {type: "button", "data-action": "copy", title: copySaid,
                                   "aria-label": copySaid,
                                   onclick: function () { copyOwnProgram(path); }}, "\u29c9") : null,
    remove ? h("button", {type: "button", "data-action": "delete", title: removeSaid,
                          "aria-label": removeSaid, onclick: remove}, "\u00d7") : null);
}

async function copyOwnProgram(path) {
  try {
    var copy = await copyProgram(path);
    setPrograms(await drivePrograms(drive.dirHandle, true));
    if (boardSet.program === path) boardSet.program = copy;
    banner("Copied to " + copy + " on the FX drive. Open it in Thonny or another editor to " +
           "change it.");
  } catch (e) {
    banner("Could not copy " + path.split("/").pop() + ". " + await driveTrouble(e, path), true);
  }
  draw();
}

function sizeShown(path) {
  var screen = state.screens && state.screens.A;
  if (screen && screen.there && screen.size) return screen.size;
  var size = ((programNamed(path) || {}).args || []).filter(function (argument) {
    return argument.kind === "size";
  })[0];
  return (size && size.default) || "2.8";
}

function framedPanel(path, url) {
  var image = thumbImages[url];
  var upright = image && image.height > image.width;
  return screenHooks.panelPreview({size: sizeShown(path), turn: upright ? 0 : 90,
                                   art: {url: url, w: upright ? 240 : 320, h: upright ? 320 : 240,
                                         pixelated: true}});
}

function programPicture(path) {
  var shown = PICTURES[path] || [];
  var onScreen = usesOf(path).some(function (key) {
    return ["screen", "either", "pair", "hub"].indexOf(key) >= 0;
  });
  if (!onScreen || !shown.length) return h("figure", {}, programThumb(path));
  return h("figure", {"data-panels": shown.length > 1 ? "2" : "1"},
    shown.slice(0, 2).map(function (url) { return framedPanel(path, url); }));
}

function emptyPicture() {
  if (SCREEN_PORTS.length) {
    return h("figure", {"data-panels": "1"}, screenHooks.panelPreview({size: "2.8", turn: 0}));
  }
  return h("figure", {}, thumbCanvas("outputs:off", 1));
}

function heroNote(path) {
  if (!path) {
    return programNote("No program chosen, so the board plays the effects. Choose one below to " +
                       "run it instead.");
  }
  return programNote(
    "The board runs " + path.split("/").pop() + " instead of the effects. The effects are " +
    "kept, and play if the program is missing or stops, with the reason in errors.txt.",
    h("button", {type: "button", onclick: function () {
      boardSet.program = null;
      draw();
    }}, "Choose none"));
}

function heroWords(path) {
  if (!path) {
    var taken = ["outputs"];
    if (SCREEN_PORTS.length) taken.push(SCREEN_PORTS.length > 1 ? "screens" : "screen");
    if (BOARD.sound) taken.push("sound");
    return h("div", {},
      h("h2", {}, "Choose a program"),
      h("p", {}, "A program takes over the whole board, its " + spoken(taken) + ", while it runs."));
  }
  var program = programNamed(path) || {};
  var uses = usesOf(path);
  return h("div", {},
    h("h2", {}, programTitle(path)),
    h("p", {}, program.does || "No description."),
    h("p", {}, h("small", {}, path + (program.example ? ", built in" : ", on the drive"))),
    uses.length ? h("ul", {}, uses.map(function (key) {
      return h("li", {}, featureIcon(key), featureNamed(key)[1]);
    })) : null,
    programArguments(path, false));
}

function programHero(path) {
  return h("article", {"aria-label": "Chosen program", "data-chosen": !!path},
    heroNote(path),
    h("div", {}, path ? programPicture(path) : emptyPicture(), heroWords(path)));
}

function programGroup(title, paths, kept) {
  var own = title === OWN_GROUP;
  var open = !programGroupFolded(title);
  return h("section", {"aria-label": title},
    h("h2", {},
      h("button", {type: "button", "aria-expanded": String(open),
                   onclick: function () {
                     programsFolded[title] = open;
                     draw();
                   }},
        title, groupSays(title) ? h("small", {}, groupSays(title)) : null)),
    open && own && !paths.length ? h("p", {}, "None yet. Customise an example to make one.") : null,
    open && kept.length ? h("ul", {}, kept.map(programCard)) : null);
}

function programListing() {
  if (!drive.dirHandle) {
    return [h("p", {}, CAN_REACH_A_DRIVE ? "Open the FX drive to see the programs on it."
                                         : "This browser cannot open the FX drive, so programs " +
                                           "cannot be listed. Use Chrome or Edge.")];
  }
  if (programsReading || !programsKnown) {
    return [h("p", {}, "Reading the Python files on the drive" + (programsReading
      ? ", " + programsReading[0] + " of " + programsReading[1] + "..." : "..."))];
  }
  var groups = [];
  var listed = 0;
  offeredGroups().forEach(function (offered) {
    var title = offered[0], paths = offered[1];
    var kept = paths.filter(passesFilter);
    listed += paths.length;
    if (kept.length || title === OWN_GROUP) groups.push([programGroup(title, paths, kept), kept.length]);
  });
  var shown = groups.reduce(function (sum, group) { return sum + group[1]; }, 0);
  var parts = [featureFilter(chipFeatures(), {
    all: function () { return []; },
    none: function (keys) { return keys; }
  })].concat(groups.map(function (group) { return group[0]; }));
  if (!shown) {
    parts.push(h("p", {}, listed ? "Every program here needs hardware that is not ticked."
                                 : "There are no programs on this drive."));
  }
  var examples = programHooks.examples && programHooks.examples();
  if (examples) {
    if (groups.length > 1) parts.splice(parts.indexOf(groups[1][0]), 0, examples);
    else parts.push(examples);
  }
  return parts;
}

export function renderProgramView() {
  programView.hidden = !onProgramPage;
  if (!onProgramPage) return replace(programView);
  replace(programView, programHero(boardSet.program), programListing());
}

export var CHIPLESS = ["either", "outputs", "rgb", "button"];

export var unhad = [];

function had(key) { return unhad.indexOf(key) < 0; }

export function passesFilter(path) {
  return usesOf(path).every(function (key) {
    return key === "either" ? had("screen") || had("pair") : had(key);
  });
}

function chipFeatures() {
  var offered = offeredPaths();
  return FEATURES.filter(function (feature) {
    return CHIPLESS.indexOf(feature[0]) < 0 && offered.some(function (path) {
      return usesOf(path).indexOf(feature[0]) >= 0;
    });
  });
}

function offeredPaths() {
  var offered = [];
  offeredGroups().forEach(function (group) { offered = offered.concat(group[1]); });
  return offered;
}

export function featureFilter(features, choices) {
  var keys = features.map(function (feature) { return feature[0]; });
  return h("div", {class: "featurefilter", role: "group", "aria-label": "Show programs using"},
    h("span", {}, "With:"),
    features.map(function (feature) {
      var key = feature[0];
      return h("button", {type: "button", "aria-pressed": String(had(key)), "data-feature": key,
                          title: had(key) ? "Showing programs that use " + feature[1]
                                          : "Hiding programs that need " + feature[1],
                          onclick: function () {
                            var at = unhad.indexOf(key);
                            if (at >= 0) unhad.splice(at, 1);
                            else unhad.push(key);
                            draw();
                          }},
        featureIcon(key), feature[2]);
    }),
    h("span", {},
      ["all", "none"].map(function (which) {
        return h("button", {type: "button", onclick: function () {
          unhad = choices[which](keys);
          draw();
        }}, which);
      })));
}

function toEffects() {
  onProgramPage = false;
  boardSet.program = null;
  draw();
}

function toProgram() {
  onProgramPage = true;
  draw();
}

var pageSwitch = null;

function effectsFace() {
  var swatch = h("span", {class: "accswatch", "aria-hidden": "true"});
  tabSwatch(swatch, "outPanel");
  return h("span", {}, swatch);
}

function pageTab(page, name, said, face, choose) {
  var current = (page === "program") === onProgramPage;
  return h("li", {"data-page": page},
    h("button", {type: "button", "aria-current": current ? "page" : null, onclick: choose},
      face, h("span", {}, h("b", {}, name), said ? h("small", {}, said) : null)));
}

function renderPageSwitch() {
  var program = boardSet.program;
  replace(pageSwitch, h("ul", {},
    pageTab("effects", "Effects", "", effectsFace(), toEffects),
    pageTab("program", "Programs", program ? programTitle(program) : "",
            program ? programThumb(program)
                    : thumbCanvas(SCREEN_PORTS.length ? "stars" : "outputs:rainbow", 3),
            toProgram)));
}

(function () {
  var named = document.querySelector("header h1");
  var actions = h("span", {id: "headActions"});
  while (named.nextSibling) actions.appendChild(named.nextSibling);
  pageSwitch = h("nav", {id: "headSwitch", "aria-label": "Pages"});
  named.parentNode.appendChild(pageSwitch);
  named.parentNode.appendChild(actions);
  programView = h("section", {id: "programView", "aria-label": "Programs",
                              hidden: true});
  var body = document.getElementById("sceneBody");
  body.parentNode.insertBefore(programView, body.nextSibling);
}());

drawSteps.before.push(function () {
  document.body.toggleAttribute("data-program-page", onProgramPage);
});

drawSteps.after.push(function () {
  document.body.dataset.pageway = "headsplit";
  renderPageSwitch();
  renderProgramView();
  scenesInTheTab();
  headerOnOneLine();
  paintAll();
});

export function loadThumbs(sources) {
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

var COLUMN_REM = 57.2;

function headerOnOneLine() {
  var header = document.querySelector("header");
  header.removeAttribute("data-oneline");
  var rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  var style = getComputedStyle(header);
  var inner = header.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  var gap = rem;
  var side = (inner - COLUMN_REM * rem) / 2 - gap;
  var name = document.querySelector("header h1").scrollWidth;
  var shown = Array.prototype.filter.call(document.getElementById("headActions").children,
    function (one) {
      return one.offsetWidth && getComputedStyle(one).position !== "absolute";
    });
  var rest = shown.length ? shown[shown.length - 1].getBoundingClientRect().right -
                            shown[0].getBoundingClientRect().left : 0;
  var above = parseFloat(style.paddingTop);
  var border = parseFloat(style.borderBottomWidth) || 0;
  var button = document.getElementById("open").getBoundingClientRect().height;
  header.style.setProperty("--headgap", (above - border) + "px");
  header.style.setProperty("--buttonheight", button + "px");
  header.style.setProperty("--tabheight", (button + above) + "px");
  if (name <= side && rest + 8 <= side) header.setAttribute("data-oneline", "");
}

window.addEventListener("resize", headerOnOneLine);

function scenesInTheTab() {
  var into = !state.scenes.length && !onProgramPage &&
             pageSwitch.querySelector("li[data-page=effects]");
  document.body.toggleAttribute("data-scenes-in-tab", !!into);
  if (!into) return;
  var plus = document.getElementById("addScene");
  if (plus) into.appendChild(plus);
}
