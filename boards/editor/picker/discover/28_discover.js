import {BOARD} from "../01_looks.js";
import {draw, drawSteps} from "../03_runs.js";
import {apply, driveParts, slotAt, state, store} from "../04_scenes.js";
import {SCREEN_PORTS} from "../07_board.js";
import {banner, drive, driveTrouble} from "../18_drive.js";
import {PROGRAMS, boardSet, programNamed, programsElsewhere} from "../19_board_settings.js";
import {
  CHIPLESS, FEATURES, featureIcon, had, loadThumbs, passesFilter, programCard, programCardSteps,
  programTitle, programView, programViewSteps, unhad, usesOf
} from "../22_program.js";
import {
  OTHER_EXAMPLES, exampleSections, isExampleMedia, nameShown, scanMedia
} from "../26_drive_files.js";
import {
  EXAMPLES_ROOT, PICTURES, SECTIONS, copyProgram, folderAt, forgetMissingPrograms, programFrom
} from "../26_drive_programs.js";

// ---- examples to discover -----------------------------------------------------------------------
// The Discover button on each tab with examples, and the gallery it opens. Pressed, it fetches the
// index tools/build_examples_index.py writes and checks the drive against it, offering the examples
// the drive lacks to download and those it holds an older version of as updates. Each file is
// checked against the index's hash before it is written, and an example on the drive can be
// deleted, as it can be downloaded again. build_editor.py takes this folder only for a board whose
// description names its examples_index.

// The branch the index and the files are fetched from
export var discoverKinds = {};

var DISCOVER_BRANCH = "patch/spidisplay-external-rebased";

// Where the repository's files are served from, at that branch
var DISCOVER_SOURCE = "https://raw.githubusercontent.com/pimoroni/picofx/refs/heads/" +
                      DISCOVER_BRANCH + "/";

// A file's address, by its path on the drive. The index sits beside the examples folder it lists
function discoverFileUrl(path) {
  var index = BOARD.examples_index;
  return DISCOVER_SOURCE + index.slice(0, index.lastIndexOf("/") + 1) + path;
}

// The firmware's version, which an example may need newer than
var DISCOVER_FIRMWARE = "__VERSION__".split(" ")[0];

// A check of one tab's examples
function discoverFreshCheck() {
  // status is idle, checking, done or failed. progress is [files read, of] while the drive is read,
  // refreshing the same while it is read again quietly, updating [updated, of] while Update all
  // runs, and notice what the last download said, as [text, warn]
  return {status: "idle", progress: null, refreshing: null, updating: null, error: null,
          index: null, notice: null};
}

// What the page says where the examples cannot be fetched. Where they come from is never named
var DISCOVER_OFFLINE = "Could not connect. Check this computer is online.";

// What went wrong, in the page's words, in place of the browser's own. fetch() fails with a
// TypeError where the network cannot reach GitHub, an Error is one this part threw, and anything
// else is the drive's
async function discoverTrouble(e) {
  if (e.name === "TypeError") return DISCOVER_OFFLINE;
  if (e.name === "Error") return e.message;
  return await driveTrouble(e);
}

// Say how a download went, where the gallery's examples start and in the banner at the top of the
// page
export function discoverSay(kind, text, warn) {
  var notice = discover[kind].notice = [text, warn];
  banner(text, warn);
  // One saying a download went well gives the line back after a while, and a failure stays
  if (warn) return;
  setTimeout(function () {
    if (discover[kind].notice !== notice) return;
    discover[kind].notice = null;
    draw();
  }, DISCOVER_NOTICE_MS);
}

// How long a notice that a download went well is shown
var DISCOVER_NOTICE_MS = 8000;

var discover = {
  program: discoverFreshCheck(),
  sound: discoverFreshCheck(),
  drawing: discoverFreshCheck(),
  // Each example's state by path: missing, current, update, changed or moved
  states: {},
  // Each file's state by path, as {state: missing, same, old or changed, at: where the drive has it}
  files: {},
  // The examples needing newer firmware than the board's, by path
  newer: {},
  // The examples being downloaded, by path
  busy: {},
  // The path a moved example has now, by the path the drive has it at
  movedTo: {}
};

// The examples the drive lacks, as the program tab and the galleries list them
var discoverPrograms = {};
export var discoverDrawings = {};
export var discoverSounds = {};
// Each missing example's thumbnail, and a second screen's where it has one, as object URLs, by path
export var discoverThumbs = {};
var discoverSecondThumbs = {};

// Whether version a is older than version b, each as dotted numbers
function discoverOlder(a, b) {
  var x = a.split("."), y = b.split(".");
  for (var at = 0; at < Math.max(x.length, y.length); at++) {
    var difference = (parseInt(x[at], 10) || 0) - (parseInt(y[at], 10) || 0);
    if (difference) return difference < 0;
  }
  return false;
}

// A file's hash, the one git gives its contents, as the index lists it
async function discoverHash(bytes) {
  var head = new TextEncoder().encode("blob " + bytes.length + "\0");
  var whole = new Uint8Array(head.length + bytes.length);
  whole.set(head);
  whole.set(bytes, head.length);
  var digest = new Uint8Array(await crypto.subtle.digest("SHA-1", whole));
  return Array.from(digest, function (byte) { return byte.toString(16).padStart(2, "0"); }).join("");
}

// A lambda that finds a file on the drive by path, or null, reading each folder's list once
function discoverFinder() {
  var folders = {};
  function folder(path) {
    if (path in folders) return folders[path];
    folders[path] = (async function () {
      var parts = path ? path.split("/") : [];
      var handle = drive.dirHandle;
      if (parts.length) {
        var parent = await folder(parts.slice(0, -1).join("/"));
        if (!parent || !parent.folders[parts[parts.length - 1]]) return null;
        handle = parent.folders[parts[parts.length - 1]];
      }
      var listed = {files: {}, folders: {}};
      for await (var pair of handle.entries())
        listed[pair[1].kind === "file" ? "files" : "folders"][pair[0]] = pair[1];
      return listed;
    })();
    return folders[path];
  }
  return async function (path) {
    var listed = await folder(path.slice(0, Math.max(0, path.lastIndexOf("/"))));
    return listed ? listed.files[path.slice(path.lastIndexOf("/") + 1)] || null : null;
  };
}

