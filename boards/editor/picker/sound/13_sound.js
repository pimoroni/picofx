import {banner} from "../00_banner.js";
import {h, replace} from "../00_dom.js";
import {draw, drawSteps} from "../00_draw.js";
import {quoted} from "../01_looks.js";
import {entryParts, unquoted} from "../03_reading.js";
import {allBodies, bodyParts, driveParts, state} from "../04_scenes.js";
import {TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches, tabUnder} from "../11_tabs.js";
import {nameShown} from "../18_drive.js";
import {OWN_GROUP} from "../22_program.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../26_drive_files.js";

state.sound = null;
state.soundLoop = false;
state.soundVolume = 100;
state.soundKept = null;
state.sounds = [];
state.soundInfo = {};
state.soundOff = false;

var SOUND_SAMPLES = 96;

export var soundHooks = {tileSteps: [], examplesBar: null};

function soundUnder() {
  if (state.at < 0 || state.sound || state.soundKept || state.soundOff) return null;
  return state.always.body.sound || null;
}

function canSilence() { return state.at >= 0 && !!state.always.body.sound; }

function chooseSound(name) {
  state.sound = name;
  state.soundOff = false;
  state.soundKept = null;
  draw();
}

function chooseNothing() {
  state.sound = null;
  state.soundOff = false;
  state.soundLoop = false;
  state.soundVolume = 100;
  state.soundKept = null;
  draw();
}

function chooseSilence() {
  state.sound = null;
  state.soundKept = null;
  state.soundLoop = false;
  state.soundVolume = 100;
  state.soundOff = true;
  draw();
}

function keepAsIs() {
  state.sound = null;
  state.soundLoop = false;
  state.soundVolume = 100;
  draw();
}

function soundLine(body) {
  if (body.soundOff) return "audio: none";
  if (body.sound)
    return "audio: wav file=" + quoted(body.sound) +
           (body.soundLoop ? " loop=true" : "") +
           (body.soundVolume < 100 ? " volume=" + body.soundVolume + "%" : "");
  return body.soundKept;
}

bodyParts.push({
  capture: function (body) {
    body.sound = state.sound;
    body.soundLoop = state.soundLoop;
    body.soundVolume = state.soundVolume;
    body.soundKept = state.soundKept;
    body.soundOff = state.soundOff;
  },
  apply: function (body) {
    if (!("sound" in body)) return;
    state.sound = body.sound;
    state.soundLoop = body.soundLoop;
    state.soundVolume = body.soundVolume;
    state.soundKept = body.soundKept;
    state.soundOff = !!body.soundOff;
  },
  blank: function (body) {
    body.sound = null;
    body.soundLoop = false;
    body.soundVolume = 100;
    body.soundKept = null;
    body.soundOff = false;
  },
  hasContent: function (body) { return !!(body.sound || body.soundOff); },
  sets: function (body) {
    return body.sound || body.soundKept ? ["sound", "Sound"]
         : body.soundOff ? ["sound", "Silence"] : null;
  },
  named: function (body) { return body.sound ? [nameShown(body.sound)] : []; },
  entries: function (body, lines) {
    var sound = "sound" in body ? soundLine(body) : null;
    if (sound) lines.unshift(sound);
    return lines;
  },
  read: readSound
});

function readSound(bodies) {
  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      if (parts && parts.selector === "audio" && one.text === "audio: none" && !body.sound &&
          !body.soundOff) {
        body.soundOff = true;
        if (one.comments.length) body.notes[one.text] = one.comments;
        return false;
      }
      if (!parts || parts.selector !== "audio" || parts.effect !== "wav" || body.sound ||
          !Object.keys(parts.right).every(function (key) {
            return key === "file" || key === "loop" || key === "volume";
          })) {
        return true;
      }
      var percent = /^(\d+)%$/.exec(parts.right.volume || "");
      var sounding = {sound: unquoted(parts.right.file), soundLoop: parts.right.loop === "true",
                      soundVolume: percent ? Number(percent[1]) : 100, soundKept: null};
      if (!sounding.sound || soundLine(sounding) !== one.text) return true;
      body.sound = sounding.sound;
      body.soundLoop = sounding.soundLoop;
      body.soundVolume = sounding.soundVolume;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });
}

