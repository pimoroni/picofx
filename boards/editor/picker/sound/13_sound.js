
// ---- a Sound tab ----------------------------------------------------------------------------
// One wav at a time, chosen from a row of tiles each showing its shape and how long it runs,
// with whether it loops and silence on a line above them.
//
// The drawing asks of its page the sounds on the drive, and each scene keeping its own sound.
// The board takes one per scene, and the one in the always-on tab plays in any scene that
// brings none of its own. Nothing about the sound is the board's, so setting up leaves it
// standing back.

state.sound = null;
state.soundLoop = false;
state.soundKept = null;
state.sounds = [];
state.soundInfo = {};

// The Sound tab's row of sounds and its setting, which renderSound below puts in the page's style
function renderSoundTab() {
  var box = document.getElementById("sound");
  box.textContent = "";
  document.getElementById("soundSays").textContent = !state.fileHandle
    ? "open the FX drive to see the sounds on it"
    : !state.scanned
      ? "reading the drive..."
    : !(state.sounds.length || state.sound || state.soundKept)
      ? "no sounds on the drive yet; drop a wav onto it"
    : !state.scenes.length
      ? "one wav, playing on while the lights run"
    : state.at < 0
      ? "played in any scene that brings no sound of its own"
      : "played while this scene shows, picking up where it left off";

  // How the sound is played rather than which one it is, so it sits above them,
  // where a screen keeps its settings
  var again = document.createElement("button");
  again.className = "again" + (state.soundLoop && state.sound ? " on" : "");
  again.textContent = "on repeat";
  again.disabled = !state.sound;
  again.title = state.sound
    ? "Start it again as it ends, instead of playing once as the board starts"
    : "Nothing is playing, so there is nothing to repeat";
  again.onclick = function () { state.soundLoop = !state.soundLoop; draw(); };
  var above = document.createElement("div");
  above.style.margin = "0 0 .7rem";
  above.appendChild(again);
  box.appendChild(above);

  var row = document.createElement("div");
  row.className = "sounds";
  // A sound the file names that the drive does not hold still gets its tile, since
  // the board may find it on its own storage
  var names = state.sounds.slice();
  if (state.sound && names.indexOf(state.sound) < 0) names.unshift(state.sound);
  if (state.soundKept) row.appendChild(soundKeptTile());
  names.forEach(function (name) { row.appendChild(soundTile(name)); });
  row.appendChild(soundTile(null));
  if (state.fileHandle)
    row.appendChild(adderTile("add sounds",
      {description: "Sounds the board plays", accept: {"audio/wav": [".wav"]}},
      "sounds", /\.wav$/i));
  box.appendChild(row);
}

function soundKeptTile() {
  var tile = document.createElement("button");
  tile.className = "sound" + (state.sound ? "" : " picked");
  tile.title = state.soundKept;
  tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'><rect x='0' " +
                   "y='14' width='104' height='2' rx='1' fill='#c9c3b9'/></svg>";
  var title = document.createElement("b");
  title.textContent = "As it is";
  tile.appendChild(title);
  var says = document.createElement("small");
  says.textContent = state.soundKept.slice(0, 40);
  tile.appendChild(says);
  tile.onclick = function () {
    state.sound = null;
    state.soundLoop = false;
    draw();
  };
  return tile;
}

// A sound's tile, which soundTile below draws the sound on
function plainSoundTile(name) {
  var picked = name === null ? !state.sound && !state.soundKept : state.sound === name;
  var info = name ? state.soundInfo[name] : null;
  var tile = document.createElement("button");
  tile.className = "sound" + (picked ? " picked" : "") + (name ? "" : " quiet");
  var colour = picked ? "#0f8a72" : "#c9c3b9";
  if (name && info && info.bars) {
    var cells = [];
    info.bars.forEach(function (tall, i) {
      var high = Math.max(2, tall * 26);
      cells.push("<rect x='" + (i * 4) + "' y='" + ((30 - high) / 2) + "' width='2.6' " +
                 "height='" + high + "' rx='1.3' fill='" + colour + "'/>");
    });
    tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'>" +
                     cells.join("") + "</svg>";
  } else {
    tile.innerHTML = "<svg viewBox='0 0 104 30' preserveAspectRatio='none'><rect x='0' " +
                     "y='14' width='104' height='2' rx='1' fill='" + colour + "'/></svg>";
  }
  var title = document.createElement("b");
  title.textContent = name || "Silence";
  tile.appendChild(title);
  var says = document.createElement("small");
  says.textContent = !name ? "nothing plays"
                   : info && info.seconds ? info.seconds + "s" +
                     (picked && state.soundLoop ? ", on repeat" : "")
                   : state.sounds.indexOf(name) < 0 ? "not on the drive" : "";
  tile.appendChild(says);
  tile.onclick = function () {
    state.sound = name;
    if (name) state.soundKept = null;
    if (!name) {
      state.soundLoop = false;
      state.soundKept = null;
    }
    draw();
  };
  if (name && state.sounds.indexOf(name) >= 0) tile.appendChild(binButton(name, "wav"));
  return tile;
}

