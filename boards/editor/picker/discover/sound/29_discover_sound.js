import {draw} from "../../03_runs.js";
import {state} from "../../04_scenes.js";
import {isExampleMedia, nameShown} from "../../26_drive_files.js";
import {
  discoverBin, discoverElement, discoverKinds, discoverPill, discoverPlaceBar, discoverSay,
  discoverSounds
} from "../28_discover.js";
import {hearing, soundSteps, soundTileSteps, stopHearing} from "../../sound/13_sound.js";

// ---- examples to discover, on the Sound tab -----------------------------------------------------
// The Sound tab's examples line, where its example sounds start. An example sound on the drive
// can be deleted, as it can be downloaded again, and carries its mark, Update or the firmware it
// needs. 28_discover.js does the rest. A board without sound has no Sound tab to add them to.

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
  var card = discoverElement("div", "sound discoveroffer");
  card.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none' aria-hidden='true'>" +
    "<path d='M0 15 Q6.5 3 13 15 T26 15 T39 15 T52 15 T65 15 T78 15 T91 15 T104 15' fill='none' " +
    "stroke='#c9c3b9' stroke-width='2'/></svg>";
  card.appendChild(discoverElement("b", "", sound.title));
  card.appendChild(discoverElement("small", "", sound.seconds ? sound.seconds + "s" : "WAV file"));
  var playing = hearing.name === path;
  var listen = discoverElement("span", "hear" + (playing ? " playing" : ""),
                             playing ? "\u25a0" : "\u25b6");
  listen.setAttribute("role", "button");
  listen.title = (playing ? "Stop " : "Play ") + sound.title + " here";
  listen.onclick = function (e) {
    e.stopPropagation();
    discoverHear(path, sound.url);
  };
  card.appendChild(listen);
  return card;
}

// Play a sound from GitHub, or stop it where it is playing, one sound at a time as the Sound tab
// plays them
async function discoverHear(path, url) {
  var was = hearing.name;
  stopHearing();
  if (was === path) {
    draw();
    return;
  }
  var audio = new Audio(url);
  hearing = {name: path, audio: audio, url: null};
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
