
// ---- the page, started ---------------------------------------------------------------------------
// Every part is in place, so the always-on tab takes what they hold and the page is drawn once,
// then the lights are set going, or held on one frame where motion is turned down

// Last of the draw's steps, once every part has drawn
drawSteps.after.push(holdTabsPlace);

state.always.body = capture();
workOn(chosenTab);
showChosen();
draw();
// What the page opens with is not a change to keep, until a drive is read or saved to
drive.text = currentText();
if (HOLDING_STILL) { beat = 0.37; paintAll(); } else { step(); }
