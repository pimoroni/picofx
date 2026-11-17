import {boardSet, driveMeansSomething} from "./board_settings.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "./draw.js";

// ---- how the board takes a save, on the save button ----------------------------------------------
// Whether a save plays without an eject, and whether the drive stays hidden at start, are about
// saving, so they are set where the drive is saved to, in a menu on a small arrow joined to the
// save button

var saveMenu = document.getElementById("saveMenu");
var saveArrow = document.getElementById("saveArrow");

// A choice in the menu, a checkbox that calls flip() with its new state, said with a hint below,
// or with the reason it cannot be changed
function saveChoice(words, hint, on, flip, refused) {
  var box = h("input", {
    type: "checkbox", checked: on, disabled: !!refused,
    onchange: function () {
      flip(box.checked);
      draw();
    }
  });
  return h("label", {className: "savechoice" + (refused ? " refused" : "")},
           box, h("span", {}, words, h("small", {}, refused || hint)));
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

// Opened under its own arrow, its right edge at the arrow's, wherever the header has put it
saveArrow.onclick = function () {
  showSaveMenu(saveMenu.hidden);
  if (saveMenu.hidden) return;
  var within = saveMenu.offsetParent.getBoundingClientRect();
  var under = saveArrow.getBoundingClientRect();
  saveMenu.style.left = "auto";
  saveMenu.style.right = (within.right - under.right) + "px";
  saveMenu.style.top = (under.bottom - within.top + 6) + "px";
};

document.addEventListener("click", function (event) {
  if (saveMenu.hidden || saveMenu.contains(event.target) || saveArrow.contains(event.target)) return;
  closeSaveMenu();
});

document.addEventListener("keydown", function (event) {
  if (event.key !== "Escape" || saveMenu.hidden) return;
  closeSaveMenu();
  saveArrow.focus();
});

addStep(drawSteps.after, DRAW_AFTER, "saveMenu", renderSaveMenu);
