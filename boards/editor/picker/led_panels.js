import {h, replace} from "./dom.js";
import {drawParts} from "./draw.js";
import {targetFor} from "./lines.js";
import {lookNamed} from "./looks.js";
import {widthOf} from "./outputs.js";
import {NOTCH_INSET, active, chosenSteps, mono, outs} from "./runs.js";

// ---- the LED panels -----------------------------------------------------------------------------
// The panel of settings under the chosen stretch, pointing up at it, and the two sides of the
// Outputs panel sized to the lamps they hold.

export function iconButton(drawing, says, off, done) {
  return h("button", {
    className: "round", title: says, "aria-label": says, disabled: off, onclick: done,
    html: "<svg viewBox='0 0 17 17' width='15' height='15' fill='none' " +
          "stroke='currentColor' stroke-width='1.5' stroke-linecap='round' " +
          "stroke-linejoin='round'>" + drawing + "</svg>"
  });
}

// A strip's count of stretches, said after its chip. Zoomed in, the bar shows only some of them
export function stretchCount(run) {
  return h("span", {className: "stretchcount"},
           "Cut into " + run.sections.length +
           (run.sections.length === 1 ? " stretch" : " stretches"));
}

export function renderChosen(where, run) {
  renderChosenPanel(where, run);
  chosenSteps.forEach(function (step) { step(where, run); });
  pointFrom(where, run);
}

// Make the chosen stretch's panel point up at its stretch in the bar above. The panel is pointed
// again whenever its size changes and when a long strip's bar scrolls under it
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
  var section = run.sections[run.picked];
  if (!section) {
    replace(box);
    return;
  }
  var first = run.lamps[section.from];
  var look = lookNamed(section.look);
  replace(box, h("div", {className: "chosen"},
    h("div", {className: "who"}, h("b", {}, targetFor(run, section).selector),
      ", " + widthOf(section) + (widthOf(section) === 1 ? " light" : " lights") +
      ", " + (first && first.colour ? "colour" : "mono")),
    look ? h("div", {className: "tuning"},
                h("label", {htmlFor: where + "-" + (look.solid ? "mood" : "pace")},
                  look.solid ? "Brightness" : "Speed"),
                slider(look.solid ? "mood" : "pace"),
                look.solid ? null : [h("label", {htmlFor: where + "-mood"}, look.mood),
                                     slider("mood")])
         : null));

  // Make a slider for the setting key=. Its id is its focus key, so the label beside it names it
  function slider(key) {
    var range = h("input", {
      type: "range", min: 0, max: 1, step: 0.01, value: section[key], "data-focus": where + "-" + key,
      id: where + "-" + key, name: key,
      // Through the run, since settling makes the run's stretches afresh and leaves this one behind
      oninput: function () {
        run.sections[run.picked][key] = Number(range.value);
        drawParts.preview();
      }
    });
    return range;
  }
}

// Size the two sides, each as wide as the lamps it holds, so the divide between them moves as
// outputs are broken out and put back, and every lamp has the same room. The sides carry no names,
// so breaking an output out never adds or takes away a row above the cards
function renderSides() {
  [{run: outs, side: "sideA"}, {run: mono, side: "sideB"}].forEach(function (set) {
    var box = document.getElementById(set.side);
    var count = set.run.lamps.length;
    // A side with no lamps is hidden, and the other takes the whole width. An output comes back
    // from the arrow on one of its channels, so an empty side has nothing to offer
    box.style.display = count ? "" : "none";
    box.style.flex = count + " 1 0";
    box.className = "side";
  });
}
drawParts.sides = renderSides;
// Both sides are in the one panel, so one stretch's settings serve whichever was last worked on
drawParts.chosen = function () { renderChosen("outChosen", active); };
