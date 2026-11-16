import {draw} from "./00_draw.js";
import {BLINK, blinkNamed} from "./02_blink.js";
import {chosenSteps} from "./03_runs.js";

// ---- blinking through several colours, on the chosen stretch ------------------------------------
// The chips of the colours Blink steps through, drawn among the chosen stretch's settings.

// Above the swatches, the colours it blinks through, each a chip that the picker changes
// while it is chosen, with a way to add another and to take one away
chosenSteps.push(function (where, run) {
  var box = document.getElementById(where);
  var section = run && run.sections[run.picked];
  var pick = box && box.querySelector(".chosen .colourpick");
  var first = section && run.lamps[section.from];
  if (!pick || section.look !== BLINK || !first || !first.colour) return;
  function live() { return run.sections[run.picked]; }
  var blinks = section.blinks || {colours: [section.colour || "#ff0000"], at: 0};
  blinks.colours[blinks.at] = section.colour;
  section.blinks = blinks;

  function choose(at) {
    var mine = live();
    mine.blinks.at = at;
    mine.colour = mine.blinks.colours[at];
    mine.custom = !blinkNamed(mine.colour);
    draw();
  }

  var row = document.createElement("div");
  row.className = "blinklist";
  var said = document.createElement("span");
  said.className = "blinksay";
  said.textContent = blinks.colours.length > 1 ? "Blinks through" : "Blinks in";
  row.appendChild(said);
  blinks.colours.forEach(function (hex, at) {
    var chip = document.createElement("button");
    chip.type = "button";
    chip.className = "blinkchip" + (at === blinks.at ? " on" : "");
    chip.style.setProperty("--chip", hex);
    chip.title = (at === blinks.at ? "the colour being edited below, " : "change ") +
                 (blinkNamed(hex) || hex);
    chip.onclick = function () { choose(at); };
    row.appendChild(chip);
    if (blinks.colours.length > 1) {
      var drop = document.createElement("button");
      drop.type = "button";
      drop.className = "blinkdrop";
      drop.textContent = "\u00d7";
      drop.title = "stop blinking in " + (blinkNamed(hex) || hex);
      drop.onclick = function () {
        var mine = live();
        mine.blinks.colours.splice(at, 1);
        var left = mine.blinks.colours;
        mine.blinks.at = Math.min(mine.blinks.at, left.length - 1);
        mine.colour = left[mine.blinks.at];
        mine.custom = !blinkNamed(mine.colour);
        if (left.length === 1) mine.blinks = undefined;
        draw();
      };
      row.appendChild(drop);
    }
  });
  var more = document.createElement("button");
  more.type = "button";
  more.className = "blinkmore";
  more.textContent = "+ another colour";
  more.title = "blink through several colours, one per blink";
  // The colour added is a copy of the last, a custom one included, to be changed from there
  more.onclick = function () {
    var mine = live();
    if (!mine.blinks) mine.blinks = {colours: [mine.colour], at: 0};
    var colours = mine.blinks.colours;
    colours.push(colours[colours.length - 1]);
    choose(colours.length - 1);
  };
  row.appendChild(more);
  pick.insertBefore(row, pick.firstChild);
});
