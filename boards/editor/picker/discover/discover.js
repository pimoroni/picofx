import {banner} from "../banner.js";
import {SCREEN_PORTS} from "../board.js";
import {
  PROGRAMS, boardSet, programNamed, programsElsewhere, setPrograms
} from "../board_settings.js";
import {h, replace} from "../dom.js";
import {draw, drawSteps} from "../draw.js";
import {drive, driveTrouble, nameShown} from "../drive.js";
import {OTHER_EXAMPLES, exampleSections, isExampleMedia, scanMedia} from "../drive_files.js";
import {
  EXAMPLES_ROOT, PICTURES, SECTIONS, copyProgram, folderAt, forgetMissingPrograms, loadThumbs,
  programFrom
} from "../drive_programs.js";
import {BOARD, VERSION} from "../looks.js";
import {
  CHIPLESS, FEATURES, featureFilter, passesFilter, programCardFace, programHooks, programTitle,
  programUsesSaid, unhad, usesOf
} from "../program.js";
import {apply, driveParts, slotAt, state, store} from "../scenes.js";

export var discoverKinds = {};

var DISCOVER_BRANCH = "patch/spidisplay-external-rebased";

var DISCOVER_SOURCE = "https://raw.githubusercontent.com/pimoroni/picofx/refs/heads/" +
                      DISCOVER_BRANCH + "/";

function discoverFileUrl(path) {
  var index = BOARD.examples_index;
  return DISCOVER_SOURCE + index.slice(0, index.lastIndexOf("/") + 1) + path;
}

var DISCOVER_FIRMWARE = VERSION.split(" ")[0];

function discoverFreshCheck() {
  return {status: "idle", progress: null, refreshing: null, updating: null, error: null,
          index: null, notice: null};
}

var DISCOVER_OFFLINE = "Could not connect. Check this computer is online.";

async function discoverTrouble(e) {
  if (e.name === "TypeError") return DISCOVER_OFFLINE;
  if (e.name === "Error") return e.message;
  return await driveTrouble(e);
}

export function discoverSay(kind, text, warn) {
  var notice = discover[kind].notice = [text, warn];
  banner(text, warn);
  if (warn) return;
  setTimeout(function () {
    if (discover[kind].notice !== notice) return;
    discover[kind].notice = null;
    draw();
  }, DISCOVER_NOTICE_MS);
}

var DISCOVER_NOTICE_MS = 8000;

export var discover = {
  program: discoverFreshCheck(),
  sound: discoverFreshCheck(),
  drawing: discoverFreshCheck(),
  states: {},
  files: {},
  newer: {},
  busy: {},
  movedTo: {}
};

var discoverPrograms = {};
export var discoverDrawings = {};
export var discoverSounds = {};
export var discoverThumbs = {};
var discoverSecondThumbs = {};

function discoverOlder(a, b) {
  var x = a.split("."), y = b.split(".");
  for (var at = 0; at < Math.max(x.length, y.length); at++) {
    var difference = (parseInt(x[at], 10) || 0) - (parseInt(y[at], 10) || 0);
    if (difference) return difference < 0;
  }
  return false;
}

async function discoverHash(bytes) {
  var head = new TextEncoder().encode("blob " + bytes.length + "\0");
  var whole = new Uint8Array(head.length + bytes.length);
  whole.set(head);
  whole.set(bytes, head.length);
  var digest = new Uint8Array(await crypto.subtle.digest("SHA-1", whole));
  return Array.from(digest, function (byte) { return byte.toString(16).padStart(2, "0"); }).join("");
}

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

async function discoverFileState(file, find) {
  var places = [file.path].concat(file.moved_from || []);
  for (var place of places) {
    var handle = await find(place);
    if (handle) return {state: await discoverCompare(file, handle), at: place};
  }
  return {state: "missing", at: null};
}

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

