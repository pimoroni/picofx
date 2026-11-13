import {draw, drawSteps, paintAll} from "./00_draw.js";
import {HOLDING_STILL, setBeat, step} from "./02_preview.js";
import {active, mono, outs} from "./03_runs.js";
import {renderSides} from "./04_led_panels.js";
import {capture, state} from "./04_scenes.js";
import {renderWiringRun} from "./09_wiring.js";
import {workOn} from "./10_led_sections.js";
import {chosenTab, showChosen} from "./11_tabs.js";
import {renderPreview} from "./18_drive.js";
import {renderStretches} from "./31_stretch_bar.js";
import {renderEditor} from "./32_stretch_editor.js";
import {renderGallery} from "./33_gallery.js";

drawSteps.during.push(
  renderGallery,
  function () { renderWiringRun("outRun", outs); },
  function () { renderStretches("outBar", outs); },
  function () { renderWiringRun("monoRun", mono); },
  function () { renderStretches("monoBar", mono); },
  renderSides,
  function () { renderEditor("outChosen", active); },
  renderPreview,
  paintAll
);

state.always.body = capture();
workOn(chosenTab);
showChosen();
draw();
if (HOLDING_STILL) { setBeat(0.37); paintAll(); } else { step(); }
