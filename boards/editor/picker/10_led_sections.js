import {MONO_FIRST} from "./03_outputs.js";
import {active, mono, outs, pick, runs} from "./03_runs.js";
import {STRIPS} from "./05_effects.js";

export var LED_PANELS = ["outPanel"].concat(STRIPS.map(function (strip) { return strip.id + "Panel"; }));

export function runsOfPanel(panel) {
  if (panel === "outPanel") return MONO_FIRST ? [mono, outs] : [outs, mono];
  return runs.filter(function (run) { return run.strip && run.id + "Panel" === panel; });
}

export function workOn(panel) {
  var mine = runsOfPanel(panel);
  if (mine.indexOf(active) >= 0) return;
  var run = mine[0];
  if (run) pick(run, run.picked);
}