// How a drive file compares with the index's: same, old where it matches an earlier version, or
// changed. A file that is not text is compared by its size, as reading every picture was most of a
// check's time, and a text file by its hash, also taken without Windows line endings, as a build
// from a Windows clone writes them
async function discoverCompare(file, handle) {
  var got = await handle.getFile();
  if (!/\.(py|txt)$/i.test(file.path)) {
    if (got.size === file.size) return "same";
    return file.was.some(function (one) { return one.size === got.size; }) ? "old" : "changed";
  }
  var bytes = new Uint8Array(await got.arrayBuffer());
  var hashes = [await discoverHash(bytes)];
  if (bytes.indexOf(13) >= 0) {
    hashes.push(await discoverHash(new TextEncoder().encode(
      new TextDecoder().decode(bytes).replace(/\r\n/g, "\n"))));
  }
  if (hashes.indexOf(file.hash) >= 0) return "same";
  return file.was.some(function (one) { return hashes.indexOf(one.hash) >= 0; }) ? "old"
                                                                                  : "changed";
}

// Where the drive has a file, at its path or one it was moved from, and how it compares
async function discoverFileState(file, find) {
  var places = [file.path].concat(file.moved_from || []);
  for (var place of places) {
    var handle = await find(place);
    if (handle) return {state: await discoverCompare(file, handle), at: place};
  }
  return {state: "missing", at: null};
}

// The index, fetched afresh
async function discoverIndex() {
  var answer;
  try {
    answer = await fetch(discoverFileUrl("index.json"), {cache: "no-store"});
  } catch (e) {
    throw new Error(DISCOVER_OFFLINE);
  }
  if (!answer.ok) throw new Error("Could not find the list of examples.");
  return await answer.json();
}

// Check every example of one tab against the drive, then fetch what the missing ones need to be
// shown.
//
// With quiet, after a check has been done, only the drive is read again, against the index already
// fetched, and what the last check found stays shown while it reads, its progress in refreshing
async function discoverCheck(kind, quiet) {
  var check = discover[kind];
  if (check.status === "checking" || check.refreshing || !drive.dirHandle) return;
  if (kind === "program" ? !EXAMPLES_ROOT : kind === "sound" ? !BOARD.sound : !SCREEN_PORTS.length)
    return;
  quiet = quiet && check.status === "done" && check.index;
  if (quiet) {
    check.refreshing = [0, 1];
  } else {
    check.status = "checking";
    check.progress = null;
    check.notice = null;
  }
  draw();
  try {
    var index = quiet ? check.index : await discoverIndex();
    var offered = index.examples.filter(function (entry) { return discoverTab(entry) === kind; });
    var files = [];
    offered.forEach(function (entry) {
      entry.files.forEach(function (file) {
        if (!files.some(function (one) { return one.path === file.path; })) files.push(file);
      });
    });
    var find = discoverFinder();
    var reading = [0, files.length];
    if (quiet) check.refreshing = reading;
    else check.progress = reading;
    for (var at = 0; at < files.length; at++) {
      discover.files[files[at].path] = await discoverFileState(files[at], find);
      reading[0] = at + 1;
      if (at % 20 === 19) draw();
    }
    Object.keys(discover.movedTo).forEach(function (old) {
      var moved = discoverEntry(discover.movedTo[old]);
      if (moved && discoverTab(moved) === kind) delete discover.movedTo[old];
    });
    offered.forEach(function (entry) {
      discover.states[entry.path] = discoverStateOf(entry);
      var own = discover.files[entry.files[0].path];
      if (discover.states[entry.path] === "moved") discover.movedTo[own.at] = entry.path;
      if (discoverOlder(DISCOVER_FIRMWARE, entry.firmware)) discover.newer[entry.path] = true;
      else delete discover.newer[entry.path];
    });
    var same = check.index === index;
    check.index = index;
    await discoverFetchMissing(kind, offered, same);
    check.status = "done";
  } catch (e) {
    check.status = "failed";
    check.error = await discoverTrouble(e);
  }
  check.progress = null;
  check.refreshing = null;
  draw();
}

// An example's state from its files': missing where its own file is, moved where the drive has
// it where it used to be kept, changed where the user changed any file, an update where any is
// old or missing, and current where every one is GitHub's
function discoverStateOf(entry) {
  var own = discover.files[entry.files[0].path];
  if (own.state === "missing") return "missing";
  if (own.at !== entry.files[0].path) return "moved";
  var states = entry.files.map(function (file) { return discover.files[file.path]; });
  if (states.some(function (one) { return one.state === "changed"; })) return "changed";
  return entry.files.every(function (file, at) {
    return states[at].state === "same" && states[at].at === file.path;
  }) ? "current" : "update";
}

// Fetch each missing example's source and thumbnail, four at a time, so it can be listed. With
// same, the index being the one the last check read, one it listed is kept as it was
async function discoverFetchMissing(kind, offered, same) {
  var missing = offered.filter(function (entry) { return discover.states[entry.path] === "missing"; });
  var listed = {};
  var before = same ? discoverListedOn(kind) : {};
  async function one(entry) {
    // One the last check listed is listed again as it was, without fetching it again
    if (before[entry.path]) {
      listed[entry.path] = before[entry.path];
      return;
    }
    try {
      // A picture is its own thumbnail, a slideshow its first, and the index names it
      if (entry.kind === "picture") {
        if (!discoverThumbs[entry.path]) {
          discoverThumbs[entry.path] = URL.createObjectURL(
            await (await fetch(discoverFileUrl(entry.files[0].path))).blob());
        }
        listed[entry.path] = {name: entry.path, kind: "picture", offered: true,
                              picture: {title: entry.name, section: entry.section,
                                        slideshow: entry.slideshow, count: entry.files.length}};
        return;
      }
      // A sound is known by its header alone, fetched as its first few bytes, which say how long
      // it plays. It is heard from GitHub as it is, unfetched
      if (entry.kind === "sound") {
        var head = await (await fetch(discoverFileUrl(entry.path),
                                      {headers: {Range: "bytes=0-4095"}})).arrayBuffer();
        listed[entry.path] = {name: entry.path, kind: "sound", offered: true,
                              sound: {title: entry.name, section: entry.section,
                                      seconds: discoverWavSeconds(head, entry.files[0].size),
                                      url: discoverFileUrl(entry.path)}};
        return;
      }
      var source = await (await fetch(discoverFileUrl(entry.path))).text();
      var stem = entry.path.replace(/\.py$/i, "");
      // Its thumbnail, and a second screen's beside it where it has one
      for (var suffix of [".png", "-2.png"]) {
        var held = suffix === ".png" ? discoverThumbs : discoverSecondThumbs;
        var thumb = entry.files.filter(function (file) { return file.path === stem + suffix; })[0];
        if (thumb && !held[entry.path]) {
          var blob = await (await fetch(discoverFileUrl(thumb.path))).blob();
          held[entry.path] = URL.createObjectURL(blob);
        }
      }
      if (kind === "program") {
        var folder = entry.path.slice(EXAMPLES_ROOT.length, entry.path.lastIndexOf("/"));
        var program = programFrom(entry.path, folder, source);
        if (program) {
          program.offered = true;
          listed[entry.path] = program;
        }
      } else {
        var drawing = discoverKinds.drawing && discoverKinds.drawing.said(source);
        if (drawing) listed[entry.path] = {name: entry.path, kind: "drawing", drawing: drawing,
                                           offered: true};
      }
    } catch (e) {
      // One that will not fetch is left out of this check
    }
  }
  for (var at = 0; at < missing.length; at += 4) await Promise.all(missing.slice(at, at + 4).map(one));
  if (kind === "program") {
    discoverPrograms = listed;
    // Their thumbnails decoded ahead, as the program tab's are, to be drawn whole the first time
    var urls = [];
    Object.keys(listed).forEach(function (path) { urls = urls.concat(discoverPicturesOf(path)); });
    loadThumbs(urls);
  } else if (kind === "sound") {
    discoverSounds = listed;
  } else {
    discoverDrawings = listed;
  }
}

