
// ---- a program, coming soon -----------------------------------------------------------------------
// The page taken to the board for testing shows both tabs under the header, as it will ship, with
// the program's tab marked coming soon and closed. The program page is all there behind it, so
// opening it later is taking this part away.

toProgram = function () {};

var oneSoonPageSwitch = renderPageSwitch;

renderPageSwitch = function () {
  oneSoonPageSwitch();
  var cover = document.querySelector("#headSwitch .cover[data-page=program]");
  if (!cover) return;
  cover.classList.add("soon");
  cover.classList.remove("on");
  cover.setAttribute("aria-disabled", "true");
  cover.tabIndex = -1;
  cover.onclick = null;
  cover.onkeydown = null;
  cover.title = "Running a program of your own in place of the effects, coming soon";
  var words = cover.querySelector("span");
  if (words) words.innerHTML = "<b>A program</b><small>coming soon</small>";
};
