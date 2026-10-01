
// ---- the page held where it is, through every draw ---------------------------------------------
// A draw empties and refills much of the page, and reads its layout part way through, and a
// browser may move the scroll to hold something in view while it is half drawn. Seen in
// Chrome as a jump of the whole page when a tab was chosen, with nothing changing height.
// So whatever a draw does, the page ends it scrolled where it began. A scroll a page means,
// such as holding a pressed button still, is made after the draw and is left alone.

var oneSteadyDraw = draw;

draw = function () {
  var across = window.scrollX;
  var down = window.scrollY;
  oneSteadyDraw();
  if (window.scrollX !== across || window.scrollY !== down) window.scrollTo(across, down);
};
