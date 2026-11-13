import {h} from "../../00_dom.js";
import {draw} from "../../00_draw.js";
import {state} from "../../04_scenes.js";
import {isExampleMedia, nameShown} from "../../26_drive_files.js";
import {
  discoverBar, discoverBin, discoverKinds, discoverPill, discoverSay, discoverSounds
} from "../28_discover.js";
import {hearButton, hearing, soundHooks, startHearing, stopHearing} from "../../sound/13_sound.js";

soundHooks.tileSteps.push(function (tile, name) {
  if (isExampleMedia(name) && state.sounds.indexOf(name) >= 0)
    tile.append(discoverBin(name, "sound"));
  var pill = discoverPill(name);
  if (pill) tile.append(pill);
});

soundHooks.examplesBar = function () { return discoverBar("sound"); };

function stillWave() {
  return h("svg:svg", {viewBox: "0 0 104 30", preserveAspectRatio: "none", "aria-hidden": "true"},
    h("svg:path", {d: "M0 15 Q6.5 3 13 15 T26 15 T39 15 T52 15 T65 15 T78 15 T91 15 T104 15"}));
}

function discoverSoundFace(path) {
  var sound = discoverSounds[path].sound;
  return h("div", {class: "soundoffer discoveroffer"},
    stillWave(),
    h("b", {}, sound.title),
    h("small", {}, sound.seconds ? sound.seconds + "s" : "WAV file"),
    hearButton(path, sound.title, function () { discoverHear(path, sound.url); }));
}

async function discoverHear(path, url) {
  var was = hearing.name;
  stopHearing();
  if (was === path) {
    draw();
    return;
  }
  var audio = new Audio(url);
  startHearing(path, audio, null);
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
