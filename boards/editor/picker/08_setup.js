
// ---- where the board is set up ----------------------------------------------------------
// Every fact about the board stays beside what it is about, the wiring on the outputs, a
// strip's length on the strip, a screen's type on the screen. Each reads as a box in its
// section's own colour, and the whole board is set up at once in a setup mode.

// Whether the whole page is in its setup mode
var setupOn = false;

// The tooltip on everything that wears the board's chip
var BOARD_SETTING_SAYS = "Board setup, shared by every scene";

// The panels that hold a board fact, and the colour each one's box takes
var BOARD_CHIP_CLASSES = {outPanel: "outs"};
STRIPS.forEach(function (strip) { BOARD_CHIP_CLASSES[strip.id + "Panel"] = strip.id; });

// Whether the board facts in this panel can be changed just now. Every board setting is changed
// where it is shown, and only the outputs' wiring waits for its own view, where lights are
// dragged into place
function canEdit(panel) { return panel === "outPanel" ? setupOn : true; }

// The Wiring chip opens the outputs' wiring view, where it shows pressed, and a second click
// closes it
document.addEventListener("click", function (event) {
  if (event.target.closest("select, input, button, header")) return;
  if (!event.target.closest("#outFacts .boardchip")) return;
  setSetup(!setupOn);
  draw();
});

// The chip a board setting's add button carries, before its words
function boardButton(words) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "boardadd";
  button.appendChild(boardIcon());
  button.appendChild(document.createTextNode(words));
  return button;
}

// The button beside a fitted part's board setting that takes the part off the board
function removeButton(what, act) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "boardremove";
  button.textContent = "remove";
  button.title = "Take this " + what + " off the board, in every scene";
  // A hub position picks itself on a click, which a removed one cannot be
  button.addEventListener("click", function (event) {
    event.stopPropagation();
    // Check if there are scenes to lose it, since nothing brings back what they played on it
    if (state.scenes.length &&
        !confirm("Remove this " + what + " from every scene? This cannot be undone.")) return;
    act();
  });
  return button;
}

// ---- selection waits while the board is set up ------------------------------------------------
// A stretch is picked to give it a look, which setup does not do, so a tap there picks
// nothing and nothing looks picked. What was picked is held by its lamp, since the wiring
// is free to move it, and is picked again when setup ends. An output broken out or put
// back meanwhile is picked instead, as it would have been outside setup

var heldPick = null;
var heldOutput = null;

function setSetup(on) {
  if (on && !setupOn) {
    var section = active.sections[active.picked];
    heldPick = section ? lampKey(active.lamps[section.from]) : null;
    heldOutput = null;
  }
  setupOn = on;
  if (!on) {
    if (heldOutput !== null) {
      pickOutput(heldOutput);
    } else if (heldPick) {
      runs.some(function (run) {
        var at = run.lamps.map(lampKey).indexOf(heldPick);
        if (at >= 0) pick(run, sectionAt(run, at));
        return at >= 0;
      });
    }
    heldPick = null;
    heldOutput = null;
  }
  showChosen();
}

// Nothing looks picked while setup is on. The marks are drawn by the pages below, so they
// are taken off once drawn
function unmark() {
  document.querySelectorAll(".sec.picked, .card.picked").forEach(function (one) {
    one.classList.remove("picked");
  });
}

// A section's coloured box, the chip icon inside it with whatever the fact says
function boardBox(panel, parts) {
  var box = document.createElement("span");
  box.className = "chip boardchip " + BOARD_CHIP_CLASSES[panel];
  box.title = BOARD_SETTING_SAYS;
  box.appendChild(boardIcon());
  parts.forEach(function (part) {
    box.appendChild(typeof part === "string" ? document.createTextNode(part) : part);
  });
  return box;
}

function small(words) {
  var said = document.createElement("small");
  said.textContent = words;
  return said;
}

// The board's chip, three legs a side, set three apart as the smallest spacing that still
// reads as legs at 16px. It carries the board's tooltip itself, so a chip with no box around it
// says it too
function boardIcon() {
  var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("width", "13");
  svg.setAttribute("height", "13");
  svg.setAttribute("class", "boardicon");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = "<title>" + BOARD_SETTING_SAYS + "</title>" +
                  "<rect x='3' y='3' width='8' height='8' rx='1' fill='none' " +
                  "stroke='currentColor' stroke-width='1.3'/>" +
                  "<path d='M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2" +
                  "M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2' " +
                  "stroke='currentColor' stroke-width='1.3' stroke-linecap='round'/>";
  return svg;
}

// ---- the facts, in place --------------------------------------------------------------------

// Where the wiring cannot be changed an output's arrow is left out. What stands in its place
// takes no room, as the arrow does, or each output's lamps would sit further apart outside setup
function noArrow() {
  var none = document.createElement("span");
  none.style.position = "absolute";
  return none;
}

