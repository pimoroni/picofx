import {BOARD_LINE_AFTER, boardLineSteps} from "../board.js";
import {h, replace} from "../dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "../draw.js";
import {filterResidue} from "../kept.js";
import {boardTokens, unquoted} from "../reading.js";
import {BOARD_CHIP_CLASSES} from "../runs.js";
import {PART_DRAWINGS, REMOTE_COLOURS} from "../scene_tray.js";
import {
  BODY_ORDER, addScene, bodyParts, sceneHooks, sceneMark, sceneMarked, sceneNamed, sceneRestarts,
  state
} from "../scenes.js";
import {
  PIR_ART, REMOTE_ART_JOINS, REMOTE_ART_RADIUS, REMOTE_BUTTONS, REMOTE_ROWS, remoteArt,
  remoteArtAt, remoteArtJoin
} from "./sensor_art.js";
import {boardBox, boardButton, removeButton, small} from "../setup.js";
import {FEATURE_TABS, TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches} from "../tabs.js";

// ---- the Sensor tab -----------------------------------------------------------------------------
// This part draws the Sensor tab, after Sound, for what is on the sensor connector and what it
// does. Only what is fitted is board setup. What each of a remote's buttons does is set on the
// Always on tab for every scene, and a scene can change any button while it shows, as it can any
// light. Two buttons are the board's in every scene. OK / Stop puts it in standby and wakes it, so
// there is always a way to stop it, and Play / Pause holds the effects where they stand.

// What the sensor connector can have on it, as [kind, as the choice says it, under the tab's name]
var SENSOR_KINDS = [["none", "not fitted", "none"],
                    ["ir", "Aye Arr Remote", "Aye Arr"],
                    ["pir", "PIR Stick", "PIR Stick"]];

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
// A choice is a word, one of nothing, order (a number's scene by place), next, previous, first,
// restart, or "scene:" and a scene's own mark, which keeps the button on that scene when it moves.
// The board's own two buttons are standby and pause. A number is bound to the scene in its place,
// as the scene's colour is its button's, so a number only goes there or does nothing

function isNumber(button) { return /^\d_/.test(button); }

// The buttons that do the same in every scene, and what they do
var REMOTE_FIXED = {OK_STOP: ["standby", "Standby and wake, in every scene"],
                    PLAY_PAUSE: ["pause", "Pause the effects where they stand, in every scene"]};

// A scene can wait for a button while a remote is fitted, or for motion while a PIR Stick is
sceneHooks.canWait = function () { return remoteFitted() || pirFitted(); };
sceneHooks.waitsFor = function () { return pirFitted() ? "motion" : "a button"; };