async function discoverFetchMissing(kind, offered, same) {
  var missing = offered.filter(function (entry) { return discover.states[entry.path] === "missing"; });
  var listed = {};
  var before = same ? discoverListedOn(kind) : {};
  async function one(entry) {
    if (before[entry.path]) {
      listed[entry.path] = before[entry.path];
      return;
    }
    try {
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
    }
  }
  for (var at = 0; at < missing.length; at += 4) await Promise.all(missing.slice(at, at + 4).map(one));
  if (kind === "program") {
    discoverPrograms = listed;
    var urls = [];
    Object.keys(listed).forEach(function (path) { urls = urls.concat(discoverPicturesOf(path)); });
    loadThumbs(urls);
  } else if (kind === "sound") {
    discoverSounds = listed;
  } else {
    discoverDrawings = listed;
  }
}

function discoverPicturesOf(path) {
  return discoverThumbs[path] ? [discoverThumbs[path]].concat(discoverSecondThumbs[path] || []) : [];
}

function discoverWavSeconds(head, size) {
  var view = new DataView(head);
  if (view.byteLength < 12 || view.getUint32(0) !== 0x52494646 || view.getUint32(8) !== 0x57415645)
    return 0;
  var at = 12, byteRate = 0;
  while (at + 8 <= view.byteLength) {
    var id = view.getUint32(at), length = view.getUint32(at + 4, true);
    if (id === 0x666d7420) byteRate = view.getUint32(at + 16, true);
    else if (id === 0x64617461)
      return byteRate ? Math.max(1, Math.round(Math.min(length, size - at - 8) / byteRate)) : 0;
    at += 8 + length + (length % 2);
  }
  return 0;
}

function discoverTab(entry) {
  return entry.kind === "program" || entry.kind === "sound" ? entry.kind : "drawing";
}

var DISCOVER_TABS = ["program", "drawing", "sound"];
var DISCOVER_WORDS = {program: "programs", drawing: "pictures and drawings", sound: "sounds"};

function discoverAsked(kind) {
  var held = kind === "program"
    ? PROGRAMS.some(function (program) { return program.example; })
    : kind === "sound" ? state.sounds.some(isExampleMedia)
    : state.media.some(function (media) { return !media.offered && isExampleMedia(media.name); });
  return (held ? "more example " : "example ") + DISCOVER_WORDS[kind];
}

function discoverListedOn(kind) {
  return kind === "program" ? discoverPrograms : kind === "sound" ? discoverSounds : discoverDrawings;
}

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

function discoverTarget(path) {
  return discover.movedTo[path] || path;
}

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

async function discoverRemove(path) {
  var parts = path.split("/");
  var name = parts.pop();
  var folder = await folderAt(drive.dirHandle, parts);
  if (folder) await folder.removeEntry(name);
}

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

