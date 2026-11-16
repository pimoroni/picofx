import {breakingOutputs, brokenSaid} from "./board.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps, paintAll} from "./draw.js";
import {stretchCount} from "./led_panels.js";
import {workOn} from "./led_sections.js";
import {outputSaid} from "./outputs.js";
import {BOARD_CHIP_CLASSES, active, canEdit, outs, settle, setupOn} from "./runs.js";
import {
  STRIPS, STRIP_BRIGHTNESSES, STRIP_FEWEST, STRIP_MOST, STRIP_ORDERS, stripBlockedBy,
  stripChipShown, stripDrawing, stripDrop, stripPercent, stripSet, stripThere
} from "./strips.js";
import {headSteps} from "./wiring.js";

// ---- the board set up, on the page --------------------------------------------------------------
// The facts about the board shown beside the lights, as each strip's chip and the outputs'
// adapters, and the button that turns setting up the board on.

// What follows a strip's length on the board line, its brightness or its colour order, as the
// choice on its chip
function stripChipChoice(run) {
  var choice;
  if (run.made === null) {
    choice = h("select", {
      title: "The strip's colour order. Change it if red shows as another colour",
      onchange: function () {
        stripSet(run, {order: choice.value});
        draw();
      }
    }, STRIP_ORDERS.map(function (pair) {
      return h("option", {value: pair[0], selected: (run.order || "") === pair[0]}, pair[1]);
    }));
    return choice;
  }
  // A brightness read from a file stays offered, though the list does not hold it
  var offered = STRIP_BRIGHTNESSES.indexOf(run.brightness) < 0 ?
    STRIP_BRIGHTNESSES.concat([run.brightness]).sort(function (a, b) { return a - b; }) :
    STRIP_BRIGHTNESSES;
  choice = h("select", {
    title: "Overall strip brightness, applied on top of each stretch's level",
    onchange: function () {
      stripSet(run, {brightness: Number(choice.value)});
      draw();
    }
  }, offered.map(function (brightness) {
    return h("option", {value: brightness, selected: brightness === run.brightness},
             stripPercent(brightness) + (brightness === run.made ? " (default)" : ""));
  }));
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
  return h("span", {className: "chip boardchip " + BOARD_CHIP_CLASSES[panel],
                    title: "Board setup, shared by every scene"}, boardIcon(), parts);
}

export function small(words) {
  return h("small", {}, words);
}

// The board's chip, three legs a side, set three apart as the smallest spacing that still
// reads as legs at 16px
export function boardIcon() {
  return h("svg:svg", {viewBox: "0 0 14 14", width: "13", height: "13", class: "boardicon",
                       "aria-hidden": "true",
                       html: "<rect x='3' y='3' width='8' height='8' rx='1' fill='none' " +
                             "stroke='currentColor' stroke-width='1.3'/>" +
                             "<path d='M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2" +
                             "M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2' " +
                             "stroke='currentColor' stroke-width='1.3' stroke-linecap='round'/>"});
}

function renderOutFacts() {
  var box = document.getElementById("outFacts");
  var hint = null;
  if (canEdit("outPanel")) {
    var breaking = breakingOutputs();
    var said = "Drag lights to match your build." +
      (breaking.length > 1 ? " Arrows split or rejoin an output's three lights."
       : breaking.length ? " The arrow on " + outputSaid(breaking[0]) + " splits or rejoins it."
       : "");
    // Cut short on a narrow page, the hint is whole in its tooltip
    hint = h("span", {className: "hint", title: said}, said);
  }
  replace(box, boardBox("outPanel", ["Wiring", small(brokenSaid())]), hint);
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
    replace(box, boardBox(panel, ["Strip", small(stripBuilt(run))]));
  }
  box.appendChild(stretchCount(run));
  headSteps(box, run);
}
stripDrawing.leds = renderLeds;

addStep(drawSteps.after, DRAW_AFTER, "setup", function () {
  renderOutFacts();
  // What is not the board stands back while it is set up
  document.body.classList.toggle("setupall", setupOn);
  if (setupOn) unmark();
  paintAll();
});

// A strip's chip, its length and its order or brightness to set, shown while the board is set up
function renderStripChip(where, run) {
  var count = h("input", {
    type: "number", min: STRIP_FEWEST, max: STRIP_MOST, value: run.leds,
    onchange: function () {
      var want = Math.max(STRIP_FEWEST, Math.min(STRIP_MOST, parseInt(count.value, 10) ||
                                                             STRIP_FEWEST));
      if (want === run.leds) return;
      stripSet(run, {leds: want});
      settle();
      draw();
    }
  });
  replace(document.getElementById(where),
          h("div", {className: "chip strip"}, "Strip", count, small("LEDs"), stripChipChoice(run)),
          h("span", {className: "says"}, "shared by every scene"));
}

// A strip not fitted offers to be added, which only editing the board can take up, or says
// why it cannot be
function renderStripOut(box, run, panel) {
  var blocked = stripBlockedBy(run);
  replace(box, boardBox(panel, ["Strip", small("not fitted")]),
          blocked ? h("span", {className: "stripblocked says"}, blocked)
          : h("button", {
            type: "button", className: "addstrip", disabled: !canEdit(panel),
            onclick: function () {
              stripThere(run, true);
              workOn(panel);
              draw();
            }
          }, "add this strip"));
}

// Each section is only ever seen on its own here, so each keeps its own stretch's settings
// whichever is worked on, and none changes height when another tab is chosen. The outputs'
// are for whichever of their two sides was last worked on
export var lastOutputRun = outs;

// Set the output run last worked on
export function setLastOutputRun(run) {
  lastOutputRun = run;
}
