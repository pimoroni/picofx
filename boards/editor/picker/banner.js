// ---- the banner ---------------------------------------------------------------------------------
// The line that says what the page is doing, and the spots that move along it while a save is
// under way.

var SPOT_STEP_MS = 120;

var spotTimer = null;

function stopSpots() {
  if (spotTimer !== null) clearInterval(spotTimer);
  spotTimer = null;
}

export function saving(text) {
  banner(text, "hold");
  var row = document.createElement("span");
  row.className = "spots";
  for (var i = 0; i < 7; i++) row.appendChild(document.createElement("i"));
  document.getElementById("banner").firstChild.appendChild(row);
  var at = 0;
  spotTimer = setInterval(function () {
    for (var i = 0; i < row.children.length; i++)
      row.children[i].className = i === at ? "lit" : "";
    at = (at + 1) % row.children.length;
  }, SPOT_STEP_MS);
}

// The parts that also show what banner() says, each given its text and warn as banner() is
export var bannerSteps = [];

export function banner(text, warn, detail) {
  stopSpots();
  bannerSteps.forEach(function (step) { step(text, warn); });
  var box = document.getElementById("banner");
  box.textContent = "";
  if (!text) return;
  var note = document.createElement("div");
  // The warn argument may also be "hold", the amber of a save or check still under way
  note.className = warn === "hold" ? "banner hold" : warn ? "banner warn" : "banner";
  note.textContent = text;
  if (detail) {
    var pre = document.createElement("pre");
    pre.textContent = detail;
    note.appendChild(pre);
  }
  box.appendChild(note);
}