// A missing program's pictures, as the program tab holds a program's: its own, and a second
// screen's after it
function discoverPicturesOf(path) {
  return discoverThumbs[path] ? [discoverThumbs[path]].concat(discoverSecondThumbs[path] || []) : [];
}

// How many seconds a WAV file plays, from its first bytes and its whole size, as the Sound tab
// reads a sound on the drive, or 0 where its header does not say
function discoverWavSeconds(head, size) {
  var view = new DataView(head);
  if (view.byteLength < 12 || view.getUint32(0) !== 0x52494646 || view.getUint32(8) !== 0x57415645)
    return 0;
  var at = 12, byteRate = 0;
  while (at + 8 <= view.byteLength) {
    var id = view.getUint32(at), length = view.getUint32(at + 4, true);
    if (id === 0x666d7420) byteRate = view.getUint32(at + 16, true);  // "fmt "
    else if (id === 0x64617461)                                         // "data"
      return byteRate ? Math.max(1, Math.round(Math.min(length, size - at - 8) / byteRate)) : 0;
    at += 8 + length + (length % 2);
  }
  return 0;
}

// The tab an example is offered on and checked from: a program on the program tab, a sound on the
// Sound tab, and a drawing or a picture on the Screens tab, as "drawing"
function discoverTab(entry) {
  return entry.kind === "program" || entry.kind === "sound" ? entry.kind : "drawing";
}

// Every tab with examples to offer, and what each calls them
var DISCOVER_TABS = ["program", "drawing", "sound"];
var DISCOVER_WORDS = {program: "programs", drawing: "pictures and drawings", sound: "sounds"};

// What a tab's examples are called, "more" before them only where the drive holds some already
function discoverAsked(kind) {
  var held = kind === "program"
    ? PROGRAMS.some(function (program) { return program.example; })
    : kind === "sound" ? state.sounds.some(isExampleMedia)
    : state.media.some(function (media) { return !media.offered && isExampleMedia(media.name); });
  return (held ? "more example " : "example ") + DISCOVER_WORDS[kind];
}

// The examples a tab's last check found missing, by path
function discoverListedOn(kind) {
  return kind === "program" ? discoverPrograms : kind === "sound" ? discoverSounds : discoverDrawings;
}

// The index entry at a path, from whichever check last read it
function discoverEntry(path) {
  var found = null;
  DISCOVER_TABS.forEach(function (kind) {
    var index = discover[kind].index;
    if (!found && index) found = index.examples.filter(function (entry) {
      return discoverTab(entry) === kind && entry.path === path;
    })[0] || null;
  });
  return found;
}

// The example a card stands for, the path it has now for one the drive keeps where it used to be
function discoverTarget(path) {
  return discover.movedTo[path] || path;
}

// Write a file to the drive, making its folders
async function discoverWrite(path, blob) {
  var parts = path.split("/");
  var name = parts.pop();
  var folder = drive.dirHandle;
  for (var at = 0; at < parts.length; at++)
    folder = await folder.getDirectoryHandle(parts[at], {create: true});
  var writable = await (await folder.getFileHandle(name, {create: true})).createWritable();
  await writable.write(blob);
  await writable.close();
}

// Delete a file from the drive, where it is still there
async function discoverRemove(path) {
  var parts = path.split("/");
  var name = parts.pop();
  var folder = await folderAt(drive.dirHandle, parts);
  if (folder) await folder.removeEntry(name);
}

// Download an example, or its update, writing only the files that differ from the index's, and
// deleting those left where it used to be kept. A program downloaded new is chosen, as a tapped
// card is. Returns false where it failed, else where the user's changed copy was kept or true.
// With quiet, one of several, only a failure is said and nothing is chosen
async function discoverDownload(path, quiet) {
  var entry = discoverEntry(path);
  if (!entry || discover.busy[path] || discover.newer[path]) return false;
  var tab = discoverTab(entry);
  discover.busy[path] = true;
  if (!quiet) discoverSay(tab, "Downloading " + nameShown(path) + "...", "hold");
  draw();
  var fresh = discover.states[path] === "missing";
  var own = discover.files[entry.files[0].path];
  var was = own.at;
  var kept = null;
  try {
    // The user's changes are kept as their own copy, as Customise makes one. A picture or sound
    // has no Customise, so a changed one is replaced
    if (own.state === "changed" && (entry.kind === "program" || entry.kind === "drawing"))
      kept = entry.kind === "program" ? await copyProgram(was) : "drawings/" + await discoverKinds.drawing.copy(was);
    var written = {};
    for (var file of entry.files) {
      var held = discover.files[file.path];
      if (held.state === "same" && held.at === file.path) continue;
      var blob = await (await fetch(discoverFileUrl(file.path))).blob();
      if (await discoverHash(new Uint8Array(await blob.arrayBuffer())) !== file.hash)
        throw new Error("The downloaded file did not match. Try again.");
      await discoverWrite(file.path, blob);
      written[file.path] = blob;
    }
    // What was left where the example used to be kept goes, now it is in its new place
    for (file of entry.files) {
      held = discover.files[file.path];
      if (held.at && held.at !== file.path) await discoverRemove(held.at);
      discover.files[file.path] = {state: "same", at: file.path};
    }
    if (was && was !== path) delete discover.movedTo[was];
    discover.states[path] = "current";
    await discoverListed(entry, written, fresh && !quiet, was);
    if (!quiet) {
      discoverSay(tab, (fresh ? "Downloaded " : "Updated ") + nameShown(path) + "." +
                (kept ? " Your changed copy is kept as " + kept + "." : ""));
    }
    var done = kept || true;
  } catch (e) {
    discoverSay(tab, "Could not download " + nameShown(path) + ". " + await discoverTrouble(e),
              true);
    done = false;
  }
  delete discover.busy[path];
  draw();
  return done;
}

