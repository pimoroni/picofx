import {draw} from "../00_draw.js";
import {setupOn} from "../03_runs.js";
import {allBodies, apply, frozen, slotAt, state, store} from "../04_scenes.js";
import {boardIcon} from "../08_setup.js";
import {nameShown} from "../18_drive.js";
import {OWN_GROUP, foldHead} from "../22_program.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../26_drive_files.js";
import {
  SCREENS, SCREEN_NAMES, assetSteps, screenButton, screenParts, screenShown, screenUnder,
  screensHeadSteps, screensPaired
} from "./12_screens.js";
import {mediaArt, panelPreview} from "./13_screen_art.js";
import {drawingCopyTile, lightRow, lookSections, showingLine} from "./16_screen_settings.js";

// ---- the Screens tab ----------------------------------------------------------------------------
// Each screen's preview in the scene on show, and the gallery of the drive's pictures and drawings.

// A screen's preview. One the scene shows nothing on shows Always on's picture faded where the board
// plays it there, in Always on's own settings
function previewInScene(screen, letter) {
  var under = screen.shows ? null : screenUnder(letter);
  if (!under || !under.always) return panelPreview(screen);
  var always = state.always.body.screens[letter];
  var drawing = panelPreview(Object.assign({}, screen, {shows: always.shows, turn: always.turn || 0,
                                                        look: always.look || screen.look}));
  drawing.classList.add("under");
  drawing.title = "Always on's picture, which shows here in this scene";
  return drawing;
}

// The gallery's pictures by group: the user's own, then the example drawings' groups and the
// example pictures'
function mediaGroups() {
  var groups = [[OWN_GROUP, "your own pictures and drawings", state.media.filter(function (media) {
    return !isExampleMedia(media.name);
  }), false]];
  ["drawings", "pictures"].forEach(function (kind) {
    groups = groups.concat(exampleGroups(kind, state.media));
  });
  // The user's own group stays where it is empty, being where pictures are added
  return groups.filter(function (group, at) { return !at || group[2].length; });
}

