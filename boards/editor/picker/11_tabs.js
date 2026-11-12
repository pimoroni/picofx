
// ---- the LED sections as tabs -----------------------------------------------------------
// The outputs and each strip as tabs, one section shown at a time, so the one being worked on
// is never a scroll away. Choosing a tab makes it the one worked on, and the gallery goes in
// its box, as the screens' pictures and the programs sit under what they are for. Each tab
// says in a small swatch what its section plays. ?above on the page's address keeps the
// gallery above the tabs.
//
// The tabs sit in the scene's body and not with the scene tabs, and are drawn as a row of
// names with a line under the chosen one, so they read as parts of one board and not as
// another row of scenes. Setting up the board is one button at the end of the tabs, and
// keeps to them: the whole board is being set up, a section at a time, and the tabs stay
// live to move between sections while it is.

var TAB_NAMES = {outPanel: BOARD.output_words.tab};
BOARD.strips.forEach(function (strip) { TAB_NAMES[strip.name + "Panel"] = strip.tab; });

// The sections with a tab, the LED ones and any other a page adds. A board whose strips are what it
// is for has their tabs first and opens on the first one fitted
var TAB_PANELS = LED_PANELS.slice();
if (BOARD.strips_first) TAB_PANELS.push(TAB_PANELS.shift());

var chosenTab = "outPanel";
if (BOARD.strips_first) {
  var firstFitted = STRIPS.filter(function (strip) { return strip.there; })[0];
  if (firstFitted) chosenTab = firstFitted.id + "Panel";
}

// Whether the section shown is one the gallery can give a look to, which a strip not fitted is not
function chosenTakesLooks() {
  return LED_PANELS.indexOf(chosenTab) >= 0 &&
         runsOfPanel(chosenTab).every(function (run) { return run.there !== false; });
}

// A look goes to the stretch being worked on, so that stays in the section shown. Pressing Done in
// Edit board and changing scene each put back a stretch of their own, which can be another tab's
drawSteps.before.push(function () {
  if (!setupOn && chosenTakesLooks()) workOn(chosenTab);
});

// Every tab's section stays laid out in one shared place, only the chosen one seen, so the
// place is as tall as the tallest and choosing a tab never moves what is below it
function showChosen() {
  TAB_PANELS.forEach(function (panel) {
    var node = document.getElementById(panel);
    node.open = true;
    node.hidden = false;
    node.classList.toggle("tabhidden", panel !== chosenTab);
    node.classList.add("tabbed");
  });
  // The looks stay where they are and stand back, so the tabs do not move under the
  // pointer, where the section shown is one they mean nothing for
  document.body.classList.toggle("nolooks", !chosenTakesLooks());
  // Under the sections, the looks go in the box of the one they are for, as a screen's pictures do
  if (document.body.classList.contains("looksbelow") && chosenTakesLooks()) {
    document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
  }
}

// With the looks in the box of the section they are for, the shared place is held at the tallest
// box with the looks counted in, whichever box has them, so choosing a tab still moves nothing.
// Run after every part has drawn, the boxes then being their full height
function holdTabsPlace() {
  if (!document.body.classList.contains("looksbelow")) return;
  var stack = document.getElementById("tabStack");
  var looks = document.getElementById("looks");
  // What the looks add to a box, measured as the box with them less the box without, as the
  // margins either side of them count too
  var holder = looks.parentNode;
  var withLooks = holder.getBoundingClientRect().height;
  var after = looks.nextSibling;
  holder.removeChild(looks);
  var extra = withLooks - holder.getBoundingClientRect().height;
  holder.insertBefore(looks, after);
  stack.style.minHeight = "";
  var tallest = 0;
  TAB_PANELS.forEach(function (panel) {
    var node = document.getElementById(panel);
    var high = node.getBoundingClientRect().height;
    if (LED_PANELS.indexOf(panel) >= 0 && !node.contains(looks)) high += extra;
    tallest = Math.max(tallest, high);
  });
  stack.style.minHeight = tallest + "px";
}

// A tab's swatch, drawn by whichever part has that panel
var tabSwatches = {};

function tabSwatch(swatch, panel) { tabSwatches[panel](swatch, panel); }

// Why a tab's section cannot be used just now, or nothing where it can. Its tab greys and
// still opens, so the section can say why
function tabBlocked(panel) {
  var run = runsOfPanel(panel)[0];
  return run && run.strip ? stripBlockedBy(run) : "";
}

function renderLedTabs() {
  var bar = document.getElementById("ledTabs");
  bar.textContent = "";
  TAB_PANELS.forEach(function (panel) {
    var tab = document.createElement("button");
    tab.type = "button";
    var blocked = tabBlocked(panel);
    tab.className = "ledtab" + (panel === chosenTab ? " on" : "") + (blocked ? " blocked" : "");
    if (blocked) tab.title = blocked;
    tab.dataset.panel = panel;
    var name = document.createElement("b");
    name.textContent = TAB_NAMES[panel];
    tab.appendChild(name);
    var swatch = document.createElement("span");
    swatch.className = "accswatch";
    tabSwatch(swatch, panel);
    tab.appendChild(swatch);
    tab.addEventListener("click", function () {
      chosenTab = panel;
      if (chosenTakesLooks()) workOn(panel);
      showChosen();
      draw();
    });
    bar.appendChild(tab);
  });

  var gap = document.createElement("span");
  gap.className = "gap";
  bar.appendChild(gap);
  // The tabs grow and shrink as setting up opens and closes, so they are held where they
  // were on the screen
  bar.appendChild(setupButton(setupOn ? "Done" : "Edit board", setupOn, function () {
    var was = bar.getBoundingClientRect().top;
    setSetup(!setupOn);
    draw();
    window.scrollBy(0, document.getElementById("ledTabs").getBoundingClientRect().top - was);
  }));
}

// A section shown as a tab is not folded away, the tab being how it is left
function keptOpen(panel) {
  var node = document.getElementById(panel);
  node.addEventListener("toggle", function () {
    if (!node.open) node.open = true;
  });
}

LED_PANELS.forEach(keptOpen);

// Each section is only ever seen on its own here, so each keeps its own tools and settings
// whichever is worked on, and none changes height when another tab is chosen. The outputs'
// are for whichever of their two sides was last worked on
var lastOutputRun = outs;

drawSteps.after.push(function () {
  if (!active.strip) lastOutputRun = active;
  if (active.strip) {
    renderTools("outTools", lastOutputRun);
    renderChosen("outChosen", lastOutputRun);
  }
  runs.filter(function (run) { return run.strip && run !== active; }).forEach(function (run) {
    renderTools(run.id + "Tools", run);
    renderChosen(run.id + "Chosen", run);
  });
  renderLedTabs();
});

(function () {
  var bar = document.createElement("div");
  bar.className = "ledtabs";
  bar.id = "ledTabs";
  var first = document.getElementById("outPanel");
  first.parentNode.insertBefore(bar, first);

  // The one place every tab's section is laid out in. A section a page adds after one of
  // these lands in it too
  var stack = document.createElement("div");
  stack.className = "tabstack";
  stack.id = "tabStack";
  first.parentNode.insertBefore(stack, first);
  LED_PANELS.forEach(function (panel) {
    stack.appendChild(document.getElementById(panel));
  });

  // The looks go in the box of the chosen section, unless the page's address asks for them above
  if (!/[?&]above\b/.test(location.search)) {
    document.body.classList.add("looksbelow");
    document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
  }
}());
