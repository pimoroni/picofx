import {draw, drawSteps} from "../03_runs.js";
import {
  PART_DRAWINGS, REMOTE_COLOURS, addScene, bodyParts, sceneCanWait, sceneMark, sceneMarked,
  sceneNumbers, sceneRestarts, sceneTriggerLeads, sceneWaitsFor, state
} from "../04_scenes.js";
import {boardLineSteps} from "../07_board.js";
import {BOARD_CHIP_CLASSES, boardBox, canEdit, small} from "../08_setup.js";
import {TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches} from "../11_tabs.js";
import {boardResidue, boardTokens, unquoted} from "../27_readback.js";
import {
  PIR_ART, REMOTE_ART_JOINS, REMOTE_ART_RADIUS, REMOTE_BUTTONS, REMOTE_ROWS, remoteArt,
  remoteArtAt, remoteArtJoin
} from "./14_sensor_art.js";

// ---- the Sensor tab -----------------------------------------------------------------------------
// What is on the sensor connector and what it does, as a tab after Sound. Only what is fitted is
// board setup, chosen in Edit board. What each of a remote's buttons does is set on the Always on
// tab for every scene, and a scene can change any button while it shows, as it can any light.
// Two buttons are the board's in every scene: OK / Stop puts it in standby and wakes it, so there
// is always a way to stop it, and Play / Pause holds the effects where they stand.

// What the sensor connector can have on it: [kind, as the choice says it, under the tab's name,
// where it sits]
var SENSOR_KINDS = [["none", "nothing", "none", ""],
                    ["ir", "an Aye Arr Remote", "Aye Arr",
                     "through an IR Receiver Stick on the sensor connector"],
                    ["pir", "a PIR Stick", "PIR Stick", "on the sensor connector"]];

state.sensorKind = "none";
// The choices of the tab being edited, by button, where it changes what a button does
state.remote = {};
// The buttons the file gave twice in the tab being edited, whose second lines are kept as written
state.remoteRepeats = [];

BOARD_CHIP_CLASSES.sensorPanel = "sensor";

function sensorFacts() {
  return SENSOR_KINDS.filter(function (one) { return one[0] === state.sensorKind; })[0];
}

function remoteFitted() { return state.sensorKind === "ir"; }
function pirFitted() { return state.sensorKind === "pir"; }

// A PIR Stick's two triggers, chosen for as a remote's buttons are, and held with them
var MOTION_TRIGGERS = ["MOTION_STARTS", "MOTION_STOPS"];

// Whether what a trigger belongs to is fitted, a button the remote and motion the PIR Stick
function triggerFitted(trigger) {
  return MOTION_TRIGGERS.indexOf(trigger) >= 0 ? pirFitted() : remoteFitted();
}

// The triggers of what is fitted, in the order their lines are written
function fittedTriggers() {
  return pirFitted() ? MOTION_TRIGGERS
       : remoteFitted() ? REMOTE_BUTTONS.map(function (button) { return button[0]; }) : [];
}

// ---- what each button does --------------------------------------------------------------------
// A choice is a word: nothing, order (a number's scene by place), next, previous, first, restart,
// or scene: and a scene's own mark, which keeps the button on that scene when it moves. The board's
// own two buttons are standby and pause. A number is bound to the scene in its place, as the
// scene's colour is its button's, so a number only goes there or does nothing

function isNumber(button) { return /^\d_/.test(button); }

// The buttons that do the same in every scene, and what they do
var REMOTE_FIXED = {OK_STOP: ["standby", "Standby and wake, in every scene"],
                    PLAY_PAUSE: ["pause", "Pause the effects where they stand, in every scene"]};

// A scene can wait for a button while a remote is fitted
sceneCanWait = function () { return remoteFitted() || pirFitted(); };
sceneWaitsFor = function () { return pirFitted() ? "motion" : "a button"; };

// The scenes a scene goes to on what is fitted, from each trigger's choice in that scene: its
// own, then Always on's, then the trigger's default. The tab being edited holds its choices in
// state.remote rather than its body
sceneTriggerLeads = function (at) {
  var count = state.scenes.length;
  var always = state.at < 0 ? state.remote : state.always.body && state.always.body.remote || {};
  var body = state.scenes[at].body;
  var own = at === state.at ? state.remote : body && body.remote || {};
  var leads = [];
  fittedTriggers().forEach(function (trigger) {
    if (REMOTE_FIXED[trigger]) return;
    var choice = own[trigger] !== undefined ? own[trigger]
               : always[trigger] !== undefined ? always[trigger] : remoteDefault(trigger);
    var scene = choice === "order" ? sceneInOrder(trigger)
              : choice.indexOf("scene:") === 0 ? sceneMarked(choice.slice(6)) : null;
    if (scene) leads.push(state.scenes.indexOf(scene));
    else if (choice === "next") leads.push((at + 1) % count);
    else if (choice === "previous") leads.push((at + count - 1) % count);
    else if (choice === "first") leads.push(0);
  });
  return leads;
};

// What a button does where Always on chooses nothing else: a number goes to the scene in its
// place, 0 to the tenth, and the side arrows step back and on. With no scenes none of them has
// anywhere to go
function remoteDefault(button) {
  if (/^\d_/.test(button)) return "order";
  if (!state.scenes.length) return "nothing";
  if (button === "LEFT") return "previous";
  if (button === "RIGHT") return "next";
  return "nothing";
}

// The scene a number goes to in order, 0 being the tenth
function sceneInOrder(button) {
  var number = Number(button.charAt(0));
  return state.scenes[(number || 10) - 1] || null;
}

