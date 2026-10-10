
// ---- the effects page, or a program page ------------------------------------------------------
// Only program= and args= reach a program, which takes the whole board, so the page is one of
// two: the effects, as it opens, or a program run in their place. The program page replaces the
// effects view whole, scenes and all, since none of it plays while a program runs. Saving and
// the drive are on the save button's menu.
//
// The programs offered are those on the drive that name a section, and those at its top level,
// which the page learns only once the drive is open. Each has a small thumbnail at a screen's
// shape: its picture where one sits beside it, drawn here where there is not.

// The programs at the top of the drive that name no section, the group they make
var OWN_GROUP = "On the drive";

// The offered programs by group, as [name, paths]: the drive's own, then sections.txt's sections
// in its order, then any other a program names, each group's programs by title
function offeredGroups() {
  var named = SECTIONS.map(function (one) { return one[0]; });
  PROGRAMS.forEach(function (one) {
    if (one.section && named.indexOf(one.section) < 0) named.push(one.section);
  });
  var own = PROGRAMS.filter(function (one) { return !one.example && !one.section; });
  var groups = [[OWN_GROUP, own]].concat(named.map(function (name) {
    return [name, PROGRAMS.filter(function (one) { return one.section === name; })];
  }));
  return groups.map(function (group) {
    var paths = group[1].map(function (one) { return one.path; });
    paths.sort(function (a, b) { return programTitle(a) < programTitle(b) ? -1 : 1; });
    return [group[0], paths];
  }).filter(function (group) { return group[1].length; });
}

// What a group's heading says after its name, as the looks' groups do, a section's from
// sections.txt
function groupSays(title) {
  if (title === OWN_GROUP) return "your own programs";
  var listed = SECTIONS.filter(function (one) { return one[0] === title; })[0];
  return listed ? listed[1] : "";
}

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

// What a program uses, read from its source
function usesOf(path) {
  var program = programNamed(path);
  return program ? program.uses : [];
}

// A program's name to show: its own where it gives one, else its file's, in words
function programTitle(path) {
  var program = programNamed(path);
  if (program && program.name) return program.name;
  var words = path.split("/").pop().replace(/\.py$/, "").split("_").join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// ---- thumbnails ----------------------------------------------------------------------------------
// A drawn thumbnail is a screen's shape at a fifth of a 2.8" panel's pixels, blocky on purpose. A
// picture, a captured frame or a drive program's own, is drawn at half a panel's pixels, smooth

var THUMB_W = 64, THUMB_H = 48;
var PICTURE_W = 160, PICTURE_H = 120;
var thumbImages = {};

function thumbCanvas(kind, seed, uses) {
  var picture = /^(shot|pair):/.test(kind);
  var canvas = document.createElement("canvas");
  canvas.width = picture ? PICTURE_W : THUMB_W;
  canvas.height = picture ? PICTURE_H : THUMB_H;
  canvas.className = picture ? "progthumb picture" : "progthumb";
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
  var W = canvas.width, H = canvas.height, i;
  var chance = scatter(seed);
  function fill(ink) { g.fillStyle = ink; g.fillRect(0, 0, W, H); }
  function dotRow(ink, top, count, size, gap) {
    g.fillStyle = ink;
    for (i = 0; i < count; i++) g.fillRect(3 + i * (size + gap), top, size, size);
  }
  // A pair's two pictures side by side, each whole in its half, as the two panels stand
  if (kind.indexOf("pair:") === 0) {
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
  // A program's picture, read from beside it on the drive
  if (kind.indexOf("shot:") === 0) {
    fill("#111");
    var src = PICTURES[kind.slice("shot:".length)][0];
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
  if (kind.indexOf("outputs:") === 0) {
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
    var row = inks[kind.slice("outputs:".length)] || inks.mono;
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
  case "shot":
    // A captured frame not yet read from the drive, as the ground it is drawn on
    fill("#111");
    break;
  case "stars":
    fill("#02030a");
    for (i = 0; i < 60; i++) {
      var far = chance();
      g.fillStyle = far < 0.8 ? "#8a93b8" : "#ffffff";
      g.fillRect(Math.floor(chance() * W), Math.floor(chance() * H), far < 0.9 ? 1 : 2, 1);
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
  // A picture where it has one, else what its Thumbnail line draws, else a plain tile: dark for an
  // example, whose picture is still to be captured, and a prompt for the drive's own
  var program = programNamed(path) || {};
  var shown = PICTURES[path] || [];
  var kind = shown.length > 1 ? "pair:" + path : shown.length ? "shot:" + path
           : program.thumbnail || (program.example ? "shot" : "drive");
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
  var at = (program.args || []).map(function (argument) {
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
  var shown = PICTURES[path] || [];
  var onScreen = usesOf(path).some(function (key) {
    return ["screen", "either", "pair", "hub"].indexOf(key) >= 0;
  });
  if (onScreen && shown.length) {
    // A pair's second frame goes on a second panel, the two drawn smaller to stand side by side
    if (shown.length < 2) return framedPanel(path, shown[0]);
    var both = document.createElement("div");
    both.className = "twopanels";
    both.appendChild(framedPanel(path, shown[0]));
    both.appendChild(framedPanel(path, shown[1]));
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
  var big = thumbCanvas("outputs:off", 1);
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
                    (program.example ? ", comes with the board" : ", on the drive") + "</p>";
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
  // The programs are the drive's, so none is listed until it is open
  if (!drive.dirHandle) {
    var closed = document.createElement("p");
    closed.className = "prognone";
    closed.textContent = CAN_REACH_A_DRIVE ? "Open the FX drive to see the programs on it."
                                           : "This browser cannot open the FX drive, so its " +
                                             "programs cannot be listed. Chrome and Edge can.";
    programView.appendChild(closed);
    return;
  }
  // Each program is read off the drive in turn, which takes a while, so the count is shown
  if (programsReading) {
    var reading = document.createElement("p");
    reading.className = "prognone";
    reading.textContent = "Reading the programs on the drive, " + programsReading[0] + " of " +
                          programsReading[1] + "...";
    programView.appendChild(reading);
    return;
  }
  programView.appendChild(featureFilter());
  var shown = 0;
  var listed = 0;
  function group(title, paths) {
    listed += paths.length;
    var kept = paths.filter(passesFilter);
    if (!kept.length) return;
    shown += kept.length;
    var heading = document.createElement("div");
    heading.className = "gallery-head";
    heading.appendChild(document.createTextNode(title));
    if (groupSays(title)) {
      var says = document.createElement("span");
      says.className = "says";
      says.textContent = groupSays(title);
      heading.appendChild(says);
    }
    programView.appendChild(heading);
    var grid = document.createElement("div");
    grid.className = "proggrid";
    kept.forEach(function (path) { grid.appendChild(programCard(path)); });
    programView.appendChild(grid);
  }
  offeredGroups().forEach(function (offered) { group(offered[0], offered[1]); });
  if (!shown) {
    var none = document.createElement("p");
    none.className = "prognone";
    none.textContent = listed ? "Every program here needs something not ticked."
                              : "There are no programs on this drive.";
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
  var offered = [];
  offeredGroups().forEach(function (group) { offered = offered.concat(group[1]); });
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
             : thumbCanvas(SCREEN_PORTS.length ? "stars" : "outputs:rainbow", 3);
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
