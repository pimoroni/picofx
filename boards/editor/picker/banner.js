import {h, replace} from "./dom.js";

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
  var row = h("span", {className: "spots"}, [0, 1, 2, 3, 4, 5, 6].map(function () { return h("i"); }));
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
  // The warn argument may also be "hold", the amber of a save or check still under way
  replace(box, text ? h("div", {className: warn === "hold" ? "banner hold" : warn ? "banner warn"
                                                                                : "banner"},
                        text, detail ? h("pre", {}, detail) : null)
                    : null);
}
