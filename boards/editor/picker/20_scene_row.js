import {h, replace} from "./00_dom.js";
import {draw} from "./03_runs.js";
import {
  removeScene, renderSceneTray, sceneAfter, sceneBand, sceneCanWait, sceneEdge, sceneLoops,
  sceneMark, sceneMarked, sceneNameProblem, sceneRestarts, sceneShowsAgain, sceneWaitsFor, state,
  unreachedScenes
} from "./04_scenes.js";
import {renderPreview} from "./18_drive.js";

var sceneRow = document.getElementById("sceneTabRow");
var scenePlaceLine = null;

export function renderSceneSettings() {
  sceneRow.hidden = !state.scenes.length;
  if (!state.scenes.length) {
    replace(sceneRow);
    return;
  }
  var picked = state.at < 0 ? null : state.scenes[state.at];
  sceneRow.style.setProperty("--frame", sceneEdge(picked));
  sceneRow.style.setProperty("--band", sceneBand(picked));
  scenePlaceLine = h("p", {});
  replace(sceneRow,
    picked ? sceneControls(picked)
           : h("p", {}, "Always on plays under every scene. A scene that uses the same lights, " +
                        "screen or sound overrides it while showing."),
    scenePlaceLine,
    picked ? h("button", {type: "button", title: "Remove this scene",
                          onclick: removeSceneShown}, "Remove scene")
           : null);
  renderScenePlace();
}

function removeSceneShown() {
  removeScene(state.at);
}

function renderScenePlace() {
  var count = state.scenes.length;
  if (state.at < 0) {
    scenePlaceLine.textContent = "Under " + count + (count === 1 ? " scene" : " scenes");
    scenePlaceLine.removeAttribute("data-warn");
    scenePlaceLine.removeAttribute("title");
    return;
  }
  var picked = state.scenes[state.at];
  var after = sceneAfter(picked);
  var problem = sceneNameProblem(picked, picked.name);
  var unreached = unreachedScenes();
  if (!problem && unreached.scenes.indexOf(picked) >= 0) {
    problem = unreached.stopper ? "Never shows, as " + unreached.stopper.name.trim() +
                                  " waits forever before it"
                                : "Never shows, as no scene goes on to it";
  }
  var ends = picked.waits ? "waits " + (sceneCanWait() ? "for " + sceneWaitsFor() : "forever")
           : after === picked ? "then itself" : after ? "then " + after.name : "on its own";
  scenePlaceLine.textContent = problem || "Scene " + (state.at + 1) + " of " + count + ", " + ends;
  scenePlaceLine.title = scenePlaceLine.textContent;
  scenePlaceLine.toggleAttribute("data-warn", !!problem);
}

function sceneControls(scene) {
  var lone = state.scenes.length === 1;
  return h("fieldset", {"aria-label": "Scene settings"},
    sceneNameField(scene),
    h("select", {"aria-label": "How the scene ends",
                 onchange: function (event) {
                   scene.waits = event.target.value === "waits";
                   draw();
                 }},
      h("option", {value: "shows", selected: !scene.waits}, "shows for"),
      h("option", {value: "waits", selected: scene.waits}, "waits")),
    scene.waits ? null : [
      h("input", {type: "number", min: 1, value: scene.seconds, "aria-label": "Seconds",
                  "data-focus": "scene-seconds",
                  onchange: function (event) {
                    scene.seconds = Math.max(1, Number(event.target.value) || 1);
                    draw();
                  }}),
      h("span", {}, lone ? "s, then itself" : "s, then"),
      lone ? null : sceneThenChoice(scene)
    ],
    restartToggle(scene));
}

function sceneNameField(scene) {
  if (scene.goodName === undefined && !sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
  var field = h("input", {type: "text", value: scene.name, "aria-label": "Scene name",
                          "data-focus": "scene-name",
                          oninput: function () {
                            scene.name = field.value.replace(/[\[\]:]/g, "");
                            if (field.value !== scene.name) field.value = scene.name;
                            markName();
                            renderSceneTray();
                            renderScenePlace();
                            renderPreview();
                          },
                          onchange: function () {
                            scene.name = scene.name.trim();
                            if (!sceneNameProblem(scene, scene.name)) scene.goodName = scene.name;
                            else if (scene.goodName) scene.name = scene.goodName;
                            draw();
                          }});
  function markName() {
    var problem = sceneNameProblem(scene, scene.name);
    field.setAttribute("aria-invalid", problem ? "true" : "false");
    field.title = problem || "Scene name";
  }
  markName();
  return field;
}

function sceneThenChoice(scene) {
  var inOrder = state.scenes[(state.at + 1) % state.scenes.length];
  var chosen = scene.then && sceneMarked(scene.then) && sceneMarked(scene.then) !== inOrder
             ? scene.then : "";
  return h("select", {"aria-label": "Scene after",
                      title: "The scene after this one, the next in order unless another is chosen",
                      onchange: function (event) {
                        scene.then = event.target.value || null;
                        draw();
                      }},
    h("option", {value: "", selected: chosen === ""}, "the next scene"),
    state.scenes.filter(function (other) { return other !== inOrder; }).map(function (other) {
      var mark = sceneMark(other);
      return h("option", {value: mark, selected: chosen === mark},
               other === scene ? "itself" : other.name);
    }));
}

function restartToggle(scene) {
  var loops = sceneLoops(scene);
  var once = !sceneShowsAgain(scene);
  var on = sceneRestarts(scene);
  return h("button", {type: "button", "aria-pressed": on && !once ? "true" : "false",
                      disabled: loops || once,
                      title: loops ? "A scene that goes back to itself always restarts"
                           : once ? "This scene shows only once, so it has nothing to restart"
                           : "Restart this scene's effects each time it plays, instead of " +
                             "resuming where they left off",
                      onclick: function () {
                        scene.restart = !on;
                        draw();
                      }},
    h("span", {"aria-hidden": "true"}, "\u21b6"), " Restart");
}
