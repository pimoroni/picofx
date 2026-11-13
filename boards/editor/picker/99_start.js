import {HOLDING_STILL, setBeat} from "./02_preview.js";
import {draw, paintAll, step} from "./03_runs.js";
import {capture, state} from "./04_scenes.js";
import {workOn} from "./10_led_sections.js";
import {chosenTab, showChosen} from "./11_tabs.js";

state.always.body = capture();
workOn(chosenTab);
showChosen();
draw();
if (HOLDING_STILL) { setBeat(0.37); paintAll(); } else { step(); }
