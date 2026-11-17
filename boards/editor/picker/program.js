import {banner} from "./banner.js";
import {SCREEN_PORTS, screenHooks} from "./board.js";
import {
  PROGRAMS, argsFor, boardSet, onProgramPage, programNamed, programsReadingSteps, setProgramPage,
  setPrograms
} from "./board_settings.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps, paintAll} from "./draw.js";
import {CAN_REACH_A_DRIVE, drive, driveTrouble} from "./drive.js";
import {
  OWN_FOLDER, PICTURES, SECTIONS, copyProgram, driveHasCredentials, drivePrograms, programsKnown,
  programsReading, removeProgram, thumbImages
} from "./drive_programs.js";
import {spoken} from "./lines.js";
import {BOARD} from "./looks.js";
import {state} from "./scenes.js";
import {BOARD_SETTING_SAYS, boardIcon} from "./setup.js";
import {tabSwatch} from "./tabs.js";

// ---- the effects page, or a program page ------------------------------------------------------
// Only program= and args= reach a program, which takes the whole board, so the page is one of
// two. It shows the effects, as it opens, or a program run in their place. The program page
// replaces the effects view whole, scenes and all, since none of it plays while a program runs.
// The settings for saving and the drive are on the save button's menu.
//
// The programs offered are the user's own, at the drive's top level or in its programs folder,
// and the examples that name a section. The page learns them only once the drive is open, and
// leaves out any going online where the drive holds no WiFi credentials. Each has a small
// thumbnail at a screen's shape, which is the picture beside it or else one drawn here.

// The name of the group for the user's own programs that name no section
export var OWN_GROUP = "On the drive";

// The offered programs by group, as [name, paths]. The drive's own group comes first and is
// always kept, then sections.txt's sections in its order, then any other a program names. Each
// group's programs are sorted by title
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
    // Numbers in titles counted, so name 2 comes before name 10
    paths.sort(function (a, b) {
      return programTitle(a).localeCompare(programTitle(b), undefined, {numeric: true});
    });
    return [group[0], paths];
  }).filter(function (group, at) { return !at || group[1].length; });
}

// What a group's heading says after its name, as the looks' groups do. A section takes its words
// from sections.txt, and the drive's own group has words of its own
function groupSays(title) {
  if (title === OWN_GROUP) return "your own programs";
  var listed = SECTIONS.filter(function (one) { return one[0] === title; })[0];
  return listed ? listed[1] : "";
}

// Whether each of the program tab's groups is folded, by name, for those folded or opened
var programsFolded = {};

// Whether a group is folded. Each starts open unless sections.txt marks its section folded
function programGroupFolded(title) {
  if (title in programsFolded) return programsFolded[title];
  var listed = SECTIONS.filter(function (one) { return one[0] === title; })[0];
  return !!(listed && listed[2]);
}

// A group's heading, pressed to fold or open it. It shows the group's name and what it holds
export function foldHead(title, says, open, toggle) {
  return h("button", {
    type: "button", className: "gallery-head foldhead" + (open ? " open" : ""),
    "aria-expanded": String(open),
    onclick: function () {
      toggle();
      draw();
    }
  }, title, says ? h("span", {className: "says"}, says) : null);
}

// Round holes cut through a filled shape, one at each point, as a path's own subpaths
function holes(points, radius) {
  return points.map(function (at) {
    return "M" + (at[0] - radius) + " " + at[1] + "a" + radius + " " + radius + " 0 1 0 " +
           radius * 2 + " 0a" + radius + " " + radius + " 0 1 0 " + -radius * 2 + " 0";
  }).join("");
}

