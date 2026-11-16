import {DRAW_AFTER, addStep, draw, drawSteps} from "./00_draw.js";
import {BOARD, lookNamed, toggle} from "./01_looks.js";
import {runs} from "./03_runs.js";
import {
  addScene, bodyParts, capture, renderSceneAside, sceneAfter, sceneHooks, sceneLoops, sceneMark,
  sceneMarked, sceneNameProblem, sceneRestarts, sceneShowsAgain, spanTray, state, store,
  stretchPlaying, switchTo
} from "./04_scenes.js";
import {TAB_NAMES} from "./11_tabs.js";
import {escapeHtml, renderPreview} from "./18_file_preview.js";
import {featureIcon} from "./22_program.js";

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
  var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("viewBox", "0 0 24 24");
  icon.setAttribute("class", "featureicon");
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = PART_DRAWINGS[key];
  return icon;
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

function sceneTab(which, slot, name, says) {
  var here = state.at === which;
  var body = here ? capture() : slot.body;
  var tab = document.createElement("button");
  tab.className = "tab" + (here ? " on" : "") + (which < 0 ? " always" : "");
  tab.draggable = which >= 0;
  // The scene's colour is its tab's band and tint, and the selected tab is ringed as the page
  // rings anything chosen
  var scene = which < 0 ? null : slot;
  tab.style.setProperty("--scene", sceneColour(scene));
  if (which >= 0) {
    tab.style.setProperty("--band", sceneBand(scene));
    if (sceneIsPale(scene)) tab.classList.add("pale");
  }
  if (which < 0) says = alwaysSays(body);

  // A scene's card is three rows, its name, what it sets, and how it ends beside its remote
  // number. Always on's is its name, what it is for and what it plays, then what it sets
  var title = document.createElement("b");
  // The name is cut short where it is long, and the whole of it is in the card's tip
  var named = document.createElement("span");
  named.className = "cardname";
  named.textContent = name;
  title.appendChild(named);
  tab.title = name;
  // A scene's card is moved by dragging it, which a grip at the end of its name says
  if (which >= 0) {
    title.insertAdjacentHTML("beforeend", "<svg class='grip' viewBox='0 0 8 12' aria-hidden='true'>" +
      "<circle cx='2' cy='2' r='1.1'/><circle cx='6' cy='2' r='1.1'/><circle cx='2' cy='6' r='1.1'/>" +
      "<circle cx='6' cy='6' r='1.1'/><circle cx='2' cy='10' r='1.1'/><circle cx='6' cy='10' r='1.1'/>" +
      "</svg>");
    title.lastChild.insertAdjacentHTML("afterbegin", "<title>Drag to move this scene</title>");
  }
  tab.appendChild(title);
  // An icon for each part the scene sets itself, in a shade of its colour
  var icons = document.createElement("span");
  icons.className = "partsset";
  icons.style.color = sceneShade(scene);
  partsSet(body, which < 0).forEach(function (part) {
    var icon = partIcon(part[0]);
    icon.insertAdjacentHTML("afterbegin", "<title>" + escapeHtml(part[1]) + "</title>");
    icons.appendChild(icon);
  });

  var parts = document.createElement("span");
  parts.className = "cardparts";
  parts.appendChild(icons);
  var under = document.createElement("small");
  under.className = "says";
  under.textContent = says;

  if (which < 0) {
    var role = document.createElement("small");
    role.className = "role";
    role.textContent = "Plays under every scene";
    tab.appendChild(role);
    if (says) tab.appendChild(under);
    tab.appendChild(parts);
  } else {
    tab.appendChild(parts);
    var turn = document.createElement("span");
    turn.className = "cardturn";
    turn.appendChild(under);
    // Each of the remote's number buttons that goes to the scene, drawn as the remote draws it
    var numbers = sceneHooks.numbers(scene);
    if (numbers.length) {
      var badges = document.createElement("span");
      badges.className = "irbadges";
      numbers.forEach(function (number) {
        var badge = document.createElement("span");
        badge.className = "irbadge" + (number ? "" : " zero");
        badge.textContent = String(number);
        badge.title = "Press " + number + " on the remote for this scene";
        // The white button's ring is drawn in a light grey, which shows on a card
        if (number) badge.style.setProperty("--ring", number === 8 ? "#cfccc6" : REMOTE_COLOURS[number - 1]);
        badges.appendChild(badge);
      });
      turn.appendChild(badges);
    }
    tab.appendChild(turn);
  }

  tab.onclick = function () { if (state.at !== which) switchTo(which); };

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

var carriedTab = null;

// A scene's row of settings, its time and whether it starts afresh. The scene row part
// restyles it and speaks for the always-on tab
function renderSceneRow() {
  var box = document.getElementById("sceneSettings");
  box.textContent = "";
  if (state.at < 0) return;
  var scene = state.scenes[state.at];

  var row = document.createElement("div");
  row.className = "sceneset";

  var name = document.createElement("input");
  name.type = "text";
  name.value = scene.name;
  name.title = "Scene name";
  name.dataset.focus = "scene-name";
  // The last name left in the field that broke no rule, which the scene goes back to if it is
  // left with one that does. It is kept with the scene, as a draw makes the field afresh while it
  // is being typed in, and a name half typed is not taken for it
  if (scene.goodName === undefined && !sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
  function marked() {
    var problem = sceneNameProblem(scene, scene.name);
    name.classList.toggle("invalid", !!problem);
    name.title = problem || "Scene name";
  }
  name.oninput = function () {
    // The brackets and the colon are the heading's own punctuation
    scene.name = name.value.replace(/[\[\]:]/g, "");
    if (name.value !== scene.name) name.value = scene.name;
    marked();
    renderScenes();
    renderPreview();
  };
  name.onchange = function () {
    scene.name = scene.name.trim();
    if (!sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
    else if (scene.goodName) scene.name = scene.goodName;
    draw();
  };
  marked();
  row.appendChild(name);

  // How the scene ends. A waiting scene has no time and no scene after
  var lone = state.scenes.length === 1;
  var ends = document.createElement("select");
  ends.className = "sceneends";
  [["shows", "shows for"], ["waits", "waits"]].forEach(function (way) {
    var option = document.createElement("option");
    option.value = way[0];
    option.textContent = way[1];
    ends.appendChild(option);
  });
  ends.value = scene.waits ? "waits" : "shows";
  ends.onchange = function () {
    scene.waits = ends.value === "waits";
    draw();
  };
  row.appendChild(ends);

  if (!scene.waits) {
    var seconds = document.createElement("input");
    seconds.type = "number";
    seconds.min = 1;
    seconds.value = scene.seconds;
    seconds.dataset.focus = "scene-seconds";
    seconds.onchange = function () {
      scene.seconds = Math.max(1, Number(seconds.value) || 1);
      draw();
    };
    row.appendChild(seconds);

    var unit = document.createElement("span");
    unit.className = "sunit";
    unit.textContent = lone ? "s, then itself" : "s, then";
    row.appendChild(unit);
  }

  // The scene after, the next in order unless another is chosen, which can be this one again
  if (!scene.waits && !lone) {
    var then = document.createElement("select");
    then.className = "scenethen";
    var inOrder = state.scenes[(state.at + 1) % state.scenes.length];
    var first = document.createElement("option");
    first.value = "";
    first.textContent = "the next scene";
    then.appendChild(first);
    state.scenes.forEach(function (other) {
      if (other === inOrder) return;
      var option = document.createElement("option");
      option.value = sceneMark(other);
      option.textContent = other === scene ? "itself" : other.name;
      then.appendChild(option);
    });
    then.value = scene.then && sceneMarked(scene.then) && sceneMarked(scene.then) !== inOrder
               ? scene.then : "";
    then.title = "The scene after this one, the next in order unless another is chosen";
    then.onchange = function () {
      scene.then = then.value || null;
      draw();
    };
    row.appendChild(then);
  }

  var again = document.createElement("label");
  var tick = document.createElement("input");
  tick.type = "checkbox";
  tick.checked = sceneRestarts(scene);
  tick.onchange = function () { scene.restart = tick.checked; draw(); };
  again.appendChild(tick);
  again.appendChild(document.createTextNode("restart each time"));
  again.title = "Restart this scene's effects each time it plays";
  row.appendChild(again);

  box.appendChild(row);
}

window.addEventListener("resize", spanTray);

addStep(drawSteps.after, DRAW_AFTER, "sceneTray", function () {
  renderScenes();
  renderSceneSettings();
});

function renderScenes() {
  var box = document.getElementById("tabs");
  box.textContent = "";

  // One scene is what a file has before anyone asks for more, and a bar of one tab
  // says nothing, so it is not drawn until there is a choice to make
  if (state.scenes.length) {
    // Always on is the tray the scenes' cards sit in, its own card the tray's first column
    box.appendChild(sceneTab(-1, state.always, "Always on", ""));
    state.scenes.forEach(function (scene, i) {
      box.appendChild(sceneTab(i, scene, scene.name, sceneTurn(scene)));
    });
  }

  var plus = document.createElement("button");
  plus.className = "plus";
  plus.innerHTML = "<svg width='11' height='11' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" +
                   (state.scenes.length ? "another scene" : "split into scenes");
  plus.title = state.scenes.length ? "Add another scene"
                                   : "Split into scenes that play one after another";
  plus.onclick = addScene;
  box.appendChild(plus);
  box.classList.toggle("tray", state.scenes.length > 0);
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

// ---- a scene's own settings, in the screens' style ---------------------------------------
// Whether the scene's effects begin again each time it comes round is a toggle with its icon, as
// the screens' Loop and Ping pong are. It is called Restart, the heading's own word, as each of
// theirs is the file's.

function renderSceneSettings() {
  renderSceneRow();
  // Check if Always on is shown with scenes for it to play under. It has no settings of its own,
  // so its row says what it is for, which keeps the gallery where it was as the tabs are switched
  if (state.at < 0 && state.scenes.length) {
    var note = document.createElement("div");
    note.className = "sceneset alwaysnote";
    note.textContent = "Always on plays under every scene. A scene that uses the " +
                       "same lights, screen or sound overrides it while showing.";
    document.getElementById("sceneSettings").appendChild(note);
    return;
  }
  var row = document.querySelector("#sceneSettings .sceneset");
  if (!row || state.at < 0) return;
  var scene = state.scenes[state.at];
  var ticked = row.querySelector("label");
  if (!ticked) return;
  // A scene going back to itself always restarts, so its toggle is held on. A scene that never
  // shows again starts once, so its toggle is greyed
  var loops = sceneLoops(scene);
  var once = !sceneShowsAgain(scene);
  var restart = toggle("&#8630;", "Restart", sceneRestarts(scene),
                       function (on) { scene.restart = on; },
                       loops ? "A scene that goes back to itself always restarts"
                       : once ? "This scene shows only once, so it has nothing to restart"
                       : "Restart this scene's effects each time it plays, instead of " +
                         "resuming where they left off", once);
  restart.disabled = loops || once;
  row.replaceChild(restart, ticked);
}
