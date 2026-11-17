import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, drawSteps, paintAll} from "./draw.js";
import {LED_PANELS, runsOfPanel} from "./led_sections.js";
import {painters} from "./preview.js";
import {inkAt} from "./runs.js";
import {tabSwatches} from "./tabs.js";

// ---- the LED tabs' swatches, live ------------------------------------------------------------
// Each LED tab's swatch is a small copy of its section's lamps, painted every frame from the
// same values the lamps are painted from, so it can never say something the lamps do not.
// The cost is movement on the row of tabs.

function liveSwatch(swatch, panel) {
  swatch.className = "accswatch liveswatch";
  // A strip not fitted is an empty dashed outline, since its lamps play nothing
  var absent = runsOfPanel(panel).every(function (run) { return run.strip && run.there === false; });
  if (absent) swatch.classList.add("absent");
  replace(swatch);
  runsOfPanel(panel).forEach(function (run) {
    var cells = run.lamps.map(function () { return swatch.appendChild(h("span")); });
    painters.push({run: run, paint: function (all) {
      // A lamp playing nothing lets the swatch's stripes through, since drawn dark it would read
      // as a lamp set to black. A lamp a scene turns off is set to black, so it is drawn dark
      cells.forEach(function (cell, at) {
        var one = all[at];
        cell.style.background = one && one.off ? "#2a2d30"
                              : !one || one.nothing ? "transparent" : inkAt(one);
      });
    }});
  });
  swatch.title = "what the lights are showing";
}

LED_PANELS.forEach(function (panel) { tabSwatches[panel] = liveSwatch; });

// The swatches are made after the page painted, so they are painted now or show dark for a frame
addStep(drawSteps.after, DRAW_AFTER, "tabSwatches", paintAll);