// What a button does on the tab being edited, as {choice, from}. From is own where the tab
// chooses it, always where a scene leaves it to Always on, and fixed for the board's own buttons
function remoteResolved(button) {
  if (REMOTE_FIXED[button]) return {choice: REMOTE_FIXED[button][0], from: "fixed"};
  if (state.remote[button] !== undefined) return {choice: state.remote[button], from: "own"};
  if (state.at < 0) return {choice: remoteDefault(button), from: "own"};
  var always = state.always.body && state.always.body.remote || {};
  return {choice: always[button] !== undefined ? always[button] : remoteDefault(button),
          from: "always"};
}

// What a choice does, in the words a row says it, or "" where it does nothing. A scene is said
// as one, so it is not taken for a step or Standby that a scene's name happens to match
function remoteSays(choice, button) {
  if (choice === "order") {
    var scene = sceneInOrder(button);
    return scene ? "Scene: " + scene.name : "";
  }
  if (choice.indexOf("scene:") === 0) {
    var marked = sceneMarked(choice.slice(6));
    return marked ? "Scene: " + marked.name : "";
  }
  // Restart begins the scene showing again, or Always on's effects where there are no scenes
  if (choice === "restart") {
    return state.at >= 0 ? "Scene: " + state.scenes[state.at].name + ", from the start"
         : state.scenes.length ? "Restart the scene showing" : "Restart the effects";
  }
  return {nothing: "", next: "Next scene", previous: "Previous scene", first: "First scene",
          standby: "Standby", pause: "Pause"}[choice];
}

// Whether going to a scene while it shows does something other than begin it again. Going to a
// scene starts it, which begins its effects again where it restarts, and otherwise starts only
// its time again. A waiting scene that does not restart has neither to do
function sceneSelfDiffers(scene) {
  return !scene.waits && !sceneRestarts(scene);
}

// The trigger in this tab that goes to the scene showing, which waits and does not restart, so
// does nothing, or null
function triggerDoingNothing() {
  if (state.at < 0) return null;
  var showing = state.scenes[state.at];
  if (sceneRestarts(showing) || sceneSelfDiffers(showing)) return null;
  return fittedTriggers().filter(function (trigger) {
    return state.remote[trigger] === "scene:" + sceneMark(showing);
  })[0] || null;
}

// Whether a button does anything on the tab being edited
function remoteDoes(button) {
  return triggerFitted(button) && remoteSays(remoteResolved(button).choice, button) !== "";
}

// The number button bound to a scene by its place, which its card wears while a remote is fitted
// and Always on leaves the number going there. None past the tenth scene
sceneNumbers = function (scene) {
  var at = state.scenes.indexOf(scene);
  if (!remoteFitted() || at > 9) return [];
  var button = REMOTE_BUTTONS.filter(function (one) {
    return one[0].charAt(0) === String((at + 1) % 10) && isNumber(one[0]);
  })[0][0];
  var always = state.at < 0 ? state.remote : state.always.body && state.always.body.remote || {};
  return always[button] === "nothing" ? [] : [(at + 1) % 10];
};

// A button's name as a reader says it, such as "1 Red" or "OK / Stop"
function remoteWords(name) {
  if (name === "ANTICLOCK") return "Anticlockwise";
  if (name === "MOTION_STARTS") return "Motion starts";
  if (name === "MOTION_STOPS") return "Motion stops";
  var words = name.split("_").map(function (word) {
    if (/^\d$/.test(word) || word === "OK") return word;
    return word.charAt(0) + word.slice(1).toLowerCase();
  });
  return /^\d_/.test(name) ? words.join(" ") : words.join(" / ");
}

// The colour of a button's leader while it does something
function remoteInk(name) {
  if (name === "8_WHITE") return "#a7a9ac";
  if (name === "6_YELLOW") return "#e0cf00";
  if (name === "0_RAINBOW") return "#92278f";
  var number = /^(\d)_/.exec(name);
  return number ? REMOTE_COLOURS[Number(number[1]) - 1] : "#808285";
}

