import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "./draw.js";
import {renderPreview} from "./file_preview.js";
import {BOARD, lookNamed, toggle} from "./looks.js";
import {featureIcon} from "./program.js";
import {runs} from "./runs.js";
import {
  addScene, bodyParts, capture, renderSceneAside, sceneAfter, sceneHooks, sceneLoops, sceneMark,
  sceneMarked, sceneNameProblem, sceneRestarts, sceneShowsAgain, spanTray, state, store,
  stretchPlaying, switchTo
} from "./scenes.js";
import {TAB_NAMES} from "./tabs.js";

// ---- the scene tray -----------------------------------------------------------------------------
// The row of scene cards, each with its colour, its time or what it waits for, and the icons of
// the parts it sets.

// What a scene's card says under its name, its time or that it waits. The scene after is named
// only where it is chosen, since a time implies the next in order
function sceneTurn(scene) {
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var turn = scene.waits ? "waits"
           : scene.seconds + "s" + (after === scene ? ", again" : after === inOrder ? ""
                                                    : ", then " + after.name);
  return turn + (sceneRestarts(scene) && !sceneLoops(scene) ? ", from the start" : "");
}

// ---- each scene's colour and the parts it sets ----------------------------------------------
// Each scene has a colour of its own, its tab's band and tint and its name wherever the page names
// it, so what the page says about a scene leads back to its tab. Always on has a neutral grey

// The colours of the Aye Arr Remote's number buttons, 1 to 9, from its artwork, and the rainbow
// round its 0. Scene 1 takes button 1, so a scene's colour is the button that goes to it. Scene
// 10 takes 0, and a later scene has no button and a neutral colour
export var REMOTE_COLOURS = ["#ed1c24", "#00a651", "#2e3192", "#00aeef", "#ec008c", "#fff200",
                      "#fbad5d", "#ffffff", "#84c1ff"];
export var REMOTE_RAINBOW = ["#ed1c24", "#f7941d", "#fff200", "#8dc63f", "#00a651", "#00aeef",
                      "#0072bc", "#2e3192", "#92278f", "#ec008c"];
var ALWAYS_COLOUR = "#8f8a82";
var UNNUMBERED_COLOUR = "#b9b3a9";

// A scene's colour, its number button's, which moves with the scene's place in the order
function sceneColour(scene) {
  if (!scene) return ALWAYS_COLOUR;
  var at = state.scenes.indexOf(scene);
  return at < 9 ? REMOTE_COLOURS[at] : UNNUMBERED_COLOUR;
}

// A scene's band, the background along the top of its card and its frame's tab. The remote's
// white is a light grey, since white does not show on the page, and button 0's is its rainbow
function sceneBand(scene) {
  if (scene && state.scenes.indexOf(scene) === 9)
    return "linear-gradient(90deg, " + REMOTE_RAINBOW.join(", ") + ")";
  var colour = sceneColour(scene) === "#ffffff" ? "#d9d6d0" : sceneColour(scene);
  return "linear-gradient(" + colour + ", " + colour + ")";
}

// A scene's outline colour, a darker shade where its colour is too pale to show on the page
function sceneEdge(scene) {
  return scene && sceneIsPale(scene)
    ? "color-mix(in srgb, " + sceneColour(scene) + " 72%, #2b2a28)" : sceneColour(scene);
}

// Check if a scene's colour is too pale to show against the page, as the remote's white and
// yellow are, by its luma
function sceneIsPale(scene) {
  var hex = sceneColour(scene).replace("#", "");
  var red = parseInt(hex.slice(0, 2), 16);
  var green = parseInt(hex.slice(2, 4), 16);
  var blue = parseInt(hex.slice(4, 6), 16);
  return 0.299 * red + 0.587 * green + 0.114 * blue > 200;
}

// A dark shade of a scene's colour, which reads on its tint and on the page
function sceneShade(scene) {
  return "color-mix(in srgb, " + sceneColour(scene) + " 65%, #2b2a28)";
}

// Each part's icon, the drawing the programs page gives the same thing, so the two pages agree.
// A part the programs page has no drawing for gives its own in PART_DRAWINGS, on the same grid
var PART_FEATURES = {lights: "outputs", strip: "strip", screens: "screen", hub: "hub",
                     sound: "sound", remote: "remote"};
export var PART_DRAWINGS = {};

function partIcon(key) {
  if (PART_FEATURES[key]) return featureIcon(PART_FEATURES[key]);
  return h("svg:svg", {viewBox: "0 0 24 24", class: "featureicon", "aria-hidden": "true",
                       html: PART_DRAWINGS[key]});
}

