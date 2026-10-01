
// ---- the figure beside each slider --------------------------------------------------------
// Each slider can show beside it the value the file writes, with its unit, in a box that takes
// one typed in. Typed within the slider's reach, the slider moves to it; typed past an end,
// the slider sits at that end and the value is kept as typed, so the file writes exactly it.
// The figures are in a drawer at the right of the sliders, shut until opened, one for the
// whole panel, and a viewer's page remembers which way they left it.
//
// Every figure rises as its slider goes right, as the setting does. So a speed set as
// an interval between steps is shown as how many times a second, and a signal's as how fast
// it runs against a real one. A slider moving several settings shows the first of its keys it
// changes, the rest following it. A wave's speed is shown without its sign, which way it runs
// being Reverse's to say.

document.body.classList.add("figures");

// The settings a slider may be shown by, in the order they are looked for
var FIGURE_KEYS = {
  pace: ["speed", "interval", "green_interval", "bright_max"],
  mood: ["length", "sat", "steps", "dimness", "duty", "flashes", "ease", "fade"]
};

// A real signal's green interval, which a signal's speed is shown against
var SIGNAL_GREEN = {"Traffic light": 12, "Pelican crossing": 20};

// How a setting's value is shown, the figure rising as the slider does, and taken back
function figureWay(key, look) {
  var times = {unit: "/s", show: function (v) { return 1 / v; },
               take: function (f) { return 1 / f; }};
  var same = function (unit) {
    return {unit: unit, show: function (v) { return v; }, take: function (f) { return f; }};
  };
  var percent = {unit: "%", show: function (v) { return v * 100; },
                 take: function (f) { return f / 100; }};
  if (key === "speed") return same("/s");
  if (key === "interval" || key === "bright_max") return times;
  if (key === "green_interval") {
    var real = SIGNAL_GREEN[look.name] || 12;
    return {unit: "\u00d7", show: function (v) { return real / v; },
            take: function (f) { return real / f; }};
  }
  if (key === "length") return same("lights");
  if (key === "ease" || key === "fade") return same("s");
  if (["sat", "dimness", "duty"].indexOf(key) >= 0) return percent;
  return same("");
}

// Whether the drawer is open, which a viewer's page keeps between visits
var FIGURES_KEPT = "fx-picker-figures-open";
var figuresOpen = false;
try {
  figuresOpen = window.localStorage.getItem(FIGURES_KEPT) === "1";
} catch (e) {
  figuresOpen = false;
}

// The typed values of the stretch whose lines are being written, which linesFor applies
var exactNow = null;

var oneExactLines = linesFor;

linesFor = function (look, target, pace, mood, colour) {
  var lines = oneExactLines(look, target, pace, mood, colour);
  if (!exactNow) return lines;
  Object.keys(exactNow).forEach(function (slider) {
    var typed = exactNow[slider];
    if (!typed) return;
    // A trail is the fall of a split fade, so a typed one replaces the part after its bar
    if (typed.key === "fade") {
      lines = lines.map(function (line) {
        return line.replace(/(\sfade=[\d.]+\|)[\d.]+/, "$1" + typed.value);
      });
      return;
    }
    var setting = new RegExp("(^|\\s)" + typed.key + "=(-?)[\\d.]+");
    lines = lines.map(function (line) {
      return line.replace(setting, function (all, space, sign) {
        return space + typed.key + "=" + sign + typed.value;
      });
    });
  });
  return lines;
};

// Both ways a stretch's lines are asked for carry its typed values: the file and the preview
function withExact(exact, write) {
  var had = exactNow;
  exactNow = exact || null;
  try {
    return write();
  } finally {
    exactNow = had;
  }
}

var oneExactSection = sectionLines;

sectionLines = function (run, section, look) {
  return withExact(section.exact, function () { return oneExactSection(run, section, look); });
};

var oneExactPlay = livePlay;

livePlay = function (look, holder, t, slot, count, sim) {
  var exact = holder && holder !== MIDDLING ? holder.exact : null;
  return withExact(exact, function () { return oneExactPlay(look, holder, t, slot, count, sim); });
};

