import {draw, drawSteps, paintAll} from "./00_draw.js";
import {outputSaid} from "./03_outputs.js";
import {BOARD_CHIP_CLASSES, active, canEdit, outs, settle, setupOn} from "./03_runs.js";
import {stretchCount} from "./04_led_panels.js";
import {
  STRIPS, STRIP_BRIGHTNESSES, STRIP_FEWEST, STRIP_MOST, STRIP_ORDERS, stripBlockedBy,
  stripChipShown, stripDrawing, stripDrop, stripPercent, stripSet, stripThere
} from "./05_strips.js";
import {breakingOutputs, brokenSaid} from "./07_board.js";
import {headSteps} from "./09_wiring.js";
import {workOn} from "./10_led_sections.js";

// ---- the board set up, on the page --------------------------------------------------------------
// The facts about the board shown beside the lights, as each strip's chip and the outputs'
// adapters, and the button that turns setting up the board on.

// What follows a strip's length on the board line, its brightness or its colour order, as the
// choice on its chip
function stripChipChoice(run) {
  var choice = document.createElement("select");
  if (run.made === null) {
    STRIP_ORDERS.forEach(function (pair) {
      var option = document.createElement("option");
      option.value = pair[0];
      option.textContent = pair[1];
      if ((run.order || "") === pair[0]) option.selected = true;
      choice.appendChild(option);
    });
    choice.title = "The strip's colour order. Change it if red shows as another colour";
    choice.onchange = function () {
      stripSet(run, {order: choice.value});
      draw();
    };
    return choice;
  }
  // A brightness read from a file stays offered, though the list does not hold it
  var offered = STRIP_BRIGHTNESSES.indexOf(run.brightness) < 0 ?
    STRIP_BRIGHTNESSES.concat([run.brightness]).sort(function (a, b) { return a - b; }) :
    STRIP_BRIGHTNESSES;
  offered.forEach(function (brightness) {
    var option = document.createElement("option");
    option.value = brightness;
    option.textContent = stripPercent(brightness) + (brightness === run.made ? " (default)" : "");
    if (brightness === run.brightness) option.selected = true;
    choice.appendChild(option);
  });
  choice.title = "Overall strip brightness, applied on top of each stretch's level";
  choice.onchange = function () {
    stripSet(run, {brightness: Number(choice.value)});
    draw();
  };
  return choice;
}
STRIPS.forEach(function (strip) { BOARD_CHIP_CLASSES[strip.id + "Panel"] = strip.id; });

// Nothing looks picked while setup is on. The marks are drawn by the pages below, so they
// are taken off once drawn
function unmark() {
  document.querySelectorAll(".sec.picked, .card.picked").forEach(function (one) {
    one.classList.remove("picked");
  });
}

// A section's coloured box, the chip icon inside it with whatever the fact says
export function boardBox(panel, parts) {
  var box = document.createElement("span");
  box.className = "chip boardchip " + BOARD_CHIP_CLASSES[panel];
  box.title = "Board setup, shared by every scene";
  box.appendChild(boardIcon());
  parts.forEach(function (part) {
    box.appendChild(typeof part === "string" ? document.createTextNode(part) : part);
  });
  return box;
}

export function small(words) {
  var said = document.createElement("small");
  said.textContent = words;
  return said;
}

// The board's chip, three legs a side, set three apart as the smallest spacing that still
// reads as legs at 16px
export function boardIcon() {
  var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("width", "13");
  svg.setAttribute("height", "13");
  svg.setAttribute("class", "boardicon");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = "<rect x='3' y='3' width='8' height='8' rx='1' fill='none' " +
                  "stroke='currentColor' stroke-width='1.3'/>" +
                  "<path d='M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2" +
                  "M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2' " +
                  "stroke='currentColor' stroke-width='1.3' stroke-linecap='round'/>";
  return svg;
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
    chip.title = "Board setup, shared by every scene";
    chip.insertBefore(boardIcon(), chip.firstChild);
    chip.appendChild(stripDrop(run));
  } else {
    box.textContent = "";
    box.appendChild(boardBox(panel, ["Strip", small(stripBuilt(run))]));
  }
  box.appendChild(stretchCount(run));
  headSteps(box, run);
}
stripDrawing.leds = renderLeds;

drawSteps.after.push(function () {
  renderOutFacts();
  // What is not the board stands back while it is set up
  document.body.classList.toggle("setupall", setupOn);
  if (setupOn) unmark();
  paintAll();
});

// A strip's chip, its length and its order or brightness to set, shown while the board is set up
function renderStripChip(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var chip = document.createElement("div");
  chip.className = "chip strip";
  chip.appendChild(document.createTextNode("Strip"));
  var count = document.createElement("input");
  count.type = "number";
  count.min = STRIP_FEWEST;
  count.max = STRIP_MOST;
  count.value = run.leds;
  count.onchange = function () {
    var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST, parseInt(count.value, 10) ||
                                                           STRIP_FEWEST));
    if (want === run.leds) return;
    stripSet(run, {leds: want});
    settle();
    draw();
  };
  chip.appendChild(count);
  var unit = document.createElement("small");
  unit.textContent = "LEDs";
  chip.appendChild(unit);
  chip.appendChild(stripChipChoice(run));
  box.appendChild(chip);
  var says = document.createElement("span");
  says.className = "says";
  says.textContent = "shared by every scene";
  box.appendChild(says);
}

// A strip not fitted offers to be added, which only editing the board can take up, or says
// why it cannot be
function renderStripOut(box, run, panel) {
  box.textContent = "";
  box.appendChild(boardBox(panel, ["Strip", small("not fitted")]));
  var blocked = stripBlockedBy(run);
  if (blocked) {
    var why = document.createElement("span");
    why.className = "stripblocked says";
    why.textContent = blocked;
    box.appendChild(why);
    return;
  }
  var add = document.createElement("button");
  add.type = "button";
  add.className = "addstrip";
  add.textContent = "add this strip";
  add.disabled = !canEdit(panel);
  add.onclick = function () {
    stripThere(run, true);
    workOn(panel);
    draw();
  };
  box.appendChild(add);
}

// Each section is only ever seen on its own here, so each keeps its own stretch's settings
// whichever is worked on, and none changes height when another tab is chosen. The outputs'
// are for whichever of their two sides was last worked on
export var lastOutputRun = outs;

// Set the output run last worked on
export function setLastOutputRun(run) {
  lastOutputRun = run;
}
