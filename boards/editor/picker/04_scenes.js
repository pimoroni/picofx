
// ---- scenes ---------------------------------------------------------------------------
// The scene tabs, adding, removing and reordering them, and a scene's own settings. A scene's
// body is how the outputs are wired and placed, and every run's cuts, what each stretch plays
// and its steps to undo.

var state = {at: -1, always: {body: null}, scenes: []};

// What each output was carried from where a stand-in took its place, which is the
// scene's, so it is held in the body with the stretches it is about
var carried = {};

function copyRun(run) {
  return {sections: run.sections.map(function (section) {
            return {from: section.from, to: section.to, look: section.look,
                    pace: section.pace, mood: section.mood, colour: section.colour,
                    custom: section.custom, reversed: section.reversed,
                    level: section.level, blinks: copyBlinks(section.blinks),
                    exact: copyExact(section.exact), timings: copyExact(section.timings)};
          }),
          picked: run.picked, was: run.was.slice(), undone: run.undone.slice()};
}

// The look that plays on most of the outputs' lamps, which is what a tab's swatch shows. A board
// whose strips are what it is for shows what the first fitted strip playing anything plays, and
// its outputs' look only where none does
function mostPlayed() {
  if (BOARD.strips_first) {
    var strips = runs.filter(function (run) { return run.strip && run.there; });
    for (var i = 0; i < strips.length; i++) {
      var look = mostPlayedOn([strips[i]]);
      if (look) return look;
    }
  }
  return mostPlayedOn([outs, mono]);
}

// The look that plays on most of the lamps of the runs given
function mostPlayedOn(among) {
  var counted = {};
  var most = null;
  among.forEach(function (run) {
    run.sections.forEach(function (section) {
      if (!section.look) return;
      counted[section.look] = (counted[section.look] || 0) + widthOf(section);
      if (!most || counted[section.look] > counted[most]) most = section.look;
    });
  });
  return most;
}

// A scene holds every run's cutting and looks. The wiring, where each lamp sits and a strip's
// length are the board's, so they sit outside the body and are not captured. The parts below
// keep their own share of a scene in the body too, each registering how it captures, applies
// and blanks that share, whether the share has content, how it adds to the scene's lines, how
// it reads them back from a file's board line and kept lines, the names of what it plays, and
// the icon and name its scene tab shows where the scene sets it. Each runs after the runs' own,
// in the order the parts come
var bodyParts = [];

// The parts that keep files on the FX drive, each registering how a walk of the drive finds
// them (begin, then file or folder for each entry, then land), what it found as text to tell
// one walk from the next, and how the scenes let go of a deleted file before the drive is walked
// again (forget) and after it (gone)
var driveParts = [];

function capture() {
  var body = {look: mostPlayed(), active: active.name, runs: {},
              carried: JSON.parse(JSON.stringify(carried))};
  runs.forEach(function (run) { body.runs[run.name] = copyRun(run); });
  bodyParts.forEach(function (part) { if (part.capture) part.capture(body); });
  return body;
}

function apply(body) {
  carried = JSON.parse(JSON.stringify(body.carried));
  runs.forEach(function (run) {
    var was = copyRun(body.runs[run.name]);
    run.sections = was.sections;
    run.picked = was.picked;
    run.was = was.was;
    run.undone = was.undone;
  });
  active = runs.filter(function (run) { return run.name === body.active; })[0] || outs;
  settle();
  bodyParts.forEach(function (part) { if (part.apply) part.apply(body); });
}

// A scene with nothing playing in it, cut as the board is now, which is what the always-on
// tab is left holding once its content has been carried into the first
function blankBody() {
  var body = capture();
  Object.keys(body.runs).forEach(function (name) {
    var run = body.runs[name];
    run.sections.forEach(function (section) { section.look = null; });
    run.was = [];
    run.undone = [];
  });
  body.look = null;
  body.carried = {};
  bodyParts.forEach(function (part) { if (part.blank) part.blank(body); });
  return body;
}

