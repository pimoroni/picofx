import {DRAW_AFTER, addStep, draw, drawSteps, paintAll} from "./draw.js";
import {drive} from "./drive.js";
import {workOn} from "./led_sections.js";
import {HOLDING_STILL, setBeat, step} from "./preview.js";
import {capture, state} from "./scenes.js";
import {chosenTab, holdTabsPlace, showChosen} from "./tabs.js";
import {currentText} from "./writing.js";

// ---- the page, started ---------------------------------------------------------------------------
// Every part is in place, so Always on takes what they hold and the page is drawn once. Then the
// lights are set going, or held on one frame where reduced motion is asked for

// Last of the draw's steps, once every part has drawn
addStep(drawSteps.after, DRAW_AFTER, "start", holdTabsPlace);

state.always.body = capture();
workOn(chosenTab);
showChosen();
draw();
// What the page opens with is not a change to keep, until a drive is read or saved to
drive.text = currentText();
if (HOLDING_STILL) { setBeat(0.37); paintAll(); } else { step(); }