var soundsFound = [];

driveParts.push({
  begin: function () { soundsFound = []; },
  file: async function (name, handle) {
    if (!/\.wav$/i.test(name)) return false;
    soundsFound.push(name);
    profileSound(name, handle);
    return true;
  },
  land: function () {
    soundsFound.sort();
    state.sounds = soundsFound;
  },
  said: function () { return JSON.stringify(state.sounds); },
  forget: function (name) {
    allBodies().forEach(function (body) {
      if (body.sound === name) {
        body.sound = null;
        body.soundLoop = false;
        body.soundVolume = 100;
      }
    });
    delete state.soundInfo[name];
  }
});

var RIFF_CHUNK = 0x52494646;
var WAVE_FORM = 0x57415645;
var FORMAT_CHUNK = 0x666d7420;
var DATA_CHUNK = 0x64617461;

async function profileSound(name, handle) {
  soundHandles[name] = handle;
  if (state.soundInfo[name] !== undefined) return;
  state.soundInfo[name] = null;
  try {
    var file = await handle.getFile();
    var head = new DataView(await file.slice(0, 8192).arrayBuffer());
    if (head.getUint32(0) !== RIFF_CHUNK || head.getUint32(8) !== WAVE_FORM)
      throw new Error("not a WAV file");
    var at = 12;
    var byteRate = 0;
    var bits = 16;
    var dataAt = 0;
    var dataSize = 0;
    while (at + 8 <= head.byteLength) {
      var id = head.getUint32(at);
      var size = head.getUint32(at + 4, true);
      if (id === FORMAT_CHUNK) {
        byteRate = head.getUint32(at + 16, true);
        bits = head.getUint16(at + 22, true);
      } else if (id === DATA_CHUNK) {
        dataAt = at + 8;
        dataSize = Math.min(size, file.size - dataAt);
        break;
      }
      at += 8 + size + (size % 2);
    }
    if (!byteRate || !dataSize) throw new Error("no sound in it");

    var bars = [];
    for (var b = 0; b < SOUND_SAMPLES; b++) {
      var from = dataAt + Math.floor(dataSize * b / SOUND_SAMPLES);
      var take = Math.min(1024, dataAt + dataSize - from);
      var slice = await file.slice(from, from + take).arrayBuffer();
      var peak = 0;
      if (bits === 16) {
        var wide = new Int16Array(slice, 0, Math.floor(slice.byteLength / 2));
        for (var i = 0; i < wide.length; i++) peak = Math.max(peak, Math.abs(wide[i]));
        peak /= 32768;
      } else {
        var thin = new Uint8Array(slice);
        for (var j = 0; j < thin.length; j++) peak = Math.max(peak, Math.abs(thin[j] - 128));
        peak /= 128;
      }
      bars.push(peak);
    }
    state.soundInfo[name] = {seconds: Math.max(1, Math.round(dataSize / byteRate)), bars: bars};
    draw();
  } catch (e) {
    state.soundInfo[name] = null;
  }
}

var soundHandles = {};
export var hearing = {name: null, audio: null, url: null};

export function stopHearing() {
  if (hearing.audio) hearing.audio.pause();
  if (hearing.url) URL.revokeObjectURL(hearing.url);
  hearing = {name: null, audio: null, url: null};
}

export function startHearing(name, audio, url) {
  hearing = {name: name, audio: audio, url: url};
}

