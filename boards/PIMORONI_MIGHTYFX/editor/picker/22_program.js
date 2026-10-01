
// ---- the effects page, or a program page ------------------------------------------------------
// Only program= and args= reach a program, which takes the whole board, so the page is one of
// two: the effects, as it opens, or a program run in their place. The program page replaces the
// effects view whole, scenes and all, since none of it plays while a program runs. Saving and
// the drive are on the save button's menu.
//
// The programs offered are those that do something the effects cannot and run by themselves:
// the showcase signs, screen pieces, and what a remote, a sensor, a speaker or a motor brings.
// The effects' own demonstrations, walkthroughs of the drawing library and calibrations are left
// out. Each has a small thumbnail, drawn here at a screen's shape and low resolution, standing in
// for frames the board itself would give once a tool captures them

// Where each offered example sits and how its thumbnail is drawn. What each uses is read from
// its source when the page is built
var OFFERED = [
  ["Signs and displays", [
    ["showcase/flip_dot_sign.py", "flipdot"],
    ["showcase/split_flap_clock.py", "flap"],
    ["showcase/split_flap_departures.py", "flapboard"],
    ["showcase/nixie_tube.py", "nixie"],
    ["showcase/acrylic_lixie.py", "lixie"],
    ["showcase/departures_list.py", "board"],
    ["showcase/departure_board.py", "board"],
    ["showcase/bus_departures.py", "bus"],
    ["showcase/tram_stop_sign.py", "amber"],
    ["showcase/roadworks_sign.py", "roadworks"],
    ["showcase/lane_control_gantry.py", "gantry"],
    ["showcase/crt_terminal.py", "crt"],
    ["showcase/status_panel.py", "asset:pirate_coin_emblem.gif"],
    ["showcase/scrolling_billboard.py", "asset:billboards/landscape/lambo.png"],
    ["showcase/trivision_billboard.py", "trivision"],
    ["showcase/skyline.py", "asset:skyline.png"],
    ["showcase/isometric_flight.py", "iso"]]],
  ["On screens", [
    ["screens/graphics/starfield.py", "stars"],
    ["screens/graphics/color_wheel.py", "wheel"],
    ["screens/graphics/led_matrix.py", "matrix"],
    ["screens/layout/kaleidoscope.py", "kaleido"],
    ["screens/layout/bouncing_logo.py", "logo"],
    ["screens/playback/traces_scroll.py", "asset:traces/traces2.png"],
    ["screens/playback/billboard_cased.py", "asset:billboards/landscape/frum.png"],
    ["screens/playback/animated_gif_recoloured.py", "asset:pirate_coin.gif"],
    ["screens/pair/carpets_paired.py", "carpet"],
    ["screens/hub/starfield_wall.py", "stars"],
    ["screens/playback/traces_wall.py", "asset:traces/traces5.png"]]],
  ["With the remote", [
    ["infrared/colour/control_rainbow_wave.py", "lamps:rainbow"],
    ["infrared/colour/control_hsv_fx.py", "lamps:warm"],
    ["infrared/mono/toggle_effects.py", "lamps:mono"],
    ["infrared/mono/control_pulse_wave.py", "lamps:pulse"]]],
  ["With a sensor", [
    ["qwst/light_level.py", "lamps:dusk"],
    ["qwst/spirit_level.py", "lamps:level"],
    ["qwst/weather_reading.py", "lamps:bar"],
    ["function/sensor_meter.py", "lamps:bar"]]],
  ["Sound", [
    ["audio/fair_use_encounters.py", "lamps:melody"],
    ["audio/race_start.py", "lamps:countdown"]]],
  ["Moving things", [
    ["servos/servo_easing.py", "servo"],
    ["servos/servo_pair.py", "servo"],
    ["motors/motor_song.py", "motor"],
    ["motors/motor_movements.py", "motor"],
    ["showcase/programmed_route.py", "servo"]]]
];

// The drive's own programs, drawn as the offered ones are, and what each uses, which a program
// on the drive would say in its opening string
var DRIVE_THUMBS = {"slideshow.py": "asset:billboards/landscape/tufty.png",
                    "departures.py": "bus", "fireplace.py": "flame"};
var DRIVE_USES = {"slideshow.py": ["screen"], "departures.py": ["either", "wifi"],
                  "fireplace.py": ["outputs"]};