// The parts of the board a slot's body sets itself, each as [icon, name]. A body's parts add
// their own, each saying from its share of the body whether it is set. always= is whether the
// body is Always on's
function partsSet(body, always) {
  var parts = [];
  function plays(list) {
    return list.some(function (run) {
      return run.lamps.some(function (lamp, at) { return stretchPlaying(body, run.name, at); });
    });
  }
  var outputs = runs.filter(function (run) { return !run.strip && run.lamps.length; });
  if (outputs.length && plays(outputs)) parts.push(["lights", BOARD.output_words.tab]);
  // One icon for the strips, as nothing in it could say which. Its tip names those that play
  var strips = runs.filter(function (run) { return run.strip && run.there && plays([run]); });
  if (strips.length) {
    parts.push(["strip", strips.map(function (run) {
      return TAB_NAMES[run.name + "Panel"] || run.label;
    }).join(", ")]);
  }
  bodyParts.forEach(function (part) {
    var set = part.sets && part.sets(body, always);
    if (set) parts.push(set);
  });
  return parts;
}

// What the Always on tab says it plays, its looks, pictures and sounds by name, which is empty
// where it plays nothing yet
function alwaysSays(body) {
  var names = [];
  function add(name) { if (name && names.indexOf(name) < 0) names.push(name); }
  Object.keys(body.runs).forEach(function (name) {
    body.runs[name].sections.forEach(function (section) {
      var look = lookNamed(section.look);
      if (look) add(look.name);
    });
  });
  bodyParts.forEach(function (part) { if (part.named) part.named(body).forEach(add); });
  if (!names.length) return "";
  return names.length <= 2 ? names.join(", ") : names[0] + " and " + (names.length - 1) + " more";
}

// The id of a scene's tab, Always on's being which= -1
function sceneTabId(which) {
  return which < 0 ? "sceneTabAlways" : "sceneTab" + which;
}

// The scene before or after with the arrow keys, from Always on to the last scene without
// wrapping, or the first or last with Home and End. The keyboard stays on the tab shown
function stepScenes(event, which) {
  var last = state.scenes.length - 1;
  var to = {ArrowRight: Math.min(last, which + 1), ArrowDown: Math.min(last, which + 1),
            ArrowLeft: Math.max(-1, which - 1), ArrowUp: Math.max(-1, which - 1),
            Home: -1, End: last}[event.key];
  if (to === undefined) return;
  event.preventDefault();
  if (to !== state.at) switchTo(to);
  document.getElementById(sceneTabId(state.at)).focus();
}

function sceneTab(which, slot, name, says) {
  var here = state.at === which;
  var body = here ? capture() : slot.body;
  var scene = which < 0 ? null : slot;
  if (which < 0) says = alwaysSays(body);

  // An icon for each part the scene sets itself, in a shade of its colour
  var parts = h("span", {className: "cardparts"},
                h("span", {className: "partsset", style: {color: sceneShade(scene)}},
                  partsSet(body, which < 0).map(function (part) {
                    var icon = partIcon(part[0]);
                    icon.prepend(h("svg:title", {}, part[1]));
                    return icon;
                  })));
  var under = h("small", {className: "says"}, says || null);

  // A scene's card is three rows, its name, what it sets, and how it ends beside its remote
  // number. Always on's is its name, what it is for and what it plays, then what it sets.
  // The name is cut short where it is long, and the whole of it is in the card's tip
  var tab = h("button", {
    className: "tab" + (here ? " on" : "") + (which < 0 ? " always" : "") +
               (scene && sceneIsPale(scene) ? " pale" : ""),
    // The scene's colour is its tab's band and tint, and the selected tab is ringed as the page
    // rings anything chosen
    style: {"--scene": sceneColour(scene), "--band": scene ? sceneBand(scene) : null},
    title: name,
    // A tab of the scenes' tablist, only the chosen one in the page's tab order
    role: "tab", id: sceneTabId(which), "aria-selected": String(here),
    "aria-controls": "sceneBody", tabindex: here ? "0" : "-1",
    onclick: function () { if (state.at !== which) switchTo(which); },
    onkeydown: function (event) { stepScenes(event, which); }
  }, h("b", {}, h("span", {className: "cardname"}, name), which >= 0 ? grip() : null),
     which < 0 ? [h("small", {className: "role"}, "Plays under every scene"), says ? under : null,
                  parts]
               : [parts, h("span", {className: "cardturn"}, under, remoteBadges(scene))]);
  tab.draggable = which >= 0;

  if (which >= 0) {
    tab.ondragstart = function (e) {
      carriedTab = which;
      tab.classList.add("carried");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", String(which));
    };
    tab.ondragend = function () { carriedTab = null; draw(); };
    tab.ondragover = function (e) {
      if (carriedTab === null || carriedTab === which) return;
      e.preventDefault();
      tab.classList.add("landing");
    };
    tab.ondragleave = function () { tab.classList.remove("landing"); };
    tab.ondrop = function (e) {
      e.preventDefault();
      if (carriedTab === null || carriedTab === which) return;
      store();
      // The scene being edited is followed by identity, since moving any tab shifts
      // the numbers of the ones it passes
      var editing = state.at >= 0 ? state.scenes[state.at] : null;
      var moved = state.scenes.splice(carriedTab, 1)[0];
      state.scenes.splice(which, 0, moved);
      state.at = editing ? state.scenes.indexOf(editing) : -1;
      carriedTab = null;
      draw();
    };
  }
  return tab;
}