// A setting's value in a stretch's lines, without its sign, or null where none names it. A
// fade is read as its fall, the part after its bar, which is what a trail is
function settingIn(lines, key) {
  var setting = new RegExp("(^|\\s)" + key + "=(?:[\\d.]+\\|)?(-?[\\d.]+)");
  for (var at = 0; at < lines.length; at++) {
    var found = lines[at].match(setting);
    if (found) return Math.abs(Number(found[2]));
  }
  return null;
}

// The stretch's lines with one slider at a value and nothing typed
function linesAt(run, section, look, slider, value) {
  var at = Object.assign({}, section, {exact: null});
  at[slider] = value;
  return sectionLines(run, at, look);
}

// The setting a slider moves, the first of its keys whose value it changes
function figureKey(run, section, look, slider) {
  var low = linesAt(run, section, look, slider, 0);
  var high = linesAt(run, section, look, slider, 1);
  return FIGURE_KEYS[slider].filter(function (key) {
    return settingIn(low, key) !== null && settingIn(low, key) !== settingIn(high, key);
  })[0] || null;
}

function figureSaid(value) {
  return String(Math.round(value * 100) / 100);
}

// The slider's place that writes nearest a value, looked for along its whole reach. Past its
// reach the slider sits at the nearer end, not at the first place that rounds to it
function placeFor(run, section, look, slider, key, value) {
  var best = 0, nearest = Infinity;
  for (var step = 0; step <= 200; step++) {
    var place = step / 200;
    var gives = settingIn(linesAt(run, section, look, slider, place), key);
    if (gives !== null && Math.abs(gives - value) < nearest) {
      nearest = Math.abs(gives - value);
      best = place;
    }
  }
  if (nearest > 1e-6) {
    var low = settingIn(linesAt(run, section, look, slider, 0), key);
    var high = settingIn(linesAt(run, section, look, slider, 1), key);
    best = Math.abs(low - value) < Math.abs(high - value) ? 0 : 1;
  }
  return {place: best, off: nearest};
}

// A palette's colours, a swatch for each its lines name, drawn afresh as its slider moves
function paintPalette(swatches, lines) {
  swatches.textContent = "";
  (lines.join(" ").match(/colour=[^\s:]+/g) || []).forEach(function (said) {
    var chip = document.createElement("span");
    chip.className = "repeatchip";
    chip.style.background = inkOf(said.slice(7));
    chip.title = said.slice(7);
    swatches.appendChild(chip);
  });
}

// The box a figure is typed in and its unit, each a cell of the sliders' grid
function figureCells(said, unit, title, take) {
  var box = document.createElement("input");
  box.type = "text";
  box.inputMode = "decimal";
  box.className = "figurebox";
  box.value = said;
  box.title = title;
  box.onchange = function () {
    var typed = parseFloat(box.value.replace(",", "."));
    if (!(typed > 0)) {
      box.value = said;
      return;
    }
    take(typed);
    draw();
  };
  var units = document.createElement("span");
  units.className = "figureunit";
  units.textContent = unit;
  return [box, units];
}

var oneFigureChosen = renderChosen;