// What a program can use beyond the board, each with its name and a small drawing, in the
// order they are shown
var FEATURES = [
  ["outputs", "the outputs", "<circle cx='3' cy='8' r='2'/><circle cx='8' cy='8' r='2'/>" +
                             "<circle cx='13' cy='8' r='2'/>"],
  ["screen", "a screen", "<rect x='2.5' y='3.5' width='11' height='9' rx='1.2' fill='none'/>"],
  ["either", "one screen or two", "<rect x='1' y='4' width='6.5' height='8' rx='1' fill='none'/>" +
                                  "<rect x='8.5' y='4' width='6.5' height='8' rx='1' fill='none' " +
                                  "stroke-dasharray='1.6 1.2'/>"],
  ["pair", "two screens", "<rect x='1' y='4' width='6.5' height='8' rx='1' fill='none'/>" +
                          "<rect x='8.5' y='4' width='6.5' height='8' rx='1' fill='none'/>"],
  ["hub", "a screen hub", "<rect x='1' y='2.5' width='4' height='4.5' rx='.6'/>" +
                          "<rect x='6' y='2.5' width='4' height='4.5' rx='.6'/>" +
                          "<rect x='11' y='2.5' width='4' height='4.5' rx='.6'/>" +
                          "<rect x='1' y='9' width='4' height='4.5' rx='.6'/>" +
                          "<rect x='6' y='9' width='4' height='4.5' rx='.6'/>" +
                          "<rect x='11' y='9' width='4' height='4.5' rx='.6'/>"],
  ["strip", "an LED strip", "<path d='M1 10 Q8 4 15 10' fill='none'/><circle cx='4' cy='7.6' r='1.3'/>" +
                            "<circle cx='8' cy='6.5' r='1.3'/><circle cx='12' cy='7.6' r='1.3'/>"],
  ["sound", "a speaker", "<path d='M2 6h3l4-3v10l-4-3H2z'/><path d='M11 5.5q2 2.5 0 5M12.8 3.8" +
                         "q3.4 4.2 0 8.4' fill='none'/>"],
  ["remote", "the IR remote", "<rect x='5' y='1.5' width='6' height='13' rx='2' fill='none'/>" +
                              "<circle cx='8' cy='5' r='1.1'/><circle cx='8' cy='9' r='.9'/>" +
                              "<circle cx='8' cy='11.8' r='.9'/>"],
  ["qwst", "a Qw/ST sensor", "<rect x='3' y='3' width='10' height='10' rx='1.5' fill='none'/>" +
                             "<path d='M5.5 9.5l2-3 1.5 2 1.5-2.5' fill='none'/>"],
  ["analog", "an analog sensor", "<path d='M2 12a6 6 0 0 1 12 0' fill='none'/>" +
                                 "<path d='M8 12l3-5' fill='none'/>"],
  ["motor", "motors", "<circle cx='8' cy='8' r='5.5' fill='none'/><circle cx='8' cy='8' r='1.6'/>" +
                      "<path d='M8 2.5v3M8 10.5v3M2.5 8h3M10.5 8h3' fill='none'/>"],
  ["servo", "servos", "<rect x='2' y='8' width='12' height='6' rx='1' fill='none'/>" +
                      "<path d='M8 8l4-5.5' fill='none'/><circle cx='8' cy='8' r='1.3'/>"],
  ["wifi", "Wi-Fi", "<path d='M1.5 6.5a9 9 0 0 1 13 0M4 9a5.5 5.5 0 0 1 8 0' fill='none'/>" +
                    "<circle cx='8' cy='12' r='1.4'/>"],
  ["button", "the Boot button", "<circle cx='8' cy='8' r='5.5' fill='none'/><circle cx='8' cy='8' " +
                                "r='2.6'/>"]
];

function featureNamed(key) {
  return FEATURES.filter(function (one) { return one[0] === key; })[0];
}

function featureIcon(key) {
  var feature = featureNamed(key);
  var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("viewBox", "0 0 16 16");
  icon.setAttribute("class", "featureicon");
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = feature[2];
  return icon;
}

// What a program uses, from its source for an example and from its opening string on the drive
function usesOf(path) {
  if (DRIVE_USES[path]) return DRIVE_USES[path];
  var example = BOARD_EXAMPLES.filter(function (one) { return one.path === path; })[0];
  return example ? example.uses : [];
}

var ASSETS = "../../../examples/mighty_fx/examples/assets/";