function hasContent(body) {
  return Object.keys(body.runs).some(function (name) {
    return body.runs[name].sections.some(function (section) { return section.look; });
  }) || bodyParts.some(function (part) { return part.hasContent && part.hasContent(body); });
}

function slotAt(which) { return which < 0 ? state.always : state.scenes[which]; }

function allBodies() {
  return [state.always.body].concat(state.scenes.map(function (scene) { return scene.body; }));
}

// ---- what a scene leaves to Always on -------------------------------------------------------
// The board plays Always on under every scene. Where a scene plays nothing of its own on a lamp,
// the board plays Always on's look there, and where Always on plays nothing either, it turns the
// lamp off if another scene plays on it. A scene tab shows the same, so its lamps look as the
// board will light them

// The scenes other than the one being edited, whose bodies are as they were last stored
function otherScenes() {
  return state.scenes.filter(function (scene, at) { return at !== state.at; });
}

function namesOf(scenes) { return scenes.map(function (scene) { return scene.name; }); }

// Grey out settings that show Always on's values in a scene, which are set on the Always on tab
function frozen(node) {
  node.classList.add("frozen");
  node.title = "Set on the Always on tab";
  node.querySelectorAll("button, input, select").forEach(function (control) {
    control.disabled = true;
  });
}

// The stretch of a stored body's run that covers one lamp and plays a look, or null. A look
// this page does not offer writes no line, so its stretch plays nothing
function stretchPlaying(body, runName, at) {
  var run = body && body.runs[runName];
  if (!run) return null;
  for (var i = 0; i < run.sections.length; i++) {
    var section = run.sections[i];
    if (section.from <= at && at <= section.to) return lookNamed(section.look) ? section : null;
  }
  return null;
}

// What the board plays on a lamp the scene being edited plays nothing on. The result holds
// always=, Always on's stretch over the lamp, or off=, every other scene that plays on it where
// Always on does not. It is null where nothing plays on the lamp, and on the Always on tab
function lampUnder(runName, at) {
  if (state.at < 0) return null;
  var section = stretchPlaying(state.always.body, runName, at);
  if (section) return {always: section};
  var by = otherScenes().filter(function (scene) {
    return stretchPlaying(scene.body, runName, at);
  });
  return by.length ? {off: by} : null;
}

function store() { slotAt(state.at).body = capture(); }

function switchTo(which) {
  store();
  state.at = which;
  apply(slotAt(which).body);
  draw();
}

function addScene() {
  store();
  var made;
  // Where scenes can wait for a button, a new one does, as one made for a remote mostly stands
  // alone. The first waits, as a time would only bring it back to itself
  if (!state.scenes.length) {
    made = {name: "Scene 1", seconds: 10, restart: false, waits: true, body: capture()};
    state.always.body = blankBody();
    // What a part keeps with Always on rather than carrying into the first scene, such as what
    // the sensor's triggers do, which is meant for every scene
    bodyParts.forEach(function (part) { if (part.split) part.split(state.always.body, made.body); });
  } else {
    var before = state.scenes[state.scenes.length - 1];
    made = {name: freeSceneName(), seconds: before.seconds,
            restart: before.restart, waits: sceneCanWait(), body: copyBody(before.body)};
    // A scene that stayed alone takes its time again, without a sensor to move it on
    if (state.scenes.length === 1 && !sceneCanWait()) before.waits = false;
  }
  state.scenes.push(made);
  state.at = state.scenes.length - 1;
  apply(made.body);
  draw();
}

function removeScene(which) {
  store();
  var gone = state.scenes.splice(which, 1)[0];
  // Taking the last scene away leaves nothing playing, so its content comes back to
  // the tab that plays all the way through, which is where the page started
  if (!state.scenes.length && !hasContent(state.always.body))
    state.always.body = gone.body;
  state.at = state.scenes.length ? Math.min(which, state.scenes.length - 1) : -1;
  settleLoneScene();
  apply(slotAt(state.at).body);
  draw();
}

