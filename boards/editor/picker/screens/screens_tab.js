import {h, replace} from "../dom.js";
import {draw, drawSteps} from "../draw.js";
import {nameShown} from "../drive.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../drive_files.js";
import {LED_PANELS} from "../led_sections.js";
import {OWN_GROUP, foldHead} from "../program.js";
import {setupOn} from "../runs.js";
import {allBodies, apply, slotAt, state, store} from "../scenes.js";
import {drawingInk, mediaArt, panelPreview} from "./screen_art.js";
import {pairControl} from "./screen_pair.js";
import {backlightSetting, drawingCopyTile, lookSettings, showingLine} from "./screen_settings.js";
import {pictureSaid} from "./screen_text.js";
import {
  SCREENS, SCREEN_INKS, SCREEN_NAMES, galleryExamples, pictureTargeting, screenShown, screenUnder,
  screensTabHooks
} from "./screens.js";
import {boardIcon} from "../setup.js";
import {TAB_NAMES, addTab, keptOpen, tabSwatches, tabUnder} from "../tabs.js";

function screenBox(letter) {
  var screen = state.screens[letter];
  var named = screenShown(letter);
  var setup = h("label", {title: "Board setup, shared by every scene"}, boardIcon(),
                screen.there ? sizeChoice(letter) : null);
  var box = h("section", {class: "screenbox", "aria-label": named,
                          style: {"--tint": SCREEN_INKS[letter]}});
  if (!screen.there) {
    return replace(box, h("div", {}, h("h3", {}, named), setup),
      h("button", {type: "button", disabled: !setupOn, onclick: function () {
        screen.there = true;
        screen.shows = null;
        screen.kept = null;
        draw();
      }}, "add this screen"));
  }
  var under = screen.shows ? null : screenUnder(letter);
  var held = screen;
  if (under && under.always) {
    var always = state.always.body.screens[letter];
    held = Object.assign({}, screen, {shows: null, turn: always.turn || 0,
                                      look: always.look || screen.look});
  }
  var frozen = held !== screen;
  return replace(box,
    h("div", {}, h("h3", {}, named), setup,
      h("button", {type: "button", "aria-label": "Remove " + named,
                   title: "Remove this screen from every scene", disabled: !setupOn,
                   onclick: function () { dropScreen(letter); }}, "\u00d7")),
    backlightSetting(held.look.backlight, function (value) { screen.look.backlight = value; },
                     "backlight", "Backlight brightness for " +
                     named.replace("Screen", "screen") + " in this scene", frozen),
    previewInScene(screen, letter),
    pairControl(letter),
    showingLine(screen, letter),
    lookSettings("screen" + letter, held, screen.size, frozen),
    screen.kept ? h("button", {type: "button", "aria-pressed": String(screen.shows === "keep"),
                               title: screen.kept,
                               onclick: function () { screen.shows = "keep"; draw(); }},
                    h("b", {}, "Keep as is"), h("code", {}, screen.kept)) : null);
}

function sizeChoice(letter) {
  var screen = state.screens[letter];
  var offered = (CATALOGUE.board_settings[SCREEN_NAMES[letter].toLowerCase()] || ["2.8", "1.54"])
    .filter(function (inches) { return inches !== "hub"; });
  var choice = h("select", {"aria-label": screenShown(letter) + " panel size",
                            title: "Panel fitted, shared by every scene", disabled: !setupOn,
                            onchange: function () {
                              if (choice.value) screen.size = choice.value;
                              draw();
                            }},
    screen.size ? null : h("option", {value: "", selected: true}, "fitted size"),
    offered.map(function (inches) {
      return h("option", {value: inches, selected: screen.size === inches}, inches + " inch");
    }));
  return choice;
}

function dropScreen(letter) {
  state.screens[letter].there = false;
  store();
  allBodies().forEach(function (held) {
    held.screens[letter].shows = null;
    held.screens[letter].kept = null;
  });
  apply(slotAt(state.at).body);
  draw();
}

