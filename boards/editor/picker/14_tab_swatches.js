
// ---- the LED tabs' swatches, live ------------------------------------------------------------
// Each LED tab's swatch a small copy of its section's lamps, painted every frame from the
// same values the lamps are painted from, so it can never say something the lamps do not.
// The cost is movement on the row of tabs.

function liveSwatch(swatch, panel) {
  swatch.textContent = "";
  swatch.className = "accswatch liveswatch";
  runsOfPanel(panel).forEach(function (run) {
    var cells = run.lamps.map(function () {
      var cell = document.createElement("span");
      swatch.appendChild(cell);
      return cell;
    });
    painters.push({run: run, paint: function (all) {
      // A lamp playing nothing lets the swatch's own stripes through, as a still swatch
      // shows nothing, where drawn dark it read as a lamp set to black
      cells.forEach(function (cell, at) {
        var one = all[at];
        cell.style.background = !one || one.nothing ? "transparent" : inkAt(one);
      });
    }});
  });
  swatch.title = "what its lights are showing now";
}

LED_PANELS.forEach(function (panel) { tabSwatches[panel] = liveSwatch; });

// The swatches are made after the page has painted, so are painted now or show dark a frame
drawSteps.after.push(paintAll);
