// ---- the bar along the top ----------------------------------------------------------------------
// Once the header has scrolled out of view a slim bar takes its place along the top, holding the
// page's name, the drive, save and check buttons, the latest thing the page said and where the
// page is. The buttons themselves move into it and back, each leaving a stand-in of its size in
// the header, so their state stays one and nothing in the header moves

// The header's parts the bar takes, in the order the bar shows them
var FLOAT_MOVED = ["open", "save", "saveArrow", "check", "saveMenu"];

var floatBar = null;

// Whether the bar is showing, the header being out of view
var floatShown = false;

var floatSaidTimer = null;

// How long a plain note stays in the bar, a warning staying until the next
var FLOAT_SAID_MS = 8000;

(function () {
  floatBar = document.createElement("div");
  floatBar.className = "floatbar";
  floatBar.setAttribute("aria-hidden", "true");
  // The name and what the page said on the left, the page and scene in the middle, the buttons
  // on the right
  var left = document.createElement("span");
  left.className = "floatleft";
  var name = document.createElement("span");
  name.className = "floatname";
  name.textContent = document.querySelector("header h1").firstChild.textContent.trim();
  var said = document.createElement("span");
  said.className = "floatsaid";
  // The whole of it, details and all, is the banner's at the top of the page
  said.onclick = function () { window.scrollTo({top: 0, behavior: "smooth"}); };
  left.appendChild(name);
  left.appendChild(said);
  var where = document.createElement("span");
  where.className = "floatwhere";
  var buttons = document.createElement("span");
  buttons.className = "floatbuttons";
  floatBar.appendChild(left);
  floatBar.appendChild(where);
  floatBar.appendChild(buttons);
  document.body.appendChild(floatBar);
  new IntersectionObserver(function (seen) {
    floatHeader(!seen[seen.length - 1].isIntersecting);
  }).observe(document.querySelector("header"));
}());

// Move the buttons into the bar as the header leaves the view, and back as it returns
function floatHeader(away) {
  if (away === floatShown) return;
  floatShown = away;
  var buttons = floatBar.querySelector(".floatbuttons");
  // The save menu is placed under its arrow as it opens, so one open is closed for the move
  document.getElementById("saveMenu").hidden = true;
  FLOAT_MOVED.forEach(function (id) {
    var one = document.getElementById(id);
    if (away) {
      var stand = document.createElement("span");
      stand.className = "floatstand";
      stand.dataset.standsFor = id;
      var box = one.getBoundingClientRect();
      stand.style.width = box.width + "px";
      stand.style.height = box.height + "px";
      one.parentNode.replaceChild(stand, one);
      buttons.appendChild(one);
    } else {
      var held = document.querySelector("[data-stands-for='" + id + "']");
      held.parentNode.replaceChild(one, held);
    }
  });
  floatBar.classList.toggle("shown", away);
  floatBar.setAttribute("aria-hidden", away ? "false" : "true");
}

// The page in the middle as the header's tabs name it, with the scene or the program chosen
drawSteps.after.push(function () {
  var shown = onProgramPage ? (boardSet.program ? programTitle(boardSet.program) : "")
            : !state.scenes.length ? ""
            : state.at < 0 ? "Always on" : state.scenes[state.at].name;
  floatBar.querySelector(".floatwhere").innerHTML =
    "<b>" + (onProgramPage ? "Programs" : "Effects") + "</b>" +
    (shown ? "<small>" + escapeHtml(shown) + "</small>" : "");
});

// What the page says goes in the bar too, so a save from far down the page is answered there
bannerSteps.push(function (text, warn) {
  var said = floatBar.querySelector(".floatsaid");
  clearTimeout(floatSaidTimer);
  said.textContent = text || "";
  said.title = text ? "Show at the top of the page" : "";
  said.className = "floatsaid" + (warn === "hold" ? " hold" : warn ? " warn" : "");
  if (text && !warn) {
    floatSaidTimer = setTimeout(function () { said.textContent = ""; }, FLOAT_SAID_MS);
  }
});
