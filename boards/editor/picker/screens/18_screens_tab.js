import {draw} from "../00_draw.js";
import {state} from "../04_scenes.js";
import {boardIcon} from "../08_setup.js";
import {nameShown} from "../18_drive.js";
import {OWN_GROUP, foldHead} from "../22_program.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../26_drive_files.js";
import {SCREENS, assetSteps, screenButton, screenUnder, screensPaired} from "./12_screens.js";
import {mediaArt, panelPreview, renderScreensParts} from "./13_screen_art.js";
import {drawingCopyTile} from "./16_screen_settings.js";

// ---- the Screens tab ----------------------------------------------------------------------------
// Each screen's preview in the scene on show, and the gallery of the drive's pictures and drawings.

// A screen's preview. One the scene shows nothing on shows Always on's picture faded where the board
// plays it there, in Always on's own settings
export function previewInScene(screen, letter) {
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

export function renderAssets() {
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
export function renderScreensTab() {
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
