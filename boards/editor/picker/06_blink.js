
// ---- blinking through several colours -----------------------------------------------------
// Blink takes one colour or several. With several it blinks through them in turn, one a beat,
// which is picofx's rgb_blink. The list is the stretch's blinks, {colours, at}, at being the
// one the picker above is changing; a stretch with no list has the one colour it always had.
// A list is written with the words and hexes at full and the stretch's brightness as level=,
// rgb_blink taking one level for all of them.

var BLINK = "Blink";

// The colours a stretch blinks through, where it has more than one and plays them in colour
function blinkList(run, section) {
  var first = run && run.lamps[section.from];
  if (section.look !== BLINK || !section.blinks || section.blinks.colours.length < 2 ||
      !first || !first.colour) return null;
  return section.blinks.colours;
}

// A colour's word, black included, which a set of colours to blink through may hold
function blinkNamed(hex) {
  return hex.replace("#", "").toLowerCase() === "000000" ? "black" : wordFor(hex);
}

function blinkWord(hex) {
  return blinkNamed(hex) || hex.replace("#", "").toLowerCase();
}

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
    chip.title = (at === blinks.at ? "the colour the picker below is changing, " : "change ") +
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
  more.title = "blink through several colours in turn, one a beat";
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
