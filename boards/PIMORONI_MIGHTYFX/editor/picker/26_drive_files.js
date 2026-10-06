
// ---- the drive's files ---------------------------------------------------------------------------
// The effects page as it goes onto an FX drive: no Screen Hub until one is set up, and the pictures
// and sounds the drive holds, each picture and wav read off the drive.

var scanBusy = false;

async function scanMedia(dir) {
  // What the drive holds that a screen can show: gifs and stills, PNG or JPEG, folders of
  // them, which play as a slideshow, and drawings. One walk at a time, built
  // aside and landed whole, so a redraw mid-scan never sees half a drive and two
  // walks can never lace their findings together
  if (scanBusy) return;
  scanBusy = true;
  var media = [];
  var sounds = [];
  try {
    for await (var pair of dir.entries()) {
      var name = pair[0], handle = pair[1];
      if (handle.kind === "file") {
        if (/\.gif$/i.test(name)) media.push({ name: name, kind: "gif", handle: handle });
        else if (/\.(png|jpe?g)$/i.test(name)) media.push({ name: name, kind: "image", handle: handle });
        else if (/\.wav$/i.test(name)) {
          sounds.push(name);
          profileSound(name, handle);
        } else if (/\.py$/i.test(name)) {
          // A Python file is a drawing only where its opening string says so
          var drawing = null;
          try {
            drawing = drawingSaid(openingString(await (await handle.getFile()).text()));
          } catch (e) {
            drawing = null;
          }
          if (drawing) media.push({name: name, kind: "drawing", drawing: drawing});
        }
      } else if (name !== "System Volume Information") {
        for await (var inner of handle.entries()) {
          if (inner[1].kind === "file" && /\.(gif|png|jpe?g)$/i.test(inner[0])) {
            media.push({ name: name, kind: "folder", thumbHandle: inner[1] });
            break;
          }
        }
      }
    }
  } finally {
    scanBusy = false;
  }
  sounds.sort();
  media.sort(function (a, b) { return a.name < b.name ? -1 : 1; });
  state.media = media;
  // A drawing cannot run in the page, so it is shown by a face made from its opening string
  media.forEach(function (one) { if (one.kind === "drawing") madeDrawing(one.name); });
  state.sounds = sounds;
  state.scanned = true;
}

async function rescanMedia() {
  if (!state.dirHandle || scanBusy) return;
  var was = JSON.stringify([state.media.map(function (m) { return m.name + m.kind; }),
                            state.sounds]);
  try {
    await scanMedia(state.dirHandle);
  } catch (e) {
    return;
  }
  var now = JSON.stringify([state.media.map(function (m) { return m.name + m.kind; }),
                            state.sounds]);
  if (now !== was) draw();
}

function adderTile(label, kinds, what, takes) {
  var tile = document.createElement("button");
  tile.className = "adder";
  tile.innerHTML = "<svg width='13' height='13' viewBox='0 0 11 11'><path d='M5.5 1 " +
                   "L5.5 10 M1 5.5 L10 5.5' stroke='currentColor' stroke-width='1.8' " +
                   "stroke-linecap='round'/></svg>" + label;
  tile.title = "Copy files from this computer onto the FX drive";
  tile.onclick = function () { addFiles(kinds, what, takes); };
  return tile;
}

function binButton(name, kind) {
  if (!CAN_REACH_A_DRIVE) return document.createTextNode("");
  var bin = document.createElement("span");
  bin.className = "bin";
  bin.textContent = "\u00d7";
  bin.title = "Delete " + name + " from the FX drive";
  bin.onclick = function (e) {
    e.stopPropagation();
    removeFromDrive(name, kind);
  };
  return bin;
}

async function addFiles(kinds, what, takes) {
  var picked;
  try {
    picked = await window.showOpenFilePicker({multiple: true, types: [kinds],
                                              excludeAcceptAllOption: true});
  } catch (e) {
    // A dismissed dialog says nothing. Anything else is the browser refusing the files
    if (e.name !== "AbortError")
      banner("The browser would not open those files (" + e.message + "). Copy them to " +
             "another folder, such as Downloads, and add them from there.", true);
    return;
  }
  var landed = 0;
  var arrived = [];
  var refused = [];
  for (var i = 0; i < picked.length; i++) {
    var file;
    try {
      // The dialog filters, and this holds where a platform's does not: a kind
      // the board cannot play never reaches the drive
      if (!takes.test(picked[i].name)) {
        refused.push(picked[i].name + " (not a kind the board plays)");
        continue;
      }
      file = await picked[i].getFile();
      var existing = null;
      try { existing = await state.dirHandle.getFileHandle(file.name); } catch (e) {}
      if (existing && !confirm(file.name + " is already on the drive. Replace it?"))
        continue;
      var handle = await state.dirHandle.getFileHandle(file.name, {create: true});
      var writable = await handle.createWritable();
      await writable.write(file);
      await writable.close();
      landed++;
      arrived.push(file.name);
    } catch (e) {
      refused.push(file ? file.name : "a file");
      if (e.name === "QuotaExceededError") {
        refused = refused.concat(picked.slice(i + 1).map(function (p) { return p.name; }));
        banner("The FX drive filled up: " + landed + " " + what + " copied, no room for " +
               refused.join(", ") + ". Delete something from it and try again.", true);
        break;
      }
    }
  }
  try { await scanMedia(state.dirHandle); } catch (e) {}
  // A Python file is offered only where its opening string makes it a drawing
  var unoffered = arrived.filter(function (name) {
    return /\.py$/i.test(name) && !mediaNamed(name);
  });
  if (refused.length && landed)
    banner(landed + " copied; these did not arrive: " + refused.join(", "), true);
  else if (refused.length)
    banner("Nothing arrived: " + refused.join(", "), true);
  else if (unoffered.length)
    banner(unoffered.join(", ") + " copied, but only a drawing is offered here, and a " +
           "drawing's opening string starts with Drawing: and its name.", true);
  else if (landed)
    banner(landed + " " + what + " copied to the drive.");
  draw();
}

