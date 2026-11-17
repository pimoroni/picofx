import {h, replace} from "../dom.js";
import {draw} from "../draw.js";
import {nameShown} from "../drive.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../drive_files.js";
import {OWN_GROUP, foldHead} from "../program.js";
import {allBodies, apply, frozen, slotAt, state, store} from "../scenes.js";
import {mediaArt, panelPreview} from "./screen_art.js";
import {drawingCopyTile, lightRow, lookSections, showingLine} from "./screen_settings.js";
import {
  SCREENS, SCREEN_NAMES, assetSteps, bandFact, screenButton, screenParts, screenShown, screenUnder,
  screensHeadSteps, screensPaired
} from "./screens.js";
import {BOARD_SETTING_SAYS, boardButton, boardIcon, removeButton} from "../setup.js";

// ---- the Screens tab ----------------------------------------------------------------------------
// Each screen's preview in the scene on show, and the gallery of the drive's pictures and drawings.

// A screen's preview. One the scene shows nothing on shows Always on's picture in the striped
// frame, where the board plays it there in Always on's own settings
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

// The gallery's groups, the user's own first and then the example drawings' and pictures'
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

// The small Off card, black, whose buttons turn a screen off in this scene. A hub gives it
// buttons for its groups and positions in place of these
function offCard() {
  // With no screen fitted there is nothing to turn off, and the card keeps its place unseen
  var fitted = (state.hub && state.hub.on) ||
               SCREENS.some(function (letter) { return state.screens[letter].there; });
  return h("div", {
    className: "card nothing small offasset", title: "Turn a screen off in this scene",
    style: {visibility: state.at < 0 || !fitted ? "hidden" : null}
  }, h("div", {className: "face"}, "Off"),
     h("div", {className: "pick", role: "group", "aria-label": "Off"},
       SCREENS.map(function (letter) {
       var screen = state.screens[letter];
       return h("button", {
         className: screen.off ? "lit" + (letter === "B" ? " b" : "") : "",
         "aria-pressed": String(!!screen.off), disabled: !screen.there,
         onclick: function () {
           screen.off = !screen.off;
           if (screen.off) screen.shows = null;
           draw();
         }
       }, screenButton(letter));
     })));
}

// A picture or drawing in the gallery, with a button for each screen to show it on
function assetTile(media) {
  var name = media.name;
  var on = {};
  SCREENS.forEach(function (l) {
    on[l] = state.screens[l].there && state.screens[l].shows === name;
  });
  var art = mediaArt(name);
  return h("div", {
    className: "asset" + (on.A && on.B ? " onAB" : on.A ? " onA" : on.B ? " onB" : ""),
    "data-name": name, title: name
  }, h("div", {
       className: "face",
       style: {background: art ? "repeating-conic-gradient(#e8e4dc 0% 25%, #cbc5bb 0% 50%) " +
                                 "0 0/12px 12px" : null}
     }, // The extension stands in only until the picture arrives
        art ? h("img", {src: art.url}) : name.split(".").pop(),
        media.kind === "image" ? null
          : h("span", {className: "kind"}, media.kind === "folder" ? "slideshow"
                                           : media.kind === "drawing" ? "drawing" : "gif"),
        h("div", {className: "label"}, nameShown(name))),
     h("div", {className: "pick", role: "group", "aria-label": "Show " + nameShown(name)},
       SCREENS.map(function (letter) {
       var lit = on[letter];
       return h("button", {
         className: lit ? "lit" + (letter === "B" ? " b" : "") : "",
         "aria-pressed": String(!!lit), disabled: !state.screens[letter].there,
         style: {opacity: state.screens[letter].there ? null : ".3"},
         onclick: function () {
           // Tapping the lit one again takes the picture off this scene's screen, back to what the
           // file said where there is something to go back to. A pair's second screen shows what
           // its first does, so either button changes the first
           var screen = state.screens[screensPaired() ? SCREENS[0] : letter];
           screen.shows = screen.shows !== name ? name
                        : screen.kept ? "keep" : null;
           screen.off = false;
           draw();
         }
       }, screenButton(letter));
     })),
     // An example keeps no bin here, since flashing the board's examples again brings it back
     isExampleMedia(name) ? null : binButton(name, media.kind),
     media.kind === "drawing" && state.fileHandle ? drawingCopyTile(name) : null);
}