function renderAssets() {
  var box = document.getElementById("assets");
  box.textContent = "";
  document.getElementById("screensSays").textContent = !state.fileHandle
    ? "open the FX drive to see its pictures and drawings"
    : !state.scanned
      ? "reading the drive..."
      : state.media.length
        ? "one set of pictures, each shown on A, B or both"
        : "no pictures on the drive yet. Drop a GIF, PNG, JPEG or drawing onto it";
  // Grouped once the drive is open, the user's own always heading the gallery
  var grouped = !!state.fileHandle;
  var groups = grouped ? mediaGroups() : [[OWN_GROUP, "", state.media, false]];
  // In a scene, Off is a card made small at the end of the first heading, as Nothing is in the
  // looks, so it is never folded away. Without headings it has a line of its own. On the Always
  // on tab it keeps its place unseen, so the gallery does not move between tabs
  if (!grouped) {
    var alone = document.createElement("div");
    alone.className = "offhead";
    alone.appendChild(offCard());
    box.appendChild(alone);
  }
  groups.forEach(function (group, at) {
    var open = groupOpen(group);
    if (grouped) {
      var fold = foldHead(group[0], group[1], open, function () {
        groupsOpen[group[0]] = !open;
      });
      if (at === 0) {
        var head = document.createElement("div");
        head.className = "offhead";
        head.appendChild(fold);
        head.appendChild(offCard());
        box.appendChild(head);
      } else {
        box.appendChild(fold);
      }
    }
    if (grouped && !open) return;
    group[2].forEach(assetTile);
    if (group[0] === OWN_GROUP) adder();
  });
  assetSteps.forEach(function (step) { step(); });

  // The small Off card, black, whose buttons turn a screen off in this scene. A hub gives it its
  // positions' buttons in place of these
  function offCard() {
    var cell = document.createElement("div");
    cell.className = "card nothing small offasset";
    cell.title = "Turn a screen off in this scene";
    if (state.at < 0) cell.style.visibility = "hidden";
    cell.innerHTML = "<div class='face'>Off</div>";
    var pick = document.createElement("div");
    pick.className = "pick";
    SCREENS.forEach(function (letter) {
      var screen = state.screens[letter];
      var button = document.createElement("button");
      button.textContent = screenButton(letter);
      button.className = screen.off ? "lit" + (letter === "B" ? " b" : "") : "";
      button.disabled = !screen.there;
      button.onclick = function () {
        screen.off = !screen.off;
        if (screen.off) screen.shows = null;
        draw();
      };
      pick.appendChild(button);
    });
    cell.appendChild(pick);
    return cell;
  }

  function adder() {
    if (state.fileHandle)
      box.appendChild(adderTile("add pictures or drawings",
        {description: "Pictures and drawings the board can play",
         accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"], "text/x-python": [".py"]}},
        "pictures", /\.(gif|png|jpe?g|py)$/i));
  }

  function assetTile(media) {
    var name = media.name;
    var on = {};
    SCREENS.forEach(function (l) {
      on[l] = state.screens[l].there && state.screens[l].shows === name;
    });
    var cell = document.createElement("div");
    cell.className = "asset" + (on.A && on.B ? " onAB" : on.A ? " onA" : on.B ? " onB" : "");
    cell.dataset.name = name;
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
    label.textContent = nameShown(name);
    face.appendChild(label);
    var pick = document.createElement("div");
    pick.className = "pick";
    SCREENS.forEach(function (letter) {
      var button = document.createElement("button");
      button.textContent = screenButton(letter);
      var lit = on[letter];
      button.className = lit ? "lit" + (letter === "B" ? " b" : "") : "";
      button.disabled = !state.screens[letter].there;
      if (button.disabled) button.style.opacity = ".3";
      button.onclick = function () {
        // Tapping the lit one again takes the picture off this scene's screen, falling back to
        // what the file said where there is something to go back to. The screen then shows
        // what Always on shows there, or goes dark where another scene uses it. A pair's second
        // screen shows what its first does, so either button changes the first
        var screen = state.screens[screensPaired() ? SCREENS[0] : letter];
        screen.shows = screen.shows !== name ? name
                     : screen.kept ? "keep" : null;
        screen.off = false;
        draw();
      };
      pick.appendChild(button);
    });
    cell.appendChild(pick);
    // An example keeps no bin here, as flashing the board's examples again brings it back. Where
    // the board's examples can be discovered, discover/screens/29_discover_screens.js gives it one
    if (!isExampleMedia(name)) cell.appendChild(binButton(name, media.kind));
    if (media.kind === "drawing" && state.fileHandle) cell.appendChild(drawingCopyTile(name));
    box.appendChild(cell);
  }
}

// Put the board's chip beside what is the board's, not before a box's name. That is a screen's
// panel size in its band, the way the hub is wired in its band, and each position's panel size
function renderScreensTab() {
  renderScreensParts();
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
    fact.title = "Board setup, shared by every scene";
    band.insertBefore(fact, size);
    fact.appendChild(chip);
    fact.appendChild(size);
    band.title = "";
  });
}
screenParts.renderTab = renderScreensTab;

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
    head.appendChild(document.createTextNode(screenShown(letter)));
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

    // Taking the screen out is the only way to have none, as a screen showing nothing would
    // say the same thing twice
    var drop = document.createElement("button");
    drop.className = "drop";
    drop.textContent = "\u00d7";
    drop.title = "Remove this screen from every scene";
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
    var offered = (CATALOGUE.board_settings[SCREEN_NAMES[letter].toLowerCase()] || ["2.8", "1.54"])
      .filter(function (inches) { return inches !== "hub"; });
    if (!screen.size) {
      var quiet = document.createElement("option");
      quiet.value = "";
      quiet.textContent = "fitted size";
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
    size.title = "Panel fitted, shared by every scene";
    head.insertBefore(size, drop);

    body.appendChild(previewInScene(screen, letter));

    // The look's sections, what it shows above them, and its backlight across the top. A screen
    // showing Always on's picture plays it in Always on's settings, so it shows those, greyed
    var under = screen.shows ? null : screenUnder(letter);
    var held = screen;
    if (under && under.always) {
      var always = state.always.body.screens[letter];
      held = Object.assign({}, screen, {shows: null, turn: always.turn || 0,
                                        look: always.look || screen.look});
    }
    var sections = lookSections("screen" + letter, held, screen.size);
    var light = lightRow(held.look.backlight, function (value) {
      screen.look.backlight = value;
    }, "backlight", "Backlight brightness for " + screenShown(letter).replace("Screen", "screen") + " in this scene");
    if (held !== screen) {
      frozen(sections);
      frozen(light);
    }
    body.appendChild(sections);
    body.insertBefore(showingLine(screen, letter), body.querySelector(".looksettings"));
    body.insertBefore(light, body.firstChild);

    // What the file already says for this screen, where the picker did not write it
    // and no picture can stand for it. It is a line of its own under the settings
    if (screen.kept) {
      var keep = document.createElement("button");
      keep.className = "keep" + (screen.shows === "keep" ? " picked" : "");
      keep.title = screen.kept;
      keep.innerHTML = "<b>Keep as is</b><code>" + screen.kept + "</code>";
      keep.onclick = function () { screen.shows = "keep"; draw(); };
      side.appendChild(keep);
    }
    box.appendChild(side);
  });
}

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
    band.title = "Board setup, shared by every scene";
  });
  // Whether a screen is fitted and its size are the board's
  if (!setupOn) {
    head.querySelectorAll(".screen-box h3 select, .screen-box h3 .drop, .body.adding button")
      .forEach(function (control) { control.disabled = true; });
  }
}

function renderScreensHead() {
  if (!screensHeadSteps.instead.some(function (step) { return step(); })) {
    document.getElementById("screensHead").classList.remove("hubbed");
    renderScreenBoxes();
  }
  screensHeadSteps.after.forEach(function (step) { step(); });
}