// The places of the scenes a scene goes to on what is fitted, from each trigger's choice in that
// scene. Its own choice comes first, then Always on's, then the trigger's default. The tab being
// edited holds its choices in state.remote rather than its body
sceneHooks.triggerLeads = function (at) {
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

// What a button does where Always on chooses nothing else. A number goes to the scene in its
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

// What a button does on the tab being edited, as {choice, from}. Its from is "own" where the tab
// chooses it, "always" where a scene leaves it to Always on and "fixed" for the board's own buttons
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

// The trigger in this tab that does nothing as it goes to the scene showing, which waits and does
// not restart, or null
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
sceneHooks.numbers = function (scene) {
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

// The tip of a row holding a choice on a scene's tab
var REMOTE_UNDER_TIP = "Striped where it does what Always on sets";

// A row's choice of what its button does. On a scene's tab the first choice leaves the button to
// Always on and says what Always on makes it do, and the row takes REMOTE_UNDER_TIP
function remoteChoice(button) {
  var resolved = remoteResolved(button);
  var showing = state.at >= 0 ? state.scenes[state.at] : null;
  function option(value, words) { return h("option", {value: value}, words); }
  var own;
  var groups = null;
  if (isNumber(button)) {
    // A number goes to the scene in its place or does nothing
    own = [option("order", "Scene: " + sceneInOrder(button).name), option("nothing", "Nothing")];
  } else if (!state.scenes.length) {
    // With no scenes there is nothing to go to, only Always on's effects to begin again
    own = [option("nothing", "Nothing"), option("restart", remoteSays("restart", button))];
  } else {
    own = [option("nothing", "Nothing")];
    // A file's choice of the scene showing where that does nothing is kept, for its note to say why
    var keptNothing = showing && resolved.from === "own" && !sceneRestarts(showing) &&
                      !sceneSelfDiffers(showing) && resolved.choice === "scene:" + sceneMark(showing);
    groups = [
      h("optgroup", {label: "Go to a scene"}, state.scenes.map(function (scene) {
        // The scene showing is offered from the start, and as itself only where that differs
        return [scene !== showing || sceneSelfDiffers(scene) || keptNothing
                  ? option("scene:" + sceneMark(scene), "Scene: " + scene.name) : null,
                scene === showing ? option("restart", remoteSays("restart", button)) : null];
      })),
      h("optgroup", {label: "Step"},
        [["next", "Next scene"], ["previous", "Previous scene"], ["first", "First scene"]]
          .concat(showing ? [] : [["restart", remoteSays("restart", button)]])
          .map(function (step) { return option(step[0], step[1]); }))
    ];
  }
  var always = state.always.body && state.always.body.remote || {};
  var under = always[button] !== undefined ? always[button] : remoteDefault(button);
  var choice = h("select", {"data-choice": button, name: "remoteChoice",
                            "aria-label": remoteWords(button)},
                 state.at >= 0 ? [h("optgroup", {label: "As Always on"},
                                    option("", remoteSays(under, button) || "Nothing")),
                                  h("optgroup", {label: "In this scene"}, own)]
                               : own,
                 groups);
  choice.value = resolved.from === "own" ? resolved.choice : "";
  // Check if it goes to the scene showing where that begins it again, which reads as from the start
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
  return choice;
}

// ---- the remote with a row for each button ----------------------------------------------------
// The remote sits in the middle and its buttons' rows down either side. A leader in the button's
// colour joins each row to its button while it does something. The art is drawn at REMOTE_SCALE
// pixels to its unit, and the leaders reach REMOTE_REACH units beyond its body on each side

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

// With no remote fitted the whole remote is faded. Fitted, each button doing nothing is darkened
// and faded, as is a join unless both its ends are in use. The art is drawn twice under two masks
// that are each other's opposite, so nothing stacks
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
  var middle = h("div", {
    className: "remotemiddle",
    html: "<svg viewBox='" + (REMOTE_BODY.left - REMOTE_REACH) + " " + REMOTE_BODY.top + " " +
          width + " " + height + "' width='100%' height='100%' role='img' " +
          "aria-label='The Aye Arr Remote'>" + remoteLayers() + leaders + covers + "</svg>"
  });

  function remoteRow(row) {
    var resolved = remoteResolved(row[0]);
    var fixed = resolved.from === "fixed";
    // A number with no scene in its place has nothing to choose until there is one
    var unbound = isNumber(row[0]) && !sceneInOrder(row[0]);
    var choosing = fitted && !fixed && !unbound;
    // 0 is bound to the tenth scene
    var said = !fitted ? null : unbound ? "No scene " + (Number(row[0].charAt(0)) || 10)
                                        : remoteSays(resolved.choice, row[0]) || null;
    // A row a scene leaves to Always on is striped, as the page marks everything Always on plays
    return h("div", {
      className: "remoterow" + (remoteDoes(row[0]) ? " lit" : "") +
                 (fitted && resolved.from === "always" ? " under" : "") + (fixed ? " fixed" : ""),
      "data-button": row[0],
      style: {top: Math.round((row[2] - REMOTE_BODY.top) * REMOTE_SCALE - REMOTE_ROW_PX / 2) + "px"},
      title: choosing ? (state.at >= 0 ? REMOTE_UNDER_TIP : null)
           : fixed && fitted ? REMOTE_FIXED[row[0]][1] : null
    }, small(remoteWords(row[0])),
       choosing ? remoteChoice(row[0]) : h("b", {}, fixed && fitted ? padlock() : null, said));
  }
  function remoteSide(side) {
    return h("div", {className: "remoteside " + side},
             REMOTE_ROWS.filter(function (row) { return row[1] === side; }).map(remoteRow));
  }
  var diagram = h("div", {
    className: "remotediagram",
    style: {height: Math.round(height * REMOTE_SCALE) + "px",
            "--middle": Math.round(width * REMOTE_SCALE) + "px"}
  }, remoteSide("left"), middle, remoteSide("right"));

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

// The padlock on a row the board keeps the same in every scene
function padlock() {
  return h("svg:svg", {
    class: "padlock", viewBox: "0 0 12 12", "aria-hidden": "true",
    html: "<rect x='2' y='5' width='8' height='6' rx='1.2' fill='currentColor'/>" +
          "<path d='M4 5V3.6a2 2 0 0 1 4 0V5' fill='none' stroke='currentColor' stroke-width='1.4'/>"
  });
}

// ---- the section ---------------------------------------------------------------------------------

// A sentence under the diagram, dimmed or a warning where className= says so
function sensorSaid(words, className) {
  return h("p", {className: className || null}, words);
}

// Fill the box saying what is on the sensor connector, as a choice with a remove button. Nothing
// on it reads as not fitted, as a strip or a screen does, and offers to add the remote
function sensorBox() {
  var facts = document.getElementById("sensorFacts");
  if (state.sensorKind === "none") {
    var add = boardButton("add a sensor");
    add.classList.add("sensoradd");
    add.onclick = function () {
      state.sensorKind = "ir";
      draw();
    };
    replace(facts, boardBox("sensorPanel", ["Sensor", small("not fitted")]), add);
    return;
  }
  var choice = h("select", {
    name: "sensorKind", "aria-label": "Sensor",
    onchange: function () {
      state.sensorKind = choice.value;
      draw();
    }
  }, SENSOR_KINDS.filter(function (kind) { return kind[0] !== "none"; }).map(function (kind) {
    return h("option", {value: kind[0], selected: kind[0] === state.sensorKind}, kind[1]);
  }));
  replace(facts, boardBox("sensorPanel", ["Sensor", choice, removeButton("sensor", function () {
    state.sensorKind = "none";
    draw();
  })]));
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
// starting and someone standing still for it stopping. The streaks step left down the runner's
// back, past the 16 unit square, so the figures' box reaches further left. Each head is classed as
// a filled part, so a part icon can draw the figure too
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
  return h("svg:svg", {viewBox: MOTION_FIGURE_BOX, class: "motionfigure", "aria-hidden": "true",
                       html: MOTION_FIGURES[trigger]});
}

// ---- a delay on motion's triggers ---------------------------------------------------------------
// Each of motion's triggers can wait seconds before doing what it does, and the opposite edge
// coming first cancels it unless told not to, so a scare can wait a moment after someone arrives
// whether or not they stay. A delay belongs to its row, so changing one in a scene makes the row
// the scene's own. The tab being edited keeps its rows' delays as {after, cancel}

state.motionTiming = {};

var MOTION_TIMING_DEFAULT = {after: 0, cancel: true};

// The question a delay asks of the opposite edge, answered by "cancel this" or "finish this first"
var MOTION_CANCELLED_BY = {MOTION_STARTS: "If motion stops first?",
                           MOTION_STOPS: "If motion starts again first?"};

// A trigger's delay on the tab being edited, the tab's own where the row is its own, or Always
// on's where a scene leaves the row to it
function motionTiming(trigger) {
  var own = state.at < 0 || state.remote[trigger] !== undefined;
  var held = own ? state.motionTiming
                 : state.always.body && state.always.body.motionTiming || {};
  return held[trigger] || MOTION_TIMING_DEFAULT;
}

// Change a trigger's delay on the tab being edited. A scene takes the row as its own, starting
// from what the row did as Always on
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

// A PIR box's two lines, "Trigger [what it does] after [3] s" and the question of the opposite
// edge. The question is greyed while there is no wait, so the box keeps its size
function motionLines(trigger) {
  var timing = motionTiming(trigger);
  var waits = timing.after > 0;
  var seconds = h("input", {
    type: "number", min: 0, step: 0.5, value: timing.after,
    title: "Seconds to wait before doing it",
    name: "motionWait", "aria-label": "Seconds to wait before doing it",
    onchange: function () {
      setMotionTiming(trigger, {after: Math.max(0, Number(seconds.value) || 0)});
    }
  });
  var cancels = h("select", {
    className: "pircancel", disabled: !waits, name: "motionCancel",
    "aria-label": MOTION_CANCELLED_BY[trigger],
    onchange: function () { setMotionTiming(trigger, {cancel: cancels.value === "yes"}); }
  }, h("option", {value: "yes", selected: timing.cancel}, "cancel this"),
     h("option", {value: "no", selected: !timing.cancel}, "finish this first"));
  return [h("div", {className: "pirtiming piraction",
                    title: state.at >= 0 ? REMOTE_UNDER_TIP : null},
            small("Trigger"), remoteChoice(trigger), small("after"), seconds, small("s")),
          h("div", {className: "pirtiming pirquestion" + (waits ? "" : " idle"),
                    title: waits ? null : "Asked once it waits"},
            small(MOTION_CANCELLED_BY[trigger]), cancels)];
}

function pirDiagram() {
  var width = PIR_STICK.width + 2 * PIR_REACH;
  // Each leader runs from the sensor's edge out to its side's row
  var leaders = PIR_ROWS.map(function (row) {
    var path = row[1] === "left"
      ? "M" + -PIR_REACH + " " + row[2] + " H" + PIR_SENSOR.left
      : "M" + PIR_SENSOR.right + " " + row[2] + " H" + (PIR_STICK.width + PIR_REACH);
    return "<path class='remoteleader' data-button='" + row[0] + "' d='" + path + "' stroke='" +
           (remoteDoes(row[0]) ? "#808285" : "#d6d3cd") + "'/>";
  }).join("");
  var middle = h("div", {
    className: "remotemiddle",
    html: "<svg viewBox='" + -PIR_REACH + " 0 " + width + " " + PIR_STICK.height + "' " +
          "width='100%' height='100%' role='img' aria-label='The PIR Stick'>" +
          PIR_ART.join("") + leaders + "</svg>"
  });
  // Each trigger has a heading across its box, its name by the leader and its figure at the outer
  // edge, and under it a box holding what it does with its delay, striped where a scene leaves it
  // to Always on as a remote's row is
  function pirSide(row) {
    var resolved = remoteResolved(row[0]);
    return h("div", {className: "pirside",
                     style: {top: Math.round(row[2] * PIR_SCALE - PIR_HEAD_PX / 2) + "px"}},
             h("div", {className: "pirhead"}, motionFigure(row[0]), remoteWords(row[0])),
             h("div", {className: "remoterow pirbox" + (remoteDoes(row[0]) ? " lit" : "") +
                                  (resolved.from === "always" ? " under" : ""),
                       "data-button": row[0]},
               motionLines(row[0])));
  }
  function remoteSide(side) {
    return h("div", {className: "remoteside " + side},
             PIR_ROWS.filter(function (row) { return row[1] === side; }).map(pirSide));
  }
  return h("div", {
    className: "remotediagram",
    style: {height: Math.round(PIR_STICK.height * PIR_SCALE) + "px",
            "--middle": Math.round(width * PIR_SCALE) + "px"}
  }, remoteSide("left"), middle, remoteSide("right"));
}

function renderSensor() {
  sensorBox();
  var said;
  if (pirFitted()) {
    said = sensorSaid(state.at < 0
      ? "What motion starting and stopping does in every scene. A scene can change either while " +
        "it shows."
      : "Striped rows do what Always on sets. Choose one to change it in this scene.");
  } else if (!remoteFitted()) {
    said = sensorSaid("The sensor connector takes one thing at a time, such as the " +
                      "Aye Arr Remote through an IR Receiver Stick.", "dim");
  } else if (state.at < 0) {
    said = [sensorSaid("What each button does in every scene. A scene can change any " +
                       "of them while it shows."),
            state.scenes.length ? null
              : [sensorSaid("With scenes, the numbers go to them and the arrows step " +
                            "through them.", "dim"),
                 h("button", {className: "plus", onclick: addScene}, "split into scenes")]];
  } else {
    said = sensorSaid("Striped buttons do what Always on sets. Choose one to change " +
                      "it in this scene.");
  }
  replace(document.getElementById("sensor"), pirFitted() ? pirDiagram() : remoteDiagram(),
          h("div", {className: "sensorwords"}, said, sensorNotes()));
}

// The warnings under the sensor's diagram, for what the file gave that the page cannot use
function sensorNotes() {
  // A trigger going to the scene showing, which waits and does not restart
  var idle = triggerDoingNothing();
  var showing = idle ? state.scenes[state.at].name : null;
  // Check if the file gave a trigger twice in this tab, whose second line is kept as written
  var repeats = fittedTriggers().length && state.remoteRepeats.length;
  return [
    idle ? sensorSaid(remoteWords(idle) + " does nothing here, as " + showing + " is " +
                      "already showing and waits. Choose \"Scene: " + showing + ", from " +
                      "the start\" to begin it again.", "warn") : null,
    repeats ? sensorSaid((state.remoteRepeats.length === 1 ? "" : "Each of ") +
                         state.remoteRepeats.map(remoteWords).join(", ") + " is given twice in " +
                         "the file here. The page uses the first and keeps the second line as " +
                         "it is.", "warn") : null
  ];
}

// ---- what the file says ---------------------------------------------------------------------------
// What is fitted is the board line's sensor=ir or sensor=pir. A remote: line holds buttons as the
// remote names them, each with what it does, which is nothing, a step, or scene and the scene's
// name. A motion: line holds starts= and stops= the same way, each with its after= and cancel=
// delay where it has one. Like board: lines, these lines add up, and a trigger given twice in one
// tab is a repeat. The page writes a line for each trigger and quotes a name only where it holds =
// or a quote. It reads several to a line, where a name runs on to the next trigger or is quoted.
// Always on's lines are above the first heading and a scene's under its own

var REMOTE_STEPS = ["nothing", "next", "previous", "first", "restart"];

// A button's line, or null where the choice names a scene no longer there, or a number's place
// holds none
function remoteLine(button, choice) {
  var said = choice;
  var scene = choice === "order" ? sceneInOrder(button)
            : choice.indexOf("scene:") === 0 ? sceneMarked(choice.slice(6)) : null;
  if ((choice === "order" || choice.indexOf("scene:") === 0) && !scene) return null;
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
  var scene = sceneNamed(named[1]);
  if (!scene) return null;
  if (isNumber(button)) return sceneInOrder(button) === scene ? "order" : null;
  return "scene:" + sceneMark(scene);
}

addStep(boardLineSteps.after, BOARD_LINE_AFTER, "sensor", function (line) {
  if (state.sensorKind === "none") return line;
  return (line || "board:") + " sensor=" + state.sensorKind;
});

// Read what is fitted from the board line, and take its token so it is not written twice
function readSensorBoard() {
  state.sensorKind = "none";
  filterResidue(function (token) {
    var fitted = /^sensor=(ir|pir)$/i.exec(token);
    if (fitted) state.sensorKind = fitted[1].toLowerCase();
    return !fitted;
  });
}

// Take each body's remote: lines, or motion: lines for a PIR Stick, that the page can hold as its
// choices. A line is taken whole or not at all. One with a trigger the page cannot hold or one the
// tab already gave stays as written, as does every line for what is not fitted. A repeated
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

// A scene keeps its own choices of what triggers do, as it keeps its looks. Its card shows the
// remote's or PIR Stick's icon where it changes any trigger, and Always on's whenever one is fitted
addStep(bodyParts, BODY_ORDER, "sensor", {
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
  // A tab's remote: or motion: lines, in the order of the triggers
  entries: function (body, lines) {
    if (!body.remote) return lines;
    var timings = body.motionTiming || {};
    fittedTriggers().forEach(function (trigger) {
      var choice = body.remote[trigger];
      // A trigger with a delay but no choice of its own does what its default does
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

// The tab has no swatch, since its name and what is fitted under it say all there is
tabSwatches.sensorPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch sensorswatch";
};

function sensorUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=sensorPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  tab.prepend(h("span", {className: "tabname"}, tab.querySelector("b"),
                h("small", {className: "tabunder"}, sensorFacts()[2])));
}

addStep(drawSteps.after, DRAW_AFTER, "sensor", function () {
  sensorUnderName();
  renderSensor();
});

document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]).after(
  h("details", {className: "panel", id: "sensorPanel", open: true},
    h("summary", {}, "Sensor"),
    h("div", {className: "facts", id: "sensorFacts"}),
    h("div", {id: "sensor"})));

TAB_NAMES.sensorPanel = "Sensor";
addStep(TAB_PANELS, FEATURE_TABS, "sensor", "sensorPanel");
keptOpen("sensorPanel");
