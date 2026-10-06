
// ---- the LED sections as tabs -----------------------------------------------------------
// Outputs, the left strip and the right strip as tabs just under the gallery, one section
// shown at a time, so the one being worked on is never a scroll away. Choosing a tab makes
// it the one worked on, so the gallery is for it, and each tab says in a small swatch what
// its section plays. Screens stay below as sections, the gallery meaning nothing for them.
//
// The tabs sit under the gallery and not with the scene tabs, and are drawn as a row of
// names with a line under the chosen one, so they read as parts of one board and not as
// another row of scenes. Setting up the board is one button at the end of the tabs, and
// keeps to them: the whole board is being set up, a section at a time, and the tabs stay
// live to move between sections while it is.

var TAB_NAMES = {outPanel: "Outputs", striplPanel: "Left strip", striprPanel: "Right strip"};

// The sections with a tab, the LED ones and any other a page adds
var TAB_PANELS = LED_PANELS.slice();

var chosenTab = "outPanel";

// Whether the section shown is one the gallery can give a look to, which a strip not fitted is not
function chosenTakesLooks() {
  return LED_PANELS.indexOf(chosenTab) >= 0 &&
         runsOfPanel(chosenTab).every(function (run) { return run.there !== false; });
}

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
}

// A tab's swatch, which for an LED section is what it plays
function tabSwatch(swatch, panel) { renderSwatch(swatch, panel); }

// Setting up is the tabs' button and no section's own
sectionButton = function () {};

function renderLedTabs() {
  var bar = document.getElementById("ledTabs");
  bar.textContent = "";
  TAB_PANELS.forEach(function (panel) {
    var tab = document.createElement("button");
    tab.type = "button";
    tab.className = "ledtab" + (panel === chosenTab ? " on" : "");
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

var oneTabsSetup = setSetup;

setSetup = function (on) {
  oneTabsSetup(on);
  showChosen();
};

// Each section is only ever seen on its own here, so each keeps its own tools and settings
// whichever is worked on, and none changes height when another tab is chosen. The outputs'
// are for whichever of their two sides was last worked on
var lastOutputRun = outs;

var oneTabsDraw = draw;

draw = function () {
  oneTabsDraw();
  if (!active.strip) lastOutputRun = active;
  if (active.strip) {
    renderTools("outTools", lastOutputRun);
    renderChosen("outChosen", lastOutputRun);
  }
  runs.filter(function (run) { return run.strip && run !== active; }).forEach(function (run) {
    renderStripTools(run.id + "Tools", run);
    renderChosen(run.id + "Chosen", run);
  });
  renderLedTabs();
};

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

  // A section's own Set up, drawn before this page took the button to the tabs
  document.querySelectorAll(".setupslot").forEach(function (slot) {
    slot.parentNode.removeChild(slot);
  });

  // The note naming which way of setting up a page tries is for the pages comparing them
  document.getElementById("setupWay").hidden = true;
}());

showChosen();
draw();