// A row's choice of what its button does. On a scene's tab the first choice leaves it to
// Always on, saying what that does, its row's stripes saying whose it is
function remoteRowChoice(row, button) {
  var resolved = remoteResolved(button);
  var choice = document.createElement("select");
  choice.dataset.choice = button;
  function option(parent, value, words) {
    var one = document.createElement("option");
    one.value = value;
    one.textContent = words;
    parent.appendChild(one);
  }
  var own = choice;
  if (state.at >= 0) {
    var always = state.always.body && state.always.body.remote || {};
    var under = always[button] !== undefined ? always[button] : remoteDefault(button);
    var kept = document.createElement("optgroup");
    kept.label = "As Always on";
    option(kept, "", remoteSays(under, button) || "Nothing");
    choice.appendChild(kept);
    own = document.createElement("optgroup");
    own.label = "In this scene";
    choice.appendChild(own);
    row.title = "Striped where it does what Always on sets";
  }
  // A number goes to the scene in its place or does nothing
  if (isNumber(button)) {
    option(own, "order", "Scene: " + sceneInOrder(button).name);
    option(own, "nothing", "Nothing");
  } else if (!state.scenes.length) {
    // With no scenes there is nothing to go to, only Always on's effects to begin again
    option(own, "nothing", "Nothing");
    option(own, "restart", remoteSays("restart", button));
  } else {
    option(own, "nothing", "Nothing");
    var showing = state.at >= 0 ? state.scenes[state.at] : null;
    // A file's choice of the scene showing where that does nothing is kept, for its note to say why
    var keptNothing = showing && resolved.from === "own" && !sceneRestarts(showing) &&
                      !sceneSelfDiffers(showing) && resolved.choice === "scene:" + sceneMark(showing);
    var scenes = document.createElement("optgroup");
    scenes.label = "Go to a scene";
    state.scenes.forEach(function (scene) {
      // The scene showing is offered from the start, and as itself only where that differs
      if (scene !== showing || sceneSelfDiffers(scene) || keptNothing) {
        option(scenes, "scene:" + sceneMark(scene), "Scene: " + scene.name);
      }
      if (scene === showing) option(scenes, "restart", remoteSays("restart", button));
    });
    choice.appendChild(scenes);
    var steps = document.createElement("optgroup");
    steps.label = "Step";
    [["next", "Next scene"], ["previous", "Previous scene"], ["first", "First scene"]]
      .concat(showing ? [] : [["restart", remoteSays("restart", button)]])
      .forEach(function (step) { option(steps, step[0], step[1]); });
    choice.appendChild(steps);
  }
  choice.value = resolved.from === "own" ? resolved.choice : "";
  // Going to the scene showing where that begins it again reads as from the start
  if (showing && choice.value === "scene:" + sceneMark(showing) && sceneRestarts(showing)) {
    choice.value = "restart";
  }
  // The whole choice, which a narrow row can cut short
  if (choice.selectedOptions.length) choice.title = choice.selectedOptions[0].textContent;
  choice.onchange = function () {
    var value = choice.value;
    // Always on choosing a button's default, or a scene choosing Always on's, keeps no choice
    if (value === "") delete state.motionTiming[button];
    if (value === "" || (state.at < 0 && value === remoteDefault(button))) delete state.remote[button];
    else state.remote[button] = value;
    settleSceneRow(button);
    draw();
  };
  row.appendChild(choice);
}

// ---- the remote with a row for each button ----------------------------------------------------
// The remote in the middle, its buttons' rows down either side, each joined to its button by a
// leader in the button's colour while it does something. The art is drawn at REMOTE_SCALE pixels
// to its unit, the leaders taking REMOTE_REACH units beyond its body on each side

var REMOTE_SCALE = 4.3;
var REMOTE_REACH = 16;
var REMOTE_BODY = {left: 71.26, right: 126.45, top: 23.5, bottom: 146};
var REMOTE_ROW_PX = 27;

// A leader from a row's edge to its button, level to where it turns, then at 45 degrees onto the
// button's edge for a middle one
function remoteLeader(row) {
  var at = remoteArtAt(row[0]);
  var left = row[1] === "left";
  var from = left ? REMOTE_BODY.left - REMOTE_REACH : REMOTE_BODY.right + REMOTE_REACH;
  var reach = REMOTE_ART_RADIUS;
  if (Math.abs(row[2] - at.y) < 0.01) return "M" + from + " " + at.y + " H" + (left ? at.x - reach : at.x + reach);
  var lean = reach * Math.SQRT1_2;
  var endX = left ? at.x - lean : at.x + lean;
  var endY = row[2] > at.y ? at.y + lean : at.y - lean;
  var turn = left ? endX - Math.abs(row[2] - endY) : endX + Math.abs(row[2] - endY);
  return "M" + from + " " + row[2] + " H" + turn.toFixed(2) + " L" + endX.toFixed(2) + " " +
         endY.toFixed(2);
}

// With no remote fitted the whole remote is washed. Fitted, each button doing nothing is darkened
// and washed, as is a join unless both its ends are in use. The art is drawn twice under two
// masks that are each other's opposite, so nothing stacks
var REMOTE_WASHED = " opacity='0.35'";
var REMOTE_IDLE = " filter='url(#raDark)' opacity='0.5'";
var REMOTE_MASK = "x='60' y='15' width='80' height='140'";

function remoteMask(id, lit, flipped) {
  function paint(colour) { return flipped ? (colour === "#fff" ? "#000" : "#fff") : colour; }
  function circle(name) {
    var at = remoteArtAt(name);
    return "<circle cx='" + at.x + "' cy='" + at.y + "' r='" + REMOTE_ART_RADIUS + "'/>";
  }
  var idle = REMOTE_BUTTONS.map(function (button) { return button[0]; }).filter(function (name) {
    return lit.indexOf(name) < 0;
  });
  var idleJoins = REMOTE_ART_JOINS.filter(function (one) {
    return lit.indexOf(one[1]) < 0 || lit.indexOf(one[2]) < 0;
  });
  // A join runs up under the buttons at its ends, so the buttons in use go back in after it
  return "<mask id='" + id + "' maskUnits='userSpaceOnUse' " + REMOTE_MASK + ">" +
         "<rect " + REMOTE_MASK + " fill='" + paint("#fff") + "'/>" +
         "<g fill='" + paint("#000") + "'>" + idle.map(circle).join("") +
         idleJoins.map(function (one) { return "<path d='" + remoteArtJoin(one[0]) + "'/>"; }).join("") +
         "</g><g fill='" + paint("#fff") + "'>" + lit.map(circle).join("") + "</g></mask>";
}

function remoteLayers() {
  var lit = REMOTE_BUTTONS.map(function (button) { return button[0]; }).filter(remoteDoes);
  // Darkening halves each channel
  var defs = "<defs><g id='raArt'>" + remoteArt() + "</g>" +
             "<filter id='raDark'><feComponentTransfer><feFuncR type='linear' slope='0.5'/>" +
             "<feFuncG type='linear' slope='0.5'/><feFuncB type='linear' slope='0.5'/>" +
             "</feComponentTransfer></filter>";
  if (!remoteFitted()) return defs + "</defs><use href='#raArt'" + REMOTE_WASHED + "/>";
  return defs + remoteMask("raFull", lit, false) + remoteMask("raRest", lit, true) +
         "</defs><use href='#raArt'" + REMOTE_IDLE + " mask='url(#raRest)'/>" +
         "<use href='#raArt' mask='url(#raFull)'/>";
}

