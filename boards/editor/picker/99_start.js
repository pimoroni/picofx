import {banner} from "./00_banner.js";
import {draw, drawWith, paintAll} from "./00_draw.js";
import {CATALOGUE_ASSUMED} from "./01_looks.js";
import {HOLDING_STILL, forgetPainters, setBeat, step} from "./02_preview.js";
import {active, lastOutputRun, mono, noteOutputRun, outs, runs} from "./03_runs.js";
import {renderSides} from "./04_led_panels.js";
import {renderSceneTray} from "./04_scene_tray.js";
import {capture, state} from "./04_scenes.js";
import {drawSetupState, renderLeds} from "./08_setup.js";
import {drawConnectors, renderWiringRun} from "./09_wiring.js";
import {workOn} from "./10_led_sections.js";
import {chosenTab, followChosenTab, renderLedTabs, showChosen} from "./11_tabs.js";
import {connectSteps} from "./18_drive.js";
import {renderPreview} from "./18_file_preview.js";
import {drawBoardSettings} from "./19_board_settings.js";
import {renderSceneSettings} from "./20_scene_row.js";
import {renderSaveMenu} from "./21_save_menu.js";
import {drawProgramPage, markProgramPage} from "./22_program.js";
import {drawFloatBar} from "./23_float_bar.js";
import {openDriveFiles} from "./26_drive_files.js";
import {openDrivePrograms} from "./26_drive_programs.js";
import {drawKept, openEffectsFile} from "./27_readback.js";
import {renderStretches} from "./31_stretch_bar.js";
import {parkLooks, placeLooks, renderEditor} from "./32_stretch_editor.js";
import {renderGallery} from "./33_gallery.js";

import "./14_tab_swatches.js";
import "./23_float_bar.js";
import "./27_readback.js";

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
