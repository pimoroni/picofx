import {toggle} from "./01_looks.js";
import {renderSceneRow, sceneLoops, sceneRestarts, sceneShowsAgain, state} from "./04_scenes.js";

// ---- a scene's own settings, in the screens' style ---------------------------------------
// Whether the scene's effects begin again each time it comes round is a toggle with its icon, as
// the screens' Loop and Ping pong are. It is called Restart, the heading's own word, as each of
// theirs is the file's.

export function renderSceneSettings() {
  renderSceneRow();
  // Always on has no settings of its own, so its row says what it is for, the gallery staying
  // where it was as the tabs are switched. Only once there are scenes for it to be under
  if (state.at < 0 && state.scenes.length) {
    var note = document.createElement("div");
    note.className = "sceneset alwaysnote";
    note.textContent = "Always on plays under every scene. A scene that uses the " +
                       "same lights, screen or sound overrides it while showing.";
    document.getElementById("sceneSettings").appendChild(note);
    return;
  }
  var row = document.querySelector("#sceneSettings .sceneset");
  if (!row || state.at < 0) return;
  var scene = state.scenes[state.at];
  var ticked = row.querySelector("label");
  if (!ticked) return;
  // A scene going back to itself always restarts, so its toggle is held on. A scene that never
  // shows again starts once, so its toggle is greyed
  var loops = sceneLoops(scene);
  var once = !sceneShowsAgain(scene);
  var restart = toggle("&#8630;", "Restart", sceneRestarts(scene),
                       function (on) { scene.restart = on; },
                       loops ? "A scene that goes back to itself always restarts"
                       : once ? "This scene shows only once, so it has nothing to restart"
                       : "Restart this scene's effects each time it plays, instead of " +
                         "resuming where they left off", once);
  restart.disabled = loops || once;
  row.replaceChild(restart, ticked);
}