// List a downloaded example as the drive's own: a program from the source just written, without
// reading every program again, and a drawing by reading the drive until the gallery has it. A
// program moved from where it was kept takes its place, chosen where that was
async function discoverListed(entry, written, fresh, was) {
  var path = entry.path;
  if (entry.kind === "program") {
    var stem = path.replace(/\.py$/i, "");
    var source = written[path] ? await written[path].text()
      : await (await (await (await folderAt(drive.dirHandle, path.split("/").slice(0, -1)))
          .getFileHandle(nameShown(path))).getFile()).text();
    var folder = path.slice(EXAMPLES_ROOT.length, path.lastIndexOf("/"));
    var program = programFrom(path, folder, source);
    PROGRAMS = PROGRAMS.filter(function (one) { return one.path !== path && one.path !== was; });
    if (program) PROGRAMS.push(program);
    delete discoverPrograms[path];
    var shown = [stem + ".png", stem + "-2.png"].filter(function (name) { return written[name]; })
      .map(function (name) { return URL.createObjectURL(written[name]); });
    if (shown.length) {
      PICTURES[path] = shown;
      loadThumbs(shown);
    } else if (was && PICTURES[was]) {
      PICTURES[path] = PICTURES[was];
    }
    if (was && was !== path) {
      delete PICTURES[was];
      if (boardSet.program === was) boardSet.program = path;
      if (boardSet.args[was]) {
        boardSet.args[path] = boardSet.args[was];
        delete boardSet.args[was];
      }
    }
    if (fresh && program) boardSet.program = path;
    return;
  }
  delete discoverDrawings[path];
  delete discoverSounds[path];
  delete state.art[path];
  for (var tries = 0; tries < 20; tries++) {
    await scanMedia(state.dirHandle);
    if (discoverKinds[entry.kind].onDrive(path)) return;
    await new Promise(function (settle) { setTimeout(settle, 100); });
  }
}

// Download every update of one kind in turn, counting them in, and stopping at one that fails
async function discoverUpdateAll(kind) {
  var paths = discoverUpdates(kind);
  var kept = [];
  for (var at = 0; at < paths.length; at++) {
    discover[kind].updating = [at, paths.length];
    discoverSay(kind, "Updating " + (at + 1) + " of " + paths.length + "...", "hold");
    var done = await discoverDownload(paths[at], true);
    if (!done) {
      discover[kind].updating = null;
      draw();
      return;
    }
    if (done !== true) kept.push(done);
  }
  discover[kind].updating = null;
  discoverSay(kind, "Updated " + paths.length + (paths.length === 1 ? " example." : " examples.") +
            (kept.length === 1 ? " Your changed copy is kept as " + kept[0] + "."
             : kept.length ? " Your changed copies are kept as " + kept.join(", ") + "." : ""));
  draw();
}

var DISCOVER_UPDATES = ["update", "changed", "moved"];

function discoverUpdates(kind) {
  return Object.keys(discover.states).filter(function (path) {
    var entry = discoverEntry(path);
    return entry && discoverTab(entry) === kind && !discover.newer[path] &&
           DISCOVER_UPDATES.indexOf(discover.states[path]) >= 0;
  });
}

// ---- the check's line, where each gallery's examples start ---------------------------------------

function discoverButton(label, press) {
  var button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.onclick = press;
  return button;
}

var DISCOVER_ICONS = {
  get: "<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M7 18.5h-.5a4.5 4.5 0 0 1-.6-8.96 " +
       "6 6 0 0 1 11.6-1.3A5 5 0 0 1 17.5 18.5H17 M12 11v8 M9 16l3 3 3-3' fill='none' " +
       "stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>",
  done: "<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M5 12.5l4.5 4.5L19 7.5' fill='none' " +
        "stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'/></svg>",
  warn: "<svg viewBox='0 0 24 24' aria-hidden='true'><path d='M12 4v10 M12 19v.5' fill='none' " +
        "stroke='currentColor' stroke-width='2.4' stroke-linecap='round'/></svg>"
};

function discoverIcon(name, className) {
  var icon = document.createElement("span");
  icon.className = className;
  icon.innerHTML = DISCOVER_ICONS[name];
  return icon;
}

export function discoverElement(tag, className, text) {
  var made = document.createElement(tag);
  made.className = className;
  if (text) made.textContent = text;
  return made;
}

// What a check found of one kind: the examples to download, the updates, and how many need newer
// firmware
function discoverFound(kind) {
  var listed = discoverListedOn(kind);
  return {
    waiting: Object.keys(listed).filter(function (path) { return !discover.newer[path]; }),
    updates: discoverUpdates(kind),
    newer: Object.keys(discover.newer).filter(function (path) {
      var entry = discoverEntry(path);
      return entry && discoverTab(entry) === kind && discover.states[path] !== "current";
    }).length
  };
}

function discoverCount(count, one, many) {
  return count + " " + (count === 1 ? one : many);
}

// A bar filling as far as [done, of] has got
function discoverProgress(at) {
  var bar = discoverElement("div", "discoverprogress");
  var fill = discoverElement("span", "");
  fill.style.width = (at ? Math.round(100 * at[0] / Math.max(1, at[1])) : 8) + "%";
  bar.appendChild(fill);
  return bar;
}

// What the last download said, marked done, under way or failed
function discoverNotice(check) {
  if (!check.notice) return null;
  var warn = check.notice[1];
  var notice = discoverElement("div", "discovernotice" + (warn === "hold" ? " hold" : warn ? " warn" : ""));
  if (warn !== "hold") notice.appendChild(discoverIcon(warn ? "warn" : "done", "discovermark"));
  notice.appendChild(document.createTextNode(check.notice[0]));
  return notice;
}

// A missing example's thumbnail, taken away where it will not load, so its dark ground shows
export function discoverThumbImage(path) {
  var img = document.createElement("img");
  img.alt = "";
  img.onerror = function () { img.remove(); };
  img.src = discoverThumbs[path];
  return img;
}

// Where a tab's examples start, a rule naming them, over the Discover button and the line under it
function discoverBar(kind) {
  var bar = discoverElement("div", "discoverbar");
  bar.appendChild(discoverDivider("Examples"));
  bar.appendChild(discoverPanel(kind));
  return bar;
}

// Put a tab's examples line where its examples start, after the user's own group, which always
// heads a tab's groups, or at the end where no example is listed
export function discoverPlaceBar(box, kind) {
  var bar = discoverBar(kind);
  var heads = box.querySelectorAll(".foldhead");
  if (heads.length > 1) box.insertBefore(bar, heads[1]);
  else box.appendChild(bar);
}