function copyBody(body) { return JSON.parse(JSON.stringify(body)); }

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
  // the picked card's colour. Its tab holds the scene's settings, beside what the page says
  // about the scene
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

// Stretch Always on's card down every row the scenes' cards and the add button wrap into, as
// many as the tray's width leaves room for. Where the scenes fill their last row, the add button
// is a thin bar the width of the tray under them, so it never takes a row as a lone card
function spanTray() {
  var box = document.getElementById("tabs");
  var always = box.querySelector(".tab.always");
  if (!always) return;
  var plus = box.querySelector(".plus");
  plus.classList.remove("wide");
  plus.style.gridColumn = "";
  always.style.gridRow = "1";
  var columns = getComputedStyle(box).gridTemplateColumns.split(" ").length;
  var perRow = Math.max(1, columns - 1);
  var scenes = box.querySelectorAll(".tab:not(.always)").length;
  if (scenes % perRow === 0) {
    plus.classList.add("wide");
    plus.style.gridColumn = "2 / -1";
  }
  always.style.gridRow = "1 / span " + Math.ceil((scenes + 1) / perRow);
}
window.addEventListener("resize", spanTray);

// Beside the frame's tab, where the picked scene comes in the turns and the way to remove it,
// or for Always on how many scenes it plays under
function renderSceneAside() {
  var aside = document.getElementById("sceneAside");
  aside.textContent = "";
  if (!state.scenes.length) return;
  var where = document.createElement("span");
  where.className = "sceneplace";
  var count = state.scenes.length;
  if (state.at < 0) {
    where.textContent = "Under " + count + (count === 1 ? " scene" : " scenes");
    aside.appendChild(where);
    return;
  }
  var picked = state.scenes[state.at];
  var after = sceneAfter(picked);
  // While the name being typed breaks a rule, the place says why instead, as it does for a scene
  // that never shows
  var problem = sceneNameProblem(picked, picked.name);
  var unreached = unreachedScenes();
  if (!problem && unreached.scenes.indexOf(picked) >= 0) {
    problem = unreached.stopper ? "Never shows, as " + unreached.stopper.name.trim() +
                                  " waits forever before it"
                                : "Never shows, as no scene goes on to it";
  }
  where.classList.toggle("warn", !!problem);
  var ends = picked.waits ? "waits " + (sceneCanWait() ? "for " + sceneWaitsFor() : "forever")
           : after === picked ? "then itself" : after ? "then " + after.name : "on its own";
  where.textContent = problem || "Scene " + (state.at + 1) + " of " + count + ", " + ends;
  where.title = where.textContent;
  aside.appendChild(where);
  var remove = document.createElement("button");
  remove.type = "button";
  remove.className = "sceneremove";
  remove.textContent = "Remove scene";
  remove.title = "Remove this scene";
  var which = state.at;
  remove.onclick = function () { removeScene(which); };
  aside.appendChild(remove);
}

// A slot's body, read from the page for the one being edited, whose stored body is out of date
function bodyAt(which) { return state.at === which ? capture() : slotAt(which).body; }

// ---- how a scene ends ---------------------------------------------------------------------------
// A scene either shows for its time and then goes to the scene after it, or waits until a button
// changes it. The scene after is the next in order unless the scene names another with then=, so
// a timed run of scenes need not follow the order the remote's numbers take

// A scene's mark, given once and kept while the scene is moved or renamed, by which another
// part names it
var sceneMarks = 0;
function sceneMark(scene) {
  if (!scene.mark) scene.mark = "s" + (++sceneMarks);
  return scene.mark;
}

function sceneMarked(mark) {
  return state.scenes.filter(function (scene) { return sceneMark(scene) === mark; })[0] || null;
}

// Whether something fitted can change scenes, so a scene can wait for it, which a board's sensor
// part answers. Without it a waiting scene waits forever
var sceneCanWait = function () { return false; };

// The places of the scenes a scene in place `at` goes to on a button or motion, which the sensor
// part gives for what is fitted
var sceneTriggerLeads = function (at) { return []; };

