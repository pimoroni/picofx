import {h, replace} from "./00_dom.js";
import {draw, drawSteps, paintAll} from "./00_draw.js";
import {BOARD} from "./01_looks.js";
import {active, blank, lampKey, outputSaid, pick, pickOutput, runs, sectionAt} from "./03_runs.js";
import {panelTools} from "./04_led_panels.js";
import {allBodies, apply, slotAt, state, store} from "./04_scenes.js";
import {stripChipChoice, stripChipShown, stripLengthField, stripSet} from "./05_effects.js";
import {breakingOutputs, brokenSaid} from "./07_board.js";
import {workOn} from "./10_led_sections.js";
import {lastOutputRun, showChosen} from "./11_tabs.js";
import {forgetKeptFor} from "./27_readback.js";

export var setupOn = false;

export var BOARD_CHIP_COLOURS = {outPanel: "var(--boardOuts)"};
BOARD.strips.forEach(function (strip) { BOARD_CHIP_COLOURS[strip.name + "Panel"] = strip.colour; });

export function canEdit(panel) { return setupOn; }

var heldPick = null;
var heldOutput = null;

export function holdOutput(out) {
  heldOutput = out;
}

export function setSetup(on) {
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

function unmark() {
  document.querySelectorAll(".lamp.ringed").forEach(function (one) {
    one.classList.remove("ringed");
  });
  document.querySelectorAll(".looks [aria-pressed=true]").forEach(function (one) {
    one.setAttribute("aria-pressed", "false");
  });
  document.querySelectorAll(".stretches li[aria-current]").forEach(function (one) {
    one.removeAttribute("aria-current");
  });
}

export function boardBox(panel, parts) {
  return h("span", {class: "chip", style: {"--chip": BOARD_CHIP_COLOURS[panel]},
                    title: "Board setup, shared by every scene"}, boardIcon(), parts);
}

export function small(words) {
  return h("small", {}, words);
}

export function boardIcon() {
  return h("svg:svg", {viewBox: "0 0 14 14", width: 13, height: 13, class: "boardicon", "aria-hidden": "true",
                       html: "<rect x='3' y='3' width='8' height='8' rx='1' fill='none' " +
                             "stroke='currentColor' stroke-width='1.3'/>" +
                             "<path d='M4 0.8V3M7 0.8V3M10 0.8V3M4 11v2.2M7 11v2.2M10 11v2.2" +
                             "M0.8 4H3M0.8 7H3M0.8 10H3M11 4h2.2M11 7h2.2M11 10h2.2' " +
                             "stroke='currentColor' stroke-width='1.3' stroke-linecap='round'/>"});
}

function renderOutFacts() {
  var hint = null;
  if (canEdit("outPanel")) {
    var breaking = breakingOutputs();
    var said = "Drag each light to match its position in your build." +
      (breaking.length > 1 ? " Arrows split an output into three mono lights, or rejoin them."
       : breaking.length ? " The arrow on " + outputSaid(breaking[0]) + " splits it into three " +
                           "mono lights, or rejoins them." : "");
    hint = h("small", {title: said}, said);
  }
  replace(document.getElementById("outFacts"),
          boardBox("outPanel", ["Wiring", small(brokenSaid())]), hint,
          setupOn ? null : panelTools(active.strip ? lastOutputRun : active));
}

function stripBuilt(run) {
  return run.leds + " LEDs, " + stripChipShown(run);
}

function stripThere(run, there) { stripSet(run, {there: there}); }

function capitalised(text) { return text.charAt(0).toUpperCase() + text.slice(1); }

export function stripBlockedBy(run) {
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

export function dropStrip(run) {
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

function stripOut(run, panel) {
  var blocked = stripBlockedBy(run);
  return [boardBox(panel, ["Strip", small("not fitted")]),
          blocked ? h("small", {}, blocked)
                  : h("button", {type: "button", disabled: !canEdit(panel),
                                 onclick: function () {
                                   stripThere(run, true);
                                   workOn(panel);
                                   draw();
                                 }}, "add this strip")];
}

export function renderLeds(where, run) {
  var panel = run.id + "Panel";
  document.getElementById(panel).toggleAttribute("data-absent", !run.there);
  var chip = !run.there ? stripOut(run, panel)
           : canEdit(panel) ? boardBox(panel, ["Strip", stripLengthField(run), small("LEDs"), stripChipChoice(run),
                                               h("button", {type: "button",
                                                            title: "Remove this strip from every scene",
                                                            onclick: function () { dropStrip(run); }}, "\u00d7")])
           : boardBox(panel, ["Strip", small(stripBuilt(run))]);
  replace(document.getElementById(where), chip, run.there && !setupOn ? panelTools(run) : null);
}

export function setupButton(label, on, act) {
  return h("button", {type: "button", class: "setupbutton", "aria-pressed": on ? "true" : "false",
                      onclick: act}, boardIcon(), label);
}

drawSteps.after.push(function () {
  renderOutFacts();
  document.body.toggleAttribute("data-setup", setupOn);
  if (setupOn) unmark();
  paintAll();
});
