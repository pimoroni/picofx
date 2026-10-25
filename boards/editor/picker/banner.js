import {h, replace} from "./dom.js";

// ---- the banner ---------------------------------------------------------------------------------
// The line that says what the page is doing, and the spots that move along it during a save.

var SPOT_STEP_MS = 120;

var spotTimer = null;

function stopSpots() {
  if (spotTimer !== null) clearInterval(spotTimer);
  spotTimer = null;
}

export function saving(text) {
  banner(text, "hold");
  // The spots only show that the save is under way, which the banner's words already say
  var row = h("span", {className: "spots", "aria-hidden": "true"},
              [0, 1, 2, 3, 4, 5, 6].map(function () { return h("i"); }));
  document.getElementById("banner").firstChild.appendChild(row);
  var at = 0;
  spotTimer = setInterval(function () {
    for (var i = 0; i < row.children.length; i++)
      row.children[i].className = i === at ? "lit" : "";
    at = (at + 1) % row.children.length;
  }, SPOT_STEP_MS);
}

// The steps that also show what banner() says, each given its text and warn= as banner() is
export var bannerSteps = [];

// The text of the save the banner reports on, or null where it reports on something else. An
// edit made after that save takes the banner down once the page's text no longer matches it
export var reportedSave = null;

// Mark the banner as reporting on the save of this text, until banner() next changes it
export function setReportedSave(text) {
  reportedSave = text;
}

export function banner(text, warn, detail) {
  stopSpots();
  reportedSave = null;
  bannerSteps.forEach(function (step) { step(text, warn); });
  var box = document.getElementById("banner");
  // The warn argument may also be "hold", the amber of a save or check still under way
  replace(box, text ? h("div", {className: warn === "hold" ? "banner hold" : warn ? "banner warn"
                                                                                : "banner"},
                        text, detail ? h("pre", {}, detail) : null)
                    : null);
}
