import {MONO_FIRST} from "./outputs.js";
import {active, mono, outs, pick, runs} from "./runs.js";
import {STRIPS} from "./strips.js";

// ---- the LED sections -----------------------------------------------------------------------
// The outputs and each strip, the sections the gallery can give a look to. The section shown is
// the one worked on, so the gallery is for it

export var LED_PANELS = ["outPanel"].concat(STRIPS.map(function (strip) { return strip.id + "Panel"; }));

export function runsOfPanel(panel) {
  if (panel === "outPanel") return MONO_FIRST ? [mono, outs] : [outs, mono];
  return runs.filter(function (run) { return run.strip && run.id + "Panel" === panel; });
}

// Make a section's run the one worked on at its picked stretch, unless one of its runs already is
export function workOn(panel) {
  var mine = runsOfPanel(panel);
  if (mine.indexOf(active) >= 0) return;
  var run = mine[0];
  if (run) pick(run, run.picked);
}
