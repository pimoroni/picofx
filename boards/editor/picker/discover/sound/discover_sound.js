import {
  discoverBin, discoverKinds, discoverPill, discoverPlaceBar, discoverSay, discoverSounds
} from "../discover.js";
import {h} from "../../dom.js";
import {draw} from "../../draw.js";
import {nameShown} from "../../drive.js";
import {isExampleMedia} from "../../drive_files.js";
import {state} from "../../scenes.js";
import {hearing, setHearing, soundSteps, soundTileSteps, stopHearing} from "../../sound/sound.js";

// ---- examples to discover, on the Sound tab -----------------------------------------------------
// The Sound tab's examples line, where its example sounds start. An example sound on the drive
// can be deleted, as it can be downloaded again, and carries its mark, Update or the firmware it
// needs. discover.js does the rest. build_editor.py takes this folder only for a board with
// sound.

soundTileSteps.push(function (tile, name) {
  if (!name) return;
  tile.dataset.name = name;
  if (isExampleMedia(name) && state.sounds.indexOf(name) >= 0)
    tile.appendChild(discoverBin(name, "sound"));
  var pill = discoverPill(name);
  if (pill) tile.appendChild(pill);
});

soundSteps.push(function () {
  var row = document.querySelector("#sound .sounds");
  if (row && state.fileHandle) discoverPlaceBar(row, "sound");
});

// A sound as the Sound tab shows one, its name and how long it plays, with a way to hear it from
// GitHub before it is downloaded. Its outline is not known until it is, so a still wave stands in
function discoverSoundFace(path) {
  var sound = discoverSounds[path].sound;
  var playing = hearing.name === path;
  return h("div", {className: "sound discoveroffer"},
           h("svg:svg", {
             viewBox: "0 0 104 30", preserveAspectRatio: "none", "aria-hidden": "true",
             html: "<path d='M0 15 Q6.5 3 13 15 T26 15 T39 15 T52 15 T65 15 T78 15 T91 15 " +
                   "T104 15' fill='none' stroke='#c9c3b9' stroke-width='2'/>"
           }),
           h("b", {}, sound.title),
           h("small", {}, sound.seconds ? sound.seconds + "s" : "WAV file"),
           h("span", {
             className: "hear" + (playing ? " playing" : ""), role: "button",
             "aria-pressed": String(!!playing),
             title: (playing ? "Stop " : "Play ") + sound.title + " here",
             onclick: function (e) {
               e.stopPropagation();
               discoverHear(path, sound.url);
             }
           }, playing ? "■" : "▶"));
}

// Play a sound from GitHub, or stop it where it is playing, one at a time as the Sound tab does
async function discoverHear(path, url) {
  var was = hearing.name;
  stopHearing();
  if (was === path) {
    draw();
    return;
  }
  var audio = new Audio(url);
  setHearing(path, audio, null);
  audio.onended = function () {
    if (hearing.audio === audio) stopHearing();
    draw();
  };
  draw();
  try {
    await audio.play();
  } catch (e) {
    if (hearing.audio === audio) stopHearing();
    if (e.name !== "AbortError") discoverSay("sound", "Could not play " + nameShown(path) + ".", true);
    draw();
  }
}

discoverKinds.sound = {
  onDrive: function (path) { return state.sounds.indexOf(path) >= 0; },
  face: discoverSoundFace
};
