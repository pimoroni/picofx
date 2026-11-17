import {bannerSteps} from "./banner.js";
import {boardSet, onProgramPage} from "./board_settings.js";
import {h, replace} from "./dom.js";
import {DRAW_AFTER, addStep, drawSteps} from "./draw.js";
import {programTitle} from "./program.js";
import {closeSaveMenu} from "./save_menu.js";
import {state} from "./scenes.js";

// ---- the bar along the top ----------------------------------------------------------------------
// Once the header has scrolled out of view a slim bar takes its place along the top, holding the
// page's name, the drive, save and check buttons, the latest thing the page said and where the
// page is. The buttons themselves move into it and back, each leaving a stand-in of its size in
// the header, so their state stays one and nothing in the header moves

// The header's parts the bar takes, in the order the bar shows them
var FLOAT_MOVED = ["open", "save", "saveArrow", "check", "saveMenu"];

// Whether the bar is showing, as it is while the header is out of view
var floatShown = false;

var floatSaidTimer = null;

// How long a plain note stays in the bar. A warning stays until the next
var FLOAT_SAID_MS = 8000;

// The whole of what the page said, details and all, is the banner's at the top of the page
var floatSaid = h("span", {className: "floatsaid",
                           onclick: function () { window.scrollTo({top: 0, behavior: "smooth"}); }});
var floatWhere = h("span", {className: "floatwhere"});
var floatButtons = h("span", {className: "floatbuttons"});

// The name and what the page said on the left, the page and scene in the middle, the buttons on
// the right. Hidden, the bar is inert, so its parts take no focus
var floatBar = h("div", {className: "floatbar", "aria-hidden": "true", inert: true},
                 h("span", {className: "floatleft"},
                   h("span", {className: "floatname"},
                     document.querySelector("header h1").firstChild.textContent.trim()),
                   floatSaid),
                 floatWhere,
                 floatButtons);
document.body.appendChild(floatBar);

new IntersectionObserver(function (seen) {
  floatHeader(!seen[seen.length - 1].isIntersecting);
}).observe(document.querySelector("header"));

// Move the buttons into the bar as the header leaves the view, and back as it returns
function floatHeader(away) {
  if (away === floatShown) return;
  floatShown = away;
  // The save menu is placed under its arrow as it opens, so one open is closed for the move
  closeSaveMenu();
  FLOAT_MOVED.forEach(function (id) {
    var one = document.getElementById(id);
    if (away) {
      var box = one.getBoundingClientRect();
      one.replaceWith(h("span", {className: "floatstand", "data-stands-for": id,
                                 style: {width: box.width + "px", height: box.height + "px"}}));
      floatButtons.appendChild(one);
    } else {
      document.querySelector("[data-stands-for='" + id + "']").replaceWith(one);
    }
  });
  floatBar.classList.toggle("shown", away);
  floatBar.setAttribute("aria-hidden", away ? "false" : "true");
  floatBar.inert = !away;
}

// The page in the middle as the header's tabs name it, with the scene or the program chosen
addStep(drawSteps.after, DRAW_AFTER, "floatBar", function () {
  var shown = onProgramPage ? (boardSet.program ? programTitle(boardSet.program) : "")
            : !state.scenes.length ? ""
            : state.at < 0 ? "Always on" : state.scenes[state.at].name;
  replace(floatWhere, h("b", {}, onProgramPage ? "Programs" : "Effects"),
          shown ? h("small", {}, shown) : null);
});

// What the page says goes in the bar too, so a save from far down the page is answered there
bannerSteps.push(function (text, warn) {
  clearTimeout(floatSaidTimer);
  floatSaid.textContent = text || "";
  floatSaid.title = text ? "Show at the top of the page" : "";
  floatSaid.className = "floatsaid" + (warn === "hold" ? " hold" : warn ? " warn" : "");
  if (text && !warn) {
    floatSaidTimer = setTimeout(function () { floatSaid.textContent = ""; }, FLOAT_SAID_MS);
  }
});
