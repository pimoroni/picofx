
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
// and blanks that share, whether the share has content, how it adds to the scene's lines, and
// how it reads them back from a file's board line and kept lines. Each runs after the runs'
// own, in the order the parts come
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
  if (!state.scenes.length) {
    made = {name: "Scene 1", seconds: 10, restart: false, body: capture()};
    state.always.body = blankBody();
  } else {
    var before = state.scenes[state.scenes.length - 1];
    made = {name: "Scene " + (state.scenes.length + 1), seconds: before.seconds,
            restart: before.restart, body: copyBody(before.body)};
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
    box.appendChild(sceneTab(-1, state.always, "Always on", "under every scene"));
    state.scenes.forEach(function (scene, i) {
      box.appendChild(sceneTab(i, scene, scene.name, scene.seconds + "s" +
                               (scene.restart ? ", from the start" : "")));
    });
  }

  var plus = document.createElement("button");
  plus.className = "plus";
  plus.innerHTML = "<svg width='11' height='11' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" +
                   (state.scenes.length ? "another scene" : "split into scenes");
  plus.title = state.scenes.length ? "Add another scene"
                                   : "Split this into scenes that take turns";
  plus.onclick = addScene;
  box.appendChild(plus);

  // The frame is what says these belong to the tab, so it appears with the tabs
  var frame = document.getElementById("sceneBody");
  frame.className = "scenebody" + (state.scenes.length ? " framed" : "");

  // Whether the tabs still sit on one row decides whether one of them can join the
  // frame below, so it is measured rather than guessed
  var tabs = box.querySelectorAll(".tab");
  var plusTop = box.querySelector(".plus").offsetTop;
  var wrapped = tabs.length > 1 &&
                (tabs[tabs.length - 1].offsetTop > tabs[0].offsetTop ||
                 plusTop > tabs[0].offsetTop);
  box.classList.toggle("wrapped", wrapped);
  if (wrapped && state.scenes.length) frame.classList.add("loose");
}

function sceneTab(which, slot, name, says) {
  var here = state.at === which;
  var body = here ? capture() : slot.body;
  var tab = document.createElement("button");
  tab.className = "tab" + (here ? " on" : "");
  tab.draggable = which >= 0;

  var swatch = document.createElement("div");
  swatch.className = "look";
  var look = lookNamed(body.look);
  if (look) look.strip.forEach(function (colour) {
    var cell = document.createElement("span");
    cell.style.background = colour;
    swatch.appendChild(cell);
  });
  tab.appendChild(swatch);

  var title = document.createElement("b");
  title.textContent = name;
  if (which >= 0) {
    var shut = document.createElement("span");
    shut.className = "shut";
    shut.textContent = "\u00d7";
    shut.title = "Take this scene out";
    shut.onclick = function (e) { e.stopPropagation(); removeScene(which); };
    title.appendChild(shut);
  }
  tab.appendChild(title);

  var under = document.createElement("small");
  under.textContent = says;
  tab.appendChild(under);

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
  name.title = "What this scene is called, which is its heading in the file";
  name.dataset.focus = "scene-name";
  name.oninput = function () {
    // The brackets and the colon are the heading's own punctuation
    scene.name = name.value.replace(/[\[\]:]/g, "");
    if (name.value !== scene.name) name.value = scene.name;
    renderScenes();
    renderPreview();
  };
  row.appendChild(name);

  var shows = document.createElement("span");
  shows.textContent = "shows for";
  row.appendChild(shows);

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
  unit.textContent = "seconds";
  row.appendChild(unit);

  var again = document.createElement("label");
  var tick = document.createElement("input");
  tick.type = "checkbox";
  tick.checked = scene.restart;
  tick.onchange = function () { scene.restart = tick.checked; draw(); };
  again.appendChild(tick);
  again.appendChild(document.createTextNode("from the start each turn"));
  again.title = "Its effects begin again every time the scene comes round";
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
  var read = scene.read;
  if (read && read.written && scene.name === read.name && scene.restart === read.restart &&
      (read.seconds === null ? scene.waits : scene.seconds === read.seconds)) {
    return read.written;
  }
  var settings = (scene.waits ? [] : [scene.seconds + "s"]).concat(scene.restart ? ["restart"] : []);
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
