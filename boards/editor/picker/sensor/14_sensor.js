import {h, replace} from "../00_dom.js";
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

var SENSOR_KINDS = [["none", "nothing", "none", ""],
                    ["ir", "an Aye Arr Remote", "Aye Arr",
                     "through an IR Receiver Stick on the sensor connector"],
                    ["pir", "a PIR Stick", "PIR Stick", "on the sensor connector"]];

state.sensorKind = "none";
state.remote = {};
state.remoteRepeats = [];

BOARD_CHIP_CLASSES.sensorPanel = "sensor";

function sensorFacts() {
  return SENSOR_KINDS.filter(function (one) { return one[0] === state.sensorKind; })[0];
}

function remoteFitted() { return state.sensorKind === "ir"; }
function pirFitted() { return state.sensorKind === "pir"; }

var MOTION_TRIGGERS = ["MOTION_STARTS", "MOTION_STOPS"];

function triggerFitted(trigger) {
  return MOTION_TRIGGERS.indexOf(trigger) >= 0 ? pirFitted() : remoteFitted();
}

function fittedTriggers() {
  return pirFitted() ? MOTION_TRIGGERS
       : remoteFitted() ? REMOTE_BUTTONS.map(function (button) { return button[0]; }) : [];
}

function isNumber(button) { return /^\d_/.test(button); }

var REMOTE_FIXED = {OK_STOP: ["standby", "Standby and wake, in every scene"],
                    PLAY_PAUSE: ["pause", "Pause the effects where they stand, in every scene"]};

sceneCanWait = function () { return remoteFitted() || pirFitted(); };
sceneWaitsFor = function () { return pirFitted() ? "motion" : "a button"; };

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

function remoteDefault(button) {
  if (/^\d_/.test(button)) return "order";
  if (!state.scenes.length) return "nothing";
  if (button === "LEFT") return "previous";
  if (button === "RIGHT") return "next";
  return "nothing";
}

function sceneInOrder(button) {
  var number = Number(button.charAt(0));
  return state.scenes[(number || 10) - 1] || null;
}

function remoteResolved(button) {
  if (REMOTE_FIXED[button]) return {choice: REMOTE_FIXED[button][0], from: "fixed"};
  if (state.remote[button] !== undefined) return {choice: state.remote[button], from: "own"};
  if (state.at < 0) return {choice: remoteDefault(button), from: "own"};
  var always = state.always.body && state.always.body.remote || {};
  return {choice: always[button] !== undefined ? always[button] : remoteDefault(button),
          from: "always"};
}

function remoteSays(choice, button) {
  if (choice === "order") {
    var scene = sceneInOrder(button);
    return scene ? "Scene: " + scene.name : "";
  }
  if (choice.indexOf("scene:") === 0) {
    var marked = sceneMarked(choice.slice(6));
    return marked ? "Scene: " + marked.name : "";
  }
  if (choice === "restart") {
    return state.at >= 0 ? "Scene: " + state.scenes[state.at].name + ", from the start"
         : state.scenes.length ? "Restart the scene showing" : "Restart the effects";
  }
  return {nothing: "", next: "Next scene", previous: "Previous scene", first: "First scene",
          standby: "Standby", pause: "Pause"}[choice];
}

function sceneSelfDiffers(scene) {
  return !scene.waits && !sceneRestarts(scene);
}

function triggerDoingNothing() {
  if (state.at < 0) return null;
  var showing = state.scenes[state.at];
  if (sceneRestarts(showing) || sceneSelfDiffers(showing)) return null;
  return fittedTriggers().filter(function (trigger) {
    return state.remote[trigger] === "scene:" + sceneMark(showing);
  })[0] || null;
}

function remoteDoes(button) {
  return triggerFitted(button) && remoteSays(remoteResolved(button).choice, button) !== "";
}

sceneNumbers = function (scene) {
  var at = state.scenes.indexOf(scene);
  if (!remoteFitted() || at > 9) return [];
  var button = REMOTE_BUTTONS.filter(function (one) {
    return one[0].charAt(0) === String((at + 1) % 10) && isNumber(one[0]);
  })[0][0];
  var always = state.at < 0 ? state.remote : state.always.body && state.always.body.remote || {};
  return always[button] === "nothing" ? [] : [(at + 1) % 10];
};

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

