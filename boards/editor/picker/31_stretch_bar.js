import {draw} from "./00_draw.js";
import {isPicked} from "./01_colours.js";
import {lookNamed} from "./01_looks.js";
import {painters} from "./02_preview.js";
import {coloursWritten, takesColour, targetFor} from "./03_lines.js";
import {CHANNEL_INKS, isChannel, kinOf, selectorFor, shortName, widthOf} from "./03_outputs.js";
import {
  active, canEdit, copyBlinks, copyExact, cutAt, dragged, inkAt, mono, pick, remember, setHolding,
  settle, uncut
} from "./03_runs.js";
import {stretchUnder, underSaid} from "./04_scenes.js";
import {BEADS_JOIN_AT, BEAD_MOST, GAP_MOST, MONO_WASH, ZOOMS_OVER} from "./05_strips.js";
import {crossing, showKin} from "./09_wiring.js";
import {escapeHtml} from "./18_file_preview.js";
import {paintFaces, takesPlace} from "./33_gallery.js";

// ---- the bar, one cell per stretch, cut between them --------------------------------------

// What a stretch's cell is washed in, the colours it plays
export function washFor(run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
}

// A stretch's coloured band. One the scene plays nothing on keeps the stripes of nothing, over a
// window onto Always on's own band where Always on plays there and over dark where it is off
function washOf(run, section, look, under) {
  var wash = document.createElement("span");
  if (look || !under) {
    wash.className = "lit" + (look ? "" : " nothing");
    if (look) wash.style.background = washFor(run, section, look);
    return wash;
  }
  wash.className = "lit through";
  // Each run of lamps that show one thing is one pane
  var wide = under.lamps.length;
  var start = 0;
  while (start < wide) {
    var end = start + 1;
    while (end < wide && sameShowing(under.lamps[end], under.lamps[start])) end++;
    wash.appendChild(paneOnto(run, under.lamps[start], start, end, wide));
    start = end;
  }
  return wash;
}

// Whether two lamps under a scene show the same thing, nothing, off or one Always on stretch
function sameShowing(one, other) {
  return one === other ||
         !!(one && other && one.section && other.section && one.section === other.section);
}

// A pane over lamps start to end of a stretch wide lamps across. Over Always on's stretch it holds
// that stretch's whole band, moved so the lamps under the pane line up with their own part of it
function paneOnto(run, shows, start, end, wide) {
  var pane = document.createElement("span");
  pane.style.left = (start * 100 / wide) + "%";
  pane.style.width = ((end - start) * 100 / wide) + "%";
  if (!shows) pane.className = "empty";
  else if (shows === "off") pane.className = "off";
  else {
    var band = document.createElement("span");
    band.style.width = (widthOf(shows.section) * 100 / (end - start)) + "%";
    band.style.left = (-shows.at * 100 / (end - start)) + "%";
    band.style.background = washFor(run, shows.section, lookNamed(shows.section.look));
    pane.appendChild(band);
  }
  return pane;
}

// The note under a cell's "Nothing" saying what shows through from Always on, or nothing where
// the stretch shows nothing at all
function beneath(under) {
  return under ? "<span class='beneath'>" + escapeHtml(under.note) + "</span>" : "";
}

// Whether a run's lamps sit inside its stretches' cards. The outputs' do, in Edit board too, so
// setting up the wiring never moves them. A strip keeps its LEDs drawn on their wire above the bar
function carded(run) {
  return !run.strip;
}

// A stretch's lamps, one for each light it holds, each face kept in faces by the lamp's place
// in the run so it can be lit as the run plays. While the wiring is set up, each lamp is a tile
// to drag to its place on the build, and an output that breaks out has its arrow on its tiles
function cardLamps(run, section, faces) {
  var row = document.createElement("span");
  row.className = "cardlamps";
  var wiring = canEdit("outPanel");
  for (var at = section.from; at <= section.to; at++) {
    var lamp = run.lamps[at];
    var one = document.createElement("span");
    var channel = !lamp.colour && isChannel(lamp);
    // A broken-out channel is marked in its channel's colour
    one.className = "cardlamp" + (channel ? " chan" : "");
    if (channel) one.style.setProperty("--chan", CHANNEL_INKS[lamp.channel]);
    var playing = lookNamed(section.look);
    one.title = selectorFor(lamp) + (playing ? ", playing " + playing.name : underSaid(run, at));
    var face = document.createElement("i");
    one.appendChild(face);
    var said = document.createElement("b");
    said.textContent = shortName(lamp);
    one.appendChild(said);
    faces[at] = face;
    if (wiring) setUpLamp(one, lamp, channel);
    row.appendChild(one);
  }
  return row;
}