// The grip at the end of a scene card's name, which says the card is moved by dragging it
function grip() {
  return h("svg:svg", {class: "grip", viewBox: "0 0 8 12", "aria-hidden": "true",
                       html: "<title>Drag to move this scene</title>" +
                             "<circle cx='2' cy='2' r='1.1'/><circle cx='6' cy='2' r='1.1'/>" +
                             "<circle cx='2' cy='6' r='1.1'/><circle cx='6' cy='6' r='1.1'/>" +
                             "<circle cx='2' cy='10' r='1.1'/><circle cx='6' cy='10' r='1.1'/>"});
}

// Each of the remote's number buttons that goes to a scene, drawn as the remote draws it, or null
// where none does
function remoteBadges(scene) {
  var numbers = sceneHooks.numbers(scene);
  if (!numbers.length) return null;
  return h("span", {className: "irbadges"}, numbers.map(function (number) {
    // The white button's ring is drawn in a light grey, which shows on a card
    return h("span", {
      className: "irbadge" + (number ? "" : " zero"),
      title: "Press " + number + " on the remote for this scene",
      style: {"--ring": !number ? null : number === 8 ? "#cfccc6" : REMOTE_COLOURS[number - 1]}
    }, String(number));
  }));
}

var carriedTab = null;

// The field for a scene's name, marked where the name breaks a rule
function sceneNameField(scene) {
  // The last name left in the field that broke no rule, which the scene goes back to if it is
  // left with one that does. It is kept with the scene, as a draw makes the field afresh while it
  // is being typed in, and a name half typed is not taken for it
  if (scene.goodName === undefined && !sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
  var field = h("input", {
    type: "text", value: scene.name, title: "Scene name", "data-focus": "scene-name",
    oninput: function () {
      // The brackets and the colon are the heading's own punctuation
      scene.name = field.value.replace(/[\[\]:]/g, "");
      if (field.value !== scene.name) field.value = scene.name;
      marked();
      renderScenes();
      renderPreview();
    },
    onchange: function () {
      scene.name = scene.name.trim();
      if (!sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
      else if (scene.goodName) scene.name = scene.goodName;
      draw();
    }
  });
  function marked() {
    var problem = sceneNameProblem(scene, scene.name);
    field.classList.toggle("invalid", !!problem);
    field.title = problem || "Scene name";
  }
  marked();
  return field;
}

// How a scene ends, shown for a time or waiting. A waiting scene has no time and no scene after
function sceneEnds(scene) {
  var ends = h("select", {
    className: "sceneends",
    onchange: function () {
      scene.waits = ends.value === "waits";
      draw();
    }
  }, h("option", {value: "shows", selected: !scene.waits}, "shows for"),
     h("option", {value: "waits", selected: scene.waits}, "waits"));
  return ends;
}

// A scene's time, the seconds it shows for and what follows them
function sceneSeconds(scene) {
  var seconds = h("input", {
    type: "number", min: 1, value: scene.seconds, "data-focus": "scene-seconds",
    onchange: function () {
      scene.seconds = Math.max(1, Number(seconds.value) || 1);
      draw();
    }
  });
  return [seconds, h("span", {className: "sunit"},
                     state.scenes.length === 1 ? "s, then itself" : "s, then")];
}

// The scene after, the next in order unless another is chosen, which can be this one again
function sceneThen(scene) {
  var inOrder = state.scenes[(state.at + 1) % state.scenes.length];
  var chosen = scene.then && sceneMarked(scene.then) && sceneMarked(scene.then) !== inOrder
             ? scene.then : "";
  var then = h("select", {
    className: "scenethen",
    title: "The scene after this one, the next in order unless another is chosen",
    onchange: function () {
      scene.then = then.value || null;
      draw();
    }
  }, h("option", {value: "", selected: chosen === ""}, "the next scene"),
     state.scenes.filter(function (other) { return other !== inOrder; }).map(function (other) {
       var mark = sceneMark(other);
       return h("option", {value: mark, selected: chosen === mark},
                other === scene ? "itself" : other.name);
     }));
  return then;
}

// Whether the scene's effects begin again each time it comes round, a toggle with its icon as the
// screens' Loop and Ping pong are. It is called Restart, the heading's own word, as each of theirs
// is the file's. A scene going back to itself always restarts, so its toggle is held on. A scene
// that never shows again starts once, so its toggle is greyed
function sceneRestart(scene) {
  var loops = sceneLoops(scene);
  var once = !sceneShowsAgain(scene);
  var restart = toggle("&#8630;", "Restart", sceneRestarts(scene),
                       function (on) { scene.restart = on; },
                       loops ? "A scene that goes back to itself always restarts"
                       : once ? "This scene shows only once, so it has nothing to restart"
                       : "Restart this scene's effects each time it plays, instead of " +
                         "resuming where they left off", once);
  restart.disabled = loops || once;
  return restart;
}

window.addEventListener("resize", spanTray);

addStep(drawSteps.after, DRAW_AFTER, "sceneTray", function () {
  renderScenes();
  renderSceneSettings();
});

// Set node's attributes while there are scenes, and take them off where there are none
function tabRoles(node, attributes) {
  Object.keys(attributes).forEach(function (name) {
    if (state.scenes.length) node.setAttribute(name, attributes[name]);
    else node.removeAttribute(name);
  });
}

function renderScenes() {
  var box = document.getElementById("tabs");
  var plus = h("button", {
    className: "plus",
    title: state.scenes.length ? "Add another scene" : "Split into scenes that play one after another",
    onclick: addScene
  }, h("svg:svg", {width: "11", height: "11", viewBox: "0 0 11 11",
                   html: "<path d='M5.5 1 L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' " +
                         "stroke-width='1.8' stroke-linecap='round'/>"}),
     state.scenes.length ? "another scene" : "split into scenes");

  // One scene is what a file has before anyone asks for more, and a bar of one tab
  // says nothing, so it is not drawn until there is a choice to make. Always on is the tray
  // the scenes' cards sit in, its own card the tray's first column
  replace(box,
          state.scenes.length ? sceneTab(-1, state.always, "Always on", "") : null,
          state.scenes.map(function (scene, i) {
            return sceneTab(i, scene, scene.name, sceneTurn(scene));
          }),
          plus);
  box.classList.toggle("tray", state.scenes.length > 0);
  // The cards are a tablist while there are scenes to choose between, the frame their panel
  tabRoles(box, {role: "tablist", "aria-label": "Scenes"});
  tabRoles(document.getElementById("sceneBody"),
           {role: "tabpanel", "aria-labelledby": sceneTabId(state.at)});
  spanTray();

  // The frame is what says these belong to the picked card, so it appears with the cards, in
  // the picked card's colour. Its tab holds the scene's settings beside what the page says about it
  var frame = document.getElementById("sceneBody");
  frame.className = "scenebody" + (state.scenes.length ? " framed" : "");
  var tabRow = document.getElementById("sceneTabRow");
  tabRow.hidden = !state.scenes.length;
  var picked = state.at < 0 ? null : state.scenes[state.at];
  [frame, tabRow].forEach(function (node) {
    node.style.setProperty("--frame", sceneEdge(picked));
    node.style.setProperty("--frameband", sceneBand(picked));
  });
  renderSceneAside();
}

// A scene's row of settings, its name, how it ends and whether it restarts
function renderSceneSettings() {
  var box = document.getElementById("sceneSettings");
  if (state.at < 0) {
    // Check if Always on is shown with scenes for it to play under. It has no settings of its
    // own, so its row says what it is for, which keeps the gallery where it was as the tabs are
    // switched
    replace(box, state.scenes.length
      ? h("div", {className: "sceneset alwaysnote"},
          "Always on plays under every scene. A scene that uses the same lights, screen or " +
          "sound overrides it while showing.")
      : null);
    return;
  }
  var scene = state.scenes[state.at];
  replace(box, h("div", {className: "sceneset"},
                 sceneNameField(scene),
                 sceneEnds(scene),
                 scene.waits ? null : sceneSeconds(scene),
                 scene.waits || state.scenes.length === 1 ? null : sceneThen(scene),
                 sceneRestart(scene)));
}