async function discoverListed(entry, written, fresh, was) {
  var path = entry.path;
  if (entry.kind === "program") {
    var stem = path.replace(/\.py$/i, "");
    var source = written[path] ? await written[path].text()
      : await (await (await (await folderAt(drive.dirHandle, path.split("/").slice(0, -1)))
          .getFileHandle(nameShown(path))).getFile()).text();
    var folder = path.slice(EXAMPLES_ROOT.length, path.lastIndexOf("/"));
    var program = programFrom(path, folder, source);
    setPrograms(PROGRAMS.filter(function (one) { return one.path !== path && one.path !== was; }));
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

var DISCOVER_ICONS = {
  get: "<path d='M7 18.5h-.5a4.5 4.5 0 0 1-.6-8.96 6 6 0 0 1 11.6-1.3A5 5 0 0 1 17.5 18.5H17 " +
       "M12 11v8 M9 16l3 3 3-3' fill='none' stroke='currentColor' stroke-width='1.8' " +
       "stroke-linecap='round' stroke-linejoin='round'/>",
  done: "<path d='M5 12.5l4.5 4.5L19 7.5' fill='none' stroke='currentColor' stroke-width='2.2' " +
        "stroke-linecap='round' stroke-linejoin='round'/>",
  warn: "<path d='M12 4v10 M12 19v.5' fill='none' stroke='currentColor' stroke-width='2.4' " +
        "stroke-linecap='round'/>"
};

var DISCOVER_ARROW = "<path d='M5.5 1 L5.5 7.5 M2.5 4.8 L5.5 7.8 L8.5 4.8 M1.5 9.8 L9.5 9.8' " +
                     "stroke='currentColor' stroke-width='1.6' fill='none' stroke-linecap='round' " +
                     "stroke-linejoin='round'/>";

function discoverIcon(name) {
  return h("svg:svg", {viewBox: "0 0 24 24", "aria-hidden": "true", html: DISCOVER_ICONS[name]});
}

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

function discoverProgress(at, idle) {
  return h("progress", {max: 100, value: at ? Math.round(100 * at[0] / Math.max(1, at[1])) : 8,
                        "data-idle": !!idle});
}

function discoverNotice(check) {
  if (!check.notice) return null;
  var warn = check.notice[1];
  var tone = warn === "hold" ? "hold" : warn ? "warn" : "done";
  return h("p", {"data-tone": tone}, tone === "hold" ? null : discoverIcon(tone), check.notice[0]);
}

export function discoverThumbImage(path) {
  var img = h("img", {alt: ""});
  img.onerror = function () { img.remove(); };
  img.src = discoverThumbs[path];
  return img;
}

export function discoverDivider(words, minor) {
  return h("div", {class: "discoverdivide", "data-minor": !!minor}, h("span", {}, words));
}

var DISCOVER_INK = {program: "var(--board)", drawing: "var(--accent)", sound: "var(--accent)"};

export function discoverBar(kind) {
  var check = discover[kind];
  var found = check.status === "done" ? discoverFound(kind) : null;
  return h("section", {class: "discoverbar", "aria-label": "Examples",
                       style: {"--discover": DISCOVER_INK[kind]}},
    discoverDivider("Examples"),
    h("button", {type: "button", onclick: function () { discoverOpenBrowser(kind); }},
      discoverIcon("get"), "Discover " + discoverAsked(kind),
      found && found.waiting.length ? h("span", {}, String(found.waiting.length)) : null),
    discoverUpdateRow(kind, check, found));
}

function discoverRowSays(check, found) {
  if (check.status === "idle") return h("p", {}, "Check the examples on the drive for newer versions.");
  if (check.status === "checking") return h("p", {}, "Checking for updates...");
  if (check.status === "failed") return h("p", {"data-failed": true}, check.error || DISCOVER_OFFLINE);
  return discoverNotice(check) || h("p", {}, found.updates.length
    ? discoverCount(found.updates.length, "update", "updates") + " for examples on the drive."
    : "The examples on the drive are up to date.");
}

function discoverUpdateRow(kind, check, found) {
  var running = check.status === "checking" ? check.progress || [0, 1]
              : check.updating || discoverFetching || check.refreshing;
  var busy = check.status === "checking" || running ||
             (check.notice && check.notice[1] === "hold");
  return h("div", {},
    discoverRowSays(check, found),
    discoverProgress(running || null, !running),
    h("button", {type: "button", disabled: !!(busy || !found || !found.updates.length),
                 onclick: function () { discoverUpdateAll(kind); }}, "Update all"),
    h("button", {type: "button", disabled: !!busy,
                 onclick: function () { discoverCheck(kind); }}, "Check for updates"));
}

var discoverBrowsing = null;
var discoverChosen = [];
var discoverAnchor = null;
var discoverSection = "";
var discoverFetching = null;
var discoverDialog = null;

function discoverOpenBrowser(kind) {
  discoverBrowsing = kind;
  discoverChosen = [];
  discoverAnchor = null;
  discoverSection = "";
  discoverCheck(kind, true);
  draw();
}

function discoverCloseBrowser() {
  discoverBrowsing = null;
  draw();
}

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
    if (held.kind === "picture") {
      return [path, held.picture.title, discoverPictureSaid(held.picture),
              held.picture.section || OTHER_EXAMPLES.pictures, "picture"];
    }
    return [path, held.drawing.title, held.drawing.description || "",
            held.drawing.section || OTHER_EXAMPLES.drawings, "drawing"];
  }).sort(function (a, b) {
    return a[1].localeCompare(b[1], undefined, {numeric: true});
  });
}

function discoverSectionKind(offers, section) {
  return offers.some(function (offer) { return offer[3] === section && offer[4] === "picture"; })
    ? "picture" : "drawing";
}

function discoverShows(offers, section) {
  if (!discoverSection) return true;
  if (discoverSection.indexOf("kind:") === 0)
    return discoverSectionKind(offers, section) === discoverSection.slice(5);
  return section === discoverSection;
}