// Make a card's lamp a tile of the wiring, dragged to its place and split or rejoined by its
// arrow. Pointing at one channel shows the other two of its output
function setUpLamp(one, lamp, channel) {
  takesPlace(one, lamp);
  one.appendChild(crossing(lamp.out, lamp.colour));
  if (!channel) return;
  (kinOf[lamp.out] = kinOf[lamp.out] || []).push(one);
  one.addEventListener("mouseenter", function () { showKin(lamp.out, true); });
  one.addEventListener("mouseleave", function () { showKin(lamp.out, false); });
}

export function renderBar(where, run) {
  var box = document.getElementById(where);
  box.textContent = "";
  var scroller = document.createElement("div");
  scroller.className = "scroller";
  var bar = document.createElement("div");
  bar.className = "bar" + (carded(run) ? " carded" : "");
  var faces = [];

  run.sections.forEach(function (section, at) {
    // A lamp is dragged out of its card while the wiring is set up, which a button would not let go
    var cell = document.createElement(carded(run) && canEdit("outPanel") ? "div" : "button");
    cell.className = "sec" + (run === active && run.picked === at ? " picked" : "");
    cell.style.flex = widthOf(section) + " 1 0";
    var first = run.lamps[section.from];
    cell.title = (first && first.colour ? "colour" : "mono") + ", " +
                 targetFor(run, section).selector;
    if (carded(run)) cell.appendChild(cardLamps(run, section, faces));

    var look = lookNamed(section.look);
    var under = look ? null : stretchUnder(run, section);
    cell.appendChild(washOf(run, section, look, under));
    if (under) cell.title = under.tip;

    var says = document.createElement("span");
    says.className = "says";
    says.innerHTML = (look ? look.name : "Nothing") + " <em>" + widthOf(section) + "</em>" +
                     beneath(under);
    cell.appendChild(says);

    // Where this stretch can be cut, one place between two lamps
    var inside = document.createElement("span");
    inside.className = "cuts";
    for (var i = section.from; i < section.to; i++) {
      inside.appendChild(cutPoint(run, i, widthOf(section), section.from));
    }
    cell.appendChild(inside);

    cell.onclick = function () {
      if (dragged) return;
      pick(run, at);
      draw();
    };
    bar.appendChild(cell);

    if (at < run.sections.length - 1) {
      var edge = document.createElement("div");
      edge.className = "edge";
      edge.title = "drag to move this cut, or click \u00d7 to remove it";
      edge.onmousedown = function (event) {
        event.preventDefault();
        remember(run);
        // The stretch being resized is the one being worked on, whichever side it is on
        pick(run, at);
        // The bar is rebuilt on every move, so what is held onto is where the bar lives
        // and not the bar itself, which would be a node already thrown away
        setHolding({run: run, which: at, where: where, had: run.sections.length});
        edge.classList.add("holding");
      };
      // Taking the cut out is its own target, so it is never confused with moving it
      var drop = document.createElement("button");
      drop.className = "drop";
      drop.textContent = "\u00d7";
      drop.title = "remove this cut and join the two stretches";
      drop.onmousedown = function (event) { event.stopPropagation(); };
      drop.onclick = function (event) {
        event.stopPropagation();
        uncut(run, at);
      };
      edge.appendChild(drop);
      bar.appendChild(edge);
    }
  });
  scroller.appendChild(bar);
  box.appendChild(scroller);
  if (carded(run)) painters.push({run: run, paint: function (all) { paintFaces(faces, all); }});
}