function renderAssets() {
  document.getElementById("screensSays").textContent = !state.fileHandle
    ? "open the FX drive to see its pictures and drawings"
    : !state.scanned
      ? "reading the drive..."
      : state.media.length
        ? SCREENS.length > 1 ? "one set of pictures, each shown on A, B or both"
                             : "pictures to show on the screen"
        : "no pictures on the drive yet. Drop a GIF, PNG, JPEG or drawing onto it";
  // Grouped once the drive is open, and the user's own group always heads the gallery
  var grouped = !!state.fileHandle;
  var groups = grouped ? mediaGroups() : [[OWN_GROUP, "", state.media, false]];
  // In a scene, Off is a card made small at the end of the first heading, as Nothing is in the
  // looks, so it is never folded away. Without headings it has a line of its own. On the Always
  // on tab it keeps its place unseen, so the gallery does not move between tabs
  var parts = grouped ? [] : [h("div", {className: "offhead"}, offCard())];
  groups.forEach(function (group, at) {
    var open = groupOpen(group);
    if (grouped) {
      var fold = foldHead(group[0], group[1], open, function () {
        groupsOpen[group[0]] = !open;
      });
      parts.push(at === 0 ? h("div", {className: "offhead"}, fold, offCard()) : fold);
    }
    if (grouped && !open) return;
    parts = parts.concat(group[2].map(assetTile));
    if (group[0] === OWN_GROUP && state.fileHandle) {
      parts.push(adderTile("add pictures or drawings",
        {description: "Pictures and drawings the board can play",
         accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"], "text/x-python": [".py"]}},
        "pictures", /\.(gif|png|jpe?g|py)$/i));
    }
  });
  replace(document.getElementById("assets"), parts);
  assetSteps.forEach(function (step) { step(); });
}

// The tab's head and its pictures
function renderScreensTab() {
  renderScreensHead();
  renderAssets();
}
screenParts.renderTab = renderScreensTab;

// Draw a box for each screen port
function renderScreenBoxes() {
  replace(document.getElementById("screensHead"), SCREENS.map(screenBox));
}

// Take a screen off the board. Every scene's choice for it goes too, since nothing is left to
// show them
function takeScreenOff(letter) {
  state.screens[letter].there = false;
  store();
  allBodies().forEach(function (held) {
    held.screens[letter].shows = null;
    held.screens[letter].kept = null;
  });
  apply(slotAt(state.at).body);
  draw();
}

// A screen's box, its band naming it over its body, or the way to add it where it is not fitted.
// Whether a screen is fitted and its size are the board's, so the band wears the board's chip,
// beside the size where there is one
function screenBox(letter) {
  var screen = state.screens[letter];
  // Check if the screen is not fitted, so it offers to be added and shows nothing at first
  if (!screen.there) {
    var add = boardButton("add this screen");
    add.onclick = function () {
      screen.there = true;
      screen.shows = null;
      screen.kept = null;
      draw();
    };
    return h("div", {className: "screen-box " + letter.toLowerCase()},
             h("h3", {title: BOARD_SETTING_SAYS}, boardIcon(), screenShown(letter),
               h("small", {className: "bandnone"}, "not fitted")),
             h("div", {className: "body adding"}, add));
  }

  // The sizes a panel can be, leaving out the catalogue's hub, which is no panel size
  var offered = (CATALOGUE.board_settings[SCREEN_NAMES[letter].toLowerCase()] || ["2.8", "1.54"])
    .filter(function (inches) { return inches !== "hub"; });
  var size = h("select", {
    className: "inband", title: "Panel fitted, shared by every scene",
    name: "screenSize", "aria-label": "Panel fitted",
    onchange: function () {
      if (size.value) screen.size = size.value;
      draw();
    }
  }, screen.size ? null : h("option", {value: "", selected: true}, "fitted size"),
     offered.map(function (inches) {
       return h("option", {value: inches, selected: screen.size === inches}, inches + " inch");
     }));

  // The look's sections, what it shows above them, and its backlight across the top. A screen
  // showing Always on's picture plays it in Always on's settings, so it shows those, greyed
  var under = screen.shows ? null : screenUnder(letter);
  var held = screen;
  if (under && under.always) {
    var always = state.always.body.screens[letter];
    held = Object.assign({}, screen, {shows: null, turn: always.turn || 0,
                                      look: always.look || screen.look});
  }
  var preview = previewInScene(screen, letter);
  var sections = lookSections("screen" + letter, held, screen.size);
  var light = lightRow(held.look.backlight, function (value) {
    screen.look.backlight = value;
  }, "backlight", "Backlight brightness for " + screenShown(letter).replace("Screen", "screen") + " in this scene");
  if (held !== screen) {
    frozen(sections);
    frozen(light);
  }
  var body = h("div", {className: "body"}, light, preview, sections);
  body.insertBefore(showingLine(screen, letter), body.querySelector(".looksettings"));

  return h("div", {className: "screen-box " + letter.toLowerCase()},
           h("h3", {title: ""}, screenShown(letter), bandFact(size),
             // Taking the screen out is the only way to have none, so the size list has no "none"
             removeButton("screen", function () { takeScreenOff(letter); })),
           body,
           // A line the file had for this screen that the picker did not write or match
           screen.kept ? h("button", {
             className: "keep" + (screen.shows === "keep" ? " picked" : ""), title: screen.kept,
             "aria-pressed": String(screen.shows === "keep"),
             onclick: function () { screen.shows = "keep"; draw(); }
           }, h("b", {}, "Keep as is"), h("code", {}, screen.kept)) : null);
}

// ---- drawing the tab -------------------------------------------------------------------------

function renderScreensHead() {
  if (!screensHeadSteps.instead.some(function (step) { return step(); })) {
    document.getElementById("screensHead").classList.remove("hubbed");
    renderScreenBoxes();
  }
  screensHeadSteps.after.forEach(function (step) { step(); });
}