// ---- the gallery: the examples the drive lacks, over the page ----------------------------------

// The kind of example whose gallery is open, or null, the examples chosen in it, the one a Shift
// press counts a run from, the section it shows, "" for all of them, and how far downloading the
// chosen has got, as [downloaded, of], while it runs
var discoverBrowsing = null;
var discoverChosen = [];
var discoverAnchor = null;
var discoverSection = "";
var discoverFetching = null;

// The colour of each kind's gallery, its tab's own
var DISCOVER_INK = {program: "var(--board)", drawing: "var(--accent)", sound: "var(--accent)"};

// The Discover button, the width of the tab, with a count of the examples it holds to download
// once checked, and the line for updates under it
function discoverPanel(kind) {
  var check = discover[kind];
  var panel = discoverElement("div", "discoverpanel");
  panel.style.setProperty("--discover", DISCOVER_INK[kind]);
  var found = check.status === "done" ? discoverFound(kind) : null;
  var open = discoverElement("button", "discoverwide");
  open.type = "button";
  open.appendChild(discoverIcon("get", "discoverwideicon"));
  open.appendChild(document.createTextNode("Discover " + discoverAsked(kind)));
  if (found && found.waiting.length)
    open.appendChild(discoverElement("span", "discovercountchip", String(found.waiting.length)));
  open.onclick = function () { discoverOpenBrowser(kind); };
  panel.appendChild(open);
  panel.appendChild(discoverUpdateRow(kind, check, found));
  return panel;
}

// The line under Discover for the examples on the drive, one height whatever it says: what the
// check found, or what a download says while it runs and a while after, a progress bar right of
// it while anything runs, and Update all and Check for updates always in place, greyed where they
// cannot be pressed. The examples on the drive are checked for updates without opening the gallery
function discoverUpdateRow(kind, check, found) {
  var row = discoverElement("div", "discoverupdaterow");
  var said = discoverElement("span", "discoverrowsaid");
  var running = check.status === "checking" ? check.progress || [0, 1]
              : check.updating || discoverFetching || check.refreshing;
  var busy = check.status === "checking" || running ||
             (check.notice && check.notice[1] === "hold");
  if (check.status === "idle") {
    said.textContent = "Check the examples on the drive for newer versions.";
  } else if (check.status === "checking") {
    said.textContent = "Checking for updates...";
  } else if (check.status === "failed") {
    said.textContent = check.error || DISCOVER_OFFLINE;
    said.classList.add("discoverwarn");
  } else {
    said.textContent = found.updates.length
      ? discoverCount(found.updates.length, "update", "updates") + " for examples on the drive."
      : "The examples on the drive are up to date.";
    var notice = discoverNotice(check);
    if (notice) said = notice;
  }
  said.classList.add("discoverrowsaid");
  row.appendChild(said);
  var progress = discoverProgress(running || null);
  if (!running) progress.classList.add("discoveridle");
  row.appendChild(progress);
  var update = discoverButton("Update all", function () { discoverUpdateAll(kind); });
  update.className = "discoverprimary";
  update.disabled = busy || !found || !found.updates.length;
  row.appendChild(update);
  var again = discoverButton("Check for updates", function () { discoverCheck(kind); });
  again.disabled = !!busy;
  row.appendChild(again);
  return row;
}

// Open a kind's gallery, checking GitHub first where it has not been
function discoverOpenBrowser(kind) {
  discoverBrowsing = kind;
  discoverChosen = [];
  discoverAnchor = null;
  discoverSection = "";
  // Every opening reads the drive again, so an example deleted since is offered, quietly where a
  // check has been done
  discoverCheck(kind, true);
  draw();
}

function discoverCloseBrowser() {
  discoverBrowsing = null;
  draw();
}

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && discoverBrowsing) discoverCloseBrowser();
});

// The examples a gallery offers, as [path, name, what it does, section], in name order
function discoverOffers(kind) {
  var listed = discoverListedOn(kind);
  return Object.keys(listed).map(function (path) {
    var held = listed[path];
    if (kind === "program")
      return [path, programTitle(path), held.does || "", held.section || "", "program"];
    if (kind === "sound") {
      return [path, held.sound.title, held.sound.seconds ? held.sound.seconds + "s" : "",
              held.sound.section || OTHER_EXAMPLES.sounds, "sound"];
    }
    // A drawing or picture in no section is in the Screens tab's group for the rest of its kind
    if (held.kind === "picture") {
      return [path, held.picture.title, discoverPictureSaid(held.picture),
              held.picture.section || OTHER_EXAMPLES.pictures, "picture"];
    }
    return [path, held.drawing.title, held.drawing.description || "",
            held.drawing.section || OTHER_EXAMPLES.drawings, "drawing"];
  }).sort(function (a, b) {
    // Numbers in names counted, so name 2 comes before name 10, as the program tab sorts them
    return a[1].localeCompare(b[1], undefined, {numeric: true});
  });
}

// A rule with words in it: "Examples" in its middle where a tab's examples start, and with minor,
// a kind's name at its left where the Screens tab's drawings or pictures start within them
export function discoverDivider(words, minor) {
  var rule = discoverElement("div", "discoverdivide" + (minor ? " minor" : ""));
  rule.appendChild(discoverElement("span", "", words));
  return rule;
}

// The kind of example a gallery section holds, "picture" or another, from the offers in it
function discoverSectionKind(offers, section) {
  return offers.some(function (offer) { return offer[3] === section && offer[4] === "picture"; })
    ? "picture" : "drawing";
}

// Whether a gallery section is shown under the filter chosen: every section, one section, or
// with "kind:" every section of one kind
function discoverShows(offers, section) {
  if (!discoverSection) return true;
  if (discoverSection.indexOf("kind:") === 0)
    return discoverSectionKind(offers, section) === discoverSection.slice(5);
  return section === discoverSection;
}

// What a picture is, in place of the description a drawing gives
export function discoverPictureSaid(picture) {
  if (picture.slideshow) return "A slideshow of " + picture.count + " pictures.";
  return "A " + picture.title.slice(picture.title.lastIndexOf(".") + 1).toUpperCase() + " picture.";
}