function cutPoint(run, after, wide, from) {
  var snip = document.createElement("i");
  snip.className = "cut";
  snip.style.left = ((after - from + 1) / wide * 100) + "%";
  snip.style.width = "min(11px, " + (55 / wide) + "%)";
  snip.dataset.says = shortName(run.lamps[after]) + " | " +
                      shortName(run.lamps[after + 1]);
  snip.title = "cut between " + snip.dataset.says.replace(" | ", " and ");
  snip.onclick = function (event) {
    event.stopPropagation();
    cutAt(run, after);
  };
  return snip;
}

export function zoomOf(run) { return run.zoom || 1; }

// The picked stretch cut into a number of stretches as near equal as its lamps allow
function splitSection(run, ways) {
  var section = run.sections[run.picked];
  if (!section || ways < 2 || widthOf(section) < ways) return;
  remember(run);
  var made = [];
  var edges = [];
  for (var i = 0; i <= ways; i++) {
    edges.push(section.from + Math.round(widthOf(section) * i / ways));
  }
  for (var g = 0; g < ways; g++) {
    made.push({from: edges[g], to: edges[g + 1] - 1, look: section.look,
               pace: section.pace, mood: section.mood, colour: section.colour});
  }
  run.sections.splice.apply(run.sections, [run.picked, 1].concat(made));
  draw();
}
// A stretch's beads, each kept in beads by its LED's place on the strip so it can be lit as the
// strip plays
function stripBeads(run, section, beads) {
  var row = document.createElement("span");
  // A stretch set to Nothing sits on the stripes Nothing wears elsewhere, inside a broken line
  row.className = "stripbeads" + (lookNamed(section.look) ? "" : " unset");
  for (var n = section.from; n <= section.to; n++) {
    var room = document.createElement("i");
    var bead = document.createElement("b");
    room.appendChild(bead);
    row.appendChild(room);
    beads[n] = bead;
  }
  return row;
}

// One end of the strip's wire, the lead block before its first LED or the ring after its last
function wireEnd(which) {
  var end = document.createElement("span");
  end.className = "wireend";
  var mark = document.createElement("span");
  mark.className = which;
  end.appendChild(mark);
  return end;
}

// Draw a strip's beads for the room each LED has, and run its wire between the two ends. Every
// card's beads take the size of the narrowest card's, so all of a strip's LEDs match
function fitBeads(bar, beads) {
  if (!beads.length || !bar.offsetWidth) return;
  var room = Infinity;
  beads.forEach(function (bead) {
    room = Math.min(room, bead.parentNode.getBoundingClientRect().width);
  });
  // How far the strip is from one continuous strip, 1 where beads are full size and 0 where they
  // have joined, which closes the gap, the corners and the edges together in a straight line
  var apart = (room - BEADS_JOIN_AT) / (BEAD_MOST + GAP_MOST - BEADS_JOIN_AT);
  apart = Math.max(0, Math.min(1, apart));
  var size = Math.min(BEAD_MOST, room - GAP_MOST * apart);
  // A bead keeps its full height whatever its width. The wire and the ends are drawn in
  // proportion to that height, as the strip was drawn before
  var wire = BEAD_MOST * 0.16;
  bar.style.setProperty("--apart", apart);
  bar.style.setProperty("--gap", (GAP_MOST * apart) + "px");
  // A gap under a pixel is drawn whole, and filled more the more it has closed. Once closed, the
  // beads meet edge to edge
  bar.style.setProperty("--fill", 1 - Math.min(1, GAP_MOST * apart));
  bar.style.setProperty("--gapdrawn", apart > 0 ? "max(var(--gap), 1px)" : "0px");
  bar.style.setProperty("--bead", size + "px");
  bar.style.setProperty("--beadtall", BEAD_MOST + "px");
  bar.style.setProperty("--wire", wire + "px");
  bar.style.setProperty("--end", BEAD_MOST + "px");

  var middle = beads[0].getBoundingClientRect();
  var from = bar.getBoundingClientRect();
  var lead = bar.querySelector(".wireend .lead").getBoundingClientRect();
  var tail = bar.querySelector(".wireend .tail").getBoundingClientRect();
  var line = bar.querySelector(".stripwire");
  line.style.top = (middle.top + middle.height / 2 - from.top - wire / 2) + "px";
  line.style.height = wire + "px";
  // The wire starts in the lead block and ends in the ring, never showing past either
  line.style.left = (lead.left + lead.width / 2 - from.left) + "px";
  line.style.right = (from.right - tail.left - tail.width / 2) + "px";
  bar.style.setProperty("--wiremiddle", (middle.top + middle.height / 2 - from.top) + "px");
}