async function removeFromDrive(name, kind) {
  var said = kind === "folder"
    ? "Delete the folder " + name + " and every picture in it from the FX drive?"
    : "Delete " + name + " from the FX drive?";
  if (!confirm(said)) return;
  try {
    await state.dirHandle.removeEntry(name, {recursive: kind === "folder"});
  } catch (e) {
    banner("Could not delete " + name + ": " + e.name + ". Is the drive showing?", true);
    return;
  }
  store();
  allBodies().forEach(function (body) {
    SCREENS.forEach(function (letter) {
      if (body.screens[letter].shows === name) body.screens[letter].shows = null;
    });
  });
  apply(slotAt(state.at).body);
  allBodies().forEach(function (body) {
    if (body.sound === name) {
      body.sound = null;
      body.soundLoop = false;
    }
  });
  apply(slotAt(state.at).body);
  delete state.soundInfo[name];
  delete state.art[name];
  try { await scanMedia(state.dirHandle); } catch (e) {}
  draw();
}

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

// ---- pictures, read off the drive in turn ------------------------------------------------------
// The drive is slow to read, so pictures come off it one at a time, those a screen or hub position
// shows in any scene first and the rest of the gallery after them

var pictureQueue = [];
var pictureReading = null;

// The pictures any scene puts on a screen or a hub position, worked out once a draw
var shownThisDraw = null;

drawSteps.before.push(function () { shownThisDraw = null; });

function picturesShown() {
  if (shownThisDraw) return shownThisDraw;
  var shown = shownThisDraw = [];
  var bodies = [capture(), state.always.body].concat(state.scenes.map(function (scene) {
    return scene.body;
  }));
  bodies.forEach(function (body) {
    if (!body) return;
    Object.keys(body.screens || {}).forEach(function (letter) {
      if (body.screens[letter].shows) shown.push(body.screens[letter].shows);
    });
    Object.keys(body.places || {}).forEach(function (place) {
      if (body.places[place].shows) shown.push(body.places[place].shows);
    });
  });
  return shown;
}

function readNextPicture() {
  if (pictureReading || !pictureQueue.length) return;
  shownThisDraw = null;
  var shown = picturesShown();
  pictureQueue.sort(function (a, b) {
    return (shown.indexOf(b.name) >= 0) - (shown.indexOf(a.name) >= 0);
  });
  var next = pictureReading = pictureQueue.shift();
  next.handle.getFile().then(function (file) {
    return new Promise(function (settle) {
      var url = URL.createObjectURL(file);
      var probe = new Image();
      probe.onload = function () {
        state.art[next.name] = {url: url, w: probe.naturalWidth, h: probe.naturalHeight,
                                ratio: probe.naturalWidth / probe.naturalHeight};
        settle();
      };
      // One that will not load stays held empty, so it is not asked for again
      probe.onerror = function () { settle(); };
      probe.src = url;
    });
  }, function () {}).then(function () {
    pictureReading = null;
    draw();
    readNextPicture();
  });
}

function mediaArt(name) {
  var held = state.art[name];
  if (held) return held.ratio ? held : null;
  var media = mediaNamed(name);
  var handle = media && (media.kind === "folder" ? media.thumbHandle : media.handle);
  if (!handle) return null;
  // Held empty while it waits, so each is asked for once
  state.art[name] = {url: null, ratio: 0};
  pictureQueue.push({name: name, handle: handle});
  setTimeout(readNextPicture, 0);
  return null;
}

// ---- files on and off the drive -----------------------------------------------------------------
// A file deleted is also taken off every hub position showing it

var oneOnBoardRemove = removeFromDrive;

removeFromDrive = async function (name, kind) {
  await oneOnBoardRemove(name, kind);
  // Still listed means the question was declined, or the delete failed and said so
  if (state.media.some(function (one) { return one.name === name; })) return;
  store();
  allBodies().forEach(function (body) {
    Object.keys(body.places || {}).forEach(function (place) {
      if (body.places[place].shows === name) body.places[place].shows = null;
    });
  });
  apply(slotAt(state.at).body);
  draw();
};

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

var oneHearingTile = soundTile;

soundTile = function (name) {
  var tile = oneHearingTile(name);
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
};

// The file starts folded, there for anyone who opens it
(function () {
  var file = document.getElementById("preview").closest("details");
  if (file) file.open = false;
}());

connectSteps.push(async function () {
  state.fileHandle = drive.fileHandle;
  draw();
  await scanMedia(drive.dirHandle);
  draw();
});

setInterval(rescanMedia, 5000);