function previewInScene(screen, letter) {
  var under = screen.shows ? null : screenUnder(letter);
  if (!under || !under.always) return panelPreview(screen);
  var always = state.always.body.screens[letter];
  return panelPreview(Object.assign({}, screen, {shows: always.shows, turn: always.turn || 0,
                                                 look: always.look || screen.look}),
                      "Always on's picture, which shows here in this scene");
}

function mediaGroups() {
  var groups = [[OWN_GROUP, "your own pictures and drawings", state.media.filter(function (media) {
    return !isExampleMedia(media.name);
  }), false]];
  ["drawings", "pictures"].forEach(function (kind) {
    groups = groups.concat(exampleGroups(kind, state.media));
  });
  return groups.filter(function (group, at) { return !at || group[2].length; });
}

function gallerySaid() {
  return !state.fileHandle ? "open the FX drive to see its pictures and drawings"
       : !state.scanned ? "reading the drive..."
       : state.media.length ? "one set of pictures, each shown on A, B or both"
       : "no pictures on the drive yet. Drop a GIF, PNG, JPEG or drawing onto it";
}

function targeting() {
  return state.hub.on && pictureTargeting.hub ? pictureTargeting.hub : pictureTargeting.screens;
}

function targetButton(target) {
  return h("button", {type: "button", "aria-pressed": String(!!target.pressed),
                      disabled: !!target.disabled, title: target.title, "data-all": !!target.all,
                      style: {"--tint": target.colour},
                      onclick: function () {
                        target.press();
                        draw();
                      }}, target.label);
}

function offCard() {
  var off = targeting().off();
  return h("div", {role: "group", "aria-label": "Off", title: off.title, inert: state.at < 0},
    h("span", {"aria-hidden": "true"}, "Off"), off.targets.map(targetButton));
}

function picturesGallery() {
  var grouped = !!state.fileHandle;
  var groups = grouped ? mediaGroups() : [[OWN_GROUP, "", state.media, false]];
  var examples = grouped && galleryExamples.offer
    ? galleryExamples.offer(groups.slice(1).map(function (group) { return group[0]; })) : null;
  var parts = [];
  groups.forEach(function (group, at) {
    var open = groupOpen(group);
    if (examples && at === 1) parts.push(examples.bar);
    if (examples && examples.dividers[group[0]]) parts.push(examples.dividers[group[0]]);
    if (grouped || !at) {
      parts.push(h("div", {class: "grouphead"},
        grouped ? foldHead(group[0], group[1], open, function () { groupsOpen[group[0]] = !open; })
                : null,
        at ? null : offCard()));
    }
    if (grouped && !open) return;
    parts.push(h("ul", {}, group[2].map(pictureTile),
      group[0] === OWN_GROUP && state.fileHandle
        ? h("li", {}, adderTile("add pictures or drawings",
            {description: "Pictures and drawings the board can play",
             accept: {"image/png": [".gif", ".png", ".jpg", ".jpeg"], "text/x-python": [".py"]}},
            "pictures", /\.(gif|png|jpe?g|py)$/i))
        : null));
  });
  if (examples && groups.length === 1) parts.push(examples.bar);
  return h("section", {class: "screenpictures", "aria-label": "Pictures"}, parts);
}

function pictureTile(media) {
  var name = media.name;
  var colour = targeting().shown(name);
  var description = media.kind === "drawing" && media.drawing.description;
  var tile = h("li", {title: description || name, "data-shown": !!colour,
                      style: {"--shown": colour}},
    pictureFace(media),
    h("div", {role: "group", "aria-label": "Show " + pictureSaid(name)},
      targeting().picture(name).map(targetButton)),
    isExampleMedia(name) ? null : binButton(name, media.kind),
    media.kind === "drawing" && state.fileHandle ? drawingCopyTile(name) : null);
  if (galleryExamples.addToTile) galleryExamples.addToTile(tile, name);
  return tile;
}