async function hear(name) {
  var wasHearing = hearing.name;
  stopHearing();
  if (wasHearing === name || !soundHandles[name]) {
    draw();
    return;
  }
  var audio = null;
  try {
    var url = URL.createObjectURL(await soundHandles[name].getFile());
    audio = new Audio(url);
    if (name === state.sound) audio.volume = state.soundVolume / 100;
    startHearing(name, audio, url);
    audio.onended = function () {
      if (hearing.audio === audio) stopHearing();
      draw();
    };
    draw();
    await audio.play();
  } catch (e) {
    if (e.name === "AbortError" && hearing.audio !== audio) return;
    if (hearing.audio === audio) stopHearing();
    banner("Could not play " + nameShown(name) + ": " + e.name + ".", true);
    draw();
  }
}

export function hearButton(name, words, onclick) {
  var playing = hearing.name === name;
  return h("button", {type: "button", "data-hear": true, "aria-pressed": String(playing),
                      "aria-label": "Hear " + words,
                      title: (playing ? "Stop " : "Play ") + words + " here",
                      onclick: function (event) {
                        event.stopPropagation();
                        onclick();
                      }},
           playing ? "\u25a0" : "\u25b6");
}

var LOUDNESS = ["#3a6fd8", "#8a4fd0", "#d0449a", "#e5443a"];
var outlinesMade = 0;

function loudnessInk(loud) {
  var at = Math.max(0, Math.min(1, loud)) * (LOUDNESS.length - 1);
  var low = Math.floor(at);
  var high = Math.min(LOUDNESS.length - 1, low + 1);
  var part = at - low;
  function channels(hex) {
    return [1, 3, 5].map(function (from) { return parseInt(hex.substr(from, 2), 16); });
  }
  var from = channels(LOUDNESS[low]);
  var to = channels(LOUDNESS[high]);
  return "rgb(" + from.map(function (value, channel) {
    return Math.round(value + (to[channel] - value) * part);
  }).join(",") + ")";
}

function silentBars() {
  var bars = [];
  for (var i = 0; i < SOUND_SAMPLES; i++) bars.push(0.04);
  return bars;
}

function soundOutline(bars) {
  var wide = 100;
  var high = 40;
  var middle = high / 2;
  var last = bars.length - 1;
  var id = "loudness" + (outlinesMade++);
  function across(at) { return (at / last) * wide; }
  var above = bars.map(function (tall, at) { return across(at) + "," + (middle - tall * middle); });
  var below = bars.map(function (tall, at) { return across(at) + "," + (middle + tall * middle); });
  return h("svg:svg", {viewBox: "0 0 " + wide + " " + high, preserveAspectRatio: "none",
                       "aria-hidden": "true"},
    h("svg:defs", {},
      h("svg:linearGradient", {id: id, x1: 0, x2: 1}, bars.map(function (tall, at) {
        return h("svg:stop", {offset: at / last, "stop-color": loudnessInk(tall)});
      }))),
    h("svg:polygon", {points: above.concat(below.reverse()).join(" "), fill: "url(#" + id + ")"}));
}

function flatSound() {
  return h("svg:svg", {viewBox: "0 0 104 30", preserveAspectRatio: "none", "aria-hidden": "true"},
    h("svg:rect", {x: 0, y: 14, width: 104, height: 2, rx: 1}));
}

function soundSentence(under) {
  if (under)
    return "Always on's " + nameShown(under) + " plays on through this scene. Choose a sound to " +
           "give this scene its own, or Silence to quieten it";
  if (state.soundOff)
    return "this scene is silent. Always on's " + nameShown(state.always.body.sound) +
           " stops while it shows";
  if (!state.fileHandle) return "open the FX drive to see the sounds on it";
  if (!state.scanned) return "reading the drive...";
  if (!(state.sounds.length || state.sound || state.soundKept))
    return "no sounds on the drive yet. Drop a WAV file onto it";
  if (!state.scenes.length) return "one WAV file, playing alongside the lights";
  if (state.at < 0) return "plays in any scene without its own sound";
  return "plays while this scene shows, resuming where it left off";
}