// The sections the offers fall in, drawings' before pictures', each kind's in the order its
// sections.txt gives them, then any it does not list by name, and those naming none last, as ""
function discoverSections(kind, offers) {
  function names(sections) {
    return (sections || []).map(function (one) { return one[0]; });
  }
  var listed = kind === "program" ? names(SECTIONS)
    : kind === "sound" ? names(exampleSections.sounds).concat([OTHER_EXAMPLES.sounds])
    : names(exampleSections.drawings).concat([OTHER_EXAMPLES.drawings],
                                            names(exampleSections.pictures), [OTHER_EXAMPLES.pictures]);
  var named = [];
  offers.forEach(function (offer) {
    if (named.indexOf(offer[3]) < 0) named.push(offer[3]);
  });
  function pictured(section) {
    return offers.some(function (offer) { return offer[3] === section && offer[4] === "picture"; });
  }
  return named.sort(function (a, b) {
    if (pictured(a) !== pictured(b)) return pictured(a) ? 1 : -1;
    if (!a || !b) return a ? -1 : b ? 1 : 0;
    var x = listed.indexOf(a), y = listed.indexOf(b);
    if (x < 0 || y < 0) return x < 0 && y < 0 ? a.localeCompare(b) : x < 0 ? 1 : -1;
    return x - y;
  });
}

// Choose an example from a press on its card, as a file manager does. A plain press chooses it
// alone, or none where it was the only one chosen. Its box, or a press with Ctrl, adds it to those
// chosen or takes it away. A press with Shift chooses every example from the last one pressed to
// it, in the order shown
function discoverChoose(path, e, toggle, shown) {
  e = e || {};
  if (e.shiftKey && discoverAnchor && shown.indexOf(discoverAnchor) >= 0) {
    var from = shown.indexOf(discoverAnchor), to = shown.indexOf(path);
    shown.slice(Math.min(from, to), Math.max(from, to) + 1).forEach(function (one) {
      if (discoverChosen.indexOf(one) < 0 && !discover.newer[one]) discoverChosen.push(one);
    });
    draw();
    return;
  }
  if (toggle || e.ctrlKey || e.metaKey) {
    var at = discoverChosen.indexOf(path);
    if (at < 0) discoverChosen.push(path);
    else discoverChosen.splice(at, 1);
  } else {
    discoverChosen = discoverChosen.length === 1 && discoverChosen[0] === path ? [] : [path];
  }
  discoverAnchor = path;
  draw();
}

// Download every chosen example in turn, choosing none of them on the program tab, unless only one
// was chosen, and stopping at one that fails
async function discoverDownloadChosen(kind) {
  var paths = discoverChosen.slice();
  if (paths.length === 1) {
    await discoverDownload(paths[0]);
    discoverChosen = [];
    draw();
    return;
  }
  for (var at = 0; at < paths.length; at++) {
    discoverFetching = [at, paths.length];
    discoverSay(kind, "Downloading " + (at + 1) + " of " + paths.length + "...", "hold");
    var done = await discoverDownload(paths[at], true);
    discoverChosen = discoverChosen.filter(function (one) { return one !== paths[at]; });
    if (!done) {
      discoverFetching = null;
      draw();
      return;
    }
  }
  discoverFetching = null;
  discoverSay(kind, "Downloaded " + discoverCount(paths.length, "example.", "examples."));
  draw();
}

drawSteps.after.push(discoverRenderBrowser);

// The gallery over the page: a way back, the section shown, a card for each example under its
// section's name, and a bar at its foot saying what is chosen, with Download
function discoverRenderBrowser() {
  var old = document.getElementById("discoverbrowser");
  var scrolled = old ? old.querySelector(".discoverscroll").scrollTop : 0;
  if (old) old.remove();
  document.body.classList.toggle("discovermodal", !!discoverBrowsing);
  if (!discoverBrowsing) return;
  var kind = discoverBrowsing;
  var check = discover[kind];
  var shade = discoverElement("div", "discovershade");
  shade.style.setProperty("--discover", DISCOVER_INK[kind]);
  shade.id = "discoverbrowser";
  shade.onclick = function (e) { if (e.target === shade) discoverCloseBrowser(); };
  var sheet = discoverElement("div", "discoversheet");
  shade.appendChild(sheet);

  var head = discoverElement("div", "discoversheethead");
  var back = discoverButton("\u2039 Back", discoverCloseBrowser);
  head.appendChild(back);
  var asked = discoverAsked(kind);
  head.appendChild(discoverElement("h2", "", asked.charAt(0).toUpperCase() + asked.slice(1)));
  sheet.appendChild(head);

  var every = check.status === "done" ? discoverOffers(kind) : [];
  // Programs are shown by what is to hand, as the program tab shows them, its chips repeated here
  // and changing both
  var offers = kind === "program" ? every.filter(function (offer) {
    return passesFilter(offer[0]);
  }) : every;
  var chips = kind === "program" ? discoverChips(every) : null;
  if (chips) sheet.appendChild(chips);
  var sections = discoverSections(kind, offers).filter(Boolean);
  // Both kinds offered, the filter groups the sections by kind, each group led by the whole kind
  var kinds = kind === "program" ? [] : ["drawing", "picture"].filter(function (one) {
    return sections.some(function (section) { return discoverSectionKind(offers, section) === one; });
  });
  var grouped = kinds.length > 1;
  var choices = grouped ? kinds.map(function (one) { return "kind:" + one; }) : [];
  if (discoverSection && sections.indexOf(discoverSection) < 0 && choices.indexOf(discoverSection) < 0)
    discoverSection = "";
  discoverChosen = discoverChosen.filter(function (path) {
    return offers.some(function (offer) { return offer[0] === path; });
  });
  var choose = document.createElement("select");
  choose.className = "discoverfilter";
  function choice(into, value, words) {
    var option = document.createElement("option");
    option.value = value;
    option.textContent = words + " (" + offers.filter(function (offer) {
      return !value || (value.indexOf("kind:") === 0
        ? discoverSectionKind(offers, offer[3]) === value.slice(5) : offer[3] === value);
    }).length + ")";
    option.selected = value === discoverSection;
    into.appendChild(option);
  }
  choice(choose, "", "All");
  if (grouped) {
    kinds.forEach(function (one) {
      var group = document.createElement("optgroup");
      group.label = one === "picture" ? "Pictures" : "Drawings";
      choice(group, "kind:" + one, one === "picture" ? "All pictures" : "All drawings");
      sections.forEach(function (section) {
        if (discoverSectionKind(offers, section) === one) choice(group, section, section);
      });
      choose.appendChild(group);
    });
  } else {
    sections.forEach(function (section) { choice(choose, section, section); });
  }
  choose.onchange = function () {
    discoverSection = choose.value;
    draw();
  };
  if (offers.length) head.appendChild(choose);

  // The cards scroll in a box of their own, so a long gallery keeps its head and foot in view
  var scroll = discoverElement("div", "discoverscroll");
  sheet.appendChild(scroll);
  if (check.status !== "done") {
    // Checking, or failed, said in the middle of the gallery
    var waiting = discoverElement("div", "discoverwaiting");
    waiting.appendChild(discoverElement("p", "", check.status === "failed"
      ? check.error || DISCOVER_OFFLINE : "Checking for examples..."));
    if (check.status !== "failed") waiting.appendChild(discoverProgress(check.progress));
    scroll.appendChild(waiting);
  } else if (!offers.length) {
    // An index with none of this kind has none to offer yet, as with sounds before any ship
    var any = check.index.examples.some(function (entry) { return discoverTab(entry) === kind; });
    scroll.appendChild(discoverElement("div", "discoverwaiting", every.length
      ? "Every example here needs hardware that is not ticked."
      : any ? "The drive has every example."
      : "There are no example " + DISCOVER_WORDS[kind] + " yet."));
  }
  var shown = [];
  var listed = discoverSections(kind, offers).filter(function (section) {
    return discoverShows(offers, section);
  });
  // Drawings and pictures both shown each start under a rule naming them, as the Screens tab does
  var named = kind !== "program" && listed.some(function (section) {
    return discoverSectionKind(offers, section) === "picture";
  }) && listed.some(function (section) {
    return discoverSectionKind(offers, section) !== "picture";
  });
  var lastKind = null;
  listed.forEach(function (section) {
    var held = offers.filter(function (offer) { return offer[3] === section; });
    var sectionKind = discoverSectionKind(offers, section);
    if (named && sectionKind !== lastKind)
      scroll.appendChild(discoverDivider(sectionKind === "picture" ? "Pictures" : "Drawings", true));
    lastKind = sectionKind;
    // Where more than one section is shown, each is named over its own cards
    if (listed.length > 1)
      scroll.appendChild(discoverElement("h3", "discoverhead", section || "Other examples"));
    // The grid each tab lays its own cards in
    var grid = discoverElement("div", "discovergrid proggrid" + (kind === "program" ? ""
      : kind === "sound" ? " discoversounds" : " discoverdrawings"));
    held.forEach(function (offer) {
      shown.push(offer[0]);
      grid.appendChild(discoverOfferCard(offer, shown));
    });
    scroll.appendChild(grid);
  });

  var foot = discoverElement("div", "discoversheetfoot");
  var footSays = discoverElement("div", "discoverfootsays");
  var chosen = offers.filter(function (offer) { return discoverChosen.indexOf(offer[0]) >= 0; });
  var busy = discoverFetching || check.refreshing ||
             chosen.some(function (offer) { return discover.busy[offer[0]]; });
  var notice = discoverNotice(check);
  if (notice && (!chosen.length || busy)) footSays.appendChild(notice);
  else if (chosen.length === 1) footSays.appendChild(discoverElement("b", "", chosen[0][1]));
  else if (chosen.length) footSays.appendChild(discoverElement("b", "",
    discoverCount(chosen.length, "example", "examples") + " chosen"));
  else if (check.refreshing) footSays.appendChild(discoverElement("span", "discoverhint",
    "Checking the drive for changes..."));
  else if (offers.length) footSays.appendChild(discoverElement("span", "discoverhint",
    "Choose an example to download. Tick its box to choose more than one."));
  if (discoverFetching || check.refreshing)
    footSays.appendChild(discoverProgress(discoverFetching || check.refreshing));
  foot.appendChild(footSays);
  if (chosen.length > 1 && !busy) {
    foot.appendChild(discoverButton("Clear", function () {
      discoverChosen = [];
      draw();
    }));
  }
  var downloading = busy && !check.refreshing;
  var get = discoverButton(downloading ? "Downloading..." : chosen.length > 1
                         ? "Download " + chosen.length : "Download",
                         function () { discoverDownloadChosen(kind); });
  get.className = "discoverprimary";
  get.disabled = !chosen.length || !!busy;
  foot.appendChild(get);
  sheet.appendChild(foot);
  document.body.appendChild(shade);
  // Only once in the page can the gallery be scrolled back to where it was
  scroll.scrollTop = scrolled;
}