export function discoverPictureSaid(picture) {
  if (picture.slideshow) return "A slideshow of " + picture.count + " pictures.";
  return "A " + picture.title.slice(picture.title.lastIndexOf(".") + 1).toUpperCase() + " picture.";
}

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

drawSteps.render.push(discoverRenderBrowser);

function discoverSheetDialog() {
  if (discoverDialog) return discoverDialog;
  discoverDialog = h("dialog", {class: "discover", "aria-labelledby": "discoverTitle",
                                onclose: function () { if (discoverBrowsing) discoverCloseBrowser(); },
                                onclick: function (event) {
                                  if (event.target === discoverDialog) discoverCloseBrowser();
                                }});
  document.body.appendChild(discoverDialog);
  return discoverDialog;
}

function discoverFocused(dialog) {
  var focused = document.activeElement;
  if (!focused || focused === dialog || !dialog.contains(focused)) return null;
  if (focused.dataset.path)
    return focused.tagName.toLowerCase() + "[data-path='" + CSS.escape(focused.dataset.path) + "']";
  if (focused.dataset.feature) return "[data-feature='" + focused.dataset.feature + "']";
  if (focused.tagName === "SELECT") return "select";
  return null;
}

function discoverRenderBrowser() {
  if (!discoverBrowsing) {
    if (discoverDialog && discoverDialog.open) {
      replace(discoverDialog);
      discoverDialog.close();
    }
    return;
  }
  var dialog = discoverSheetDialog();
  var kind = discoverBrowsing;
  var check = discover[kind];
  var oldScroll = dialog.querySelector(":scope > div:last-of-type");
  var scrolled = oldScroll ? oldScroll.scrollTop : 0;
  var focused = discoverFocused(dialog);
  var every = check.status === "done" ? discoverOffers(kind) : [];
  var offers = kind === "program" ? every.filter(function (offer) {
    return passesFilter(offer[0]);
  }) : every;
  var kinds = discoverKindsOffered(kind, offers);
  var choices = kinds.length > 1 ? kinds.map(function (one) { return "kind:" + one; }) : [];
  if (discoverSection && discoverSections(kind, offers).indexOf(discoverSection) < 0 &&
      choices.indexOf(discoverSection) < 0) discoverSection = "";
  discoverChosen = discoverChosen.filter(function (path) {
    return offers.some(function (offer) { return offer[0] === path; });
  });
  var scroll = h("div", {}, discoverSheetBody(kind, check, every, offers));
  dialog.style.setProperty("--discover", DISCOVER_INK[kind]);
  replace(dialog,
    discoverSheetHead(kind, offers),
    kind === "program" ? discoverChips(every) : null,
    scroll,
    discoverSheetFoot(kind, check, offers));
  if (!dialog.open) dialog.showModal();
  scroll.scrollTop = scrolled;
  var refocus = focused && dialog.querySelector(focused);
  if (refocus) refocus.focus();
}

function discoverSheetHead(kind, offers) {
  var asked = discoverAsked(kind);
  return h("header", {},
    h("button", {type: "button", onclick: discoverCloseBrowser}, "\u2039 Back"),
    h("h2", {id: "discoverTitle"}, asked.charAt(0).toUpperCase() + asked.slice(1)),
    offers.length ? discoverSectionChoice(kind, offers) : null);
}

function discoverKindsOffered(kind, offers) {
  var sections = discoverSections(kind, offers).filter(Boolean);
  return kind === "program" ? [] : ["drawing", "picture"].filter(function (one) {
    return sections.some(function (section) { return discoverSectionKind(offers, section) === one; });
  });
}

function discoverSectionChoice(kind, offers) {
  var sections = discoverSections(kind, offers).filter(Boolean);
  var kinds = discoverKindsOffered(kind, offers);
  var grouped = kinds.length > 1;
  function choice(value, words) {
    var count = offers.filter(function (offer) {
      return !value || (value.indexOf("kind:") === 0
        ? discoverSectionKind(offers, offer[3]) === value.slice(5) : offer[3] === value);
    }).length;
    return h("option", {value: value, selected: value === discoverSection}, words + " (" + count + ")");
  }
  return h("select", {"aria-label": "Section shown",
                      onchange: function (event) {
                        discoverSection = event.currentTarget.value;
                        draw();
                      }},
    choice("", "All"),
    grouped ? kinds.map(function (one) {
      return h("optgroup", {label: one === "picture" ? "Pictures" : "Drawings"},
        choice("kind:" + one, one === "picture" ? "All pictures" : "All drawings"),
        sections.filter(function (section) {
          return discoverSectionKind(offers, section) === one;
        }).map(function (section) { return choice(section, section); }));
    }) : sections.map(function (section) { return choice(section, section); }));
}