function loopToggle(under) {
  var looping = under ? !!state.always.body.soundLoop : !!(state.soundLoop && state.sound);
  return h("button", {type: "button", "aria-pressed": String(looping), disabled: !state.sound,
                      title: under ? "Set on the Always on tab"
                           : state.sound ? "Loop the sound instead of playing it once"
                           : "No sound chosen",
                      onclick: function () {
                        state.soundLoop = !state.soundLoop;
                        draw();
                      }},
           h("span", {"aria-hidden": "true"}, "\u21bb"), " Loop");
}

function volumeSlider(under) {
  var shown = h("output");
  var slider = h("input", {type: "range", min: 0, max: 100, step: 5,
                           value: under ? state.always.body.soundVolume : state.soundVolume,
                           disabled: !state.sound,
                           oninput: function () { shown.value = slider.value + "%"; },
                           onchange: function () {
                             state.soundVolume = Number(slider.value);
                             if (hearing.audio && hearing.name === state.sound) {
                               hearing.audio.volume = state.soundVolume / 100;
                             }
                             draw();
                           }});
  shown.value = slider.value + "%";
  return h("label", {title: under ? "Set on the Always on tab"
                          : state.sound ? "How loud the board plays the sound" : "No sound chosen"},
           "volume", slider, shown);
}

function nothingChoice() {
  var picked = !state.sound && !state.soundKept && !state.soundOff;
  return h("button", {type: "button", "aria-pressed": String(picked),
                      title: canSilence() ? "Play nothing of this scene's own" : "Play no sound",
                      onclick: chooseNothing},
           h("i"), h("b", {}, "Nothing"));
}

function silenceChoice() {
  return h("button", {type: "button", "aria-pressed": String(state.soundOff),
                      "data-unseen": !canSilence(), title: "Play no sound in this scene",
                      onclick: chooseSilence},
           h("i", {}, soundOutline(silentBars())), h("b", {}, "Silence"));
}

function playingLine(under) {
  return h("div", {},
    h("fieldset", {disabled: !!under, title: under ? "Set on the Always on tab" : null},
      h("legend", {}, "How it plays"),
      loopToggle(under),
      volumeSlider(under)),
    nothingChoice());
}

function soundLength(name, info, picked) {
  if (info && info.seconds) return info.seconds + "s" + (picked && state.soundLoop ? ", on repeat" : "");
  return state.sounds.indexOf(name) < 0 ? "not on the drive" : "";
}

function soundTile(name) {
  var info = state.soundInfo[name];
  var picked = state.sound === name;
  var onDrive = state.sounds.indexOf(name) >= 0;
  var tile = h("li", {"data-under": name === soundUnder()},
    h("button", {type: "button", "aria-pressed": String(picked),
                 onclick: function () { chooseSound(name); }},
      info && info.bars ? soundOutline(info.bars) : flatSound(),
      h("b", {}, nameShown(name)),
      h("small", {}, soundLength(name, info, picked))),
    soundHandles[name] ? hearButton(name, nameShown(name), function () { hear(name); }) : null,
    onDrive && !isExampleMedia(name) ? binButton(name, "wav") : null);
  soundHooks.tileSteps.forEach(function (step) { step(tile, name); });
  return tile;
}

function keptTile() {
  return h("li", {},
    h("button", {type: "button", "aria-pressed": String(!state.sound), title: state.soundKept,
                 onclick: keepAsIs},
      flatSound(),
      h("b", {}, "Keep as is"),
      h("small", {}, state.soundKept.slice(0, 40))));
}

function addSoundsTile() {
  return h("li", {}, adderTile("add sounds",
    {description: "Sounds the board can play", accept: {"audio/wav": [".wav"]}},
    "sounds", /\.wav$/i));
}

function soundList(tiles, tip) {
  return tiles.length ? h("ul", {title: tip}, tiles) : null;
}

function groupHeading(group, key, open) {
  return h("h3", {},
    h("button", {type: "button", "aria-expanded": String(open),
                 onclick: function () {
                   groupsOpen[key] = !open;
                   draw();
                 }},
      group[0], group[1] ? h("small", {}, group[1]) : null));
}

