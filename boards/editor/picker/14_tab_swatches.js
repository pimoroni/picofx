import {drawSteps, paintAll} from "./00_draw.js";
import {inkAt, painters} from "./03_runs.js";
import {LED_PANELS, runsOfPanel} from "./10_led_sections.js";
import {tabSwatches} from "./11_tabs.js";

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

drawSteps.after.push(paintAll);
