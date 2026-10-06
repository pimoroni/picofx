
// ---- the LED sections, for a page that shows one at a time ----------------------------------
// The outputs and each strip, which the gallery can give a look to, as against the screens,
// which it cannot. A page showing one at a time makes the one shown the one worked on, so
// the gallery is for it, and says of the others in a small swatch what they play.

var LED_PANELS = ["outPanel", "striplPanel", "striprPanel"];

function runsOfPanel(panel) {
  if (panel === "outPanel") return [outs, mono];
  return runs.filter(function (run) { return run.strip && run.id + "Panel" === panel; });
}

// The section shown becomes the run worked on, keeping its own picked stretch
function workOn(panel) {
  var mine = runsOfPanel(panel);
  if (mine.indexOf(active) >= 0) return;
  var run = mine[0];
  if (run) pick(run, run.picked);
}

// A section's swatch: each stretch in what it plays, as wide as it is long
function renderSwatch(swatch, panel) {
  swatch.textContent = "";
  var named = [];
  runsOfPanel(panel).forEach(function (run) {
    run.sections.forEach(function (section) {
      var look = lookNamed(section.look);
      var cell = document.createElement("span");
      cell.style.flex = widthOf(section) + " 1 0";
      if (look) {
        cell.style.background = washFor(run, section, look);
        if (named.indexOf(look.name) < 0) named.push(look.name);
      } else {
        cell.className = "nothing";
      }
      swatch.appendChild(cell);
    });
  });
  swatch.title = named.length ? "plays " + named.join(", ") : "plays nothing yet";
}
