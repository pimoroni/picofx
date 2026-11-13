import {banner} from "./banner.js";
import {drawBoardSettings} from "./board_settings.js";
import {draw, drawWith, paintAll} from "./draw.js";
import {connectSteps} from "./drive.js";
import {openDriveFiles} from "./drive_files.js";
import {openDrivePrograms} from "./drive_programs.js";
import {renderPreview} from "./file_preview.js";
import {drawFloatBar} from "./float_bar.js";
import {renderGallery} from "./gallery.js";
import {renderSides} from "./led_panels.js";
import {workOn} from "./led_sections.js";
import {CATALOGUE_ASSUMED} from "./looks.js";
import {HOLDING_STILL, forgetPainters, setBeat, step} from "./preview.js";
import {drawProgramPage, markProgramPage} from "./program.js";
import {drawKept, openEffectsFile} from "./readback.js";
import {active, lastOutputRun, mono, noteOutputRun, outs, runs} from "./runs.js";
import {renderSaveMenu} from "./save_menu.js";
import {renderSceneSettings} from "./scene_row.js";
import {renderSceneTray} from "./scene_tray.js";
import {capture, state} from "./scenes.js";
import {drawSetupState, renderLeds} from "./setup.js";
import {renderStretches} from "./stretch_bar.js";
import {parkLooks, placeLooks, renderEditor} from "./stretch_editor.js";
import {chosenTab, followChosenTab, renderLedTabs, showChosen} from "./tabs.js";
import {drawConnectors, renderWiringRun} from "./wiring.js";

import "./tab_swatches.js";
import "./float_bar.js";
import "./readback.js";

connectSteps.push(openDriveFiles, openDrivePrograms, openEffectsFile);

drawWith({
  settle: [forgetPainters, noteOutputRun, followChosenTab, markProgramPage, parkLooks],
  render: [
    renderGallery,
    function () { renderWiringRun("outRun", outs); },
    function () { renderStretches("outBar", outs); },
    function () { renderWiringRun("monoRun", mono); },
    function () { renderStretches("monoBar", mono); },
    renderSides,
    function () { renderEditor("outChosen", active.strip ? lastOutputRun : active); },
    renderPreview,
    function () {
      runs.filter(function (run) { return run.strip; }).forEach(function (run) {
        renderLeds(run.id + "Leds", run);
        renderStretches(run.id + "Bar", run);
        renderEditor(run.id + "Chosen", run);
      });
    },
    renderSceneTray,
    renderSceneSettings,
    drawSetupState,
    drawConnectors,
    renderLedTabs,
    drawBoardSettings,
    renderSaveMenu,
    drawProgramPage,
    drawKept
  ],
  finish: [paintAll, drawFloatBar, placeLooks]
});

document.addEventListener("DOMContentLoaded", function () {
  state.always.body = capture();
  workOn(chosenTab);
  showChosen();
  draw();
  if (HOLDING_STILL) { setBeat(0.37); paintAll(); } else { step(); }

  if (CATALOGUE_ASSUMED) {
    banner("catalogue.js is missing from this folder, so the board's ports are assumed. " +
           "Run tools/build_editor.py to write it.", true);
  }
});
