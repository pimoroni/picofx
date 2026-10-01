
// ---- a scene's own settings, in the screens' style ---------------------------------------
// The row's words take the screens' label and unit styles, and whether the scene's effects
// begin again each time it comes round is a toggle with its icon, as the screens' Loop and
// Ping pong are. It is called Restart,
// the heading's own word, as each of theirs is the file's.

var oneSceneSettings = renderSceneSettings;

renderSceneSettings = function () {
  oneSceneSettings();
  // Always on has no settings of its own, so its row says what it is for, the gallery staying
  // where it was as the tabs are switched. Only once there are scenes for it to be under
  if (state.at < 0 && state.scenes.length) {
    var note = document.createElement("div");
    note.className = "sceneset alwaysnote";
    note.textContent = "Always on plays under every scene. A scene that sets the same lights, " +
                       "screen or sound takes them over while it shows.";
    // One line, as the row it stands in for is, the whole of it in the tip where it is cut
    note.title = note.textContent;
    document.getElementById("sceneSettings").appendChild(note);
    return;
  }
  var row = document.querySelector("#sceneSettings .sceneset");
  if (!row || state.at < 0) return;
  var scene = state.scenes[state.at];
  var words = row.querySelectorAll(":scope > span");
  if (words[0]) words[0].className = "snamed";
  if (words[1]) words[1].className = "sunit";
  var ticked = row.querySelector("label");
  if (!ticked) return;
  row.replaceChild(toggle("&#8630;", "Restart", scene.restart,
                          function (on) { scene.restart = on; },
                          "Its effects begin again every time the scene comes round, " +
                          "instead of carrying on where they left off"),
                   ticked);
};

draw();