// Frames captured off a board running each example, composed to what its panel showed and scaled
// to the thumbnail's size. Where one exists it is the thumbnail, the drawn one standing in only for
// what has not been captured
var SHOTS = "../../bench/thumbs/";
var CAPTURED = ["acrylic_lixie", "animated_gif_recoloured", "billboard_cased", "bouncing_logo",
                "bus_departures", "carpets_paired", "color_wheel", "crt_terminal", "departure_board",
                "departures_list", "flip_dot_sign", "isometric_flight", "kaleidoscope",
                "lane_control_gantry", "led_matrix", "nixie_tube", "roadworks_sign",
                "scrolling_billboard", "skyline", "split_flap_clock", "split_flap_departures",
                "starfield", "starfield_wall", "status_panel", "traces_scroll", "traces_wall",
                "tram_stop_sign", "trivision_billboard"];

function offeredAt(path) {
  for (var g = 0; g < OFFERED.length; g++) {
    for (var i = 0; i < OFFERED[g][1].length; i++) {
      if ("examples/" + OFFERED[g][1][i][0] === path) return OFFERED[g][1][i];
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

function thumbCanvas(kind, seed) {
  var canvas = document.createElement("canvas");
  canvas.width = THUMB_W;
  canvas.height = THUMB_H;
  canvas.className = "progthumb";
  paintThumb(canvas.getContext("2d"), kind, seed || 1, canvas);
  return canvas;
}

// A repeatable scatter, so a thumbnail is the same every time it is drawn
function scatter(seed) {
  var state = seed * 9301 + 49297;
  return function () {
    state = (state * 9301 + 49297) % 233280;
    return state / 233280;
  };
}

function paintThumb(g, kind, seed, canvas) {
  var W = THUMB_W, H = THUMB_H, x, y, i;
  var chance = scatter(seed);
  function fill(ink) { g.fillStyle = ink; g.fillRect(0, 0, W, H); }
  function dotRow(ink, top, count, size, gap) {
    g.fillStyle = ink;
    for (i = 0; i < count; i++) g.fillRect(3 + i * (size + gap), top, size, size);
  }
  if (kind.indexOf("asset:") === 0 || kind.indexOf("shot:") === 0) {
    fill("#111");
    var src = kind.indexOf("shot:") === 0 ? SHOTS + kind.slice(5) + ".png" : ASSETS + kind.slice(6);
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
    // What the outputs do, as seven lamps on the board's dark
    fill("#1c1f22");
    var inks = {rainbow: ["#ff2d1a", "#ff9022", "#ffd21f", "#22c65a", "#28e0e0", "#2b5cff", "#9a46ff"],
                warm: ["#ffb060", "#ffc27a", "#ff9022", "#ffb060", "#ffc27a", "#ff9022", "#ffb060"],
                mono: ["#ffd9a0", "#3a3f44", "#ffd9a0", "#ffd9a0", "#3a3f44", "#ffd9a0", "#3a3f44"],
                pulse: ["#ffd9a0", "#c9aa7c", "#8a765a", "#4d4336", "#8a765a", "#c9aa7c", "#ffd9a0"],
                dusk: ["#ffe6b0", "#ffe6b0", "#ffe6b0", "#c9aa7c", "#8a765a", "#4d4336", "#3a3f44"],
                level: ["#3a3f44", "#3a3f44", "#22c65a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"],
                bar: ["#2b5cff", "#28e0e0", "#22c65a", "#ffd21f", "#3a3f44", "#3a3f44", "#3a3f44"],
                melody: ["#9a46ff", "#3a3f44", "#ff36c8", "#9a46ff", "#3a3f44", "#2b5cff", "#ff36c8"],
                countdown: ["#ff2d1a", "#ff2d1a", "#ff2d1a", "#22c65a", "#3a3f44", "#3a3f44", "#3a3f44"]};
    var row = inks[kind.slice(6)] || inks.mono;
    for (i = 0; i < 7; i++) {
      g.fillStyle = row[i];
      g.beginPath();
      g.arc(6 + i * 8.6, H / 2, 3.2, 0, Math.PI * 2);
      g.fill();
    }
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
  case "flame":
    fill("#120804");
    for (i = 0; i < 40; i++) {
      var across = 18 + chance() * 28, up = 44 - chance() * (26 - Math.abs(across - 32));
      g.fillStyle = chance() < 0.5 ? "#ff7a1a" : "#ffc27a";
      g.fillRect(across, up, 2, 44 - up);
    }
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
  var kind = offered && CAPTURED.indexOf(file) >= 0 ? "shot:" + file
           : offered ? offered[1] : DRIVE_THUMBS[path] || "flame";
  return thumbCanvas(kind, path.length);
}

// ---- the program page ------------------------------------------------------------------------

var programView = null;

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
  card.onclick = function () {
    boardSet.program = path;
    boardSet.lastProgram = path;
    draw();
  };
  return card;
}

// The picked program large, with what it does, what it needs and what it takes
function programHero(path) {
  var hero = document.createElement("div");
  hero.className = "proghero";
  var big = programThumb(path);
  big.classList.add("big");
  hero.appendChild(big);
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
  hero.appendChild(words);
  return hero;
}

function renderProgramView() {
  programView.textContent = "";
  if (!boardSet.program) return;
  var note = document.createElement("div");
  note.className = "programnote";
  note.appendChild(boardIcon());
  note.appendChild(document.createTextNode(
    "The board runs " + boardSet.program.split("/").pop() + " in place of the effects. They " +
    "are kept, and play if it is missing or stops, when errors.txt says why."));
  programView.appendChild(note);
  programView.appendChild(programHero(boardSet.program));
  programView.appendChild(featureFilter());
  var shown = 0;
  function group(title, paths) {
    var kept = paths.filter(passesFilter);
    if (!kept.length) return;
    shown += kept.length;
    var heading = document.createElement("h4");
    heading.className = "proggroup";
    heading.textContent = title;
    programView.appendChild(heading);
    var grid = document.createElement("div");
    grid.className = "proggrid";
    kept.forEach(function (path) { grid.appendChild(programCard(path)); });
    programView.appendChild(grid);
  }
  group("On the drive", DRIVE_PROGRAMS.map(function (one) { return one[0]; }));
  OFFERED.forEach(function (set) {
    group(set[0], set[1].map(function (entry) { return "examples/" + entry[0]; }));
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
// uses is on. One screen or two is had with either a screen or two, so it has no chip of its own

var unhad = [];

function had(key) { return unhad.indexOf(key) < 0; }

function passesFilter(path) {
  return usesOf(path).every(function (key) {
    return key === "either" ? had("screen") || had("pair") : had(key);
  });
}

function offeredPaths() {
  var offered = DRIVE_PROGRAMS.map(function (one) { return one[0]; });
  OFFERED.forEach(function (set) {
    set[1].forEach(function (entry) { offered.push("examples/" + entry[0]); });
  });
  return offered;
}

function featureFilter() {
  var row = document.createElement("div");
  row.className = "featurefilter";
  var said = document.createElement("span");
  said.textContent = "I have";
  row.appendChild(said);
  var offered = offeredPaths();
  FEATURES.forEach(function (feature) {
    if (feature[0] === "either") return;
    var used = offered.some(function (path) { return usesOf(path).indexOf(feature[0]) >= 0; });
    if (!used) return;
    var chip = document.createElement("button");
    chip.type = "button";
    chip.className = "featurechip" + (had(feature[0]) ? " on" : "");
    chip.dataset.feature = feature[0];
    chip.title = had(feature[0]) ? "Showing programs that use " + feature[1]
                                 : "Hiding programs that need " + feature[1];
    chip.appendChild(featureIcon(feature[0]));
    chip.appendChild(document.createTextNode(feature[1]));
    chip.onclick = function () {
      var at = unhad.indexOf(feature[0]);
      if (at >= 0) unhad.splice(at, 1);
      else unhad.push(feature[0]);
      draw();
    };
    row.appendChild(chip);
  });
  if (unhad.length) {
    var all = document.createElement("button");
    all.type = "button";
    all.className = "featureclear";
    all.textContent = "all of them";
    all.onclick = function () {
      unhad = [];
      draw();
    };
    row.appendChild(all);
  }
  return row;
}

// ---- moving between the two pages, three ways ---------------------------------------------------

var PAGE_WAYS = [["covers", "Two covers"], ["header", "Header: cards"],
                 ["headseg", "Header: one control"], ["headtabs", "Header: tabs off its foot"],
                 ["headsplit", "Header: tabs, split under it"],
                 ["headrow", "Header: a row of its own"],
                 ["binder", "Folder tabs"], ["sheet", "A sheet over"],
                 ["under", "Sheet, offered under the gallery"]];

// The ways that put the two covers in the header, each styled its own way, and those drawing
// them as tabs, whose effects tab holds the way into scenes until there are some
var HEADER_WAYS = ["header", "headseg", "headtabs", "headsplit", "headrow"];
var TAB_WAYS = ["headtabs", "headsplit"];
var pageWay = (location.search.match(/way=(\w+)/) || [])[1] || "covers";
function toEffects() {
  boardSet.program = null;
  draw();
}

// The program shown on arriving is chosen as much as one clicked, so it is the one the tab shows
// once the effects are back
function toProgram() {
  // A drive may hold no program, where the first of the examples is shown
  boardSet.program = boardSet.lastProgram ||
                     (DRIVE_PROGRAMS.length ? DRIVE_PROGRAMS[0][0] : BOARD_EXAMPLES[0].path);
  boardSet.lastProgram = boardSet.program;
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
  var bar = document.getElementById("pageSwitch");
  bar.textContent = "";
  bar.className = "pageswitch " + pageWay + (boardSet.program ? " programmed" : "");
  document.getElementById("galleryOffer").textContent = "";
  var inHeader = document.getElementById("headSwitch");
  inHeader.textContent = "";
  var program = boardSet.program || boardSet.lastProgram;
  var inTheHeader = HEADER_WAYS.indexOf(pageWay) >= 0;
  // Split under the header, the tabs are drawn as the tabs off its foot are
  inHeader.className = "headswitch " + pageWay + (pageWay === "headsplit" ? " headtabs" : "");
  if (pageWay === "covers" || inTheHeader) {
    // Two cards, what runs picked, each showing what it would run: large above the scenes, or
    // small in the header where the page's name is, taking no room from the page
    [["effects", "The effects", "scenes, looks, screens and sound"],
     ["program", "A program", program ? programTitle(program) : "in place of the effects"]]
      .forEach(function (one) {
        // A tab holds the scenes' button, and a button cannot hold another, so a tab is a
        // plain element taking the click and the keyboard
        var tabbed = TAB_WAYS.indexOf(pageWay) >= 0;
        var cover = document.createElement(tabbed ? "div" : "button");
        if (tabbed) {
          cover.setAttribute("role", "button");
          cover.tabIndex = 0;
          cover.onkeydown = function (event) {
            if (event.key === "Enter" || event.key === " ") cover.onclick();
          };
        } else {
          cover.type = "button";
        }
        cover.className = "cover" + ((one[0] === "program") === !!boardSet.program ? " on" : "");
        cover.dataset.page = one[0];
        var face = one[0] === "effects" ? effectsFace()
                 : program ? programThumb(program) : thumbCanvas("stars", 3);
        face.classList.add("coverface");
        cover.appendChild(face);
        var words = document.createElement("span");
        // Small in the header, only a program's name is said, a row of its own having room
        var brief = inTheHeader && pageWay !== "headrow";
        var under = brief && !(one[0] === "program" && program) ? "" : one[2];
        words.innerHTML = "<b>" + one[1] + "</b>" +
                          (under ? "<small>" + escapeHtml(under) + "</small>" : "");
        cover.appendChild(words);
        cover.onclick = one[0] === "effects" ? toEffects : toProgram;
        (inTheHeader ? inHeader : bar).appendChild(cover);
      });
  } else if (pageWay === "binder") {
    // Two tabs joined to the page they open, as a folder's are, above the scenes' own
    [["effects", "Effects"], ["program", "Program"]].forEach(function (one) {
      var tab = document.createElement("button");
      tab.type = "button";
      tab.className = "foldertab" + ((one[0] === "program") === !!boardSet.program ? " on" : "");
      tab.dataset.page = one[0];
      var face = one[0] === "effects" ? effectsFace()
               : program ? programThumb(program) : thumbCanvas("stars", 3);
      face.classList.add("tabface");
      tab.appendChild(face);
      tab.appendChild(document.createTextNode(one[1]));
      tab.onclick = one[0] === "effects" ? toEffects : toProgram;
      bar.appendChild(tab);
    });
  } else {
    // The effects as they are, a strip offering a program above the scenes, or under the
    // gallery; picked, a sheet takes the page, with the way back at its head
    var slot = document.getElementById("galleryOffer");
    if (!boardSet.program) {
      (pageWay === "under" ? slot : bar).appendChild(sheetOffer());
    } else {
      var head = document.createElement("div");
      head.className = "sheethead";
      var back = document.createElement("button");
      back.type = "button";
      back.dataset.page = "effects";
      back.className = "sheetback";
      back.textContent = "\u25c2 Back to the effects";
      back.onclick = toEffects;
      head.appendChild(back);
      var title = document.createElement("b");
      title.textContent = "Running a program";
      head.appendChild(title);
      bar.appendChild(head);
    }
  }
}

// A strip of what programs look like, offering one in the effects' place
function sheetOffer() {
  var offer = document.createElement("button");
  offer.type = "button";
  offer.className = "sheetoffer";
  offer.dataset.page = "program";
  var strip = document.createElement("span");
  strip.className = "filmstrip";
  ["examples/showcase/flip_dot_sign.py", "examples/showcase/nixie_tube.py",
   "examples/screens/graphics/starfield.py", "examples/showcase/split_flap_clock.py",
   "examples/showcase/crt_terminal.py"].forEach(function (path) {
    strip.appendChild(programThumb(path));
  });
  offer.appendChild(strip);
  var said = document.createElement("span");
  said.innerHTML = "<b>Run a program instead</b><small>a sign, a clock, something the effects " +
                   "cannot do. It takes the whole board.</small>";
  offer.appendChild(said);
  offer.onclick = toProgram;
  return offer;
}

function renderTrying() {
  var bar = document.getElementById("pageTrying");
  bar.textContent = "Trying:";
  PAGE_WAYS.forEach(function (way) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = way[0] === pageWay ? "on" : "";
    button.textContent = way[1];
    button.onclick = function () {
      pageWay = way[0];
      draw();
    };
    bar.appendChild(button);
  });
}

(function () {
  // Floating at the foot of the window, so it moves nothing on the page it switches
  var trying = document.createElement("div");
  trying.id = "pageTrying";
  trying.className = "trying floating";
  document.body.appendChild(trying);
  // In the header after the page's name, where one way puts its covers. What follows the name is
  // gathered into one group, so a wide header can set name, tabs and group on a single line
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
  // Under the gallery, above the tabs, where one way offers a program
  var offerSlot = document.createElement("div");
  offerSlot.id = "galleryOffer";
  var looks = document.getElementById("looksStack") || document.getElementById("looks");
  looks.parentNode.insertBefore(offerSlot, looks.nextSibling);
  var bar = document.createElement("div");
  bar.id = "pageSwitch";
  var tabs = document.getElementById("tabs");
  tabs.parentNode.insertBefore(bar, tabs);
  programView = document.createElement("div");
  programView.id = "programView";
  programView.className = "programview";
  var body = document.getElementById("sceneBody");
  body.parentNode.insertBefore(programView, body.nextSibling);
}());

var oneProgramDraw = draw;

draw = function () {
  oneProgramDraw();
  document.body.classList.toggle("programpage", !!boardSet.program);
  document.body.dataset.pageway = pageWay;
  renderTrying();
  renderPageSwitch();
  renderProgramView();
  scenesAsCards();
  scenesInTheTab();
  headerOnOneLine();
  // The effects' live swatch in the tabs is made after the page painted, so it is painted now
  paintAll();
};

// The examples' own pictures, loaded as the page opens, so a thumbnail made from one is drawn
// whole the first time it is shown and never fills in late. Once all are in, the page is drawn
// again for any thumbnail already showing
(function () {
  var sources = [];
  OFFERED.forEach(function (set) {
    set[1].forEach(function (entry) { if (entry[1].indexOf("asset:") === 0) sources.push(entry[1]); });
  });
  Object.keys(DRIVE_THUMBS).forEach(function (path) {
    if (DRIVE_THUMBS[path].indexOf("asset:") === 0) sources.push(DRIVE_THUMBS[path]);
  });
  CAPTURED.forEach(function (name) { sources.push("shot:" + name); });
  var waiting = 0;
  sources.forEach(function (kind) {
    var src = kind.indexOf("shot:") === 0 ? SHOTS + kind.slice(5) + ".png" : ASSETS + kind.slice(6);
    if (thumbImages[src]) return;
    var image = thumbImages[src] = new Image();
    waiting++;
    image.onload = image.onerror = function () {
      waiting--;
      if (!waiting) draw();
    };
    image.src = src;
  });
}());

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
  if (pageWay !== "headsplit") return;
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
  var into = TAB_WAYS.indexOf(pageWay) >= 0 && !state.scenes.length && !boardSet.program &&
             document.querySelector("#headSwitch .cover[data-page=effects]");
  document.body.classList.toggle("scenesintab", !!into);
  if (!into) return;
  var plus = document.querySelector("#tabs .plus");
  if (!plus) return;
  plus.addEventListener("click", function (event) { event.stopPropagation(); });
  into.appendChild(plus);
}

draw();
