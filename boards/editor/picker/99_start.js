import {DRAW_AFTER, addStep, draw, drawSteps, paintAll} from "./00_draw.js";
import {HOLDING_STILL, setBeat, step} from "./02_preview.js";
import {capture, state} from "./04_scenes.js";
import {workOn} from "./10_led_sections.js";
import {chosenTab, holdTabsPlace, showChosen} from "./11_tabs.js";

// ---- the page, started ---------------------------------------------------------------------------
// Every part is in place, so the always-on tab takes what they hold and the page is drawn once,
// then the lights are set going, or held on one frame where motion is turned down

// Last of the draw's steps, once every part has drawn
addStep(drawSteps.after, DRAW_AFTER, "start", holdTabsPlace);

state.always.body = capture();
workOn(chosenTab);
showChosen();
draw();
if (HOLDING_STILL) { setBeat(0.37); paintAll(); } else { step(); }
