
// ---- the LED tabs' swatches, live ------------------------------------------------------------
// Each LED tab's swatch a small copy of its section's lamps, painted every frame from the
// same values the lamps are painted from, so it can never say something the lamps do not.
// Tried against still swatches drawn in what each stretch plays, the cost being movement on
// the row of tabs.

var oneLiveSwatch = tabSwatch;

tabSwatch = function (swatch, panel) {
  if (LED_PANELS.indexOf(panel) < 0) return oneLiveSwatch(swatch, panel);
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
};

var oneLiveDraw = draw;

// The swatches are made after the page has painted, so are painted now or show dark a frame
draw = function () {
  oneLiveDraw();
  paintAll();
};

draw();
