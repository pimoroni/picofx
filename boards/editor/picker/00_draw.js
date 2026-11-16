import {litRun, painters} from "./02_preview.js";
import {kinOf} from "./03_outputs.js";
import {active, cardFaces, mono, outs, renderGalleries, runs} from "./03_runs.js";
import {renderChosen, renderSides} from "./04_led_panels.js";
import {renderPreview} from "./18_file_preview.js";
import {renderBar} from "./31_stretch_bar.js";
import {paintCards} from "./33_gallery.js";

// ---- drawing --------------------------------------------------------------------------------
// The parts below add their own steps to a draw, what each readies before the page is drawn and
// what each draws after the outputs, both in the order the parts come

export var drawSteps = {before: [], after: []};

// Whether drawing waits, while the page is changed in a way a draw would store half done
export var drawHeld = false;

export function draw() {
  if (drawHeld) return;
  // A draw empties and refills much of the page, and reads its layout part way through, and a
  // browser may move the scroll to hold something in view while it is half drawn, seen in Chrome
  // as a jump of the whole page when a tab was chosen. So the page ends a draw scrolled where it
  // began. A scroll a page means, such as holding a pressed button still, is made after the draw
  var across = window.scrollX;
  var down = window.scrollY;
  var focused = focusPlace();
  drawSteps.before.forEach(function (step) { step(); });

  painters = [];
  cardFaces = [];
  kinOf = {};
  renderGalleries();
  renderBar("outBar", outs);
  renderBar("monoBar", mono);

  // Both sides are in the one panel, so one stretch's settings serve whichever was last worked
  // on rather than a set under each
  renderSides();
  renderChosen("outChosen", active);

  renderPreview();
  paintAll();

  drawSteps.after.forEach(function (step) { step(); });
  refocus(focused);
  if (window.scrollX !== across || window.scrollY !== down) window.scrollTo(across, down);
}

// The fields a draw gives focus back to, those typed in or chosen from, so a pressed button is left
// as the browser leaves it
var FIELDS = "input, select, textarea";

// Where the focused field is, as {field, key, box, index, caret}, or null where none is. A draw
// makes most fields afresh, and a load that ends while someone types draws too, as each of the
// drive's pictures does once read. The field is found again by its data-focus, or by its place
// among the fields of the nearest box with an id
function focusPlace() {
  var field = document.activeElement;
  if (!field || field === document.body || !field.matches(FIELDS)) return null;
  var place = {field: field, key: field.dataset.focus || null, box: null, index: -1, caret: null};
  if (!place.key) {
    var box = field.parentElement ? field.parentElement.closest("[id]") : null;
    if (!box) return null;
    place.box = box.id;
    place.index = Array.prototype.indexOf.call(box.querySelectorAll(FIELDS), field);
  }
  // Only text fields have a caret, and asking another type for one throws
  try {
    if (typeof field.selectionStart === "number") place.caret = [field.selectionStart, field.selectionEnd];
  } catch (e) {
    place.caret = null;
  }
  return place;
}

// Focus the field made where the focused one was, if the draw took that one away. A field still on
// the page keeps or loses focus as it would have
function refocus(place) {
  if (!place || place.field.isConnected || document.activeElement !== document.body) return;
  var field = null;
  if (place.key) {
    field = document.querySelector("[data-focus='" + place.key + "']");
  } else {
    var box = document.getElementById(place.box);
    field = box ? box.querySelectorAll(FIELDS)[place.index] || null : null;
  }
  if (!field || field.disabled) return;
  field.focus({preventScroll: true});
  if (place.caret) {
    try {
      field.setSelectionRange(place.caret[0], place.caret[1]);
    } catch (e) {
      // A field made as another type has no caret to place
    }
  }
}

export function paintAll() {
  var lit = {};
  runs.forEach(function (run) { lit[run.name] = litRun(run); });
  painters.forEach(function (one) { one.paint(lit[one.run.name]); });
  paintCards();
}