// A program as its tab shows it, its thumbnail, or both screens' side by side, with what it uses
// along the thumbnail's foot, over its name, less its tab's buttons. What it does follows its
// name, since here it is being chosen unseen
function discoverProgramFace(path) {
  // The tab's card draws a program's pictures from PICTURES, which holds only the drive's, so the
  // missing program's are lent to it while it is made
  PICTURES[path] = discoverPicturesOf(path);
  var tabCard = programCard(path);
  delete PICTURES[path];
  var card = discoverElement("div", "progcard discoveroffer");
  var thumb = discoverElement("div", "discoverthumbwrap");
  card.appendChild(thumb);
  Array.from(tabCard.childNodes).forEach(function (part) {
    if (!part.classList || part.classList.contains("copytile") || part.classList.contains("bin"))
      return;
    (part.classList.contains("progname") ? card : thumb).appendChild(part);
  });
  card.appendChild(discoverElement("span", "discoverdoes", (programNamed(path) || {}).does || ""));
  card.title = tabCard.title;
  return card;
}

// An example as a card in the gallery, looking as it does in its own tab, its box ticked while it
// is chosen. shown is every card's path in the order shown, a Shift press counting a run along it
function discoverOfferCard(offer, shown) {
  var path = offer[0];
  var chosen = discoverChosen.indexOf(path) >= 0;
  var card = discoverBrowsing === "program" ? discoverProgramFace(path)
           : discoverKinds[discoverBrowsing].face(path);
  if (chosen) card.classList.add("picked");
  if (discover.newer[path]) card.classList.add("newer");
  card.dataset.path = path;
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-pressed", chosen);
  if (!discover.newer[path]) {
    var box = document.createElement("input");
    box.type = "checkbox";
    box.className = "discovertick";
    box.checked = chosen;
    box.title = "Choose " + offer[1];
    box.onclick = function (e) {
      e.stopPropagation();
      discoverChoose(path, e, true, shown);
    };
    card.appendChild(box);
  }
  if (discover.newer[path]) {
    var needs = discoverElement("span", "discoverpill newer", "Needs " + discoverEntry(path).firmware);
    needs.title = "Needs " + BOARD.name + " firmware " + discoverEntry(path).firmware + " or newer.";
    card.appendChild(needs);
  }
  card.onclick = function (e) {
    if (!discover.newer[path]) discoverChoose(path, e, false, shown);
  };
  card.onkeydown = function (e) {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      card.onclick(e);
    }
  };
  return card;
}