// What a waiting scene waits for, in words, which the sensor part says for what is fitted
var sceneWaitsFor = function () { return "a button"; };

// The scene a timed scene goes to when its time is up, or null for one that waits
function sceneAfter(scene) {
  if (scene.waits) return null;
  var named = scene.then ? sceneMarked(scene.then) : null;
  if (named) return named;
  var at = state.scenes.indexOf(scene);
  return state.scenes[(at + 1) % state.scenes.length];
}

// Whether a scene's time leads back to itself. Nothing would change then unless it restarts, so
// such a scene always does
function sceneLoops(scene) {
  return !scene.waits && sceneAfter(scene) === scene;
}

// Whether a scene's effects begin again each time it starts, as its heading says. A scene that
// never shows again starts once, so it has nothing to restart
function sceneRestarts(scene) {
  if (!sceneShowsAgain(scene)) return false;
  return scene.restart || sceneLoops(scene);
}

// The places of the scenes the scene in place `at` goes on to, by its time and by what is fitted
function sceneLeads(at) {
  var after = sceneAfter(state.scenes[at]);
  return sceneTriggerLeads(at).concat(after ? [state.scenes.indexOf(after)] : []);
}

// Which scenes can show from the places in `starts`, by place, those included
function scenesReachedFrom(starts) {
  var reached = state.scenes.map(function () { return false; });
  var waiting = [];
  function reach(place) {
    if (place < 0 || reached[place]) return;
    reached[place] = true;
    waiting.push(place);
  }
  starts.forEach(reach);
  while (waiting.length) sceneLeads(waiting.pop()).forEach(reach);
  return reached;
}

// Whether a scene can show again after it has shown, as it lies on a way back to itself
function sceneShowsAgain(scene) {
  var at = state.scenes.indexOf(scene);
  return at >= 0 && scenesReachedFrom(sceneLeads(at))[at];
}

// Make the only scene stay where its time would change nothing, as the board reports a lone
// scene with a time and no restart
function settleLoneScene() {
  if (state.scenes.length !== 1) return;
  var only = state.scenes[0];
  var namesItself = only.then && sceneMarked(only.then) === only;
  if (!only.waits && !only.restart && !namesItself) only.waits = true;
}

// The scenes nothing leads to from the first, as the board reports them, and the scene that
// waits forever before them where that is what leaves them out, or null
function unreachedScenes() {
  var reached = scenesReachedFrom(state.scenes.length ? [0] : []);
  var unreached = state.scenes.filter(function (scene, at) { return !reached[at]; });
  if (!unreached.length || sceneCanWait()) return {scenes: unreached, stopper: null};

  // Without a sensor the turns are one line from the first scene, which a waiting scene ends
  var stop = state.scenes[0];
  var seen = [];
  while (!stop.waits && seen.indexOf(stop) < 0) {
    seen.push(stop);
    stop = sceneAfter(stop);
  }
  return {scenes: unreached, stopper: stop.waits ? stop : null};
}

// What is wrong with a name for a scene, or "" where nothing is. A scene needs a name of its own,
// as another scene's heading can name it after "then", and Always on's is taken
function sceneNameProblem(scene, name) {
  var wanted = name.trim().toLowerCase();
  if (!wanted) return "A scene needs a name";
  if (wanted === "always on") return "That name is Always on's";
  var other = state.scenes.filter(function (one) {
    return one !== scene && one.name.trim().toLowerCase() === wanted;
  })[0];
  return other ? "Another scene is called " + other.name.trim() : "";
}

// The first of Scene 1, Scene 2 and so on that no scene is called
function freeSceneName() {
  for (var number = 1; ; number++) {
    if (!sceneNameProblem(null, "Scene " + number)) return "Scene " + number;
  }
}

// What a scene's card says under its name: its time, or that it waits. The scene after is named
// only where it is chosen, the next in order being what a time implies
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
var REMOTE_COLOURS = ["#ed1c24", "#00a651", "#2e3192", "#00aeef", "#ec008c", "#fff200",
                      "#fbad5d", "#ffffff", "#84c1ff"];