export function renderStripBar(where, run) {
  var box = document.getElementById(where);
  var was = box.querySelector(".scroller");
  var kept = was ? was.scrollLeft : run.scrolled || 0;
  box.textContent = "";

  // Zoomed in, the bar is wider than the room it has and scrolls inside it. That is
  // what puts a single light of a long strip within reach of a pointer
  var scroller = document.createElement("div");
  scroller.className = "scroller";
  var bar = document.createElement("div");
  bar.className = "bar carded stripcards";
  bar.style.width = (zoomOf(run) * 100) + "%";
  var beads = [];
  bar.appendChild(wireEnd("lead"));

  run.sections.forEach(function (section, at) {
    var wide = widthOf(section);
    var cell = document.createElement("button");
    cell.className = "sec" + (isPicked(run, at) ? " picked" : "") +
                     (wide * 40 < run.count * 8 ? " narrow" : "");
    cell.style.flex = wide + " 1 0";
    cell.title = "lights " + (section.from + 1) + " to " + (section.to + 1);
    cell.appendChild(stripBeads(run, section, beads));

    // Under its LEDs, a stretch is washed in a colour of its look and named
    var look = lookNamed(section.look);
    var under = look ? null : stretchUnder(run, section);
    cell.appendChild(washOf(run, section, look, under));
    if (under) cell.title += ". " + under.tip;

    var says = document.createElement("span");
    says.className = "says";
    says.innerHTML = (look ? look.name : "Nothing") + " <em>" + wide + "</em>" + beneath(under);
    cell.appendChild(says);

    // Where this stretch could be cut, one click to a place between two lights
    var inside = document.createElement("span");
    inside.className = "cuts";
    for (var n = section.from; n < section.to; n++) {
      inside.appendChild(cutPoint(run, n, wide, section.from));
    }
    cell.appendChild(inside);

    cell.onclick = function () { pick(run, at); draw(); };
    bar.appendChild(cell);

    // The cut this section shares with the next, dragged to move it or clicked to take it
    // out, which joins the two either side
    if (at < run.sections.length - 1) {
      var edge = document.createElement("div");
      edge.className = "edge";
      edge.title = "drag to move this cut, or click to remove it";
      edge.onmousedown = function (e) {
        e.preventDefault();
        // The bar is rebuilt on every move, so what is held onto is where it lives and
        // not the bar itself, which would be a node that has already been thrown away
        setHolding({run: run, which: at, where: where, had: run.sections.length});
        edge.classList.add("holding");
      };
      // Taking the cut out is its own target, so it is never confused with moving it
      var drop = document.createElement("button");
      drop.className = "drop";
      drop.textContent = "\u00d7";
      drop.title = "remove this cut and join the two stretches";
      drop.onmousedown = function (e) { e.stopPropagation(); };
      drop.onclick = function (e) {
        e.stopPropagation();
        uncut(run, at);
      };
      edge.appendChild(drop);
      bar.appendChild(edge);
    }
  });
  bar.appendChild(wireEnd("tail"));
  var line = document.createElement("span");
  line.className = "stripwire";
  bar.appendChild(line);
  scroller.appendChild(bar);
  box.appendChild(scroller);
  scroller.scrollLeft = kept;
  scroller.onscroll = function () { run.scrolled = scroller.scrollLeft; };
  // The beads are drawn for the room the bar has, which a hidden tab shown or a page resized
  // changes without a draw
  fitBeads(bar, beads);
  if (window.ResizeObserver) new ResizeObserver(function () { fitBeads(bar, beads); }).observe(bar);
  painters.push({run: run, paint: function (all) {
    beads.forEach(function (bead, n) {
      var one = all[n] || {level: 0, ink: "#e4e0d9"};
      // A bead playing nothing is drawn unlit, as an output's lamp is. Its colour is kept as its
      // text colour as well, which fills a closing gap beside it
      bead.style.background = bead.style.color = one.nothing ? "#2a2d30" : inkAt(one);
    });
  }});

  // Rolling the wheel over the bar zooms into the light under the pointer, keeping it
  // where it is on the screen. The buttons do the same in steps, which is what says the
  // zooming is there at all
  scroller.onwheel = function (e) {
    if (run.count <= ZOOMS_OVER) return;
    e.preventDefault();
    // The wheel holds the light under the pointer, and the buttons hold the middle of what
    // is on screen, since a button press has no place on the run to hold onto
    var box2 = scroller.getBoundingClientRect();
    var at = (scroller.scrollLeft + (e.clientX - box2.left)) / bar.offsetWidth;
    zoomTo(run, zoomOf(run) * (e.deltaY < 0 ? 1.25 : 0.8), at, e.clientX - box2.left);
  };
}