function remoteDiagram() {
  var width = REMOTE_BODY.right - REMOTE_BODY.left + 2 * REMOTE_REACH;
  var height = REMOTE_BODY.bottom - REMOTE_BODY.top;
  var diagram = document.createElement("div");
  diagram.className = "remotediagram";
  diagram.style.height = Math.round(height * REMOTE_SCALE) + "px";
  diagram.style.setProperty("--middle", Math.round(width * REMOTE_SCALE) + "px");

  var fitted = remoteFitted();
  var leaders = "", covers = "";
  REMOTE_ROWS.forEach(function (row) {
    leaders += "<path class='remoteleader' data-button='" + row[0] + "' d='" + remoteLeader(row) +
               "' stroke='" + (remoteDoes(row[0]) ? remoteInk(row[0]) : "#d6d3cd") + "'/>";
  });
  // Each button's cover is clear, there to be hovered and clicked to choose for
  REMOTE_BUTTONS.forEach(function (button) {
    var at = remoteArtAt(button[0]);
    covers += "<circle class='remotecover" + (fitted && !REMOTE_FIXED[button[0]] ? " choosable" : "") +
              "' data-button='" + button[0] + "' cx='" + at.x + "' cy='" + at.y + "' r='" +
              (REMOTE_ART_RADIUS + 0.2) + "'/>";
  });
  var middle = document.createElement("div");
  middle.className = "remotemiddle";
  middle.innerHTML = "<svg viewBox='" + (REMOTE_BODY.left - REMOTE_REACH) + " " + REMOTE_BODY.top +
                     " " + width + " " + height + "' width='100%' height='100%' role='img' " +
                     "aria-label='The Aye Arr Remote'>" + remoteLayers() + leaders + covers + "</svg>";

  var sides = {left: document.createElement("div"), right: document.createElement("div")};
  sides.left.className = "remoteside left";
  sides.right.className = "remoteside right";
  REMOTE_ROWS.forEach(function (row) {
    var resolved = remoteResolved(row[0]);
    var slot = document.createElement("div");
    // A row a scene leaves to Always on is striped, as the page marks everything Always on plays
    slot.className = "remoterow" + (remoteDoes(row[0]) ? " lit" : "") +
                     (fitted && resolved.from === "always" ? " under" : "") +
                     (resolved.from === "fixed" ? " fixed" : "");
    slot.dataset.button = row[0];
    slot.style.top = Math.round((row[2] - REMOTE_BODY.top) * REMOTE_SCALE - REMOTE_ROW_PX / 2) + "px";
    slot.appendChild(small(remoteWords(row[0])));
    // A number with no scene in its place has nothing to choose until there is one
    var unbound = isNumber(row[0]) && !sceneInOrder(row[0]);
    if (fitted && resolved.from !== "fixed" && !unbound) {
      remoteRowChoice(slot, row[0]);
    } else {
      var said = document.createElement("b");
      // 0 is bound to the tenth scene
      said.textContent = !fitted ? "" : unbound ? "No scene " + (Number(row[0].charAt(0)) || 10)
                                                : remoteSays(resolved.choice, row[0]);
      slot.appendChild(said);
      if (resolved.from === "fixed" && fitted) {
        slot.title = REMOTE_FIXED[row[0]][1];
        said.insertAdjacentHTML("afterbegin", "<svg class='padlock' viewBox='0 0 12 12' " +
          "aria-hidden='true'><rect x='2' y='5' width='8' height='6' rx='1.2' fill='currentColor'/>" +
          "<path d='M4 5V3.6a2 2 0 0 1 4 0V5' fill='none' stroke='currentColor' stroke-width='1.4'/>" +
          "</svg>");
      }
    }
    sides[row[1]].appendChild(slot);
  });
  diagram.appendChild(sides.left);
  diagram.appendChild(middle);
  diagram.appendChild(sides.right);

  // A row and its button light together, and clicking a button opens its row's choice. With no
  // remote fitted there is nothing to choose, so nothing lights
  if (!fitted) return diagram;
  function hot(name, on) {
    diagram.querySelectorAll("[data-button='" + name + "']").forEach(function (one) {
      one.classList.toggle("hot", on);
    });
  }
  diagram.querySelectorAll("[data-button]").forEach(function (one) {
    one.addEventListener("mouseenter", function () { hot(one.dataset.button, true); });
    one.addEventListener("mouseleave", function () { hot(one.dataset.button, false); });
  });
  diagram.querySelectorAll(".remotecover.choosable").forEach(function (cover) {
    cover.addEventListener("click", function () {
      var chooser = diagram.querySelector("select[data-choice='" + cover.dataset.button + "']");
      chooser.focus();
      // Opening the list outright needs a browser that has showPicker
      try { chooser.showPicker(); } catch (refused) {}
    });
  });
  return diagram;
}

// ---- the section ---------------------------------------------------------------------------------

function sensorSaid(words, dim) {
  var said = document.createElement("p");
  said.textContent = words;
  if (dim) said.className = "dim";
  return said;
}