function renderOutFacts() {
  var box = document.getElementById("outFacts");
  box.textContent = "";
  box.appendChild(boardBox("outPanel", ["Wiring", small(brokenSaid())]));
  if (canEdit("outPanel")) {
    var hint = document.createElement("span");
    hint.className = "hint";
    var breaking = breakingOutputs();
    hint.textContent = "Drag lights to match your build." +
      (breaking.length > 1 ? " Arrows split or rejoin an output's three lights."
       : breaking.length ? " The arrow on " + outputSaid(breaking[0]) + " splits or rejoins it."
       : "");
    // Cut short on a narrow page, the hint is whole in its tooltip
    hint.title = hint.textContent;
    box.appendChild(hint);
  }
  // The outputs' controls are for whichever side was last worked on, as the tools are
  headSteps(box, active.strip ? lastOutputRun : active);
}

// What a strip is built as, its length and what follows it on the board line
function stripBuilt(run) {
  return run.leds + " LEDs, " + stripChipShown(run);
}

// Whether a strip is there, on the run and on the entry a fresh run is made from
function stripThere(run, there) { stripSet(run, {there: there}); }

function capitalised(text) { return text.charAt(0).toUpperCase() + text.slice(1); }

// Why a strip cannot be fitted just now, or nothing where it can. A strip taking other strips'
// terminals cannot be fitted beside them, nor they beside it
function stripBlockedBy(run) {
  if (run.there) return "";
  var fitted = runs.filter(function (one) {
    return one.strip && one.there && run.takes.indexOf(one.name) >= 0;
  });
  if (fitted.length) {
    return capitalised(run.label) + " takes " + run.connector + ", so it cannot be fitted beside " +
           fitted.map(function (one) { return one.label; }).join(" and ") + ". Remove " +
           (fitted.length > 1 ? "them" : "it") + " to fit one here.";
  }
  var taking = runs.filter(function (one) {
    return one.strip && one.there && one.takes.indexOf(run.name) >= 0;
  })[0];
  return taking ? capitalised(taking.label) + " uses " + taking.connector +
                  ". Remove it to fit a strip here." : "";
}

// Taking a strip out clears what it plays in every scene, the lines kept from a file
// included, which leaves its length unwritten and its connector off
function dropStrip(run) {
  forgetKeptFor(run);
  store();
  allBodies().forEach(function (held) {
    var kept = held.runs[run.name];
    if (!kept) return;
    kept.sections = [blank(0, run.leds - 1, run)];
    kept.picked = 0;
    kept.was = [];
    kept.undone = [];
  });
  stripThere(run, false);
  apply(slotAt(state.at).body);
  draw();
}

// A strip not fitted offers to be added, or says why it cannot be
function renderStripOut(box, run, panel) {
  box.textContent = "";
  var blocked = stripBlockedBy(run);
  if (blocked) {
    box.appendChild(boardBox(panel, ["Strip", small("not fitted")]));
    var why = document.createElement("span");
    why.className = "stripblocked says";
    why.textContent = blocked;
    box.appendChild(why);
    return;
  }
  box.appendChild(boardBox(panel, ["Strip", small("not fitted")]));
  var add = boardButton("add this strip");
  add.classList.add("addstrip");
  add.onclick = function () {
    stripThere(run, true);
    workOn(panel);
    draw();
  };
  box.appendChild(add);
}

function renderLeds(where, run) {
  var box = document.getElementById(where);
  var panel = run.id + "Panel";
  document.getElementById(panel).classList.toggle("stripout", !run.there);
  if (!run.there) {
    renderStripOut(box, run, panel);
    return;
  }
  // The strip's own count box is already the board's, so the icon goes inside it and it
  // takes the strip's colour
  if (canEdit(panel)) {
    renderStripChip(where, run);
    var says = box.querySelector(".says");
    if (says) box.removeChild(says);
    var chip = box.querySelector(".chip");
    chip.className = "chip boardchip " + BOARD_CHIP_CLASSES[panel];
    chip.title = BOARD_SETTING_SAYS;
    chip.insertBefore(boardIcon(), chip.firstChild);
    chip.appendChild(removeButton("strip", function () { dropStrip(run); }));
  } else {
    box.textContent = "";
    box.appendChild(boardBox(panel, ["Strip", small(stripBuilt(run))]));
  }
  box.appendChild(stretchCount(run));
  headSteps(box, run);
}

// ---- turning setup on ------------------------------------------------------------------------

drawSteps.after.push(function () {
  renderOutFacts();
  // What is not the board stands back while it is set up
  document.body.classList.toggle("setupall", setupOn);
  if (setupOn) unmark();
  paintAll();
});
