export var drawSteps = {before: [], during: [], after: []};

export var paintSteps = [];

var drawHeld = false;

export function holdDrawing(on) {
  drawHeld = on;
}

export function draw() {
  if (drawHeld) return;
  var across = window.scrollX;
  var down = window.scrollY;
  var focused = focusPlace();
  drawSteps.before.forEach(function (step) { step(); });
  drawSteps.during.forEach(function (step) { step(); });
  drawSteps.after.forEach(function (step) { step(); });
  refocus(focused);
  if (window.scrollX !== across || window.scrollY !== down) window.scrollTo(across, down);
}

export function paintAll() {
  paintSteps.forEach(function (step) { step(); });
}

var FIELDS = "input, select, textarea";

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
  try {
    if (typeof field.selectionStart === "number") place.caret = [field.selectionStart, field.selectionEnd];
  } catch (e) {
    place.caret = null;
  }
  return place;
}

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
    }
  }
}
