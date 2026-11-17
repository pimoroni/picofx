import {banner} from "../banner.js";
import {h, replace} from "../dom.js";
import {DRAW_AFTER, addStep, draw, drawSteps} from "../draw.js";
import {nameShown} from "../drive.js";
import {
  adderTile, binButton, exampleGroups, groupOpen, groupsOpen, isExampleMedia
} from "../drive_files.js";
import {quoted} from "../looks.js";
import {OWN_GROUP, foldHead} from "../program.js";
import {entryParts, unquoted} from "../reading.js";
import {
  BODY_ORDER, DRIVE_ORDER, allBodies, bodyParts, driveParts, frozen, state
} from "../scenes.js";
import {FEATURE_TABS, TAB_NAMES, TAB_PANELS, keptOpen, tabSwatches} from "../tabs.js";

// ---- a Sound tab ----------------------------------------------------------------------------
// One wav at a time, chosen from a row of tiles each showing its shape and how long it runs,
// with whether it loops, its volume and silence on a line above them.
//
// The drawing asks of its page the sounds on the drive, and each scene keeping its own sound.
// The board takes one per scene, and the one in the always-on tab plays in any scene that
// brings none of its own. Nothing about the sound is the board's, so setting up leaves it
// standing back.

state.sound = null;
state.soundLoop = false;
state.soundVolume = 100;
state.soundKept = null;
state.sounds = [];
state.soundInfo = {};
// Whether the scene silences the speaker with `audio: none`, which only a scene needs, where
// Always on has a sound to silence
state.soundOff = false;

// The sound Always on plays in the scene being edited, where the scene has none of its own. It is
// null on the Always on tab, in a scene with its own sound or silence and where Always on has none
function soundUnder() {
  if (state.at < 0 || state.sound || state.soundKept || state.soundOff) return null;
  return state.always.body.sound || null;
}

// Whether the scene being edited can silence Always on's sound, there being one to silence
function canSilence() { return state.at >= 0 && !!state.always.body.sound; }

// The sentence over the Sound tab, what the scene does with its sound or why there is none to
// choose
function soundSaid() {
  var under = soundUnder();
  return under
    ? "Always on's " + nameShown(under) + " plays on through this scene. Choose a sound to " +
      "give this scene its own, or Silence to quieten it"
    : state.soundOff
    ? "this scene is silent. Always on's " + nameShown(state.always.body.sound) + " stops while " +
      "it shows"
    : !state.fileHandle
    ? "open the FX drive to see the sounds on it"
    : !state.scanned
      ? "reading the drive..."
    : !(state.sounds.length || state.sound || state.soundKept)
      ? "no sounds on the drive yet. Drop a WAV file onto it"
    : !state.scenes.length
      ? "one WAV file, playing alongside the lights"
    : state.at < 0
      ? "plays in any scene without its own sound"
      : "plays while this scene shows, resuming where it left off";
}

// How the sound plays, above the tiles where a screen keeps its settings. Loop is a toggle as the
// screens' is, drawn here as well since not every page has the screens. Nothing writes no sound
// for the scene, so Always on's plays through where it has one, as Nothing does on the lights
function soundHead() {
  // A scene playing Always on's sound shows Always on's loop, greyed
  var under = soundUnder();
  var looping = under ? state.always.body.soundLoop : state.soundLoop && state.sound;
  return h("div", {className: "soundhead"},
           h("button", {
             type: "button",
             className: "stoggle" + (looping ? " on" : "") + (under ? " frozen" : ""),
             "aria-pressed": String(!!looping),
             title: under ? "Set on the Always on tab"
                  : state.sound ? "Loop the sound instead of playing it once" : "No sound chosen",
             disabled: !state.sound,
             onclick: function () {
               state.soundLoop = !state.soundLoop;
               draw();
             }
           }, h("span", {"aria-hidden": "true"}, "↻"), " Loop"),
           volumeSlider(),
           h("div", {
             className: "card nothing small" +
                        (!state.sound && !state.soundKept && !state.soundOff ? " picked" : ""),
             title: canSilence() ? "Play nothing of this scene's own" : "Play no sound",
             onclick: function () {
               state.sound = null;
               state.soundOff = false;
               state.soundLoop = false;
               state.soundVolume = 100;
               state.soundKept = null;
               draw();
             }
           }, h("div", {className: "face"}), h("div", {className: "name"}, "Nothing")));
}