// A small mark in a card's corner: a download arrow, Update, or the firmware it needs
export function discoverPill(cardPath) {
  var path = discoverTarget(cardPath);
  var entry = discoverEntry(path);
  if (!entry || discover[discoverTab(entry)].status !== "done") return null;
  var pill = document.createElement("span");
  pill.className = "discoverpill";
  if (discover.busy[path]) {
    pill.textContent = "...";
    pill.title = "Downloading";
  } else if (discover.newer[path] && discover.states[path] !== "current") {
    pill.textContent = "Needs " + entry.firmware;
    pill.className += " newer";
    pill.title = "Needs " + BOARD.name + " firmware " + entry.firmware + " or newer.";
  } else if (discover.states[path] === "missing") {
    pill.innerHTML = "<svg width='11' height='11' viewBox='0 0 11 11' aria-hidden='true'><path " +
                     "d='M5.5 1 L5.5 7.5 M2.5 4.8 L5.5 7.8 L8.5 4.8 M1.5 9.8 L9.5 9.8' " +
                     "stroke='currentColor' stroke-width='1.6' fill='none' " +
                     "stroke-linecap='round' stroke-linejoin='round'/></svg>";
    pill.title = "Download";
  } else if (DISCOVER_UPDATES.indexOf(discover.states[path]) >= 0) {
    pill.textContent = "Update";
    pill.className += " update";
    pill.title = discover.files[entry.files[0].path].state === "changed"
      ? "Download the newer version. Your changed copy is kept."
      : "Download the newer version.";
    pill.onclick = function (e) {
      e.stopPropagation();
      discoverDownload(path);
    };
  } else {
    return null;
  }
  return pill;
}

// ---- the program tab ----------------------------------------------------------------------------

// A program the gallery offers is known by its path, as the drive's are, for its card and its uses
programsElsewhere.push(function (path) { return discoverPrograms[path] || null; });

// An example program on the drive can be deleted, as it can be downloaded again, and carries its
// mark, Update or the firmware it needs. A card the gallery makes is for a program not on the drive
programCardSteps.push(function (card, path) {
  var own = PROGRAMS.filter(function (one) { return one.path === path; })[0];
  if (!own) return;
  if (discover.busy[discoverTarget(path)]) card.classList.add("discoverbusy");
  if (own.example && drive.dirHandle) discoverBinBeside(card, discoverBin(path, "program"));
  var pill = discoverPill(path);
  if (pill) card.appendChild(pill);
});

// The examples line goes where the example programs start, once they are listed, on a board whose
// drive keeps example programs
programViewSteps.push(function () {
  if (EXAMPLES_ROOT) discoverPlaceBar(programView, "program");
});

// ---- what is to hand, in the program gallery ----------------------------------------------------

// The program tab's "With:" chips for the things the gallery's programs use, each turned on or off
// for both, with all and none beside them
function discoverChips(offers) {
  var used = FEATURES.filter(function (feature) {
    return CHIPLESS.indexOf(feature[0]) < 0 && offers.some(function (offer) {
      return usesOf(offer[0]).indexOf(feature[0]) >= 0;
    });
  });
  if (!used.length) return null;
  var row = discoverElement("div", "featurefilter discoverchips");
  row.appendChild(discoverElement("span", "", "With:"));
  used.forEach(function (feature) {
    var chip = discoverElement("button", "featurechip" + (had(feature[0]) ? " on" : ""));
    chip.type = "button";
    chip.dataset.feature = feature[0];
    chip.title = had(feature[0]) ? "Showing programs that use " + feature[1]
                                 : "Hiding programs that need " + feature[1];
    chip.appendChild(featureIcon(feature[0]));
    chip.appendChild(document.createTextNode(feature[2]));
    chip.onclick = function () {
      var at = unhad.indexOf(feature[0]);
      if (at >= 0) unhad.splice(at, 1);
      else unhad.push(feature[0]);
      draw();
    };
    row.appendChild(chip);
  });
  var clears = discoverElement("div", "featureclears");
  [["all", function () { return unhad.filter(function (key) {
     return !used.some(function (feature) { return feature[0] === key; });
   }); }],
   ["none", function () { return unhad.concat(used.map(function (feature) { return feature[0]; })); }]]
    .forEach(function (one) {
      var choice = discoverButton(one[0], function () {
        unhad = one[1]();
        draw();
      });
      choice.className = "featureclear";
      clears.appendChild(choice);
    });
  row.appendChild(clears);
  return row;
}

// ---- deleting an example ------------------------------------------------------------------------
// An example can now be downloaded again, so each on the drive has a bin as the user's own do. A
// Python file goes with the thumbnails named after it, and a slideshow with its folder. Any picture
// it shares with others is left. The galleries are read again so it is offered at once

export function discoverBin(path, kind) {
  var bin = discoverElement("span", "bin", "\u00d7");
  bin.setAttribute("role", "button");
  bin.title = "Delete " + nameShown(path) + " from the FX drive";
  bin.onclick = function (e) {
    e.stopPropagation();
    discoverDelete(path, kind);
  };
  return bin;
}

async function discoverDelete(path, kind) {
  var name = nameShown(path);
  var tab = kind === "program" || kind === "sound" ? kind : "drawing";
  if (!confirm("Delete " + name + " from the FX drive? You can download it again later.")) return;
  try {
    var parts = path.split("/");
    var leaf = parts.pop();
    var folder = await folderAt(drive.dirHandle, parts);
    if (!folder) throw {name: "NotFoundError", message: path};
    var gone = [leaf];
    if (/\.py$/i.test(leaf)) {
      var stem = leaf.replace(/\.py$/i, "");
      for await (var entry of folder.keys()) {
        if (entry === stem + ".png" || (entry.indexOf(stem + "-") === 0 && /\.png$/i.test(entry)))
          gone.push(entry);
      }
    }
    for (var one of gone) await folder.removeEntry(one, {recursive: true});
  } catch (e) {
    discoverSay(tab, "Could not delete " + name + ". " + await driveTrouble(e, path), true);
    draw();
    return;
  }
  if (kind === "program") {
    PROGRAMS = PROGRAMS.filter(function (program) { return program.path !== path; });
    delete PICTURES[path];
    forgetMissingPrograms();
  } else {
    // Whatever showed or played it lets it go, as deleting the user's own does
    store();
    driveParts.forEach(function (part) {
      if (!part.forget) return;
      part.forget(path);
      apply(slotAt(state.at).body);
    });
    for (var tries = 0; tries < 20; tries++) {
      await scanMedia(state.dirHandle);
      if (!discoverKinds[kind].onDrive(path)) break;
      await new Promise(function (settle) { setTimeout(settle, 100); });
    }
  }
  discoverSay(tab, "Deleted " + name + ".");
  if (discover[tab].status === "done") discoverCheck(tab, true);
  draw();
}

// The copy tile sits in the bin's place on an example, which had none, so it moves beside it
export function discoverBinBeside(card, bin) {
  var copy = card.querySelector(".copytile");
  if (copy) copy.classList.remove("alone");
  card.appendChild(bin);
}
