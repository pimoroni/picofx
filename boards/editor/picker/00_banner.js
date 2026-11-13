import {h, replace} from "./00_dom.js";

var SPOT_STEP_MS = 120;

var SPOT_COUNT = 7;

var spotTimer = null;

function stopSpots() {
  if (spotTimer !== null) clearInterval(spotTimer);
  spotTimer = null;
}

export function saving(text) {
  var spots = [];
  for (var made = 0; made < SPOT_COUNT; made++) spots.push(h("i"));
  showBanner(text, "hold", null, h("span", {"aria-hidden": "true"}, spots));
  var lit = 0;
  spotTimer = setInterval(function () {
    spots.forEach(function (spot, at) { spot.toggleAttribute("data-lit", at === lit); });
    lit = (lit + 1) % spots.length;
  }, SPOT_STEP_MS);
}

export var bannerSteps = [];

export function banner(text, warn, detail) {
  showBanner(text, warn, detail, null);
}

function showBanner(text, warn, detail, spots) {
  stopSpots();
  bannerSteps.forEach(function (step) { step(text, warn); });
  var box = document.getElementById("banner");
  box.dataset.tone = warn === "hold" ? "hold" : warn ? "warn" : "";
  if (!text) {
    replace(box);
    return;
  }
  replace(box, h("p", {}, text, spots), detail ? h("pre", {text: detail}) : null);
}