// The box saying what is on the sensor connector, a choice while the board is being set up
function sensorBox() {
  var facts = document.getElementById("sensorFacts");
  facts.textContent = "";
  var fitted = sensorFacts();
  var parts = ["Sensor"];
  if (canEdit("sensorPanel")) {
    var choice = document.createElement("select");
    SENSOR_KINDS.forEach(function (kind) {
      var option = document.createElement("option");
      option.value = kind[0];
      option.textContent = kind[1];
      choice.appendChild(option);
    });
    choice.value = state.sensorKind;
    choice.onchange = function () {
      state.sensorKind = choice.value;
      draw();
    };
    parts.push(choice);
    if (fitted[3]) parts.push(small(fitted[3]));
  } else {
    parts.push(small(state.sensorKind === "none" ? "nothing on the sensor connector"
                                                 : fitted[1] + ", " + fitted[3]));
  }
  facts.appendChild(boardBox("sensorPanel", parts));
  if (!canEdit("sensorPanel") && state.sensorKind === "none") {
    var hint = document.createElement("span");
    hint.className = "hint";
    hint.textContent = "Edit board to fit one.";
    facts.appendChild(hint);
  }
}

// ---- the PIR Stick with a row for each trigger --------------------------------------------------
// The PIR Stick's artwork in the middle as the remote's is, with a row for motion starting on its
// left and one for motion stopping on its right, level with its sensor

var PIR_STICK = {width: 22.692, height: 77.102};

var PIR_SCALE = 3.3;
var PIR_REACH = 14.6;
// Each trigger's row, motion starting on the left and stopping on the right, both level with the
// sensor's middle, as [trigger, side, height in the drawing]
var PIR_ROWS = [["MOTION_STARTS", "left", 11.883], ["MOTION_STOPS", "right", 11.883]];
// The sensor's outer edges across the drawing, where the leaders end
var PIR_SENSOR = {left: 0.703, right: 21.989};
// The height of a trigger's heading, which sits level with its leader
var PIR_HEAD_PX = 34;

// A figure beside each row's name, someone running with speed streaks behind them for motion
// starting, and standing still for it stopping, the two built alike. The streaks step left down
// the runner's back, past the 16 unit square, so the figures' box reaches further left. Each head
// is classed as a filled part, so a part icon can draw the figure too
var MOTION_FIGURES = {
  MOTION_STARTS: "<circle class='f' cx='10' cy='2.6' r='1.9'/><path d='M9.4 5.6 7.8 10.4 6 13.5 " +
                 "2.8 14.6M7.8 10.4l3.3 1.7 1.2 3.4M9.4 5.6 5.7 7.6 4.4 10M9.4 5.6l2.5 2.8 3 .6' " +
                 "fill='none'/><path d='M2.8 4h2.6M.3 7.5h2.4M-.2 11h2' fill='none' " +
                 "stroke-width='1.2'/>",
  MOTION_STOPS: "<circle class='f' cx='8' cy='2.1' r='1.9'/><path d='M8 5.1v4.6M8 9.7l-1.5 " +
                "6M8 9.7l1.5 6M8 5.9 4.3 9.8M8 5.9l3.7 3.9' fill='none'/>"
};
var MOTION_FIGURE_BOX = "-1.2 -0.6 17.2 17.2";

// The PIR Stick's icon on a scene's card, the figure for motion starting on the part icons' grid,
// as the Stick reacts to people moving
PART_DRAWINGS.pir = "<g transform='translate(2.4 1.5) scale(1.27)' stroke-width='1.4'>" +
                    MOTION_FIGURES.MOTION_STARTS + "</g>";

function motionFigure(trigger) {
  var figure = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  figure.setAttribute("viewBox", MOTION_FIGURE_BOX);
  figure.setAttribute("class", "motionfigure");
  figure.setAttribute("aria-hidden", "true");
  figure.innerHTML = MOTION_FIGURES[trigger];
  return figure;
}

// ---- a delay on motion's triggers ---------------------------------------------------------------
// Each of motion's triggers can wait seconds before doing what it does, and the opposite edge
// coming first cancels it unless told not to, so a scare can wait a moment after someone arrives
// whether or not they stay. A delay belongs to its row, so changing one in a scene makes the row
// the scene's own. The tab being edited keeps its rows' delays as {after, cancel}

state.motionTiming = {};

var MOTION_TIMING_DEFAULT = {after: 0, cancel: true};

// The question a delay asks of the opposite edge, which "cancel this" or "finish this first"
// answers
var MOTION_CANCELLED_BY = {MOTION_STARTS: "If motion stops first?",
                           MOTION_STOPS: "If motion starts again first?"};

// A trigger's delay on the tab being edited: the tab's own where the row is its own, or Always
// on's where a scene leaves the row to it
function motionTiming(trigger) {
  var own = state.at < 0 || state.remote[trigger] !== undefined;
  var held = own ? state.motionTiming
                 : state.always.body && state.always.body.motionTiming || {};
  return held[trigger] || MOTION_TIMING_DEFAULT;
}

// Change a trigger's delay on the tab being edited, a scene taking the row as its own with what it
// did as Always on
function setMotionTiming(trigger, change) {
  // Read before the scene takes the row, which would hide Always on's delay behind its own
  var timing = JSON.parse(JSON.stringify(motionTiming(trigger)));
  if (state.at >= 0 && state.remote[trigger] === undefined) {
    state.remote[trigger] = remoteResolved(trigger).choice;
  }
  Object.keys(change).forEach(function (key) { timing[key] = change[key]; });
  if (timing.after === 0 && timing.cancel) delete state.motionTiming[trigger];
  else state.motionTiming[trigger] = timing;
  settleSceneRow(trigger);
  draw();
}

