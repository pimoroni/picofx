// ---- steps in a stated order ----------------------------------------------------------------
// A part adds its steps to another part's lists by name, and each list keeps them in the order
// its owner states, whatever order the parts load in.

// Add a step to a list where its name falls in the list's order, after any step already added
// under that name or one before it. A name the order does not hold is refused, so no step is lost
export function addStep(steps, order, name, step) {
  var at = order.indexOf(name);
  if (at < 0) throw new Error("No place in its list's order for the step " + name);
  // The names of the steps so far, where a step added without one is taken as before every name
  var names = steps.stepNames || (steps.stepNames = steps.map(function () { return null; }));
  var place = names.findIndex(function (one) { return one !== null && order.indexOf(one) > at; });
  if (place < 0) place = steps.length;
  steps.splice(place, 0, step);
  names.splice(place, 0, name);
}

// ---- drawing --------------------------------------------------------------------------------
// The parts below add their own steps to a draw, what each readies before the page is drawn and
// what each draws after the outputs, each list in the order stated here

export var drawSteps = {before: [], after: []};
export var DRAW_BEFORE = ["tabs", "screenShown", "screenTurns", "hubTurns", "hubGroups",
                          "screenPair", "program", "firmware"];
export var DRAW_AFTER = ["sceneTray", "strips", "setup", "wiring", "tabs", "screens", "sound",
                         "sensor", "tabSwatches", "hub", "boardSettings", "saveMenu", "program",
                         "floatBar", "readback", "discover", "firmware", "start"];

// What a draw does between its before and after steps, by name, each filled in by the part that
// draws it. Those named in DRAW_ORDER go in that order, which matters: the chosen stretch's panel
// points at its cell in the bars, so the bars are drawn before it
export var drawParts = {};
var DRAW_ORDER = ["clearPainters", "clearCardFaces", "clearKin", "galleries", "bars", "sides",
                  "chosen", "preview"];

// The steps paintAll() takes, each lighting part of the page at the beat, the lamps before the
// cards
export var paintSteps = [];
export var PAINT_ORDER = ["lamps", "cards"];

// Whether drawing waits, while the page is changed in a way a draw would store half done
var drawHeld = false;

// Hold drawing while the page is changed, or let it draw again
export function holdDrawing(on) {
  drawHeld = on;
}

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
  DRAW_ORDER.forEach(function (name) { if (drawParts[name]) drawParts[name](); });
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

// Light the page at the beat, the lamps before the cards
export function paintAll() {
  paintSteps.forEach(function (step) { step(); });
}
