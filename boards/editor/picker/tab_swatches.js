import {LED_PANELS, runsOfPanel} from "./led_sections.js";
import {painters} from "./preview.js";
import {inkAt} from "./runs.js";
import {tabSwatches} from "./tabs.js";

function liveSwatch(swatch, panel) {
  swatch.textContent = "";
  swatch.className = "accswatch liveswatch";
  var absent = runsOfPanel(panel).every(function (run) { return run.strip && run.there === false; });
  swatch.toggleAttribute("data-absent", absent);
  runsOfPanel(panel).forEach(function (run) {
    var cells = run.lamps.map(function () {
      var cell = document.createElement("span");
      swatch.appendChild(cell);
      return cell;
    });
    painters.push({run: run, paint: function (all) {
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

