import {lookNamed} from "./01_looks.js";
import {targetFor} from "./03_lines.js";
import {widthOf} from "./03_outputs.js";
import {NOTCH_INSET, chosenSteps, mono, outs} from "./03_runs.js";
import {renderPreview} from "./18_file_preview.js";

// ---- the LED panels -----------------------------------------------------------------------------
// The panel of settings under the chosen stretch, pointing up at it, and the two sides of the
// Outputs panel sized to the lamps they hold.

export function iconButton(drawing, says, off, done) {
  var made = document.createElement("button");
  made.className = "round";
  made.title = says;
  made.setAttribute("aria-label", says);
  made.disabled = off;
  made.innerHTML = "<svg viewBox='0 0 17 17' width='15' height='15' fill='none' " +
                   "stroke='currentColor' stroke-width='1.5' stroke-linecap='round' " +
                   "stroke-linejoin='round'>" + drawing + "</svg>";
  made.onclick = done;
  return made;
}

// A strip's count of stretches, said after its chip. Zoomed in, the bar shows only some of them
export function stretchCount(run) {
  var says = document.createElement("span");
  says.className = "stretchcount";
  says.textContent = "Cut into " + run.sections.length +
                     (run.sections.length === 1 ? " stretch" : " stretches");
  return says;
}

export function renderChosen(where, run) {
  renderChosenPanel(where, run);
  chosenSteps.forEach(function (step) { step(where, run); });
  pointFrom(where, run);
}

// Make the chosen stretch's panel point up at its stretch in the bar above. The panel is pointed
// again whenever its size changes, which is also when a hidden tab is shown, and when a long
// strip's bar scrolls under it
function pointFrom(where, run) {
  var box = document.getElementById(where);
  var panel = box && box.querySelector(".chosen");
  var bar = document.getElementById((run.id || run.name) + "Bar");
  if (!panel || !bar) return;
  function point() { pointAt(panel, bar.querySelectorAll(".sec")[run.picked]); }
  point();
  if (window.ResizeObserver) new ResizeObserver(point).observe(panel);
  var scroller = bar.querySelector(".scroller");
  if (scroller) scroller.addEventListener("scroll", point);
}

// Point a panel at the middle of the part of a stretch's cell in view. It points at nothing where
// the cell is scrolled out of view, or is not picked since another run is being worked on
function pointAt(panel, cell) {
  if (cell && !cell.classList.contains("picked")) cell = null;
  var from = panel.getBoundingClientRect();
  var shown = cell ? cell.getBoundingClientRect() : null;
  var view = cell && cell.closest(".scroller") ? cell.closest(".scroller").getBoundingClientRect()
                                                : shown;
  var left = shown ? Math.max(shown.left, view.left) : 0;
  var right = shown ? Math.min(shown.right, view.right) : 0;
  var pointing = !!shown && from.width > 0 && right - left >= NOTCH_INSET;
  panel.classList.toggle("pointing", pointing);
  if (!pointing) return;
  // A stretch at either end of the bar is pointed at as near its middle as the corners allow
  var middle = Math.min(Math.max((left + right) / 2, from.left + NOTCH_INSET),
                        from.right - NOTCH_INSET);
  panel.style.setProperty("--notch", (middle - from.left) + "px");
}

function renderChosenPanel(where, run) {
  var box = document.getElementById(where);
  if (!box) return;
  box.textContent = "";
  var section = run.sections[run.picked];
  if (!section) return;
  var wrap = document.createElement("div");
  wrap.className = "chosen";
  var who = document.createElement("div");
  who.className = "who";
  var first = run.lamps[section.from];
  who.innerHTML = "<b>" + targetFor(run, section).selector + "</b>, " +
                  widthOf(section) + (widthOf(section) === 1 ? " light" : " lights") +
                  ", " + (first && first.colour ? "colour" : "mono");
  wrap.appendChild(who);

  var look = lookNamed(section.look);
  if (look) {
    var tuning = document.createElement("div");
    tuning.className = "tuning";
    tuning.appendChild(labelled(look.solid ? "Brightness" : "Speed"));
    tuning.appendChild(slider(look.solid ? "mood" : "pace"));
    if (!look.solid) {
      tuning.appendChild(labelled(look.mood));
      tuning.appendChild(slider("mood"));
    }
    wrap.appendChild(tuning);
  }
  box.appendChild(wrap);

  function labelled(words) {
    var label = document.createElement("label");
    label.textContent = words;
    return label;
  }
  function slider(key) {
    var range = document.createElement("input");
    range.type = "range";
    range.min = 0;
    range.max = 1;
    range.step = 0.01;
    range.value = section[key];
    range.dataset.focus = where + "-" + key;
    // Through the run, as a page that makes the stretches afresh leaves this one behind
    range.oninput = function () {
      run.sections[run.picked][key] = Number(range.value);
      renderPreview();
    };
    return range;
  }
}

// Size the two sides, each as wide as the lamps it holds, so the divide between them moves as
// outputs are broken out and put back and every lamp has the same room. The sides carry no names,
// so breaking an output out never adds or takes away a row above the cards. The lamps' labels,
// the board's box and the board's edge already say which lights are which
export function renderSides() {
  [{run: outs, side: "sideA"}, {run: mono, side: "sideB"}].forEach(function (set) {
    var box = document.getElementById(set.side);
    var count = set.run.lamps.length;
    // A side with nothing on it is not there at all. An output comes back from the arrow
    // on one of its channels, so nothing is reached by keeping an empty column open, and
    // the side that holds every lamp gets the whole width
    box.style.display = count ? "" : "none";
    box.style.flex = count + " 1 0";
    box.className = "side";
  });
}
