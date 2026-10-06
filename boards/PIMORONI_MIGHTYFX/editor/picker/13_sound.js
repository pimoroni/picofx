
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
  }
});

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
  var after = document.getElementById("screensPanel");
  after.parentNode.insertBefore(panel, after.nextSibling);
}());

TAB_NAMES.soundPanel = "Sound";
TAB_PANELS.push("soundPanel");
keptOpen("soundPanel");
