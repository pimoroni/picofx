import {h, replace} from "./00_dom.js";
import {draw, drawSteps} from "./03_runs.js";
import {boardSet, driveMeansSomething} from "./19_board_settings.js";

var saveMenu = document.getElementById("saveMenu");
var saveArrow = document.getElementById("saveArrow");

function saveChoice(words, hint, on, flip, refused) {
  return h("label", {},
    h("input", {type: "checkbox", checked: on, disabled: !!refused,
                onchange: function (event) {
                  flip(event.target.checked);
                  draw();
                }}),
    h("span", {}, words, h("small", {}, refused || hint)));
}

function renderSaveMenu() {
  replace(saveMenu,
    saveChoice("Play saves without an eject",
               boardSet.program ? "saving restarts the board and runs the program"
                                : "the first save after turning this on still needs an eject",
               boardSet.reload, function (on) { boardSet.reload = on; }, null),
    saveChoice("Keep the drive hidden at start", "double-press Boot to show it",
               boardSet.driveHidden, function (on) { boardSet.driveHidden = on; },
               driveMeansSomething() ? null : "always shown while a program runs"));
}

function showSaveMenu(shown) {
  saveMenu.hidden = !shown;
  saveArrow.setAttribute("aria-expanded", shown ? "true" : "false");
}

export function closeSaveMenu() {
  showSaveMenu(false);
}

saveArrow.addEventListener("click", function () {
  showSaveMenu(saveMenu.hidden);
});

document.addEventListener("click", function (event) {
  if (saveMenu.hidden || saveMenu.contains(event.target) || saveArrow.contains(event.target)) return;
  closeSaveMenu();
});

document.addEventListener("keydown", function (event) {
  if (event.key !== "Escape" || saveMenu.hidden) return;
  closeSaveMenu();
  saveArrow.focus();
});

drawSteps.after.push(renderSaveMenu);