function pictureFace(media) {
  var name = media.name;
  var kind = {gif: "gif", folder: "slideshow", drawing: "drawing"}[media.kind];
  var tag = kind ? h("small", {}, kind) : null;
  if (media.kind === "drawing" && !media.thumbHandle) {
    var drawing = media.drawing;
    return h("figure", {"data-made": true, style: {"--colour": drawingInk(drawing, name)}},
      tag,
      h("span", {"aria-hidden": "true", "data-letter": !drawing.icon},
        drawing.icon || drawing.title[0]),
      h("b", {}, drawing.title),
      h("figcaption", {}, h("b", {}, drawing.title)));
  }
  var art = mediaArt(name);
  if (!art || !art.w) {
    return h("figure", {}, tag, h("span", {}, name.split(".").pop()),
             h("figcaption", {}, nameShown(name)));
  }
  var file = nameShown(name);
  var dot = file.lastIndexOf(".");
  var caption = media.kind === "drawing" ? h("b", {}, media.drawing.title) : [
    h("b", {}, media.kind === "folder" ? pictureSaid(name) : dot > 0 ? file.slice(0, dot) : file),
    h("br"),
    [media.kind === "image" && dot > 0 ? file.slice(dot + 1) : null, art.w + " \u00d7 " + art.h]
      .filter(Boolean).join(" \u00b7 ")
  ];
  return h("figure", {"data-fill": media.kind === "drawing", style: {"--w": art.w, "--h": art.h}},
    tag, h("img", {src: art.url, alt: ""}), h("figcaption", {}, caption));
}

var screensTab = h("div", {class: "screenstab"});

function renderScreensTab() {
  var above = screensTabHooks.above ? screensTabHooks.above() : h("p", {}, gallerySaid());
  var hubbed = screensTabHooks.head ? screensTabHooks.head() : null;
  replace(screensTab, above, hubbed || SCREENS.map(screenBox), picturesGallery());
  screensTab.toggleAttribute("data-setup", setupOn);
}

export function swatchCell(shows, art, under) {
  return h("span", {"data-shows": shows,
                    style: {"--picture": art ? (under ? "var(--through), " : "") +
                                               "url(" + art.url + ")" : null}});
}

tabSwatches.screensPanel = function (swatch) {
  swatch.className = "accswatch screenswatch";
  replace(swatch, SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var shown = screen.shows || (under && under.always) || null;
    var art = screen.there && shown && shown !== "keep"
              ? mediaArt(shown, screen.look && screen.look.style) : null;
    var shows = !screen.there ? "absent" : screen.off ? "off" : art ? "picture"
              : shown ? "blank" : under && under.off ? "dark" : "nothing";
    return swatchCell(shows, art, under && under.always);
  }));
  swatch.title = SCREENS.map(function (letter) {
    var screen = state.screens[letter];
    var under = screen.there && !screen.shows ? screenUnder(letter) : null;
    var said = !screen.there ? "not fitted" : screen.off ? "off"
             : screen.shows || (under && under.always ? "Always on's " + under.always : "nothing");
    return SCREENS.length > 1 ? letter + ": " + said : said;
  }).join(", ");
};

tabUnder.screensPanel = function () {
  var fitted = SCREENS.map(function (letter) {
    return state.screens[letter].there ? state.screens[letter].size : "";
  });
  return fitted.some(Boolean)
    ? fitted.map(function (size) { return size ? size + "\"" : "none"; }).join(", ")
    : "no screens";
};

drawSteps.render.push(renderScreensTab);

(function () {
  var after = document.getElementById(LED_PANELS[LED_PANELS.length - 1]);
  after.after(h("details", {class: "panel", id: "screensPanel", open: true},
    h("summary", {}, "Screens"), screensTab));
}());

if (SCREENS.length) {
  TAB_NAMES.screensPanel = "Screens";
  addTab("screensPanel");
  keptOpen("screensPanel");
} else {
  document.getElementById("screensPanel").hidden = true;
}
