
// ---- the page, started ---------------------------------------------------------------------------
// Every part is in place, so the always-on tab takes what they hold and the page is drawn once,
// then the lights are set going, or held on one frame where motion is turned down

state.always.body = capture();
showChosen();
draw();
if (HOLDING_STILL) { beat = 0.37; paintAll(); } else { step(); }