function soundLine(body) {
  if (body.sound)
    return "audio: wav file=" + quoted(body.sound) +
           (body.soundLoop ? " loop=true" : "");
  return body.soundKept;
}

// How many points a sound's outline is drawn from, enough for it to look smooth at the
// pictures' size
var SOUND_SAMPLES = 96;

// ---- each scene keeps its own sound -------------------------------------------------------------

bodyParts.push({
  capture: function (body) {
    body.sound = state.sound;
    body.soundLoop = state.soundLoop;
    body.soundKept = state.soundKept;
  },
  apply: function (body) {
    if (!("sound" in body)) return;
    state.sound = body.sound;
    state.soundLoop = body.soundLoop;
    state.soundKept = body.soundKept;
  },
  blank: function (body) {
    body.sound = null;
    body.soundLoop = false;
    body.soundKept = null;
  },
  hasContent: function (body) { return !!body.sound; },
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
      if (!parts || parts.selector !== "audio" || parts.effect !== "wav" || body.sound ||
          !Object.keys(parts.right).every(function (key) { return key === "file" || key === "loop"; })) {
        return true;
      }
      var sounding = {sound: unquoted(parts.right.file), soundLoop: parts.right.loop === "true",
                      soundKept: null};
      if (!sounding.sound || soundLine(sounding) !== one.text) return true;
      body.sound = sounding.sound;
      body.soundLoop = sounding.soundLoop;
      if (one.comments.length) body.notes[one.text] = one.comments;
      return false;
    });
  });
}

// ---- the sounds on the drive --------------------------------------------------------------------

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
      }
    });
    delete state.soundInfo[name];
  }
});