// The row of sounds, grouped once the drive is open with the user's own always first, and
// Silence on the line of the first group's heading
function soundRow() {
  // A sound the file names that the drive does not hold still gets its tile, since
  // the board may find it on its own storage
  var names = state.sounds.slice();
  if (state.sound && names.indexOf(state.sound) < 0) names.unshift(state.sound);
  var grouped = !!state.fileHandle;
  var files = names.map(function (name) { return {name: name}; });
  var groups = [[OWN_GROUP, "your own sounds", files.filter(function (one) {
    return !isExampleMedia(one.name);
  }), false]];
  groups = groups.concat(exampleGroups("sounds", files));
  var shown = [];
  groups.forEach(function (group, at) {
    if (at && !group[2].length) return;
    // Keyed apart from the Screens tab's groups, since both tabs have a group of the user's own
    var kept = ["sound:" + group[0]].concat(group.slice(1));
    var open = groupOpen(kept);
    if (grouped) {
      shown.push(foldHead(group[0], group[1], open, function () {
        groupsOpen[kept[0]] = !open;
      }));
    }
    if (grouped && !open) return;
    group[2].forEach(function (one) { shown.push(soundTile(one.name)); });
    if (at) return;
    if (state.fileHandle)
      shown.push(adderTile("add sounds",
        {description: "Sounds the board can play", accept: {"audio/wav": [".wav"]}},
        "sounds", /\.wav$/i));
  });
  // Silence sits at the end of the first heading, as Off is in the screens' gallery, or on a
  // line of its own where there are no headings
  var line = h("div", {className: "offhead"}, grouped ? shown.shift() : null, soundSilenceCard());
  var keptTile = state.soundKept ? soundKeptTile() : null;
  return h("div", {className: "sounds"}, grouped ? [keptTile, line] : [line, keptTile], shown);
}

// Silence, `audio: none`, is the scene choosing no sound over Always on's. Where there is nothing
// to silence it keeps its place unseen, so the tab does not move between scenes. Its face is a
// sound with nothing in it, drawn as a tile draws a near-silent file
function soundSilenceCard() {
  return h("div", {
    className: "card nothing small" + (state.soundOff ? " picked" : ""),
    style: {visibility: canSilence() ? null : "hidden"},
    title: "Play no sound in this scene",
    onclick: function () {
      state.sound = null;
      state.soundKept = null;
      state.soundLoop = false;
      state.soundVolume = 100;
      state.soundOff = true;
      draw();
    }
  }, h("div", {className: "face silenceface"}, soundOutline(silentBars())),
     h("div", {className: "name"}, "Silence"));
}

// The volume the board plays the sound at, a percentage in steps of five
function volumeSlider() {
  // A scene playing Always on's sound shows Always on's volume, greyed, as a screen its backlight
  var under = soundUnder();
  var figure = h("span", {className: "lightfigure"});
  var slider = h("input", {
    type: "range", name: "soundVolume", min: 0, max: 100, step: 5,
    value: under ? state.always.body.soundVolume : state.soundVolume,
    disabled: !state.sound,
    oninput: function () { figure.textContent = slider.value + "%"; },
    onchange: function () {
      state.soundVolume = Number(slider.value);
      // A sound being heard here follows the slider
      if (hearing.audio && hearing.name === state.sound) {
        hearing.audio.volume = state.soundVolume / 100;
      }
      draw();
    }
  });
  figure.textContent = slider.value + "%";
  var volume = h("label", {
    className: "opt soundvolume",
    title: state.sound ? "How loud the board plays the sound" : "No sound chosen"
  }, "volume", slider, figure);
  if (under) frozen(volume);
  return volume;
}