function remoteInk(name) {
  if (name === "8_WHITE") return "#a7a9ac";
  if (name === "6_YELLOW") return "#e0cf00";
  if (name === "0_RAINBOW") return "#92278f";
  var number = /^(\d)_/.exec(name);
  return number ? REMOTE_COLOURS[Number(number[1]) - 1] : "#808285";
}

state.motionTiming = {};

var MOTION_TIMING_DEFAULT = {after: 0, cancel: true};

var MOTION_CANCELLED_BY = {MOTION_STARTS: "If motion stops first?",
                           MOTION_STOPS: "If motion starts again first?"};

function motionTiming(trigger) {
  var own = state.at < 0 || state.remote[trigger] !== undefined;
  var held = own ? state.motionTiming
                 : state.always.body && state.always.body.motionTiming || {};
  return held[trigger] || MOTION_TIMING_DEFAULT;
}

function setMotionTiming(trigger, change) {
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

var REMOTE_STEPS = ["nothing", "next", "previous", "first", "restart"];

function remoteLine(button, choice) {
  var said = choice;
  var scene = choice === "order" ? sceneInOrder(button)
            : choice.indexOf("scene:") === 0 ? sceneMarked(choice.slice(6)) : null;
  if (choice.indexOf("scene:") === 0 && !scene) return null;
  if (scene) {
    said = "scene " + scene.name.trim();
    if (/[="']/.test(scene.name)) said = scene.name.indexOf("\"") < 0 ? "\"" + said + "\"" : "'" + said + "'";
  }
  var motion = MOTION_TRIGGERS.indexOf(button) >= 0;
  return (motion ? "motion: " + button.slice(7).toLowerCase() : "remote: " + button.toLowerCase()) +
         "=" + said;
}

function triggerLine(trigger, choice, timing) {
  var line = remoteLine(trigger, choice);
  if (!line || !timing || !timing.after) return line;
  return line + " after=" + timing.after + "s" + (timing.cancel ? "" : " cancel=no");
}

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

function remoteChoiceRead(button, said) {
  if (REMOTE_FIXED[button]) return null;
  if (REMOTE_STEPS.indexOf(said.toLowerCase()) >= 0) {
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

function readSensorBoard() {
  state.sensorKind = "none";
  boardResidue = boardResidue.filter(function (token) {
    var fitted = /^sensor=(ir|pir)$/i.exec(token);
    if (fitted) state.sensorKind = fitted[1].toLowerCase();
    return !fitted;
  });
}

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
  split: function (always, first) {
    first.remote = {};
    first.remoteRepeats = [];
    first.motionTiming = {};
  },
  readBoard: readSensorBoard,
  read: readRemoteLines
});
var REMOTE_SCALE = 4.3;
var REMOTE_REACH = 16;
var REMOTE_BODY = {left: 71.26, right: 126.45, top: 23.5, bottom: 146};
var REMOTE_ROW_PX = 27;
var REMOTE_MASK_BOX = {x: 60, y: 15, width: 80, height: 140};
var LEADER_IDLE = "#d6d3cd";

var PIR_STICK = {width: 22.692, height: 77.102};
var PIR_SCALE = 3.3;
var PIR_REACH = 14.6;
var PIR_ROWS = [["MOTION_STARTS", "left", 11.883], ["MOTION_STOPS", "right", 11.883]];
var PIR_SENSOR = {left: 0.703, right: 21.989};
var PIR_HEAD_PX = 34;

var MOTION_FIGURES = {
  MOTION_STARTS: "<circle class='f' cx='10' cy='2.6' r='1.9'/><path d='M9.4 5.6 7.8 10.4 6 13.5 " +
                 "2.8 14.6M7.8 10.4l3.3 1.7 1.2 3.4M9.4 5.6 5.7 7.6 4.4 10M9.4 5.6l2.5 2.8 3 .6' " +
                 "fill='none'/><path d='M2.8 4h2.6M.3 7.5h2.4M-.2 11h2' fill='none' " +
                 "stroke-width='1.2'/>",
  MOTION_STOPS: "<circle class='f' cx='8' cy='2.1' r='1.9'/><path d='M8 5.1v4.6M8 9.7l-1.5 " +
                "6M8 9.7l1.5 6M8 5.9 4.3 9.8M8 5.9l3.7 3.9' fill='none'/>"
};
var MOTION_FIGURE_BOX = "-1.2 -0.6 17.2 17.2";

PART_DRAWINGS.pir = "<g transform='translate(2.4 1.5) scale(1.27)' stroke-width='1.4'>" +
                    MOTION_FIGURES.MOTION_STARTS + "</g>";

var IN_SCENE_TIP = "Striped where it does what Always on sets";

function buttonNames() {
  return REMOTE_BUTTONS.map(function (button) { return button[0]; });
}

function option(value, words) {
  return h("option", {value: value}, words);
}

function triggerOptions(button, resolved, showing) {
  if (isNumber(button))
    return {own: [option("order", "Scene: " + sceneInOrder(button).name), option("nothing", "Nothing")],
            more: []};
  if (!state.scenes.length)
    return {own: [option("nothing", "Nothing"), option("restart", remoteSays("restart", button))],
            more: []};
  var keptNothing = showing && resolved.from === "own" && !sceneRestarts(showing) &&
                    !sceneSelfDiffers(showing) && resolved.choice === "scene:" + sceneMark(showing);
  var scenes = [];
  state.scenes.forEach(function (scene) {
    if (scene !== showing || sceneSelfDiffers(scene) || keptNothing) {
      scenes.push(option("scene:" + sceneMark(scene), "Scene: " + scene.name));
    }
    if (scene === showing) scenes.push(option("restart", remoteSays("restart", button)));
  });
  var steps = [["next", "Next scene"], ["previous", "Previous scene"], ["first", "First scene"]]
    .concat(showing ? [] : [["restart", remoteSays("restart", button)]]);
  return {own: [option("nothing", "Nothing")],
          more: [h("optgroup", {label: "Go to a scene"}, scenes),
                 h("optgroup", {label: "Step"}, steps.map(function (step) {
                   return option(step[0], step[1]);
                 }))]};
}

function triggerChoice(button) {
  var resolved = remoteResolved(button);
  var showing = state.at >= 0 ? state.scenes[state.at] : null;
  var choices = triggerOptions(button, resolved, showing);
  var options = choices.own.concat(choices.more);
  if (state.at >= 0) {
    var always = state.always.body && state.always.body.remote || {};
    var under = always[button] !== undefined ? always[button] : remoteDefault(button);
    options = [h("optgroup", {label: "As Always on"}, option("", remoteSays(under, button) || "Nothing")),
               h("optgroup", {label: "In this scene"}, choices.own)].concat(choices.more);
  }
  var choice = h("select", {onchange: function () {
    var value = choice.value;
    if (value === "") delete state.motionTiming[button];
    if (value === "" || (state.at < 0 && value === remoteDefault(button))) delete state.remote[button];
    else state.remote[button] = value;
    settleSceneRow(button);
    draw();
  }}, options);
  choice.value = resolved.from === "own" ? resolved.choice : "";
  if (showing && choice.value === "scene:" + sceneMark(showing) && sceneRestarts(showing)) {
    choice.value = "restart";
  }
  if (choice.selectedOptions.length) choice.title = choice.selectedOptions[0].textContent;
  return choice;
}

function remoteLeader(row) {
  var at = remoteArtAt(row[0]);
  var left = row[1] === "left";
  var from = left ? REMOTE_BODY.left - REMOTE_REACH : REMOTE_BODY.right + REMOTE_REACH;
  var reach = REMOTE_ART_RADIUS;
  if (Math.abs(row[2] - at.y) < 0.01)
    return "M" + from + " " + at.y + " H" + (left ? at.x - reach : at.x + reach);
  var lean = reach * Math.SQRT1_2;
  var endX = left ? at.x - lean : at.x + lean;
  var endY = row[2] > at.y ? at.y + lean : at.y - lean;
  var turn = left ? endX - Math.abs(row[2] - endY) : endX + Math.abs(row[2] - endY);
  return "M" + from + " " + row[2] + " H" + turn.toFixed(2) + " L" + endX.toFixed(2) + " " +
         endY.toFixed(2);
}

function buttonCircle(name, grow) {
  var at = remoteArtAt(name);
  return h("svg:circle", {cx: at.x, cy: at.y, r: REMOTE_ART_RADIUS + (grow || 0)});
}

function remoteMask(id, lit, flipped) {
  var shown = flipped ? "#000" : "#fff";
  var hidden = flipped ? "#fff" : "#000";
  var idle = buttonNames().filter(function (name) { return lit.indexOf(name) < 0; });
  var idleJoins = REMOTE_ART_JOINS.filter(function (join) {
    return lit.indexOf(join[1]) < 0 || lit.indexOf(join[2]) < 0;
  });
  return h("svg:mask", Object.assign({id: id, maskUnits: "userSpaceOnUse"}, REMOTE_MASK_BOX),
    h("svg:rect", Object.assign({fill: shown}, REMOTE_MASK_BOX)),
    h("svg:g", {fill: hidden},
      idle.map(function (name) { return buttonCircle(name); }),
      idleJoins.map(function (join) { return h("svg:path", {d: remoteArtJoin(join[0])}); })),
    h("svg:g", {fill: shown}, lit.map(function (name) { return buttonCircle(name); })));
}

function remoteLayers() {
  var art = h("svg:g", {id: "raArt", html: remoteArt()});
  var darken = h("svg:filter", {id: "raDark"},
    h("svg:feComponentTransfer", {}, ["R", "G", "B"].map(function (channel) {
      return h("svg:feFunc" + channel, {type: "linear", slope: 0.5});
    })));
  if (!remoteFitted()) return [h("svg:defs", {}, art, darken), h("svg:use", {href: "#raArt", opacity: 0.35})];
  var lit = buttonNames().filter(remoteDoes);
  return [h("svg:defs", {}, art, darken, remoteMask("raFull", lit, false), remoteMask("raRest", lit, true)),
          h("svg:use", {href: "#raArt", filter: "url(#raDark)", opacity: 0.5, mask: "url(#raRest)"}),
          h("svg:use", {href: "#raArt", mask: "url(#raFull)"})];
}

function leader(button, path, ink) {
  return h("svg:path", {"data-button": button, d: path, style: {"--leader": ink}});
}

function padlock() {
  return h("svg:svg", {viewBox: "0 0 12 12", "aria-hidden": "true"},
    h("svg:rect", {x: 2, y: 5, width: 8, height: 6, rx: 1.2}),
    h("svg:path", {d: "M4 5V3.6a2 2 0 0 1 4 0V5"}));
}

function remoteRow(row, fitted, choosers) {
  var button = row[0];
  var resolved = remoteResolved(button);
  var fixed = resolved.from === "fixed";
  var unbound = isNumber(button) && !sceneInOrder(button);
  var choosable = fitted && !fixed && !unbound;
  var words = h("span", {}, remoteWords(button));
  var shown;
  if (choosable) {
    choosers[button] = triggerChoice(button);
    shown = h("label", {}, words, choosers[button]);
  } else {
    var said = !fitted ? "" : unbound ? "No scene " + (Number(button.charAt(0)) || 10)
                                      : remoteSays(resolved.choice, button);
    shown = [words, h("output", {}, fixed && fitted ? padlock() : null, said)];
  }
  return h("li", {"data-button": button, "data-does": remoteDoes(button),
                  "data-from": fixed ? "fixed" : fitted && resolved.from === "always" ? "always" : null,
                  title: fixed && fitted ? REMOTE_FIXED[button][1]
                       : choosable && state.at >= 0 ? IN_SCENE_TIP : null,
                  style: {"--top": Math.round((row[2] - REMOTE_BODY.top) * REMOTE_SCALE -
                                              REMOTE_ROW_PX / 2) + "px"}},
           shown);
}

function sideList(side, rows, drawRow) {
  return h("ul", {"data-side": side}, rows.filter(function (row) {
    return row[1] === side;
  }).map(drawRow));
}

function remoteDiagram() {
  var width = REMOTE_BODY.right - REMOTE_BODY.left + 2 * REMOTE_REACH;
  var height = REMOTE_BODY.bottom - REMOTE_BODY.top;
  var fitted = remoteFitted();
  var choosers = {};
  var leaders = REMOTE_ROWS.map(function (row) {
    return leader(row[0], remoteLeader(row), remoteDoes(row[0]) ? remoteInk(row[0]) : LEADER_IDLE);
  });
  var covers = REMOTE_BUTTONS.map(function (button) {
    var cover = buttonCircle(button[0], 0.2);
    cover.dataset.button = button[0];
    if (fitted && !REMOTE_FIXED[button[0]]) {
      cover.dataset.choosable = "";
      cover.addEventListener("click", function () {
        var chooser = choosers[button[0]];
        if (!chooser) return;
        chooser.focus();
        try { chooser.showPicker(); } catch (refused) {}
      });
    }
    return cover;
  });
  var drawRow = function (row) { return remoteRow(row, fitted, choosers); };
  var diagram = h("div", {"data-kind": "remote",
                          style: {"--middle": Math.round(width * REMOTE_SCALE) + "px",
                                  "--height": Math.round(height * REMOTE_SCALE) + "px"}},
    sideList("left", REMOTE_ROWS, drawRow),
    h("svg:svg", {viewBox: (REMOTE_BODY.left - REMOTE_REACH) + " " + REMOTE_BODY.top + " " +
                           width + " " + height,
                  role: "img", "aria-label": "The Aye Arr Remote"},
      remoteLayers(), leaders, covers),
    sideList("right", REMOTE_ROWS, drawRow));
  if (fitted) linkHover(diagram);
  return diagram;
}

function linkHover(diagram) {
  var parts = diagram.querySelectorAll("[data-button]");
  function hot(name, on) {
    parts.forEach(function (part) {
      if (part.dataset.button === name) part.toggleAttribute("data-hot", on);
    });
  }
  parts.forEach(function (part) {
    part.addEventListener("mouseenter", function () { hot(part.dataset.button, true); });
    part.addEventListener("mouseleave", function () { hot(part.dataset.button, false); });
  });
}

function motionFigure(trigger) {
  return h("svg:svg", {viewBox: MOTION_FIGURE_BOX, "aria-hidden": "true", html: MOTION_FIGURES[trigger]});
}

function motionLines(trigger) {
  var timing = motionTiming(trigger);
  var waits = timing.after > 0;
  var seconds = h("input", {type: "number", min: 0, step: 0.5, value: timing.after,
                            title: "Seconds to wait before doing it",
                            onchange: function () {
                              setMotionTiming(trigger, {after: Math.max(0, Number(seconds.value) || 0)});
                            }});
  var cancels = h("select", {disabled: !waits,
                             onchange: function () {
                               setMotionTiming(trigger, {cancel: cancels.value === "yes"});
                             }},
                  option("yes", "cancel this"), option("no", "finish this first"));
  cancels.value = timing.cancel ? "yes" : "no";
  return [
    h("p", {title: state.at >= 0 ? IN_SCENE_TIP : null},
      h("label", {}, "Trigger", triggerChoice(trigger)),
      h("label", {}, "after", seconds),
      h("span", {}, "s")),
    h("p", {"data-idle": !waits, title: waits ? null : "Asked once it waits"},
      h("label", {}, MOTION_CANCELLED_BY[trigger], cancels))];
}

function pirTrigger(row) {
  var trigger = row[0];
  var resolved = remoteResolved(trigger);
  return h("li", {style: {"--top": Math.round(row[2] * PIR_SCALE - PIR_HEAD_PX / 2) + "px"}},
    h("fieldset", {"data-button": trigger, "data-does": remoteDoes(trigger),
                   "data-from": resolved.from === "always" ? "always" : null},
      h("legend", {}, motionFigure(trigger), h("span", {}, remoteWords(trigger))),
      motionLines(trigger)));
}

function pirDiagram() {
  var width = PIR_STICK.width + 2 * PIR_REACH;
  var leaders = PIR_ROWS.map(function (row) {
    var path = row[1] === "left"
      ? "M" + -PIR_REACH + " " + row[2] + " H" + PIR_SENSOR.left
      : "M" + PIR_SENSOR.right + " " + row[2] + " H" + (PIR_STICK.width + PIR_REACH);
    return leader(row[0], path, remoteDoes(row[0]) ? "#808285" : LEADER_IDLE);
  });
  return h("div", {"data-kind": "pir",
                   style: {"--middle": Math.round(width * PIR_SCALE) + "px",
                           "--height": Math.round(PIR_STICK.height * PIR_SCALE) + "px"}},
    sideList("left", PIR_ROWS, pirTrigger),
    h("svg:svg", {viewBox: -PIR_REACH + " 0 " + width + " " + PIR_STICK.height,
                  role: "img", "aria-label": "The PIR Stick", html: PIR_ART.join("")},
      leaders),
    sideList("right", PIR_ROWS, pirTrigger));
}

function sensorFitting() {
  var fitted = sensorFacts();
  var parts = ["Sensor"];
  if (canEdit("sensorPanel")) {
    var choice = h("select", {"aria-label": "Sensor", onchange: function () {
      state.sensorKind = choice.value;
      draw();
    }}, SENSOR_KINDS.map(function (kind) { return option(kind[0], kind[1]); }));
    choice.value = state.sensorKind;
    parts.push(choice);
    if (fitted[3]) parts.push(small(fitted[3]));
  } else {
    parts.push(small(state.sensorKind === "none" ? "nothing on the sensor connector"
                                                 : fitted[1] + ", " + fitted[3]));
  }
  return h("p", {}, boardBox("sensorPanel", parts),
           !canEdit("sensorPanel") && state.sensorKind === "none" ? h("small", {}, "Edit board to fit one.") : null);
}

function said(words, tone) {
  return h("p", {"data-tone": tone}, words);
}

function sensorWords() {
  var words = [];
  if (pirFitted()) {
    words.push(said(state.at < 0
      ? "What motion starting and stopping does in every scene. A scene can change either while " +
        "it shows."
      : "Striped rows do what Always on sets. Choose one to change it in this scene."));
  } else if (!remoteFitted()) {
    words.push(said("The sensor connector takes one thing at a time, such as the Aye Arr Remote " +
                    "through an IR Receiver Stick.", "dim"));
  } else if (state.at < 0) {
    words.push(said("What each button does in every scene. A scene can change any of them while " +
                    "it shows."));
    if (!state.scenes.length) {
      words.push(said("With scenes, the numbers go to them and the arrows step through them.", "dim"));
      words.push(h("button", {type: "button", onclick: addScene}, "split into scenes"));
    }
  } else {
    words.push(said("Striped buttons do what Always on sets. Choose one to change it in this scene."));
  }
  return words.concat(sensorWarnings());
}

function sensorWarnings() {
  var warnings = [];
  var idle = triggerDoingNothing();
  if (idle) {
    var showing = state.scenes[state.at].name;
    warnings.push(said(remoteWords(idle) + " does nothing here, as " + showing + " is already " +
                       "showing and waits. Choose \"Scene: " + showing + ", from the start\" to " +
                       "begin it again.", "warn"));
  }
  if (fittedTriggers().length && state.remoteRepeats.length) {
    warnings.push(said((state.remoteRepeats.length === 1 ? "" : "Each of ") +
      state.remoteRepeats.map(remoteWords).join(", ") + " is given twice in the file here. The " +
      "page uses the first and keeps the second line as it is.", "warn"));
  }
  return warnings;
}

var sensorTab = h("section", {class: "sensortab", "aria-label": "Sensor"});

function renderSensor() {
  replace(sensorTab,
    sensorFitting(),
    pirFitted() ? pirDiagram() : remoteDiagram(),
    h("div", {}, sensorWords()));
}

tabSwatches.sensorPanel = function (swatch) {
  swatch.className = "accswatch";
  replace(swatch);
};

function sensorUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=sensorPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  tab.prepend(h("span", {class: "tabname"}, tab.querySelector("b"),
                h("small", {class: "tabunder"}, sensorFacts()[2])));
}

drawSteps.after.push(function () {
  sensorUnderName();
  renderSensor();
});

document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]).after(
  h("details", {class: "panel", id: "sensorPanel", open: true}, h("summary", {}, "Sensor"), sensorTab));

TAB_NAMES.sensorPanel = "Sensor";
TAB_PANELS.push("sensorPanel");
keptOpen("sensorPanel");