// Hand a scene's row back to Always on where its choice and delay match Always on's, so a row is
// only a scene's own where it does something different
function settleSceneRow(trigger) {
  if (state.at < 0 || state.remote[trigger] === undefined) return;
  var always = state.always.body && state.always.body.remote || {};
  var under = always[trigger] !== undefined ? always[trigger] : remoteDefault(trigger);
  var alwaysTimings = state.always.body && state.always.body.motionTiming || {};
  var own = state.motionTiming[trigger] || MOTION_TIMING_DEFAULT;
  var held = alwaysTimings[trigger] || MOTION_TIMING_DEFAULT;
  if (state.remote[trigger] !== under || own.after !== held.after || own.cancel !== held.cancel) {
    return;
  }
  delete state.remote[trigger];
  delete state.motionTiming[trigger];
}

// A PIR box's two lines: "Trigger [what it does] after [3] s", then the question of the opposite
// edge, greyed while there is no wait, so the box keeps its size
function motionLines(trigger, box) {
  var timing = motionTiming(trigger);
  var line = document.createElement("div");
  line.className = "pirtiming piraction";
  line.appendChild(small("Trigger"));
  remoteRowChoice(line, trigger);
  box.appendChild(line);
  line.appendChild(small("after"));
  var seconds = document.createElement("input");
  seconds.type = "number";
  seconds.min = 0;
  seconds.step = 0.5;
  seconds.value = timing.after;
  seconds.title = "Seconds to wait before doing it";
  seconds.onchange = function () {
    setMotionTiming(trigger, {after: Math.max(0, Number(seconds.value) || 0)});
  };
  line.appendChild(seconds);
  line.appendChild(small("s"));
  var asked = document.createElement("div");
  asked.className = "pirtiming pirquestion" + (timing.after > 0 ? "" : " idle");
  asked.appendChild(small(MOTION_CANCELLED_BY[trigger]));
  var cancels = document.createElement("select");
  cancels.className = "pircancel";
  [["yes", "cancel this"], ["no", "finish this first"]].forEach(function (answer) {
    var option = document.createElement("option");
    option.value = answer[0];
    option.textContent = answer[1];
    cancels.appendChild(option);
  });
  cancels.value = timing.cancel ? "yes" : "no";
  cancels.disabled = !(timing.after > 0);
  if (cancels.disabled) asked.title = "Asked once it waits";
  cancels.onchange = function () { setMotionTiming(trigger, {cancel: cancels.value === "yes"}); };
  asked.appendChild(cancels);
  box.appendChild(asked);
}

function pirDiagram() {
  var width = PIR_STICK.width + 2 * PIR_REACH;
  var diagram = document.createElement("div");
  diagram.className = "remotediagram";
  diagram.style.height = Math.round(PIR_STICK.height * PIR_SCALE) + "px";
  diagram.style.setProperty("--middle", Math.round(width * PIR_SCALE) + "px");
  // Each leader runs from the sensor's edge out to its side's row
  var leaders = PIR_ROWS.map(function (row) {
    var path = row[1] === "left"
      ? "M" + -PIR_REACH + " " + row[2] + " H" + PIR_SENSOR.left
      : "M" + PIR_SENSOR.right + " " + row[2] + " H" + (PIR_STICK.width + PIR_REACH);
    return "<path class='remoteleader' data-button='" + row[0] + "' d='" + path + "' stroke='" +
           (remoteDoes(row[0]) ? "#808285" : "#d6d3cd") + "'/>";
  }).join("");
  var middle = document.createElement("div");
  middle.className = "remotemiddle";
  middle.innerHTML = "<svg viewBox='" + -PIR_REACH + " 0 " + width + " " + PIR_STICK.height + "' " +
                     "width='100%' height='100%' role='img' aria-label='The PIR Stick'>" +
                     PIR_ART.join("") +
                     leaders + "</svg>";
  var sides = {left: document.createElement("div"), right: document.createElement("div")};
  sides.left.className = "remoteside left";
  sides.right.className = "remoteside right";
  // Each trigger has a heading across its box, its name by the leader and its figure at the outer
  // edge, and under it a box holding what it does with its delay, striped where a scene leaves it
  // to Always on as a remote's row is
  PIR_ROWS.forEach(function (row) {
    var resolved = remoteResolved(row[0]);
    var side = document.createElement("div");
    side.className = "pirside";
    side.style.top = Math.round(row[2] * PIR_SCALE - PIR_HEAD_PX / 2) + "px";
    var head = document.createElement("div");
    head.className = "pirhead";
    head.appendChild(motionFigure(row[0]));
    head.appendChild(document.createTextNode(remoteWords(row[0])));
    side.appendChild(head);
    var box = document.createElement("div");
    box.className = "remoterow pirbox" + (remoteDoes(row[0]) ? " lit" : "") +
                    (resolved.from === "always" ? " under" : "");
    box.dataset.button = row[0];
    motionLines(row[0], box);
    side.appendChild(box);
    sides[row[1]].appendChild(side);
  });
  diagram.appendChild(sides.left);
  diagram.appendChild(middle);
  diagram.appendChild(sides.right);
  return diagram;
}

