import {boardLine} from "./board.js";
import {HEADER} from "./looks.js";
import {fileHead, lampLines} from "./runs.js";
import {
  apply, bodyParts, sceneAfter, sceneNamed, sceneRestarts, slotAt, state, store
} from "./scenes.js";

// ---- what the whole file says now -------------------------------------------------------

// The line a file with no entries ends in, so the board has nothing to play
export var NOTHING_PLAYING = "# Nothing is playing yet.";

// A body's entries. The lamps' lines are written from the runs as they stand, so the body is
// applied first, which keeps one writer for every scene
function entriesOf(body) {
  apply(body);
  var lines = lampLines().filter(function (line) { return line.trim(); });
  bodyParts.forEach(function (part) { if (part.entries) lines = part.entries(body, lines); });
  return lines;
}

// A scene's heading. One read from a file with no time waits, and is written back without one.
// A heading read from a file is written back as it was while the scene still says the same
function sceneHeading(scene) {
  // Where the scene that follows is not the next in order, name it after "then". That goes last,
  // since the rest of the heading after it is read as the name
  var after = sceneAfter(scene);
  var inOrder = state.scenes[(state.scenes.indexOf(scene) + 1) % state.scenes.length];
  var named = after && after !== inOrder ? after.name.trim() || "Scene" : null;
  var read = scene.read;
  // A file's "then" naming no scene keeps the heading as written, while the scene has none
  var sameAfter = read && (read.after === named || (read.after && !scene.then &&
    !sceneNamed(read.after)));
  if (read && read.written && scene.name === read.name && sceneRestarts(scene) === read.restart &&
      sameAfter && (read.seconds === null ? scene.waits
                                          : !scene.waits && scene.seconds === read.seconds)) {
    return read.written;
  }
  // Restart is written wherever sceneRestarts() says, which a scene going back to itself needs
  var settings = (scene.waits ? [] : [scene.seconds + "s"])
    .concat(sceneRestarts(scene) ? ["restart"] : [])
    .concat(named !== null ? ["then " + named] : []);
  return "[" + (scene.name.trim() || "Scene") + (settings.length ? ": " + settings.join(" ") : "") +
         "]";
}

export function currentText() {
  store();
  var lines = entriesOf(state.always.body);
  state.scenes.forEach(function (scene) {
    lines.push("");
    // Comments a file had above the heading, where it was read from one
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
         (lines.length ? lines.join("\n") : NOTHING_PLAYING);
}