renderChosen = function (where, run) {
  oneFigureChosen(where, run);
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var look = section && lookNamed(section.look);
  var tuning = box && box.querySelector(".chosen .tuning");
  if (!tuning || !look) return;
  function live() { return run.sections[run.picked]; }
  tuning.classList.toggle("figuresopen", figuresOpen);

  var ranges = Array.prototype.slice.call(tuning.querySelectorAll("input[type=range]"));
  var boxes = [];
  ranges.forEach(function (range) {
    var slider = (range.dataset.focus || "").split("-").pop();
    var cells, way = null, key = null, widest = 3;
    var timing = range.dataset.timing;
    if (timing) {
      // A signal's timing is its seconds already, typed past the slider's ends as it is
      widest = Math.max(String(range.min).length, String(range.max).length) + 2;
      cells = figureCells(figureSaid(Number(range.value)), "s",
                          "seconds, typed exactly, past the slider's ends too", function (typed) {
        var mine = live();
        mine.timings = Object.assign({}, mine.timings);
        mine.timings[timing] = Math.round(typed * 100) / 100;
      });
    } else if (slider === "mood" && look.mood === "Palette") {
      // A palette is its colours, not a number, so its slot shows them
      var swatches = document.createElement("span");
      swatches.className = "figurebox paletteswatches";
      paintPalette(swatches, sectionLines(run, section, look));
      // Across the box and unit columns, from where the boxes start, being wider than a box
      swatches.style.gridColumn = "span 2";
      cells = [swatches, null];
    } else if (slider === "level") {
      var bright = section.level === undefined ? 1 : section.level;
      cells = figureCells(String(Math.round(bright * 100)), "%",
                          "how bright, typed as a percentage", function (typed) {
        live().level = Math.max(0.01, Math.min(1, typed / 100));
      });
    } else if (slider === "pace" || slider === "mood") {
      key = figureKey(run, section, look, slider);
      if (key) {
        way = figureWay(key, look);
        // As wide as the widest figure the slider can reach, so dragging it never resizes its
        // column and with it the slider
        [0, 0.5, 1].forEach(function (place) {
          var reach = figureSaid(way.show(settingIn(linesAt(run, section, look, slider, place),
                                                   key)));
          widest = Math.max(widest, reach.length);
        });
        var typedHere = section.exact && section.exact[slider];
        var value = typedHere ? typedHere.value : settingIn(sectionLines(run, section, look), key);
        cells = figureCells(figureSaid(way.show(value)), way.unit,
                            "the file's " + key + ", typed exactly, past the slider's ends too",
                            function (typed) {
          var wanted = way.take(typed);
          var mine = live();
          var found = placeFor(run, mine, look, slider, key, wanted);
          mine[slider] = found.place;
          mine.exact = Object.assign({}, mine.exact);
          if (found.off > 1e-6) {
            mine.exact[slider] = {key: key, value: Math.round(wanted * 1000) / 1000};
          } else {
            delete mine.exact[slider];
          }
        });
      }
    } else {
      return;
    }
    // A slider with no one figure keeps its row's cells, empty, so the columns stay whole
    if (!cells) {
      cells = [document.createElement("span"), document.createElement("span")];
      cells[0].className = "figurebox";
      cells[1].className = "figureunit";
    }
    // A figure typed past the slider's end, wider than any it reaches, widens it to fit
    if (cells[0].tagName === "INPUT") {
      boxes.push({box: cells[0], chars: Math.max(widest, String(cells[0].value || "").length)});
    }
    if (cells[1]) range.parentNode.insertBefore(cells[1], range.nextSibling);
    range.parentNode.insertBefore(cells[0], range.nextSibling);

    // Moved, the slider is the setting again, and its figure follows it
    var moved = range.oninput;
    range.oninput = function () {
      var mine = live();
      if (mine.exact && mine.exact[slider]) {
        mine.exact = Object.assign({}, mine.exact);
        delete mine.exact[slider];
      }
      if (moved) moved.call(range);
      if (cells[0].classList.contains("paletteswatches")) {
        paintPalette(cells[0], sectionLines(run, mine, look));
        return;
      }
      if (cells[0].tagName !== "INPUT") return;
      if (timing) cells[0].value = figureSaid(Number(range.value));
      else if (slider === "level") cells[0].value = String(Math.round(Number(range.value) * 100));
      else cells[0].value = figureSaid(way.show(settingIn(sectionLines(run, mine, look), key)));
    };
  });

  // Every box in the panel as wide as the widest, so they line up and none moves as it changes
  var chars = boxes.reduce(function (most, one) { return Math.max(most, one.chars); }, 3);
  boxes.forEach(function (one) { one.box.style.width = (chars + 0.5) + "ch"; });

  // The drawer's handle, down the right of the sliders, which opens and shuts every figure
  var handle = document.createElement("button");
  handle.type = "button";
  handle.className = "figurehandle";
  handle.textContent = figuresOpen ? "\u203a" : "\u2039";
  handle.title = figuresOpen ? "hide the figures" : "show each setting's figure, to type one in";
  handle.setAttribute("aria-expanded", figuresOpen ? "true" : "false");
  handle.style.gridRow = "1 / span " + ranges.length;
  handle.onclick = function () {
    figuresOpen = !figuresOpen;
    try {
      window.localStorage.setItem(FIGURES_KEPT, figuresOpen ? "1" : "0");
    } catch (e) {
      // Kept only for this visit where the page may not keep anything
    }
    draw();
  };
  tuning.appendChild(handle);
};

draw();
