import {HEADER} from "./01_looks.js";
import {lampLines} from "./03_runs.js";
import {apply, bodyParts, sceneAfter, sceneRestarts, slotAt, state, store} from "./04_scenes.js";
import {boardLine} from "./07_board.js";

var WRITTEN_IN_ORDER = ["sound", "screens", "sensor", "hub", "kept"];

function entriesOf(body) {
  apply(body);
  var lines = lampLines().filter(function (line) { return line.trim(); });
  WRITTEN_IN_ORDER.forEach(function (writes) {
    bodyParts.forEach(function (part) {
      if (part.writes === writes) lines = part.entries(body, lines);
    });
  });
  return lines;
}

function sceneHeading(scene) {
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var named = after && after !== inOrder ? after.name.trim() || "Scene" : null;
  var read = scene.read;
  var sameAfter = read && (read.after === named || (read.after && !scene.then &&
    !state.scenes.some(function (other) { return other.name === read.after; })));
  if (read && read.written && scene.name === read.name && sceneRestarts(scene) === read.restart &&
      sameAfter && (read.seconds === null ? scene.waits
                                          : !scene.waits && scene.seconds === read.seconds)) {
    return read.written;
  }
  var settings = (scene.waits ? [] : [scene.seconds + "s"])
    .concat(sceneRestarts(scene) ? ["restart"] : [])
    .concat(named !== null ? ["then " + named] : []);
  return "[" + (scene.name.trim() || "Scene") + (settings.length ? ": " + settings.join(" ") : "") +
         "]";
}

export var fileHead = {under: [], above: []};

export function currentText() {
  store();
  var lines = entriesOf(state.always.body);
  state.scenes.forEach(function (scene) {
    lines.push("");
    lines = lines.concat(scene.comments || []);
    lines.push(sceneHeading(scene));
    lines = lines.concat(entriesOf(scene.body));
  });
  apply(slotAt(state.at).body);

  var head = [];
  fileHead.under.forEach(function (lines) { head = head.concat(lines()); });
  head.push("");
  fileHead.above.forEach(function (lines) { head = head.concat(lines()); });
  var board = boardLine();
  if (board) head.push(board, "");
  return HEADER + head.join("\n") + "\n" +
         (lines.length ? lines.join("\n") : "# Nothing is playing yet.");
}