function renderSensor() {
  sensorBox();
  var box = document.getElementById("sensor");
  box.textContent = "";
  var words = document.createElement("div");
  words.className = "sensorwords";
  if (pirFitted()) {
    box.appendChild(pirDiagram());
    words.appendChild(sensorSaid(state.at < 0
      ? "What motion starting and stopping does in every scene. A scene can change either while " +
        "it shows."
      : "Striped rows do what Always on sets. Choose one to change it in this scene."));
    sensorNotes(words);
    box.appendChild(words);
    return;
  }
  box.appendChild(remoteDiagram());
  if (!remoteFitted()) {
    words.appendChild(sensorSaid("The sensor connector takes one thing at a time, such as the " +
                                 "Aye Arr Remote through an IR Receiver Stick.", true));
  } else if (state.at < 0) {
    words.appendChild(sensorSaid("What each button does in every scene. A scene can change any " +
                                 "of them while it shows."));
    if (!state.scenes.length) {
      words.appendChild(sensorSaid("With scenes, the numbers go to them and the arrows step " +
                                   "through them.", true));
      var split = document.createElement("button");
      split.className = "plus";
      split.textContent = "split into scenes";
      split.onclick = addScene;
      words.appendChild(split);
    }
  } else {
    words.appendChild(sensorSaid("Striped buttons do what Always on sets. Choose one to change " +
                                 "it in this scene."));
  }
  sensorNotes(words);
  box.appendChild(words);
}

// The warnings under the sensor's diagram, for what the file gave that the page cannot use as it is
function sensorNotes(words) {
  // A trigger going to the scene showing, which waits and does not restart
  var idle = triggerDoingNothing();
  if (idle) {
    var showing = state.scenes[state.at].name;
    var nothing = sensorSaid(remoteWords(idle) + " does nothing here, as " + showing + " is " +
                             "already showing and waits. Choose \"Scene: " + showing + ", from " +
                             "the start\" to begin it again.");
    nothing.className = "warn";
    words.appendChild(nothing);
  }
  // A button the file gave twice in this tab, whose second line is kept as written
  if (fittedTriggers().length && state.remoteRepeats.length) {
    var repeated = sensorSaid((state.remoteRepeats.length === 1 ? "" : "Each of ") +
      state.remoteRepeats.map(remoteWords).join(", ") + " is given twice in the file here. The " +
      "page uses the first and keeps the second line as it is.");
    repeated.className = "warn";
    words.appendChild(repeated);
  }
}

// ---- what the file says ---------------------------------------------------------------------------
// What is fitted is the board line's sensor=ir or sensor=pir. A remote: line holds buttons as the
// remote names them, each with what it does: nothing, a step, or scene and the scene's name. Like
// board: lines, remote: lines add up, and a button given twice in one tab is a repeat. The page
// writes a line for each button, so a name needs no quotes, and reads several to a line, where a
// name runs on to the next button or is quoted. Always on's lines are above the first heading and a
// scene's under its own (proposed, which autofx does not read yet)

var REMOTE_STEPS = ["nothing", "next", "previous", "first", "restart"];