function discoverSheetBody(kind, check, every, offers) {
  if (check.status !== "done") {
    return h("div", {role: "status"},
      h("p", {}, check.status === "failed" ? check.error || DISCOVER_OFFLINE
                                           : "Checking for examples..."),
      check.status === "failed" ? null : discoverProgress(check.progress));
  }
  if (!offers.length) {
    var any = check.index.examples.some(function (entry) { return discoverTab(entry) === kind; });
    return h("div", {role: "status"},
      h("p", {}, every.length ? "Every example here needs hardware that is not ticked."
               : any ? "The drive has every example."
               : "There are no example " + DISCOVER_WORDS[kind] + " yet."));
  }
  var shown = [];
  var listed = discoverSections(kind, offers).filter(function (section) {
    return discoverShows(offers, section);
  });
  var named = kind !== "program" && listed.some(function (section) {
    return discoverSectionKind(offers, section) === "picture";
  }) && listed.some(function (section) {
    return discoverSectionKind(offers, section) !== "picture";
  });
  var lastKind = null;
  return listed.map(function (section) {
    var sectionKind = discoverSectionKind(offers, section);
    var divider = named && sectionKind !== lastKind
      ? discoverDivider(sectionKind === "picture" ? "Pictures" : "Drawings", true) : null;
    lastKind = sectionKind;
    var held = offers.filter(function (offer) { return offer[3] === section; });
    return [divider,
            listed.length > 1 ? h("h3", {}, section || "Other examples") : null,
            h("ul", {"data-kind": kind}, held.map(function (offer) {
              shown.push(offer[0]);
              return discoverOfferCard(offer, shown);
            }))];
  });
}

function discoverFootSays(check, offers, chosen, busy) {
  var notice = discoverNotice(check);
  if (notice && (!chosen.length || busy)) return notice;
  if (chosen.length === 1) return h("p", {}, h("strong", {}, chosen[0][1]));
  if (chosen.length) {
    return h("p", {}, h("strong", {}, discoverCount(chosen.length, "example", "examples") + " chosen"));
  }
  if (check.refreshing) return h("p", {}, "Checking the drive for changes...");
  if (offers.length) return h("p", {}, "Choose an example to download. Tick its box to choose more than one.");
  return null;
}

function discoverSheetFoot(kind, check, offers) {
  var chosen = offers.filter(function (offer) { return discoverChosen.indexOf(offer[0]) >= 0; });
  var busy = discoverFetching || check.refreshing ||
             chosen.some(function (offer) { return discover.busy[offer[0]]; });
  var downloading = busy && !check.refreshing;
  return h("footer", {},
    h("div", {},
      discoverFootSays(check, offers, chosen, busy),
      discoverFetching || check.refreshing ? discoverProgress(discoverFetching || check.refreshing)
                                           : null),
    chosen.length > 1 && !busy ? h("button", {type: "button", onclick: function () {
      discoverChosen = [];
      draw();
    }}, "Clear") : null,
    h("button", {type: "button", disabled: !chosen.length || !!busy,
                 onclick: function () { discoverDownloadChosen(kind); }},
      downloading ? "Downloading..." : chosen.length > 1 ? "Download " + chosen.length : "Download"));
}

function discoverProgramFace(path) {
  PICTURES[path] = discoverPicturesOf(path);
  var face = h("div", {class: "programcard", title: programUsesSaid(path)},
    programCardFace(path), h("small", {}, (programNamed(path) || {}).does || ""));
  delete PICTURES[path];
  return face;
}