function soundGroups(tip) {
  var names = state.sounds.slice();
  if (state.sound && names.indexOf(state.sound) < 0) names.unshift(state.sound);
  var files = names.map(function (name) { return {name: name}; });
  var groups = [[OWN_GROUP, "your own sounds", files.filter(function (one) {
    return !isExampleMedia(one.name);
  }), false]].concat(exampleGroups("sounds", files));
  var kept = state.soundKept ? [keptTile()] : [];

  if (!state.fileHandle) {
    var tiles = kept.slice();
    groups.forEach(function (group) {
      group[2].forEach(function (one) { tiles.push(soundTile(one.name)); });
    });
    return h("section", {}, h("div", {}, silenceChoice()), soundList(tiles, tip));
  }

  var sections = [];
  groups.forEach(function (group, at) {
    if (at && !group[2].length) return;
    var key = "sound:" + group[0];
    var open = groupOpen([key].concat(group.slice(1)));
    var tiles = at ? [] : kept.slice();
    if (open) group[2].forEach(function (one) { tiles.push(soundTile(one.name)); });
    if (open && !at) tiles.push(addSoundsTile());
    sections.push(h("section", {},
      h("div", {}, groupHeading(group, key, open), at ? null : silenceChoice()),
      soundList(tiles, tip)));
    if (!at && soundHooks.examplesBar) sections.push(soundHooks.examplesBar());
  });
  return sections;
}

var soundTab = h("section", {class: "soundtab", "aria-label": "Sound"});

function renderSound() {
  var under = soundUnder();
  var sentence = soundSentence(under);
  var explains = /^(one WAV|plays)/.test(sentence);
  var tip = explains ? sentence.charAt(0).toUpperCase() + sentence.slice(1) : null;
  replace(soundTab,
    h("p", {hidden: explains && !state.scenes.length, "data-unseen": explains}, sentence),
    playingLine(under),
    soundGroups(tip));
}

function repeatMark() {
  return h("svg:svg", {viewBox: "0 0 16 16", "aria-hidden": "true"},
    h("svg:path", {d: "M3 7a5 5 0 0 1 9-3M13 9a5 5 0 0 1-9 3"}),
    h("svg:path", {d: "M12 1v3.5H8.5M4 15v-3.5h3.5"}));
}

tabSwatches.soundPanel = function (swatch) {
  swatch.className = "accswatch soundswatch";
  var under = soundUnder();
  var info = state.sound ? state.soundInfo[state.sound] : under ? state.soundInfo[under] : null;
  if (state.soundOff) {
    replace(swatch, soundOutline(silentBars()));
    swatch.title = "silence";
  } else if (!info) {
    replace(swatch);
    swatch.dataset.shows = "nothing";
    swatch.title = under ? "Always on's " + nameShown(under) : "nothing";
  } else if (under) {
    replace(swatch, soundOutline(info.bars));
    swatch.dataset.shows = "under";
    swatch.title = "Always on's " + nameShown(under);
  } else {
    replace(swatch, soundOutline(info.bars), state.soundLoop ? repeatMark() : null);
    swatch.title = nameShown(state.sound) + (state.soundLoop ? ", on repeat" : "") +
                   (state.soundVolume < 100 ? ", " + state.soundVolume + "% volume" : "");
  }
};

tabUnder.soundPanel = function () {
  return state.sound || state.soundKept ? "wav" : state.soundOff ? "silence"
       : soundUnder() ? "Always on" : "nothing";
};

drawSteps.after.push(function () {
  renderSound();
});

document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]).after(
  h("details", {class: "panel", id: "soundPanel", open: true}, h("summary", {}, "Sound"), soundTab));

TAB_NAMES.soundPanel = "Sound";
TAB_PANELS.push("soundPanel");
keptOpen("soundPanel");
