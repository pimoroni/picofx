import {h, replace} from "./dom.js";
import {draw} from "./draw.js";
import {LED_PANELS, runsOfPanel, workOn} from "./led_sections.js";
import {BOARD} from "./looks.js";
import {setSetupMode, setupOn} from "./runs.js";
import {setupButton} from "./setup.js";
import {STRIPS, stripBlockedBy} from "./strips.js";

export var TAB_NAMES = {outPanel: BOARD.output_words.tab};
BOARD.strips.forEach(function (strip) { TAB_NAMES[strip.name + "Panel"] = strip.tab; });

export var TAB_PANELS = LED_PANELS.slice();
if (BOARD.strips_first) TAB_PANELS.push(TAB_PANELS.shift());

var FEATURE_TABS = ["screensPanel", "soundPanel", "sensorPanel"];

export function addTab(panel) {
  TAB_PANELS.push(panel);
  TAB_PANELS.sort(function (a, b) { return FEATURE_TABS.indexOf(a) - FEATURE_TABS.indexOf(b); });
}

export var chosenTab = "outPanel";
if (BOARD.strips_first) {
  var firstFitted = STRIPS.filter(function (strip) { return strip.there; })[0];
  if (firstFitted) chosenTab = firstFitted.id + "Panel";
}

function chosenTakesLooks() {
  return LED_PANELS.indexOf(chosenTab) >= 0 &&
         runsOfPanel(chosenTab).every(function (run) { return run.there !== false; });
}

export function followChosenTab() {
  if (!setupOn && chosenTakesLooks()) workOn(chosenTab);
}

export function showChosen() {
  TAB_PANELS.forEach(function (panel) {
    var node = document.getElementById(panel);
    node.open = true;
    node.hidden = panel !== chosenTab;
    node.setAttribute("role", "tabpanel");
    node.setAttribute("aria-labelledby", "tab-" + panel);
  });
  document.body.toggleAttribute("data-no-looks", !chosenTakesLooks());
  if (document.body.hasAttribute("data-looks-below") && chosenTakesLooks()) {
    document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
  }
}

export var tabSwatches = {};
export var tabUnder = {};

export function tabSwatch(swatch, panel) { tabSwatches[panel](swatch, panel); }

function tabBlocked(panel) {
  var run = runsOfPanel(panel)[0];
  return run && run.strip ? stripBlockedBy(run) : "";
}

function choose(panel) {
  chosenTab = panel;
  if (chosenTakesLooks()) workOn(panel);
  showChosen();
  draw();
  document.getElementById("tab-" + panel).focus();
}

function sectionTab(panel) {
  var blocked = tabBlocked(panel);
  var under = tabUnder[panel] ? tabUnder[panel]() : "";
  var swatch = h("span", {class: "accswatch", "aria-hidden": "true"});
  tabSwatch(swatch, panel);
  return h("button", {type: "button", role: "tab", id: "tab-" + panel, "data-panel": panel,
                      "aria-selected": String(panel === chosenTab), "aria-controls": panel,
                      tabindex: panel === chosenTab ? 0 : -1,
                      "aria-disabled": blocked ? "true" : null, title: blocked || null,
                      onclick: function () { choose(panel); },
                      onkeydown: function (event) {
                        var step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
                        var at = TAB_PANELS.indexOf(panel);
                        var to = event.key === "Home" ? 0 : event.key === "End" ? TAB_PANELS.length - 1
                               : step ? (at + step + TAB_PANELS.length) % TAB_PANELS.length : -1;
                        if (to < 0) return;
                        event.preventDefault();
                        choose(TAB_PANELS[to]);
                      }},
    h("span", {}, h("b", {}, TAB_NAMES[panel]), under ? h("small", {}, under) : null),
    swatch);
}

export function renderLedTabs() {
  var bar = document.getElementById("ledTabs");
  replace(bar,
    h("div", {role: "tablist", "aria-label": "Parts of the board"}, TAB_PANELS.map(sectionTab)),
    setupButton(setupOn ? "Done" : "Edit board", setupOn, function () {
      var was = bar.getBoundingClientRect().top;
      setSetup(!setupOn);
      draw();
      window.scrollBy(0, bar.getBoundingClientRect().top - was);
    }));
}

export function keptOpen(panel) {
  var node = document.getElementById(panel);
  node.addEventListener("toggle", function () {
    if (!node.open) node.open = true;
  });
}

LED_PANELS.forEach(keptOpen);


(function () {
  var first = document.getElementById("outPanel");
  first.parentNode.insertBefore(h("nav", {class: "sectiontabs", id: "ledTabs"}), first);
  var stack = h("div", {class: "tabstack", id: "tabStack"});
  first.parentNode.insertBefore(stack, first);
  LED_PANELS.forEach(function (panel) {
    stack.appendChild(document.getElementById(panel));
  });
  if (!/[?&]above\b/.test(location.search)) {
    document.body.setAttribute("data-looks-below", "");
    document.getElementById(chosenTab).appendChild(document.getElementById("looks"));
  }
}());

export function setSetup(on) {
  setSetupMode(on);
  showChosen();
}