// A wav's length and outline, the outline read at SOUND_SAMPLES points
async function profileSound(name, handle) {
  soundHandles[name] = handle;
  if (state.soundInfo[name] !== undefined) return;
  state.soundInfo[name] = null;
  try {
    var file = await handle.getFile();
    var head = new DataView(await file.slice(0, 8192).arrayBuffer());
    if (head.getUint32(0) !== 0x52494646 || head.getUint32(8) !== 0x57415645)
      throw new Error("not a wav");
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
var hearing = {name: null, audio: null, url: null};

function stopHearing() {
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
  try {
    var url = URL.createObjectURL(await soundHandles[name].getFile());
    var audio = new Audio(url);
    hearing = {name: name, audio: audio, url: url};
    audio.onended = function () {
      if (hearing.audio === audio) stopHearing();
      draw();
    };
    draw();
    await audio.play();
  } catch (e) {
    stopHearing();
    banner("Could not play " + name + ": " + e.name + ".", true);
    draw();
  }
}

// A sound's tile with a way to hear it here, where the open drive holds it
function withHearButton(tile, name) {
  if (!name || !soundHandles[name]) return tile;
  var playing = hearing.name === name;
  // A tile is a button already, so this is a plain element taking the click, as its cross is
  var button = document.createElement("span");
  button.className = "hear" + (playing ? " playing" : "");
  button.setAttribute("role", "button");
  button.textContent = playing ? "\u25a0" : "\u25b6";
  button.title = (playing ? "Stop " : "Play ") + name + " here";
  button.onclick = function (event) {
    event.stopPropagation();
    hear(name);
  };
  tile.appendChild(button);
  return tile;
}

// ---- drawing the tab ---------------------------------------------------------------------------

// A sound's outline, filled edge to edge and mirrored about the middle. Each moment of it is
// coloured by how loud it is, blue when quiet through violet and pink to red when loud, the
// violet keeping the middle of the run clear where blue straight to red goes muddy
var LOUDNESS = ["#3a6fd8", "#8a4fd0", "#d0449a", "#e5443a"];
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

function soundOutline(bars) {
  var wide = 100, high = 40, middle = high / 2, last = bars.length - 1;
  var id = "loudness" + (outlinesMade++);
  function across(at) { return (at / last) * wide; }
  var above = bars.map(function (tall, at) { return across(at) + "," + (middle - tall * middle); });
  var below = bars.map(function (tall, at) { return across(at) + "," + (middle + tall * middle); });
  var outline = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  outline.setAttribute("viewBox", "0 0 " + wide + " " + high);
  outline.setAttribute("preserveAspectRatio", "none");
  outline.setAttribute("class", "soundoutline");
  outline.innerHTML = "<defs><linearGradient id='" + id + "' x1='0' x2='1'>" +
    bars.map(function (tall, at) {
      return "<stop offset='" + at / last + "' stop-color='" + loudnessInk(tall) + "'/>";
    }).join("") + "</linearGradient></defs>" +
    "<polygon points='" + above.concat(below.reverse()).join(" ") + "' fill='url(#" + id + ")'/>";
  return outline;
}

// The Sound section's tiles draw their sound the same way, each with a way to hear it here
function soundTile(name) {
  var tile = plainSoundTile(name);
  var info = name ? state.soundInfo[name] : null;
  var drawn = tile.querySelector("svg");
  if (info && info.bars && drawn) tile.replaceChild(soundOutline(info.bars), drawn);
  // Silence wears the stripes that nothing playing wears everywhere else on the page
  if (name === null && drawn) {
    var nothing = document.createElement("span");
    nothing.className = "nothingface";
    tile.replaceChild(nothing, drawn);
  }
  return withHearButton(tile, name);
}

// The tab in the page's style. What the scene does with its sound is the row's tip, no other
// tab opening on a sentence; the sentence stays only where there are no sounds to show, since
// it is then all there is. Repeat is a toggle with its icon, as the screens' Loop is, and
// silence the small card Nothing is in the gallery, at the end of that line
function renderSound() {
  renderSoundTab();
  var box = document.getElementById("sound");
  var says = document.getElementById("soundSays");
  var row = box.querySelector(".sounds");
  var explains = /^(one wav|played)/.test(says.textContent);
  if (row && explains) row.title = says.textContent.charAt(0).toUpperCase() +
                                   says.textContent.slice(1);
  says.hidden = explains;

  var again = box.querySelector("button.again");
  var head = again && again.parentNode;
  if (!head) return;
  head.removeAttribute("style");
  head.className = "soundhead";
  // The screens' toggle, drawn here as well since not every page has the screens
  var loop = document.createElement("button");
  loop.type = "button";
  loop.className = "stoggle" + (state.soundLoop && state.sound ? " on" : "");
  loop.innerHTML = "<span aria-hidden='true'>&#8635;</span> Loop";
  loop.title = again.title;
  loop.disabled = !state.sound;
  loop.onclick = function () {
    state.soundLoop = !state.soundLoop;
    draw();
  };
  head.replaceChild(loop, again);

  var quiet = row && row.querySelector(".sound.quiet");
  if (!quiet) return;
  var silence = document.createElement("div");
  silence.className = "card nothing small" + (quiet.classList.contains("picked") ? " picked" : "");
  silence.title = quiet.title || "play no sound";
  silence.innerHTML = "<div class='face'></div><div class='name'>Silence</div>";
  silence.onclick = quiet.onclick;
  head.appendChild(silence);
  row.removeChild(quiet);
}

// The tab's swatch is the shape of the sound playing, or silence
tabSwatches.soundPanel = function (swatch) {
  swatch.textContent = "";
  swatch.className = "accswatch soundswatch";
  var info = state.sound ? state.soundInfo[state.sound] : null;
  if (!info) {
    swatch.classList.add("silent");
    swatch.title = "silence";
    return;
  }
  swatch.appendChild(soundOutline(info.bars));
  // On repeat, the Sound section's one setting, as a loop in the preview's corner
  if (state.soundLoop) {
    var mark = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    mark.setAttribute("viewBox", "0 0 16 16");
    mark.setAttribute("class", "repeatmark");
    mark.innerHTML = "<path d='M3 7a5 5 0 0 1 9-3M13 9a5 5 0 0 1-9 3' fill='none' " +
                     "stroke='currentColor' stroke-width='2' stroke-linecap='round'/>" +
                     "<path d='M12 1v3.5H8.5M4 15v-3.5h3.5' fill='none' stroke='currentColor' " +
                     "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/>";
    swatch.appendChild(mark);
    swatch.classList.add("repeats");
  }
  swatch.title = state.sound + (state.soundLoop ? ", on repeat" : "");
};

// Under the tab's name, the kind of sound playing, which a tone will join once the board
// plays one. The file's name is the Sound section's to say
function kindUnderName() {
  var tab = document.querySelector("#ledTabs .ledtab[data-panel=soundPanel]");
  if (!tab || tab.querySelector(".tabname")) return;
  var named = document.createElement("span");
  named.className = "tabname";
  named.appendChild(tab.querySelector("b"));
  var kind = document.createElement("small");
  kind.className = "tabunder";
  kind.textContent = state.sound || state.soundKept ? "wav" : "silence";
  named.appendChild(kind);
  tab.insertBefore(named, tab.firstChild);
}

drawSteps.after.push(function () {
  kindUnderName();
  renderSound();
});

(function () {
  var panel = document.createElement("details");
  panel.className = "panel";
  panel.id = "soundPanel";
  panel.open = true;
  panel.innerHTML = "<summary>Sound</summary>" +
                    "<p class='says soundsays' id='soundSays'></p>" +
                    "<div id='sound'></div>";
  var after = document.getElementById(TAB_PANELS[TAB_PANELS.length - 1]);
  after.parentNode.insertBefore(panel, after.nextSibling);
}());

TAB_NAMES.soundPanel = "Sound";
TAB_PANELS.push("soundPanel");
keptOpen("soundPanel");
