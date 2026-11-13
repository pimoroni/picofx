import {bannerSteps} from "./banner.js";
import {boardSet, onProgramPage} from "./board_settings.js";
import {h, replace} from "./dom.js";
import {programTitle} from "./program.js";
import {closeSaveMenu} from "./save_menu.js";
import {state} from "./scenes.js";

var FLOAT_SAID_MS = 8000;

var driveButtons = document.getElementById("drive");
var driveStandIn = h("span", {"data-standin": true, "aria-hidden": "true"});
var floatShown = false;
var floatSaidTimer = null;

var floatSaid = h("button", {type: "button", hidden: true,
                             title: "Show at the top of the page",
                             onclick: function () { window.scrollTo({top: 0, behavior: "smooth"}); }});
var floatWhere = h("p", {});
var floatSlot = h("div", {});
var floatBar = h("div", {id: "floatBar", "aria-hidden": "true", inert: true},
  h("p", {},
    h("strong", {}, document.querySelector("header h1").firstChild.textContent.trim()),
    floatSaid),
  floatWhere,
  floatSlot);
document.body.appendChild(floatBar);

new IntersectionObserver(function (seen) {
  floatHeader(!seen[seen.length - 1].isIntersecting);
}).observe(document.querySelector("header"));

function floatHeader(away) {
  if (away === floatShown) return;
  floatShown = away;
  closeSaveMenu();
  if (away) {
    var size = driveButtons.getBoundingClientRect();
    driveStandIn.style.width = size.width + "px";
    driveStandIn.style.height = size.height + "px";
    driveButtons.replaceWith(driveStandIn);
    floatSlot.appendChild(driveButtons);
  } else {
    driveStandIn.replaceWith(driveButtons);
  }
  floatBar.toggleAttribute("data-shown", away);
  floatBar.setAttribute("aria-hidden", away ? "false" : "true");
  floatBar.inert = !away;
}

export function drawFloatBar() {
  var shown = onProgramPage ? (boardSet.program ? programTitle(boardSet.program) : "")
            : !state.scenes.length ? ""
            : state.at < 0 ? "Always on" : state.scenes[state.at].name;
  replace(floatWhere, h("b", {}, onProgramPage ? "Programs" : "Effects"),
          shown ? h("small", {}, shown) : null);
}

bannerSteps.push(function (text, warn) {
  clearTimeout(floatSaidTimer);
  floatSaid.textContent = text || "";
  floatSaid.hidden = !text;
  floatSaid.dataset.tone = warn === "hold" ? "hold" : warn ? "warn" : "";
  if (text && !warn) {
    floatSaidTimer = setTimeout(function () {
      floatSaid.textContent = "";
      floatSaid.hidden = true;
    }, FLOAT_SAID_MS);
  }
});