// A button's line, or null where the choice names a scene no longer there
function remoteLine(button, choice) {
  var said = choice;
  var scene = choice === "order" ? sceneInOrder(button)
            : choice.indexOf("scene:") === 0 ? sceneMarked(choice.slice(6)) : null;
  if (choice.indexOf("scene:") === 0 && !scene) return null;
  if (scene) {
    said = "scene " + scene.name.trim();
    // A name holding = or a quote is quoted, as it would otherwise read as the next button
    if (/[="']/.test(scene.name)) said = scene.name.indexOf("\"") < 0 ? "\"" + said + "\"" : "'" + said + "'";
  }
  // A PIR Stick's triggers are motion: starts= and stops=
  var motion = MOTION_TRIGGERS.indexOf(button) >= 0;
  return (motion ? "motion: " + button.slice(7).toLowerCase() : "remote: " + button.toLowerCase()) +
         "=" + said;
}

// A trigger's whole line, with a motion trigger's delay after it where it has one
function triggerLine(trigger, choice, timing) {
  var line = remoteLine(trigger, choice);
  if (!line || !timing || !timing.after) return line;
  return line + " after=" + timing.after + "s" + (timing.cancel ? "" : " cancel=no");
}

// A remote: line's buttons and what each does, as [button, words]. A word with no = carries on
// the words before it, so an unquoted scene name runs on to the next button
function remotePairs(text) {
  var pairs = [];
  boardTokens(text).forEach(function (token) {
    var equals = token.indexOf("=");
    if (equals > 0 && !/^["']/.test(token)) {
      pairs.push([token.slice(0, equals).toUpperCase(), token.slice(equals + 1)]);
    } else if (pairs.length) {
      pairs[pairs.length - 1][1] += " " + token;
    } else {
      pairs.push([null, token]);
    }
  });
  return pairs.map(function (pair) { return [pair[0], unquoted(pair[1].trim())]; });
}

// What a line's words choose for its button, or null where the page cannot hold it
function remoteChoiceRead(button, said) {
  if (REMOTE_FIXED[button]) return null;
  if (REMOTE_STEPS.indexOf(said.toLowerCase()) >= 0) {
    // A number only goes to its own scene or does nothing
    return isNumber(button) && said.toLowerCase() !== "nothing" ? null : said.toLowerCase();
  }
  var named = /^scene\s+(.+)$/i.exec(said);
  if (!named) return null;
  var scene = state.scenes.filter(function (one) { return one.name.trim() === named[1].trim(); })[0];
  if (!scene) return null;
  if (isNumber(button)) return sceneInOrder(button) === scene ? "order" : null;
  return "scene:" + sceneMark(scene);
}

boardLineSteps.after.push(function (line) {
  if (state.sensorKind === "none") return line;
  return (line || "board:") + " sensor=" + state.sensorKind;
});

// Read what is fitted from the board line, the token taken so it is not written twice
function readSensorBoard() {
  state.sensorKind = "none";
  boardResidue = boardResidue.filter(function (token) {
    var fitted = /^sensor=(ir|pir)$/i.exec(token);
    if (fitted) state.sensorKind = fitted[1].toLowerCase();
    return !fitted;
  });
}

// Take each body's remote: lines, or motion: lines for a PIR Stick, that the page can hold as its
// choices. A line is taken whole or not at all: one with a trigger the page cannot hold, or one the
// tab already gave, stays as written, as does every line for what is not fitted. A repeated
// trigger is noted for the tab
function readRemoteLines(bodies) {
  var entry = pirFitted() ? /^motion:(.*)$/i : /^remote:(.*)$/i;
  var triggers = fittedTriggers();
  bodies.forEach(function (body) {
    body.remote = {};
    body.remoteRepeats = [];
    if (!triggers.length) return;
    var given = [];
    body.motionTiming = {};
    body.kept = body.kept.filter(function (one) {
      var line = entry.exec(one.text || "");
      if (!line) return true;
      var choices = {};
      var timings = {};
      var held = true;
      var last = null;
      remotePairs(line[1]).forEach(function (pair) {
        // A motion trigger's after= and cancel= are its delay, belonging to the trigger before them
        if (pirFitted() && (pair[0] === "AFTER" || pair[0] === "CANCEL")) {
          var timing = timings[last] || JSON.parse(JSON.stringify(MOTION_TIMING_DEFAULT));
          var seconds = /^(\d+(?:\.\d+)?)s?$/i.exec(pair[1]);
          var cancel = pair[1].toLowerCase();
          if (!last || (pair[0] === "AFTER" ? !seconds : cancel !== "yes" && cancel !== "no")) {
            held = false;
            return;
          }
          if (pair[0] === "AFTER") timing.after = Number(seconds[1]);
          else timing.cancel = cancel === "yes";
          timings[last] = timing;
          return;
        }
        var button = pair[0] && pirFitted() ? "MOTION_" + pair[0] : pair[0];
        last = button;
        if (button && given.indexOf(button) >= 0) {
          if (body.remoteRepeats.indexOf(button) < 0) body.remoteRepeats.push(button);
          held = false;
        }
        if (button) given.push(button);
        var known = button && triggers.indexOf(button) >= 0;
        var choice = known ? remoteChoiceRead(button, pair[1]) : null;
        if (choice === null) held = false;
        else choices[button] = choice;
      });
      if (!held) return true;
      // A line's comments go above the first of the lines it is written back as
      Object.keys(choices).forEach(function (button, at) {
        body.remote[button] = choices[button];
        if (timings[button]) body.motionTiming[button] = timings[button];
        if (at === 0 && one.comments.length) {
          body.notes[triggerLine(button, choices[button], timings[button])] = one.comments;
        }
      });
      return false;
    });
  });
}

// A scene keeps its own choices of what buttons do, as it keeps its looks. A scene's card shows
// the remote's icon where it changes any button, and Always on's where a remote is fitted
bodyParts.push({
  capture: function (body) {
    body.remote = JSON.parse(JSON.stringify(state.remote));
    body.remoteRepeats = state.remoteRepeats.slice();
    body.motionTiming = JSON.parse(JSON.stringify(state.motionTiming));
  },
  apply: function (body) {
    state.remoteRepeats = (body.remoteRepeats || []).slice();
    state.motionTiming = JSON.parse(JSON.stringify(body.motionTiming || {}));
    state.remote = JSON.parse(JSON.stringify(body.remote || {}));
    // A number only goes to the scene in its place or does nothing
    Object.keys(state.remote).forEach(function (button) {
      if (isNumber(button) && ["order", "nothing"].indexOf(state.remote[button]) < 0) {
        delete state.remote[button];
      }
    });
  },
  sets: function (body, always) {
    if (!fittedTriggers().length) return null;
    var changed = body.remote && Object.keys(body.remote).length;
    return always || changed ? [pirFitted() ? "pir" : "remote", "Sensor"] : null;
  },
  // A tab's remote: or motion: lines come after its other lines, in the order of the triggers
  // A trigger with a delay but no choice of its own does what its default does
  entries: function (body, lines) {
    if (!body.remote) return lines;
    var timings = body.motionTiming || {};
    fittedTriggers().forEach(function (trigger) {
      var choice = body.remote[trigger];
      if (choice === undefined && timings[trigger]) choice = remoteDefault(trigger);
      var line = choice === undefined ? null : triggerLine(trigger, choice, timings[trigger]);
      if (line) lines.push(line);
    });
    return lines;
  },
  // Splitting into scenes leaves what the triggers do with Always on, where it holds in every
  // scene, and the first scene starts with no choices of its own
  split: function (always, first) {
    first.remote = {};
    first.remoteRepeats = [];
    first.motionTiming = {};
  },
  readBoard: readSensorBoard,
  read: readRemoteLines
});

// The tab has no swatch, its name and what is fitted under it saying all there is
tabSwatches.sensorPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch sensorswatch";
};

function sensorUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=sensorPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  var named = document.createElement("span");
  named.className = "tabname";
  named.appendChild(tab.querySelector("b"));
  var kind = document.createElement("small");
  kind.className = "tabunder";
  kind.textContent = sensorFacts()[2];
  named.appendChild(kind);
  tab.insertBefore(named, tab.firstChild);
}

drawSteps.after.push(function () {
  sensorUnderName();
  renderSensor();
});

(function () {
  var panel = document.createElement("details");
  panel.className = "panel";
  panel.id = "sensorPanel";
  panel.open = true;
  panel.innerHTML = "<summary>Sensor</summary><div class='facts' id='sensorFacts'></div>" +
                    "<div id='sensor'></div>";
  var after = document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]);
  after.parentNode.insertBefore(panel, after.nextSibling);
}());

TAB_NAMES.sensorPanel = "Sensor";
TAB_PANELS.push("sensorPanel");
keptOpen("sensorPanel");