export function middleOfView(run) {
  var scroller = document.querySelector("#" + run.id + "Bar .scroller");
  if (!scroller) return 0.5;
  var bar = scroller.querySelector(".bar");
  return (scroller.scrollLeft + scroller.clientWidth / 2) / bar.offsetWidth;
}

// Zooming keeps whatever was under the pointer under the pointer, which is the only way a
// zoom on a long run is any use, as otherwise the thing being aimed at runs away
export function zoomTo(run, want, at, from) {
  // Held to three places, and to exactly 1 near it, since the buttons step by 1.6 each way and
  // coming back out leaves 1.0000000000000002, a bar a hair wider than its box that scrolls
  want = Math.round(want * 1000) / 1000;
  if (Math.abs(want - 1) < 0.01) want = 1;
  run.zoom = Math.max(1, Math.min(24, want));
  draw();
  var scroller = document.querySelector("#" + run.id + "Bar .scroller");
  if (!scroller) return;
  var bar = scroller.querySelector(".bar");
  var to = at * bar.offsetWidth - (from === undefined ? scroller.clientWidth / 2 : from);
  scroller.scrollLeft = Math.max(0, to);
  run.scrolled = scroller.scrollLeft;
}

// ---- what a stretch plays, carried through the tools -----------------------------------------
// Everything a stretch holds besides where it is, copied, so splitting it keeps what it played.
// splitSection() copies only its look, pace, setting and colour, and joinAll() starts from one
// stretch playing nothing
export function playsOf(section) {
  return {look: section.look, pace: section.pace, mood: section.mood, colour: section.colour,
          custom: section.custom, reversed: section.reversed, level: section.level,
          blinks: copyBlinks(section.blinks), exact: copyExact(section.exact),
          timings: copyExact(section.timings)};
}

function divide(run, ways) {
  var section = run.sections[run.picked];
  if (!section) return;
  var had = playsOf(section);
  var at = run.picked, count = run.sections.length;
  splitSection(run, ways);
  for (var made = at; made < at + run.sections.length - count + 1; made++) {
    Object.assign(run.sections[made], playsOf(had));
  }
  draw();
}

// ---- splitting a strip's chosen stretch ------------------------------------------------------
// The chosen stretch's panel splits it into a number of parts or into lengths of a number of
// lights, in the screens' button style. It is one outlined group read as a sentence, its words
// first, then its number, then the buttons that act, so the number is never apart from them.

// The picked stretch cut every so many lights from its start, a shorter one last where they
// do not divide it evenly
function divideLengths(run, each) {
  var section = run.sections[run.picked];
  if (!section || each < 1 || each >= widthOf(section)) return;
  remember(run);
  var had = playsOf(section);
  var made = [];
  for (var from = section.from; from <= section.to; from += each) {
    made.push(Object.assign({from: from, to: Math.min(section.to, from + each - 1)},
                            playsOf(had)));
  }
  run.sections.splice.apply(run.sections, [run.picked, 1].concat(made));
  settle();
  draw();
}

export function toolButton(icon, words, off, act, title) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "stoggle";
  button.innerHTML = "<span aria-hidden='true'>" + icon + "</span> " + words;
  button.disabled = off;
  button.title = title;
  button.dataset.act = act;
  return button;
}

