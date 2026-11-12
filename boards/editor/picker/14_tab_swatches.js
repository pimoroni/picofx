
// ---- the LED tabs' swatches, live ------------------------------------------------------------
// Each LED tab's swatch a small copy of its section's lamps, painted every frame from the
// same values the lamps are painted from, so it can never say something the lamps do not.
// The cost is movement on the row of tabs.

function liveSwatch(swatch, panel) {
  swatch.textContent = "";
  swatch.className = "accswatch liveswatch";
  // A strip not fitted is crossed through, as a screen not fitted is, its lamps playing nothing
  var absent = runsOfPanel(panel).every(function (run) { return run.strip && run.there === false; });
  if (absent) swatch.classList.add("absent");
  runsOfPanel(panel).forEach(function (run) {
    var cells = run.lamps.map(function () {
      var cell = document.createElement("span");
      swatch.appendChild(cell);
      return cell;
    });
    painters.push({run: run, paint: function (all) {
      // A lamp playing nothing lets the swatch's own stripes through, as a still swatch
      // shows nothing, where drawn dark it read as a lamp set to black. A lamp a scene turns
      // off is one set to black, so it is drawn dark
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

// The swatches are made after the page has painted, so are painted now or show dark a frame
drawSteps.after.push(paintAll);
