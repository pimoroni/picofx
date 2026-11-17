import {h, replace} from "./dom.js";
import {DRAW_AFTER, DRAW_BEFORE, addStep, draw, drawSteps} from "./draw.js";
import {renderChosen} from "./led_panels.js";
import {LED_PANELS, runsOfPanel, workOn} from "./led_sections.js";
import {BOARD} from "./looks.js";
import {active, runs, setSetupMode, setupOn} from "./runs.js";
import {lastOutputRun, setLastOutputRun} from "./setup.js";
import {STRIPS, stripBlockedBy} from "./strips.js";

// ---- the LED sections as tabs -----------------------------------------------------------
// The outputs and each strip as tabs, one section shown at a time, so the one being worked on
// is never a scroll away. Choosing a tab makes it the one worked on, and the gallery goes in its
// box. The tabs sit in the scene's body, apart from the scene tabs, as parts of one board. The
// outputs' wiring view opens from their Wiring chip and closes when another tab is chosen.

// Open or close the outputs' wiring view, and show the tab chosen
function setSetup(on) {
  setSetupMode(on);
  showChosen();
}

// The Wiring chip opens the outputs' wiring view and shows pressed, and a second click closes it
document.addEventListener("click", function (event) {
  if (event.target.closest("select, input, button, header")) return;
  if (!event.target.closest("#outFacts .boardchip")) return;
  setSetup(!setupOn);
  draw();
});

// Enter and Space work the Wiring chip as a click does
document.addEventListener("keydown", function (event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  if (!event.target.matches || !event.target.matches("#outFacts .boardchip")) return;
  event.preventDefault();
  setSetup(!setupOn);
  draw();
});

export var TAB_NAMES = {outPanel: BOARD.output_words.tab};
BOARD.strips.forEach(function (strip) { TAB_NAMES[strip.name + "Panel"] = strip.tab; });

// The sections with a tab, the LED ones and those the feature parts add. A board whose strips are
// what it is for has the strips' tabs first
export var TAB_PANELS = LED_PANELS.slice();
if (BOARD.strips_first) TAB_PANELS.push(TAB_PANELS.shift());
// The tabs the feature parts add after the LED ones, in this order
export var FEATURE_TABS = ["screens", "sound", "sensor"];

// The tab shown, at first the first strip fitted where the board's strips are what it is for
export var chosenTab = "outPanel";
if (BOARD.strips_first) {
  var firstFitted = STRIPS.filter(function (strip) { return strip.there; })[0];
  if (firstFitted) chosenTab = firstFitted.id + "Panel";
}

// Whether the section shown is one the gallery can give a look to, which a strip not fitted is not
function chosenTakesLooks() {
  return LED_PANELS.indexOf(chosenTab) >= 0 &&
         runsOfPanel(chosenTab).every(function (run) { return run.there !== false; });
}

// A look goes to the stretch being worked on, so that stays in the section shown. Closing the
// wiring view and changing scene each put back a stretch of their own, which can be another tab's
addStep(drawSteps.before, DRAW_BEFORE, "tabs", function () {
  if (!setupOn && chosenTakesLooks()) workOn(chosenTab);
  // A strip added or removed where it is shown changes whether the looks are for this tab
  showChosen();
});

// Show only the chosen tab's section. Every section stays laid out in one shared place, so the
// place is as tall as the tallest and choosing a tab never moves what is below it
export function showChosen() {
  TAB_PANELS.forEach(function (panel) {
    var node = document.getElementById(panel);
    node.open = true;
    node.hidden = false;
    node.classList.toggle("tabhidden", panel !== chosenTab);
    node.classList.add("tabbed");
  });
  // Where the section shown is one the looks mean nothing for, they stay in place and stand back,
  // so the tabs do not move under the pointer
  document.body.classList.toggle("nolooks", !chosenTakesLooks());
  // Under the sections, the looks go in the box of the one they are for
  if (chosenTakesLooks()) {
    document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
  }
}

// Hold the shared place at the tallest section's height, counting the looks into every LED
// section, so choosing a tab moves nothing. The sections must be drawn in full first
export function holdTabsPlace() {
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

// The function that draws each tab's swatch, by panel, set by the part that has the panel
export var tabSwatches = {};

export function tabSwatch(swatch, panel) { tabSwatches[panel](swatch, panel); }

// Why a tab's section cannot be used just now, or nothing where it can. Its tab greys and
// still opens, so the section can say why
function tabBlocked(panel) {
  var run = runsOfPanel(panel)[0];
  return run && run.strip ? stripBlockedBy(run) : "";
}

// Show a tab's section, and keep the keyboard on its tab, which the draw has made afresh
function choose(panel) {
  // The wiring view is the outputs' own, so leaving their tab closes it
  if (setupOn && panel !== "outPanel") setSetup(false);
  chosenTab = panel;
  if (chosenTakesLooks()) workOn(panel);
  showChosen();
  draw();
  document.getElementById("tab-" + panel).focus();
}

// The tab before or after with the arrow keys, wrapping round, or the first or last with Home and
// End, as a screen reader expects of a row of tabs
function stepTab(event, panel) {
  var step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
  var at = TAB_PANELS.indexOf(panel);
  var to = event.key === "Home" ? 0 : event.key === "End" ? TAB_PANELS.length - 1
         : step ? (at + step + TAB_PANELS.length) % TAB_PANELS.length : -1;
  if (to < 0) return;
  event.preventDefault();
  choose(TAB_PANELS[to]);
}

// Draw the tabs as a tablist, where only the chosen one is in the page's tab order
function renderLedTabs() {
  var bar = document.getElementById("ledTabs");
  replace(bar, TAB_PANELS.map(function (panel) {
    var blocked = tabBlocked(panel);
    var chosen = panel === chosenTab;
    var swatch = h("span", {className: "accswatch", "aria-hidden": "true"});
    tabSwatch(swatch, panel);
    return h("button", {
      type: "button", role: "tab", id: "tab-" + panel,
      className: "ledtab" + (chosen ? " on" : "") + (blocked ? " blocked" : ""),
      title: blocked || null, "data-panel": panel,
      "aria-selected": String(chosen), "aria-controls": panel, tabindex: chosen ? "0" : "-1",
      // A blocked tab still opens, to say why
      "aria-disabled": blocked ? "true" : null,
      onclick: function () { choose(panel); },
      onkeydown: function (event) { stepTab(event, panel); }
    }, h("b", {}, TAB_NAMES[panel]), swatch);
  }));
}

// Keep a section shown as a tab open, since the tab is how it is left
export function keptOpen(panel) {
  var node = document.getElementById(panel);
  node.addEventListener("toggle", function () {
    if (!node.open) node.open = true;
  });
}

LED_PANELS.forEach(keptOpen);

addStep(drawSteps.after, DRAW_AFTER, "tabs", function () {
  if (!active.strip) setLastOutputRun(active);
  if (active.strip) renderChosen("outChosen", lastOutputRun);
  runs.filter(function (run) { return run.strip && run !== active; }).forEach(function (run) {
    renderChosen(run.id + "Chosen", run);
  });
  renderLedTabs();
});

// The tabs, then the place every section is laid out in, including one a part adds after these
var sectionStack = h("div", {className: "tabstack", id: "tabStack"});
document.getElementById("outPanel").before(h("div", {className: "ledtabs", id: "ledTabs",
                                                  role: "tablist",
                                                  "aria-label": "Parts of the board"}),
                                           sectionStack);
LED_PANELS.forEach(function (panel) { sectionStack.appendChild(document.getElementById(panel)); });

// The looks go in the box of the chosen section
document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