function toolNumber(value, low, high, focus, change) {
  var box = document.createElement("input");
  box.type = "number";
  box.min = low;
  box.max = high;
  box.value = value;
  box.dataset.focus = focus;
  box.onchange = function () {
    change(Math.max(low, Math.min(high, Number(box.value) || low)));
    draw();
  };
  return box;
}

// The Split into group for a strip's chosen stretch, shown in its panel. Splitting earns its place
// along a strip's many LEDs, while the outputs are few and cut one at a time between their lamps
export function splitTools(where, run) {
  var section = run.sections[run.picked];
  var wide = section ? widthOf(section) : 1;
  var row = document.createElement("span");
  row.className = "stretchtools";

  var ways = run.ways || 3;
  var split = toolGroup("&#9986;", "Split into");
  split.appendChild(toolNumber(ways, 1, Math.max(2, wide), where + "-ways",
                               function (value) { run.ways = value; }));
  var parts = toolAct("stretches", wide < 2 || ways < 2, "split",
                      "split the selected stretch into " + ways + " equal parts");
  parts.onclick = function () { divide(run, Math.min(ways, wide)); };
  split.appendChild(parts);
  var lengths = toolAct("lights each", ways >= wide, "lengths",
                        "split the selected stretch every " + ways +
                        (ways === 1 ? " light" : " lights") + ", with a " +
                        "shorter last stretch if it does not divide evenly");
  lengths.onclick = function () { divideLengths(run, ways); };
  split.appendChild(lengths);
  row.appendChild(split);
  return row;
}

// A run's stretches as its bar draws them, in order
export function barCells(run) {
  var bar = run.strip ? run.id + "Bar" : run === mono ? "monoBar" : "outBar";
  return Array.prototype.slice.call(document.querySelectorAll("#" + bar + " .bar > .sec"));
}

// One outlined group, its icon and words, then what is put inside it
function toolGroup(icon, words) {
  var group = document.createElement("span");
  group.className = "toolset";
  var said = document.createElement("span");
  said.className = "toolsays";
  said.innerHTML = "<span aria-hidden='true'>" + icon + "</span> " + words;
  group.appendChild(said);
  return group;
}

// A button inside a group that does what the group says
function toolAct(words, off, act, title) {
  var button = document.createElement("button");
  button.type = "button";
  button.className = "toolact";
  button.textContent = words;
  button.disabled = off;
  button.title = title;
  button.dataset.act = act;
  return button;
}

// A cut's label, which lights it falls between, is centred on the cut, so near either end of a
// bar it would overhang the bar. Though hidden until pointed at, it still takes its room, and
// would make an unzoomed bar scroll. A label within its own width of an end is turned inward,
// and a bar at its whole width does not scroll at all
export function fitBars() {
  document.querySelectorAll(".scroller").forEach(function (scroller) {
    var bar = scroller.querySelector(".bar");
    if (!bar) return;
    var zoomed = bar.style.width && parseFloat(bar.style.width) > 100;
    scroller.style.overflowX = zoomed ? "auto" : "hidden";
    scroller.classList.toggle("zoomed", !!zoomed);
    var edges = bar.getBoundingClientRect();
    bar.querySelectorAll(".cut").forEach(function (cut) {
      var at = cut.getBoundingClientRect();
      var middle = (at.left + at.right) / 2;
      cut.classList.toggle("nearstart", middle - edges.left < 40);
      cut.classList.toggle("nearend", edges.right - middle < 40);
    });
  });
}

// A look given a colour is drawn in it, and one playing several, as Party does, in those.
// Any other look is drawn in its card's colours, since one colour in its line is no picture
// of what it plays. Campfire's single flame colour is not the flicker its card shows
function stretchWash(look, section, run, mono) {
  if (mono) return MONO_WASH;
  var inks = run && section ? coloursWritten(look, section, run) : [];
  if (!takesColour(look) && inks.length < 2) inks = look.strip || [];
  if (inks.length > 1) return "linear-gradient(90deg," + inks.join(",") + ")";
  return inks[0] || "rgba(138,131,120,0.16)";
}