function discoverOfferCard(offer, shown) {
  var path = offer[0];
  var chosen = discoverChosen.indexOf(path) >= 0;
  var newer = !!discover.newer[path];
  var face = discoverBrowsing === "program" ? discoverProgramFace(path)
           : discoverKinds[discoverBrowsing].face(path);
  face.dataset.path = path;
  face.tabIndex = 0;
  face.setAttribute("role", "button");
  face.setAttribute("aria-pressed", String(chosen));
  face.onclick = function (e) {
    if (!discover.newer[path]) discoverChoose(path, e, false, shown);
  };
  face.onkeydown = function (e) {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      face.onclick(e);
    }
  };
  var firmware = newer ? discoverEntry(path).firmware : null;
  return h("li", {"data-newer": newer},
    face,
    newer ? h("span", {class: "discoverpill", "data-state": "newer",
                       title: "Needs " + BOARD.name + " firmware " + firmware + " or newer."},
              "Needs " + firmware)
          : h("input", {type: "checkbox", checked: chosen, "data-path": path,
                        title: "Choose " + offer[1], "aria-label": "Choose " + offer[1],
                        onclick: function (e) {
                          e.stopPropagation();
                          discoverChoose(path, e, true, shown);
                        }}));
}

export function discoverPill(cardPath) {
  var path = discoverTarget(cardPath);
  var entry = discoverEntry(path);
  if (!entry || discover[discoverTab(entry)].status !== "done") return null;
  if (discover.busy[path]) {
    return h("span", {class: "discoverpill", "data-state": "busy", title: "Downloading"}, "...");
  }
  if (discover.newer[path] && discover.states[path] !== "current") {
    return h("span", {class: "discoverpill", "data-state": "newer",
                      title: "Needs " + BOARD.name + " firmware " + entry.firmware + " or newer."},
             "Needs " + entry.firmware);
  }
  if (discover.states[path] === "missing") {
    return h("span", {class: "discoverpill", "data-state": "missing", title: "Download"},
             h("svg:svg", {width: 11, height: 11, viewBox: "0 0 11 11", "aria-hidden": "true",
                           html: DISCOVER_ARROW}));
  }
  if (DISCOVER_UPDATES.indexOf(discover.states[path]) < 0) return null;
  return h("span", {class: "discoverpill", "data-state": "update", role: "button", tabindex: 0,
                    title: discover.files[entry.files[0].path].state === "changed"
                      ? "Download the newer version. Your changed copy is kept."
                      : "Download the newer version.",
                    onclick: function (e) {
                      e.stopPropagation();
                      discoverDownload(path);
                    },
                    onkeydown: function (e) {
                      if (e.key !== "Enter" && e.key !== " ") return;
                      e.preventDefault();
                      e.stopPropagation();
                      discoverDownload(path);
                    }},
           "Update");
}

programsElsewhere.push(function (path) { return discoverPrograms[path] || null; });

programHooks.extras.push(function (path) {
  var own = PROGRAMS.filter(function (one) { return one.path === path; })[0];
  if (!own) return null;
  return {busy: !!discover.busy[discoverTarget(path)],
          remove: own.example && drive.dirHandle ? function () { discoverDelete(path, "program"); }
                                                 : null,
          badge: discoverPill(path)};
});

programHooks.examples = function () {
  return EXAMPLES_ROOT ? discoverBar("program") : null;
};

function discoverChips(offers) {
  var used = FEATURES.filter(function (feature) {
    return CHIPLESS.indexOf(feature[0]) < 0 && offers.some(function (offer) {
      return usesOf(offer[0]).indexOf(feature[0]) >= 0;
    });
  });
  if (!used.length) return null;
  return featureFilter(used, {
    all: function (keys) {
      return unhad.filter(function (key) { return keys.indexOf(key) < 0; });
    },
    none: function (keys) { return unhad.concat(keys); }
  });
}

export function discoverBin(path, kind) {
  return h("span", {class: "bin", role: "button", title: "Delete " + nameShown(path) + " from the FX drive",
                    onclick: function (e) {
                      e.stopPropagation();
                      discoverDelete(path, kind);
                    }}, "\u00d7");
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
    setPrograms(PROGRAMS.filter(function (program) { return program.path !== path; }));
    delete PICTURES[path];
    forgetMissingPrograms();
  } else {
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

export function discoverBinBeside(card, bin) {
  var copy = card.querySelector("[data-copy]");
  if (copy) copy.dataset.copy = "";
  card.appendChild(bin);
}
