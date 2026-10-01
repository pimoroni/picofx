
// ---- how the board takes a save, on the save button ----------------------------------------------
// Whether a save plays without an eject, and whether the drive stays hidden at start, are about
// saving, so they are set where the drive is saved to: a menu on a small arrow joined to the save
// button. Neither waits for Edit board, neither being how the board is built

function saveMenu() {
  var menu = document.getElementById("saveMenu");
  menu.textContent = "";
  function choice(words, hint, on, flip, refused) {
    var label = document.createElement("label");
    label.className = "savechoice" + (refused ? " refused" : "");
    var box = document.createElement("input");
    box.type = "checkbox";
    box.checked = on;
    box.disabled = !!refused;
    box.onchange = function () {
      flip(box.checked);
      draw();
    };
    label.appendChild(box);
    var said = document.createElement("span");
    said.innerHTML = words + "<small>" + (refused || hint) + "</small>";
    label.appendChild(said);
    menu.appendChild(label);
  }
  choice("Play saves without an eject",
         "the save that first turns this on still needs one",
         boardSet.reload, function (on) { boardSet.reload = on; },
         savingMeansSomething() ? null : "a program keeps the board busy: press Reset to play a " +
                                         "change");
  choice("Keep the drive hidden at start", "double-press Boot to bring it back",
         boardSet.driveHidden, function (on) { boardSet.driveHidden = on; },
         driveMeansSomething() ? null : "shown anyway while a program runs");
}

(function () {
  var save = document.getElementById("save");
  var arrow = document.createElement("button");
  arrow.type = "button";
  arrow.id = "saveArrow";
  arrow.className = "savearrow";
  arrow.textContent = "\u25be";
  arrow.title = "How the board takes a save";
  save.parentNode.insertBefore(arrow, save.nextSibling);
  var menu = document.createElement("div");
  menu.id = "saveMenu";
  menu.className = "savemenu";
  menu.hidden = true;
  document.querySelector("header").appendChild(menu);
  // Opened under its own arrow, its right edge at the arrow's, wherever the header has put it
  arrow.onclick = function () {
    menu.hidden = !menu.hidden;
    if (menu.hidden) return;
    var within = menu.offsetParent.getBoundingClientRect();
    var under = arrow.getBoundingClientRect();
    menu.style.left = "auto";
    menu.style.right = (within.right - under.right) + "px";
    menu.style.top = (under.bottom - within.top + 6) + "px";
  };
  document.addEventListener("click", function (event) {
    if (!menu.hidden && !menu.contains(event.target) && event.target !== arrow) menu.hidden = true;
  });
}());

var oneSaveMenuDraw = draw;

draw = function () {
  oneSaveMenuDraw();
  saveMenu();
};