// A flat line, the face of a sound with no outline to draw
function flatLine(colour) {
  return h("svg:svg", {viewBox: "0 0 104 30", preserveAspectRatio: "none",
                       html: "<rect x='0' y='14' width='104' height='2' rx='1' fill='" + colour +
                             "'/>"});
}

function soundKeptTile() {
  return h("button", {
    className: "sound" + (state.sound ? "" : " picked"), "aria-pressed": String(!state.sound),
    title: state.soundKept,
    onclick: function () {
      state.sound = null;
      state.soundLoop = false;
      state.soundVolume = 100;
      draw();
    }
  }, flatLine("#c9c3b9"), h("b", {}, "Keep as is"), h("small", {}, state.soundKept.slice(0, 40)));
}

function soundLine(body) {
  if (body.soundOff) return "audio: none";
  if (body.sound)
    return "audio: wav file=" + quoted(body.sound) +
           (body.soundLoop ? " loop=true" : "") +
           (body.soundVolume < 100 ? " volume=" + body.soundVolume + "%" : "");
  return body.soundKept;
}

// How many points a sound's outline is drawn from, enough for it to look smooth on a tile
var SOUND_SAMPLES = 96;

// ---- each scene keeps its own sound -------------------------------------------------------------

addStep(bodyParts, BODY_ORDER, "sound", {
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
  // A scene's sound is its first line
  entries: function (body, lines) {
    var sound = "sound" in body ? soundLine(body) : null;
    if (sound) lines.unshift(sound);
    return lines;
  },
  read: readSound
});