var REMOTE_RAINBOW = ["#ed1c24", "#f7941d", "#fff200", "#8dc63f", "#00a651", "#00aeef",
                      "#0072bc", "#2e3192", "#92278f", "#ec008c"];
var ALWAYS_COLOUR = "#8f8a82";
var UNNUMBERED_COLOUR = "#b9b3a9";

// The remote's number buttons that go to a scene, which its card wears. None on a board with no
// sensor part, which replaces this with its own
var sceneNumbers = function (scene) { return []; };

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

// A scene's name in its colour, for a sentence the page writes as markup
function sceneNameHtml(scene) {
  return "<b class='scenename' style='color:" + sceneShade(scene) + "'>" +
         escapeHtml(scene.name) + "</b>";
}

// Each part's icon, the drawing the programs page gives the same thing, so the two pages agree.
// A part the programs page has no drawing for gives its own in PART_DRAWINGS, on the same grid
var PART_FEATURES = {lights: "outputs", strip: "strip", screens: "screen", hub: "hub",
                     sound: "sound", remote: "remote"};
var PART_DRAWINGS = {};

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
  // One icon for the strips, as nothing in it could say which, its tip naming those that play
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

  // A scene's card is three rows: its name, what it sets, and how it ends beside its remote
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
    var numbers = sceneNumbers(scene);
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


// ---- what the whole file says now -------------------------------------------------------

// The lamps' lines are written from the runs as they stand, so each scene's body is applied in
// turn, which keeps one writer for all of them
function entriesOf(body) {
  apply(body);
  var lines = lampLines().filter(function (line) { return line.trim(); });
  bodyParts.forEach(function (part) { if (part.entries) lines = part.entries(body, lines); });
  return lines;
}

// A scene's heading. One read from a file with no time waits, and is written back without one.
// A heading read from a file is written back as it was while the scene still says the same
function sceneHeading(scene) {
  // A scene after other than the next in order is named after "then", a proposed word autofx does
  // not read yet. "then" comes last, as the rest of the heading after it is the name
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var named = after && after !== inOrder ? after.name.trim() || "Scene" : null;
  var read = scene.read;
  // A scene after that the file names but no scene is called keeps its heading as written
  var sameAfter = read && (read.after === named || (read.after && !scene.then &&
    !state.scenes.some(function (other) { return other.name === read.after; })));
  if (read && read.written && scene.name === read.name && sceneRestarts(scene) === read.restart &&
      sameAfter && (read.seconds === null ? scene.waits
                                          : !scene.waits && scene.seconds === read.seconds)) {
    return read.written;
  }
  // A scene going back to itself is written with restart, which the board needs to change anything
  var settings = (scene.waits ? [] : [scene.seconds + "s"])
    .concat(sceneRestarts(scene) ? ["restart"] : [])
    .concat(named !== null ? ["then " + named] : []);
  return "[" + (scene.name.trim() || "Scene") + (settings.length ? ": " + settings.join(" ") : "") +
         "]";
}

// What the parts below write above the scenes: lines straight under the file's header, then,
// after a blank line, lines above the board line. Each is a list of functions giving lines
var fileHead = {under: [], above: []};

function currentText() {
  store();
  var lines = entriesOf(state.always.body);
  state.scenes.forEach(function (scene) {
    lines.push("");
    // Comments a file had above the heading, where it was read from one
    lines = lines.concat(scene.comments || []);
    lines.push(sceneHeading(scene));
    lines = lines.concat(entriesOf(scene.body));
  });
  apply(slotAt(state.at).body);

  var head = [];
  fileHead.under.forEach(function (lines) { head = head.concat(lines()); });
  head.push("");
  fileHead.above.forEach(function (lines) { head = head.concat(lines()); });
  var board = boardLine();
  if (board) head.push(board, "");
  return HEADER + head.join("\n") + "\n" +
         (lines.length ? lines.join("\n") : "# Nothing is playing yet.");
}

drawSteps.after.push(function () {
  renderScenes();
  renderSceneSettings();
});