// What a program can use, in the order they are shown. Each has its key, its name, the shorter
// name its chip in the filter takes, and a drawing on a 24 grid. A part classed "f" is filled,
// "fs" filled and outlined, and the rest outlined, so each reads as a silhouette at 18px
export var FEATURES = [
  ["outputs", "the outputs", "outputs",
   "<circle class='f' cx='3.8' cy='10' r='3'/><circle class='f' cx='12' cy='10' r='3'/>" +
   "<circle class='f' cx='20.2' cy='10' r='3'/><path d='M1.5 18h21' stroke-width='2.2'/>"],
  // Three lights overlapping, as the three channels of one RGB output
  ["rgb", "the RGB output", "RGB",
   "<circle class='f' cx='12' cy='8' r='5'/><circle cx='8' cy='15' r='5' stroke-width='2'/>" +
   "<circle cx='16' cy='15' r='5' stroke-width='2'/>"],
  ["screen", "a screen", "screen", "<rect class='f' x='3' y='5' width='18' height='14' rx='2'/>"],
  // Two panels apart, the second outlined as it is optional
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
  // as the effects page draws a strip. Its LEDs are holes cut out of it
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

export function featureIcon(key) {
  return h("svg:svg", {viewBox: "0 0 24 24", class: "featureicon", "aria-hidden": "true",
                       html: featureNamed(key)[3]});
}

// What a program uses, read from its source
export function usesOf(path) {
  var program = programNamed(path);
  return program ? program.uses : [];
}

// A program's name to show: its own where it gives one, else its file's, in words
export function programTitle(path) {
  var program = programNamed(path);
  if (program && program.name) return program.name;
  var words = path.split("/").pop().replace(/\.py$/, "").split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---- thumbnails ----------------------------------------------------------------------------------
// A thumbnail is a screen's shape at half a 2.8" panel's pixels, drawn or a picture, a captured
// frame or a drive program's own

var THUMB_W = 160, THUMB_H = 120;

function thumbCanvas(kind, seed, uses) {
  var canvas = h("canvas", {width: THUMB_W, height: THUMB_H, className: "progthumb"});
  paintThumb(canvas.getContext("2d"), kind, seed || 1, canvas, uses || []);
  return canvas;
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

// A rectangle with rounded corners, filled
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

// What marks a machine's motion
var MOTION = "#ffd21f";

// A turn along part of an ellipse from one angle to another, backwards being anticlockwise, with
// a head at its end pointing along it
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

// A wheel seen edge on, upright and centred on its axle, with its turn beside it to the right
function drawWheel(g, x, y) {
  g.fillStyle = "#62666e";
  fillRounded(g, x - 7.5, y - 42, 15, 84, 7.5);
  g.fillStyle = "#7c8089";
  for (var tread = -35; tread < 37; tread += 5) g.fillRect(x - 5.5, y + tread, 11, 2);
  drawTurn(g, x + 17.5, y, 6, 24, Math.PI * 0.34, Math.PI * 2.1, false);
}

// A servo's colours, its body's translucent blue lighter towards the top, and its white horn
var BLUE = "#2f62d6", BLUE_DARK = "#1d43a6", BLUE_LIGHT = "#5d8bef", WHITE = "#eef1f5";

// A micro servo from the side, its body's top left corner at (x, y - 4), its spline on top and the
// wires out of its lower left. Its horn, where it has one, is long to the right of the spline
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
  // The mounting tabs, through the body a little above its middle
  g.fillStyle = BLUE_DARK;
  g.fillRect(x - 15, y + 6, 98, 9);
  g.fillStyle = BLUE;
  g.fillRect(x - 15, y + 6, 98, 6);
  // The body steps in twice towards the top, each step drawn before the one below so it hides its
  // rounded foot. The upper step is lighter and lit along its top edge
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

// The servo's sweep, part of a turn round its spline, across the front of its horn
function drawSweep(g, x, y) {
  drawTurn(g, x + 17, y - 36, 36, 8, Math.PI * 0.95, Math.PI * 0.12, true);
}

// A gearmotor's colours, its can's silver, the gearbox's brass and the end cap's plastic
var SILVER = "#c3cad3", SILVER_LIGHT = "#dfe4ea", BRASS = "#d9a93a", BRASS_DARK = "#a77d1f",
    PLASTIC = "#4b5058";

// A micro metal gearmotor from the side at a height, its pins and end cap to the left, then its
// can, its gearbox and the shaft
function drawMotor(g, y) {
  g.fillStyle = SILVER;
  g.fillRect(12, y - 13, 10, 3);
  g.fillRect(12, y + 10, 10, 3);
  g.fillStyle = PLASTIC;
  fillRounded(g, 19, y - 20, 13, 40, 3);
  // The can, lighter along its top, with two slots pressed into its side
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
  // The gears between the gearbox's plates, then the rods holding the plates apart
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

// A repeatable scatter, so a thumbnail is the same every time it is drawn
function scatter(seed) {
  var state = seed * 9301 + 49297;
  return function () {
    state = (state * 9301 + 49297) % 233280;
    return state / 233280;
  };
}

function paintThumb(g, kind, seed, canvas, uses) {
  var W = canvas.width, H = canvas.height, i;
  var chance = scatter(seed);
  function fill(ink) { g.fillStyle = ink; g.fillRect(0, 0, W, H); }
  function dotRow(ink, top, count, size, gap) {
    g.fillStyle = ink;
    for (i = 0; i < count; i++) g.fillRect(3 + i * (size + gap), top, size, size);
  }
  if (kind.indexOf("pair:") === 0) {
    // A pair's two pictures side by side, each whole in its half, as the two panels stand
    fill("#111");
    PICTURES[kind.slice("pair:".length)].forEach(function (src, side) {
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
  if (kind.indexOf("shot:") === 0) {
    // A program's picture, read from beside it on the drive
    fill("#111");
    var src = PICTURES[kind.slice("shot:".length)][0];
    var image = thumbImages[src];
    if (!image) {
      image = thumbImages[src] = new Image();
      image.src = src;
    }
    var drawn = function () {
      // One taller than wide is shown whole, as cropping it to fill would lose its top and foot
      var upright = image.height > image.width;
      var scale = (upright ? Math.min : Math.max)(W / image.width, H / image.height);
      g.imageSmoothingEnabled = true;
      g.drawImage(image, (W - image.width * scale) / 2, (H - image.height * scale) / 2,
                  image.width * scale, image.height * scale);
    };
    if (image.complete && image.width) drawn();
    else image.addEventListener("load", drawn);
    return;
  }
  if (kind.indexOf("outputs:") === 0) {
    // What the outputs do, as a lamp for each on the board's dark, spread across seven lamps' width
    fill("#16181b");
    var inks = {rainbow: ["#ff2d1a", "#ff9022", "#ffd21f", "#22c65a", "#28e0e0", "#2b5cff", "#9a46ff"],
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
                off: ["#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44", "#3a3f44"]};
    var row = inks[kind.slice("outputs:".length)] || inks.mono;
    var lamps = BOARD.outputs;
    // On a board with mono outputs and a colour one, the colour lamp sits two rows below the rest as
    // on the board, and a lamp is lit only where the program uses its kind of output
    var mixed = lamps.some(function (output) { return output.kind === "mono"; }) &&
                lamps.some(function (output) { return output.kind !== "mono"; });
    var usesMono = !mixed || uses.indexOf("outputs") >= 0;
    var usesColour = !mixed || uses.indexOf("rgb") >= 0;
    lamps.forEach(function (output, at) {
      var isMono = output.kind === "mono";
      var ink = row[Math.min(at, row.length - 1)];
      if (!(isMono ? usesMono : usesColour)) ink = "#3a3f44";
      // A program lighting only the colour output shows its pattern's first colour there
      else if (!isMono && !usesMono) ink = row[0];
      g.fillStyle = isMono ? monoInk(ink) : ink;
      g.beginPath();
      g.arc(lamps.length > 1 ? 17 + at * 21 * 6 / (lamps.length - 1) : W / 2,
            H / 2 + (mixed ? (isMono ? -21 : 21) : 0), 7.5, 0, Math.PI * 2);
      g.fill();
    });
    return;
  }
  if (/^servo(:|$)/.test(kind)) {
    // A servo, sweeping, in a pair or driving a wheel
    fill("#16181b");
    if (kind === "servo:pair") {
      // Two sweeping, the second mirrored so its horn and sweep run the other way
      [1, -1].forEach(function (side) {
        g.save();
        g.translate(side > 0 ? 2 : 158, 24);
        g.scale(0.66 * side, 0.66);
        drawServo(g, 30, 52, true);
        drawSweep(g, 30, 52);
        g.restore();
      });
    } else if (kind === "servo:wheel") {
      // A continuous servo laid on its side, wires below, driving a wheel. The spline's end lands
      // at (24, 17) once turned, which the whole is lifted by to put the axle level
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
    return;
  }
  if (/^motor(:|$)/.test(kind)) {
    // A gearmotor driving a wheel, or under notes for one that plays
    fill("#16181b");
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
    // Drawn smaller about the card's middle, to leave the wheel and its turn room on the right
    g.save();
    g.translate(72, 60);
    g.scale(0.94, 0.94);
    g.translate(-80, -60);
    drawMotor(g, 60);
    drawWheel(g, 142, 60);
    g.restore();
    return;
  }
  switch (kind) {
  case "shot":
    // A captured frame not yet read from the drive, shown as the dark background it is drawn on
    fill("#111");
    break;
  case "stars":
    // Stars on a grid of 64 by 48, each a square of it, so the field is as coarse at any size
    fill("#02030a");
    var cell = W / 64;
    for (i = 0; i < 60; i++) {
      var far = chance();
      g.fillStyle = far < 0.8 ? "#8a93b8" : "#ffffff";
      g.fillRect(Math.floor(chance() * 64) * cell, Math.floor(chance() * 48) * cell,
                 (far < 0.9 ? 1 : 2) * cell, cell);
    }
    break;
  case "drive":
    // A program of the user's own that names no picture, shown as a prompt waiting for code
    fill("#1c1f22");
    g.fillStyle = "#8a93a0";
    g.font = "bold 40px monospace";
    g.fillText(">_", 55, 75);
    break;
  default:
    fill("#ddd");
  }
}

// A program's thumbnail, as its picture where it has one, else what its Thumbnail line draws. A
// program with neither has a plain tile, dark for an example whose picture is still to be
// captured, or a prompt for the drive's own
function programThumb(path) {
  var program = programNamed(path) || {};
  var shown = PICTURES[path] || [];
  var kind = shown.length > 1 ? "pair:" + path : shown.length ? "shot:" + path
           : program.thumbnail || (program.example ? "shot" : "drive");
  return thumbCanvas(kind, path.length, usesOf(path));
}

// ---- the program page ------------------------------------------------------------------------

export var programView = null;

// A card's copy tile, in the bin's place on an example, which has none, or beside the bin on the
// user's own. An example is customised and one of the user's own duplicated, into the folder named
export function copyTile(example, file, folder, copy) {
  return h("span", {
    className: "bin copytile" + (example ? " alone" : ""),
    title: (example ? "Customise a copy of " : "Duplicate ") + file + " in the " + folder +
           " folder",
    onclick: function (e) {
      e.stopPropagation();
      copy();
    }
  }, "\u29c9");
}

// A program as a card, as the looks are, its thumbnail over its name, and what it uses as a row
// of small drawings along the foot of the thumbnail
export function programCard(path) {
  var uses = usesOf(path);
  var example = !!(programNamed(path) || {}).example;
  var file = path.split("/").pop();
  var card = h("button", {
    type: "button",
    className: "progcard" + (boardSet.program === path ? " picked" : ""),
    "aria-pressed": String(boardSet.program === path),
    "data-path": path,
    title: ((programNamed(path) || {}).does || "") + (uses.length ? "\nUses " +
      uses.map(function (key) { return featureNamed(key)[1]; }).join(", ") : ""),
    // Picked again, the program is put back, leaving none chosen
    onclick: function () {
      boardSet.program = boardSet.program === path ? null : path;
      draw();
    }
  }, programThumb(path),
     uses.length ? h("span", {className: "proguses"}, uses.map(featureIcon)) : null,
     h("span", {className: "progname"}, programTitle(path)),
     // A copy to change, which takes the original's place where it was chosen
     drive.dirHandle ? copyTile(example, file, OWN_FOLDER, async function () {
       try {
         var copy = await copyProgram(path);
         setPrograms(await drivePrograms(drive.dirHandle, true));
         if (boardSet.program === path) boardSet.program = copy;
         banner("Copied to " + copy + " on the FX drive. Open it in Thonny or another editor to " +
                "change it.");
       } catch (e) {
         banner("Could not copy " + file + ". " + await driveTrouble(e, path), true);
       }
       draw();
     }) : null,
     // Check if the program is the user's own, which can be deleted as the effects' media can
     example ? null : h("span", {
       className: "bin", title: "Delete " + file + " from the FX drive",
       onclick: function (e) {
         e.stopPropagation();
         removeProgram(path);
       }
     }, "\u00d7"));
  programCardSteps.forEach(function (step) { step(card, path); });
  return card;
}

// What the parts after this one add to each program card, each given the card and its path
export var programCardSteps = [];

// The screen size a program is shown on: screen A's, else the program's own default, else a 2.8".
// Its picture was taken at its defaults, so what it is given changes nothing here
function sizeShown(path) {
  var screen = state.screens && state.screens.A;
  if (screen && screen.there && screen.size) return screen.size;
  var size = ((programNamed(path) || {}).args || []).filter(function (argument) {
    return argument.kind === "size";
  })[0];
  return (size && size.default) || "2.8";
}

// One captured frame on a module at the program's screen size, turned as the program turns it.
// A frame taller than wide was taken from a panel upright
function framedPanel(path, url) {
  var image = thumbImages[url];
  var upright = image && image.height > image.width;
  return screenHooks.panelPreview({size: sizeShown(path), turn: upright ? 0 : 90,
                                   art: {url: url, w: upright ? 240 : 320, h: upright ? 320 : 240,
                                         pixelated: true}});
}

// The picked program's picture. A screen program shows its captured frame on the panel it
// would play on, as the Screens tab draws one, turned as the program turns it. Any other
// program, and any program on a board without screens, shows its thumbnail large
function programPicture(path) {
  var shown = PICTURES[path] || [];
  var onScreen = SCREEN_PORTS.length && usesOf(path).some(function (key) {
    return ["screen", "either", "pair", "hub"].indexOf(key) >= 0;
  });
  if (onScreen && shown.length) {
    if (shown.length < 2) return framedPanel(path, shown[0]);
    // A pair's second frame goes on a second panel, the two drawn smaller to stand side by side
    return h("div", {className: "twopanels"},
             framedPanel(path, shown[0]), framedPanel(path, shown[1]));
  }
  var big = programThumb(path);
  big.classList.add("big");
  return big;
}

// The picture before a program is chosen, as an empty panel upright so its words read across, or
// on a board without screens its lamps unlit
function emptyPicture() {
  if (SCREEN_PORTS.length) return screenHooks.panelPreview({size: "2.8", turn: 0});
  var big = thumbCanvas("outputs:off", 1);
  big.classList.add("big");
  return big;
}

// The line along the preview's top, saying what the board runs, with the way to choose none
function heroNote(path) {
  return h("div", {className: "programnote", title: BOARD_SETTING_SAYS}, boardIcon(),
           h("span", {}, path
             ? "The board runs " + path.split("/").pop() + " instead of the effects. The " +
               "effects are kept, and play if the program is missing or stops, with the reason " +
               "in errors.txt."
             : "No program chosen, so the board plays the effects. Choose one below to run it " +
               "instead."),
           path ? h("button", {
             type: "button", className: "progchoosenone",
             onclick: function () {
               boardSet.program = null;
               draw();
             }
           }, "Choose none") : null);
}

// What a picked program does, what it needs and what it takes, or before one is picked, what
// choosing one does
function programWords(path) {
  if (!path) {
    var taken = ["outputs"];
    if (SCREEN_PORTS.length) taken.push(SCREEN_PORTS.length > 1 ? "screens" : "screen");
    if (BOARD.sound) taken.push("sound");
    return h("div", {className: "progwords"},
             h("h3", {}, "Choose a program"),
             h("p", {}, "A program takes over the whole board, its " + spoken(taken) +
                        ", while it runs."));
  }
  var program = programNamed(path) || {};
  var uses = usesOf(path);
  return h("div", {className: "progwords"},
           h("h3", {}, programTitle(path)),
           h("p", {}, program.does || "No description."),
           h("p", {className: "progwhere"},
             path + (program.example ? ", built in" : ", on the drive")),
           // What it uses, each drawn and named, as the filter below names them
           uses.length ? h("div", {className: "herouses"}, uses.map(function (key) {
             return h("span", {}, featureIcon(key), featureNamed(key)[1]);
           })) : null,
           argsFor(path, false));
}

// The picked program large, with what it does, what it needs and what it takes. With none picked
// the box keeps its size, an empty panel in the picture's place, so choosing one moves nothing
function programHero(path) {
  return h("div", {className: "proghero" + (path ? "" : " unchosen")},
           heroNote(path),
           h("div", {className: "herobody"},
             h("div", {className: "progpicture"}, path ? programPicture(path) : emptyPicture()),
             programWords(path)));
}

// The programs under the picked one, grouped and filtered, or what keeps them from being listed
function programListing() {
  // Check if the drive is not open. The programs are the drive's, so none is listed until it is
  if (!drive.dirHandle) {
    return h("p", {className: "prognone"},
             CAN_REACH_A_DRIVE ? "Open the FX drive to see the programs on it."
                               : "This browser cannot open the FX drive, so programs cannot be " +
                                 "listed. Use Chrome or Edge.");
  }
  // Check if the drive's Python files are still being read. Each is read in turn, which takes a
  // while, so the count is shown once the files are counted
  if (programsReading || !programsKnown) {
    return h("p", {className: "prognone"},
             "Reading the Python files on the drive" + (programsReading
               ? ", " + programsReading[0] + " of " + programsReading[1] + "..." : "..."));
  }
  var parts = [featureFilter()];
  var shown = 0;
  var listed = 0;
  offeredGroups().forEach(function (offered) {
    var title = offered[0];
    var paths = offered[1];
    listed += paths.length;
    var kept = paths.filter(passesFilter);
    // The user's own is always there, as the effects' are, saying how to start one where empty
    var own = title === OWN_GROUP;
    if (!kept.length && !own) return;
    shown += kept.length;
    var open = !programGroupFolded(title);
    parts.push(foldHead(title, groupSays(title), open, function () {
      programsFolded[title] = open;
    }));
    if (!open) return;
    if (own && !paths.length) {
      parts.push(h("p", {className: "prognone"}, "None yet. Customise an example to make one."));
    }
    if (kept.length) parts.push(h("div", {className: "proggrid"}, kept.map(programCard)));
  });
  if (!shown) {
    parts.push(h("p", {className: "prognone"},
                 listed ? "Every program here needs hardware that is not ticked."
                        : "There are no programs on this drive."));
  }
  return parts;
}

function renderProgramView() {
  if (!onProgramPage) {
    replace(programView);
    return;
  }
  replace(programView, programHero(boardSet.program), programListing());
  if (drive.dirHandle && programsKnown && !programsReading) {
    programViewSteps.forEach(function (step) { step(); });
  }
}
programsReadingSteps.push(renderProgramView);

// What the parts after this one add to the program tab once its programs are listed
export var programViewSteps = [];

// ---- choosing by what is to hand ----------------------------------------------------------------
// A chip for each thing an offered program can use, all on to begin with. A chip turned off is
// something not to hand, so every program needing it goes, and a program stays only while all it
// uses is on. One screen or two is had with either a screen or two, so it has no chip of its own.
// Every board has its outputs and its Boot button, and any RGB output, so none of those has one

export var CHIPLESS = ["either", "outputs", "rgb", "button"];

export var unhad = [];

// Set the parts the program filter takes as not to hand
export function setUnhad(list) {
  unhad = list;
}

export function had(key) { return unhad.indexOf(key) < 0; }

export function passesFilter(path) {
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
  var offered = [];
  offeredGroups().forEach(function (group) { offered = offered.concat(group[1]); });
  return offered;
}

function featureFilter() {
  var chips = chipFeatures();
  return h("div", {className: "featurefilter"},
           h("span", {}, "With:"),
           chips.map(function (feature) {
             return h("button", {
               type: "button", className: "featurechip" + (had(feature[0]) ? " on" : ""),
               "aria-pressed": String(had(feature[0])),
               "data-feature": feature[0],
               title: had(feature[0]) ? "Showing programs that use " + feature[1]
                                      : "Hiding programs that need " + feature[1],
               onclick: function () {
                 var at = unhad.indexOf(feature[0]);
                 if (at >= 0) unhad.splice(at, 1);
                 else unhad.push(feature[0]);
                 draw();
               }
             }, featureIcon(feature[0]), feature[2]);
           }),
           // Buttons to turn every chip on, or every chip off for ticking what is to hand. They
           // are kept together in one box where the row wraps
           h("div", {className: "featureclears"},
             [["all", function () { return []; }],
              ["none", function () { return chips.map(function (feature) { return feature[0]; }); }]]
               .map(function (one) {
                 return h("button", {
                   type: "button", className: "featureclear",
                   onclick: function () {
                     unhad = one[1]();
                     draw();
                   }
                 }, one[0]);
               })));
}

// ---- moving between the two pages ---------------------------------------------------------------
// Two tabs split under the header, the effects tab holding the way into scenes until there are some

// Go back to the effects, so the file runs them again
function toEffects() {
  setProgramPage(false);
  boardSet.program = null;
  draw();
}

// Over to the programs with none chosen, until one is picked
function toProgram() {
  setProgramPage(true);
  draw();
}

// The effects summed up small in a live swatch of the outputs, as their own tab has. It is painted
// every frame from what the lamps play, so it never stops on whichever frame a redraw caught
function effectsFace() {
  var swatch = h("span", {className: "accswatch"});
  tabSwatch(swatch, "outPanel");
  return h("span", {className: "effectsface"}, swatch);
}

function renderPageSwitch() {
  var inHeader = document.getElementById("headSwitch");
  var program = boardSet.program;
  // Split under the header, the tabs are drawn as the tabs off its foot are
  inHeader.className = "headswitch headsplit headtabs";
  // Two tabs, each showing what it would run, with the page shown marked. They sit small in the
  // header where the page's name is, taking no room from the page
  replace(inHeader, [["effects", "Effects"],
                     ["program", "Programs", program ? programTitle(program) : ""]].map(function (one) {
    // With no program chosen its tab shows a starfield, or the lamps lit on a board without screens
    var face = one[0] === "effects" ? effectsFace()
             : program ? programThumb(program)
             : thumbCanvas(SCREEN_PORTS.length ? "stars" : "outputs:rainbow", 3);
    face.classList.add("coverface");
    // A tab holds the scenes' button, and a button cannot hold another, so a tab is a plain
    // element taking the click and the keyboard. Only a program's name is said under its tab
    var cover = h("div", {
      role: "button", tabIndex: 0,
      className: "cover" + ((one[0] === "program") === onProgramPage ? " on" : ""),
      "data-page": one[0],
      onkeydown: function (event) {
        if (event.key === "Enter" || event.key === " ") cover.onclick();
      },
      onclick: one[0] === "effects" ? toEffects : toProgram
    }, face, h("span", {}, h("b", {}, one[1]), one[2] ? h("small", {}, one[2]) : null));
    return cover;
  }));
}

// In the header after the page's name. What follows the name is gathered into one group, so a
// wide header can set name, tabs and group on a single line
var headActions = h("span", {id: "headActions", className: "headactions"});
var pageName = document.querySelector("header h1");
while (pageName.nextSibling) headActions.appendChild(pageName.nextSibling);
pageName.after(h("span", {id: "headSwitch", className: "headswitch"}), headActions);
programView = h("div", {id: "programView", className: "programview"});
document.getElementById("sceneBody").after(programView);

// Before anything is drawn, as the effects' parts measure themselves and measure nothing while
// the program page hides them
addStep(drawSteps.before, DRAW_BEFORE, "program", function () {
  document.body.classList.toggle("programpage", onProgramPage);
});

addStep(drawSteps.after, DRAW_AFTER, "program", function () {
  document.body.dataset.pageway = "headsplit";
  renderPageSwitch();
  renderProgramView();
  scenesInTheTab();
  headerOnOneLine();
  // The effects' live swatch in the tabs is made after the page painted, so it is painted now
  paintAll();
});

// The width of the page's column in rem. It must match the stylesheet's
var COLUMN_REM = 57.2;

// Split under the header, the tabs stand over the page's column. Where the window is wide
// enough for the name to fit left of that column and the rest right of it, all three share one
// line, measured, since what fits depends on the name and on which buttons show
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
// kept above the gallery for it. Once there are scenes their cards take that place
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