// Try each kept line of each body as a sound, moving the one that writes back exactly
function readSound(bodies) {
  bodies.forEach(function (body) {
    body.kept = body.kept.filter(function (one) {
      var parts = entryParts(one.text);
      // A scene's silence is read as itself
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
      // A volume written any other way than the slider writes it fails the match below, and
      // its line is kept as it is
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

// ---- the sounds on the drive --------------------------------------------------------------------

var soundsFound = [];

addStep(driveParts, DRIVE_ORDER, "sound", {
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

// Read a wav's length and its outline at SOUND_SAMPLES points into state.soundInfo
async function profileSound(name, handle) {
  soundHandles[name] = handle;
  if (state.soundInfo[name] !== undefined) return;
  state.soundInfo[name] = null;
  try {
    var file = await handle.getFile();
    var head = new DataView(await file.slice(0, 8192).arrayBuffer());
    if (head.getUint32(0) !== 0x52494646 || head.getUint32(8) !== 0x57415645)
      throw new Error("not a WAV file");
    var at = 12;
    var byteRate = 0;
    var bits = 16;
    var dataAt = 0;
    var dataSize = 0;
    while (at + 8 <= head.byteLength) {
      var id = head.getUint32(at);
      var size = head.getUint32(at + 4, true);
      if (id === 0x666d7420) {                       // "fmt "
        byteRate = head.getUint32(at + 16, true);
        bits = head.getUint16(at + 22, true);
      } else if (id === 0x64617461) {                // "data"
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

// ---- hearing a sound --------------------------------------------------------------------------
// Each sound on the drive has a play button in its tile's corner, so it can be heard as well as
// seen. One plays at a time, and pressing it again, or playing another, stops it

var soundHandles = {};
export var hearing = {name: null, audio: null, url: null};

// Set the sound playing here, its name, its audio and the URL it plays from, if any
export function setHearing(name, audio, url) {
  hearing = {name: name, audio: audio, url: url};
}

export function stopHearing() {
  if (hearing.audio) hearing.audio.pause();
  if (hearing.url) URL.revokeObjectURL(hearing.url);
  hearing = {name: null, audio: null, url: null};
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
    // The chosen sound is heard at its volume, any other as recorded
    if (name === state.sound) audio.volume = state.soundVolume / 100;
    hearing = {name: name, audio: audio, url: url};
    audio.onended = function () {
      if (hearing.audio === audio) stopHearing();
      draw();
    };
    draw();
    await audio.play();
  } catch (e) {
    // A sound stopped or replaced before it began is cancelled with AbortError, which is no fault
    if (e.name === "AbortError" && hearing.audio !== audio) return;
    if (hearing.audio === audio) stopHearing();
    banner("Could not play " + nameShown(name) + ": " + e.name + ".", true);
    draw();
  }
}

// The way to hear a sound here, where the open drive holds it, or null
function hearButton(name) {
  if (!soundHandles[name]) return null;
  var playing = hearing.name === name;
  // A tile is a button already, so this is a plain element taking the click, as its cross is
  return h("span", {
    className: "hear" + (playing ? " playing" : ""),
    role: "button", "aria-pressed": String(playing),
    title: (playing ? "Stop " : "Play ") + nameShown(name) + " here",
    onclick: function (event) {
      event.stopPropagation();
      hear(name);
    }
  }, playing ? "\u25a0" : "\u25b6");
}

// ---- drawing the tab ---------------------------------------------------------------------------

// The colours a sound's outline runs through, blue when quiet through violet and pink to red when
// loud. The violet keeps the middle of the run clear, where blue straight to red goes muddy
var LOUDNESS = ["#3a6fd8", "#8a4fd0", "#d0449a", "#e5443a"];
// A count that gives each outline's gradient an id of its own
var outlinesMade = 0;

// The colour for a loudness from 0 to 1, between the two nearest of LOUDNESS
function loudnessInk(loud) {
  var at = Math.max(0, Math.min(1, loud)) * (LOUDNESS.length - 1);
  var low = Math.floor(at), high = Math.min(LOUDNESS.length - 1, low + 1), part = at - low;
  function parts(hex) {
    return [1, 3, 5].map(function (from) { return parseInt(hex.substr(from, 2), 16); });
  }
  var from = parts(LOUDNESS[low]), to = parts(LOUDNESS[high]);
  return "rgb(" + from.map(function (value, channel) {
    return Math.round(value + (to[channel] - value) * part);
  }).join(",") + ")";
}

// The bars of a sound with nothing in it, a thin band in the quietest colour
function silentBars() {
  var bars = [];
  for (var i = 0; i < SOUND_SAMPLES; i++) bars.push(0.04);
  return bars;
}

// A sound's outline, filled edge to edge, mirrored about the middle and coloured by loudness
function soundOutline(bars) {
  var wide = 100, high = 40, middle = high / 2, last = bars.length - 1;
  var id = "loudness" + (outlinesMade++);
  function across(at) { return (at / last) * wide; }
  var above = bars.map(function (tall, at) { return across(at) + "," + (middle - tall * middle); });
  var below = bars.map(function (tall, at) { return across(at) + "," + (middle + tall * middle); });
  return h("svg:svg", {
    viewBox: "0 0 " + wide + " " + high, preserveAspectRatio: "none", class: "soundoutline",
    html: "<defs><linearGradient id='" + id + "' x1='0' x2='1'>" +
          bars.map(function (tall, at) {
            return "<stop offset='" + at / last + "' stop-color='" + loudnessInk(tall) + "'/>";
          }).join("") + "</linearGradient></defs>" +
          "<polygon points='" + above.concat(below.reverse()).join(" ") + "' fill='url(#" + id +
          ")'/>"
  });
}

// A sound's tile, with its outline, how long it runs and a way to hear it here. Always on's
// sound, playing in a scene with none of its own, wears the striped frame a screen showing Always
// on's picture wears
function soundTile(name) {
  var picked = state.sound === name;
  var info = state.soundInfo[name];
  var tile = h("button", {
    className: "sound" + (picked ? " picked" : "") + (name === soundUnder() ? " under" : ""),
    "aria-pressed": String(!!picked),
    onclick: function () {
      state.sound = name;
      state.soundOff = false;
      state.soundKept = null;
      draw();
    }
  }, info && info.bars ? soundOutline(info.bars) : flatLine(picked ? "#0f8a72" : "#c9c3b9"),
     h("b", {}, nameShown(name)),
     h("small", {}, info && info.seconds ? info.seconds + "s" +
                                           (picked && state.soundLoop ? ", on repeat" : "")
                  : state.sounds.indexOf(name) < 0 ? "not on the drive" : null),
     // An example keeps no bin here, as flashing the board's examples again brings it back.
     // Where the board's examples can be discovered, discover/sound/discover_sound.js gives it one
     state.sounds.indexOf(name) >= 0 && !isExampleMedia(name) ? binButton(name, "wav") : null);
  soundTileSteps.forEach(function (step) { step(tile, name); });
  var hear = hearButton(name);
  if (hear) tile.appendChild(hear);
  return tile;
}

// What the parts after this one add to each sound's tile, each given the tile and its sound's
// name
export var soundTileSteps = [];

// Draw the Sound tab. A sentence that only says what the scene does with its sound becomes the
// row's tip, since no other tab opens on a sentence, and any other sentence stays
function renderSound() {
  var says = document.getElementById("soundSays");
  says.textContent = soundSaid();
  var explains = /^(one WAV|plays)/.test(says.textContent);
  var row = soundRow();
  if (explains) row.title = says.textContent.charAt(0).toUpperCase() + says.textContent.slice(1);
  // With scenes, a sentence one tab shows and another does not keeps its place unseen, so the tab
  // does not move between them
  says.hidden = explains && !state.scenes.length;
  says.style.visibility = explains ? "hidden" : "";
  replace(document.getElementById("sound"), soundHead(), row);
  soundSteps.forEach(function (step) { step(); });
}

// What the parts after this one add to the Sound tab once its tiles are made
export var soundSteps = [];

// The tab's swatch is the shape of the sound playing, or silence
tabSwatches.soundPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch soundswatch";
  var under = soundUnder();
  // The scene's Silence is the flat line its card shows
  if (state.soundOff) {
    swatch.appendChild(soundOutline(silentBars()));
    swatch.title = "silence";
    return;
  }
  var info = state.sound ? state.soundInfo[state.sound] : under ? state.soundInfo[under] : null;
  if (!info) {
    swatch.classList.add("silent");
    swatch.title = under ? "Always on's " + nameShown(under) : "nothing";
    return;
  }
  // Always on's sound is drawn faded, as its looks are on the lamps
  if (under) {
    swatch.appendChild(soundOutline(info.bars));
    swatch.classList.add("under");
    swatch.title = "Always on's " + nameShown(under);
    return;
  }
  swatch.appendChild(soundOutline(info.bars));
  // Check if the sound is on repeat, which shows as a loop in the swatch's corner
  if (state.soundLoop) {
    swatch.appendChild(h("svg:svg", {
      viewBox: "0 0 16 16", class: "repeatmark",
      html: "<path d='M3 7a5 5 0 0 1 9-3M13 9a5 5 0 0 1-9 3' fill='none' " +
            "stroke='currentColor' stroke-width='2' stroke-linecap='round'/>" +
            "<path d='M12 1v3.5H8.5M4 15v-3.5h3.5' fill='none' stroke='currentColor' " +
            "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>"
    }));
    swatch.classList.add("repeats");
  }
  swatch.title = nameShown(state.sound) + (state.soundLoop ? ", on repeat" : "") +
                 (state.soundVolume < 100 ? ", " + state.soundVolume + "% volume" : "");
};

// Put the kind of sound playing under the tab's name. The file's name is the Sound section's to say
function kindUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=soundPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  tab.prepend(h("span", {className: "tabname"}, tab.querySelector("b"),
                h("small", {className: "tabunder"},
                  state.sound || state.soundKept ? "wav" : state.soundOff ? "silence"
                  : soundUnder() ? "Always on" : "nothing")));
}

addStep(drawSteps.after, DRAW_AFTER, "sound", function () {
  kindUnderName();
  renderSound();
});

document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]).after(
  h("details", {className: "panel", id: "soundPanel", open: true},
    h("summary", {}, "Sound"),
    h("p", {className: "says soundsays", id: "soundSays"}),
    h("div", {id: "sound"})));

TAB_NAMES.soundPanel = "Sound";
addStep(TAB_PANELS, FEATURE_TABS, "sound", "soundPanel");
keptOpen("soundPanel");
