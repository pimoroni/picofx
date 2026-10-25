import {h, replace} from "./dom.js";
import {draw} from "./draw.js";
import {coloursWritten, takesColour} from "./lines.js";
import {lookNamed} from "./looks.js";
import {shortName, widthOf} from "./outputs.js";
import {painters} from "./preview.js";
import {
  cutAt, inkAt, isPicked, mono, pick, playsOf, remember, setHolding, settle, uncut
} from "./runs.js";
import {stretchUnder} from "./scenes.js";
import {BEADS_JOIN_AT, BEAD_MOST, GAP_MOST, MONO_WASH, ZOOMS_OVER, stripDrawing} from "./strips.js";

// Each run's bar of stretches with its cuts, and a strip's beads, zoom and split tools.

// ---- the bar, one cell per stretch, cut between them --------------------------------------

// What a stretch's cell is washed in, the colours it plays
export function washFor(run, section, look) {
  var first = run.lamps[section.from];
  return stretchWash(look, section, run, !!first && !first.colour);
}

// A stretch's coloured band. One the scene plays nothing on keeps the stripes of nothing, over a
// window onto Always on's own band where Always on plays there and over dark where it is off
export function washOf(run, section, look, under) {
  if (look || !under) {
    return h("span", {className: "lit" + (look ? "" : " nothing"),
                      style: {background: look ? washFor(run, section, look) : null}});
  }
  // Each run of lamps that show one thing is one pane
  var panes = [];
  var wide = under.lamps.length;
  var start = 0;
  while (start < wide) {
    var end = start + 1;
    while (end < wide && sameShowing(under.lamps[end], under.lamps[start])) end++;
    panes.push(paneOnto(run, under.lamps[start], start, end, wide));
    start = end;
  }
  return h("span", {className: "lit through"}, panes);
}

// Whether two lamps under a scene show the same thing, nothing, off or one Always on stretch
function sameShowing(one, other) {
  return one === other ||
         !!(one && other && one.section && other.section && one.section === other.section);
}

// A pane over lamps start to end of a stretch wide lamps across. Over Always on's stretch it holds
// that stretch's whole band, moved so the lamps under the pane line up with their own part of it
function paneOnto(run, shows, start, end, wide) {
  return h("span", {
    className: !shows ? "empty" : shows === "off" ? "off" : null,
    style: {left: start * 100 / wide + "%", width: (end - start) * 100 / wide + "%"}
  }, shows && shows !== "off" ? h("span", {style: {
    width: widthOf(shows.section) * 100 / (end - start) + "%",
    left: -shows.at * 100 / (end - start) + "%",
    background: washFor(run, shows.section, lookNamed(shows.section.look))
  }}) : null);
}

// The note under a cell's "Nothing" saying what shows through from Always on, or null for none
function beneath(under) {
  return under ? h("span", {className: "beneath"}, under.note) : null;
}

// A stretch's cell's words, its look and width, and what shows through where it plays nothing
export function cellSays(look, wide, under) {
  return h("span", {className: "says"}, (look ? look.name : "Nothing") + " ",
           h("em", {}, wide), beneath(under));
}

// Whether a run's lamps sit inside its stretches' cards. The outputs' do, in the wiring view too,
// so setting up the wiring never moves them. A strip's cards hold beads on a wire instead
export function carded(run) {
  return !run.strip;
}

export function cutPoint(run, after, wide, from) {
  var says = shortName(run.lamps[after]) + " | " + shortName(run.lamps[after + 1]);
  return h("i", {
    className: "cut",
    style: {left: (after - from + 1) / wide * 100 + "%", width: "min(11px, " + 55 / wide + "%)"},
    "data-says": says, title: "cut between " + says.replace(" | ", " and "),
    onclick: function (event) {
      event.stopPropagation();
      cutAt(run, after);
    }
  });
}

export function zoomOf(run) { return run.zoom || 1; }

// Cut the picked stretch into ways= stretches as near equal as its lamps allow
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
// A stretch's beads, each kept in beads[] at its LED's place on the strip to be lit as it plays
function stripBeads(run, section, beads) {
  var rooms = [];
  for (var n = section.from; n <= section.to; n++) {
    beads[n] = h("b");
    rooms.push(h("i", {}, beads[n]));
  }
  // A stretch set to Nothing sits on the stripes Nothing wears elsewhere, inside a broken line
  return h("span", {className: "stripbeads" + (lookNamed(section.look) ? "" : " unset")}, rooms);
}

// One end of the strip's wire, the lead block before its first LED or the ring after its last
function wireEnd(which) {
  return h("span", {className: "wireend"}, h("span", {className: which}));
}

// Draw a strip's beads for the room each LED has, and run its wire between the two ends. Every
// bead takes the size the narrowest LED's room allows, so all of a strip's LEDs match
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
  // A bead keeps its full height whatever its width, and the wire and ends are in proportion to it
  var wire = BEAD_MOST * 0.16;
  bar.style.setProperty("--apart", apart);
  bar.style.setProperty("--gap", (GAP_MOST * apart) + "px");
  // A gap under a pixel is drawn whole, filled more as it closes, until beads meet edge to edge
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

function renderStripBar(where, run) {
  var box = document.getElementById(where);
  var was = box.querySelector(".scroller");
  var kept = was ? was.scrollLeft : run.scrolled || 0;

  // Zoomed in, the bar is wider than the room it has and scrolls inside it. That is
  // what puts a single light of a long strip within reach of a pointer
  var beads = [];
  var bar = h("div", {className: "bar carded stripcards", style: {width: zoomOf(run) * 100 + "%"}},
              wireEnd("lead"),
              run.sections.map(function (section, at) {
                return [stripCard(run, section, at, beads),
                        at < run.sections.length - 1 ? stripEdge(run, at, where) : null];
              }),
              wireEnd("tail"),
              h("span", {className: "stripwire"}));
  var scroller = h("div", {className: "scroller"}, bar);
  replace(box, scroller);
  scroller.scrollLeft = kept;
  scroller.onscroll = function () { run.scrolled = scroller.scrollLeft; };
  // The beads are drawn for the room the bar has, which a resized page changes without a draw
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

  // Rolling the wheel over the bar zooms in or out about the light under the pointer, keeping it
  // where it is on the screen. The zoom buttons are what show that zooming is there at all
  scroller.onwheel = function (e) {
    if (run.count <= ZOOMS_OVER) return;
    e.preventDefault();
    var box2 = scroller.getBoundingClientRect();
    var at = (scroller.scrollLeft + (e.clientX - box2.left)) / bar.offsetWidth;
    zoomTo(run, zoomOf(run) * (e.deltaY < 0 ? 1.25 : 0.8), at, e.clientX - box2.left);
  };
}

// A strip's stretch as a card, its LEDs over its look's wash, named, with its places to cut
function stripCard(run, section, at, beads) {
  var wide = widthOf(section);
  var rooms = stripBeads(run, section, beads);
  var look = lookNamed(section.look);
  var under = look ? null : stretchUnder(run, section);
  var cuts = [];
  // Where this stretch can be cut, one place between each two lights
  for (var n = section.from; n < section.to; n++) cuts.push(cutPoint(run, n, wide, section.from));
  return h("button", {
    className: "sec" + (isPicked(run, at) ? " picked" : "") +
               (wide * 40 < run.count * 8 ? " narrow" : ""),
    style: {flex: wide + " 1 0"},
    title: "lights " + (section.from + 1) + " to " + (section.to + 1) +
           (under ? ". " + under.tip : ""),
    onclick: function () { pick(run, at); draw(); }
  }, rooms, washOf(run, section, look, under), cellSays(look, wide, under),
     h("span", {className: "cuts"}, cuts));
}

// The cut a stretch shares with the next, dragged to move it or taken out to join the two stretches
function stripEdge(run, at, where) {
  var edge = h("div", {
    className: "edge", title: "drag to move this cut, or click to remove it",
    onmousedown: function (e) {
      e.preventDefault();
      remember(run);
      // The bar is rebuilt on every move, so what is held onto is where the bar lives and not the
      // bar itself, which would be a node already thrown away
      setHolding({run: run, which: at, where: where, had: run.sections.length});
      edge.classList.add("holding");
    }
  }, // Taking the cut out is its own target, so it is never confused with moving it
     h("button", {
       className: "drop", title: "remove this cut and join the two stretches",
       onmousedown: function (e) { e.stopPropagation(); },
       onclick: function (e) {
         e.stopPropagation();
         uncut(run, at);
       }
     }, "×"));
  return edge;
}

export function middleOfView(run) {
  var scroller = document.querySelector("#" + run.id + "Bar .scroller");
  if (!scroller) return 0.5;
  var bar = scroller.querySelector(".bar");
  return (scroller.scrollLeft + scroller.clientWidth / 2) / bar.offsetWidth;
}

// Zoom a run's bar to want=, holding the place at= across the bar at from= pixels into the view,
// or at its middle without from=, so the thing being aimed at does not run away
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
// lights. It is one outlined group read as a sentence, its words first, then its number, then the
// buttons that act, so the number is never apart from them.

// Cut the picked stretch every each= lights from its start, with a shorter last one if uneven
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
  return h("button", {type: "button", className: "stoggle", disabled: off, title: title,
                      "data-act": act},
           h("span", {"aria-hidden": "true", html: icon}), " " + words);
}

// A number for a tool, named label= for a screen reader
function toolNumber(value, low, high, focus, change, label) {
  var box = h("input", {
    type: "number", min: low, max: high, value: value, "data-focus": focus,
    name: "toolNumber", "aria-label": label,
    onchange: function () {
      change(Math.max(low, Math.min(high, Number(box.value) || low)));
      draw();
    }
  });
  return box;
}

// The Split into group for a strip's chosen stretch, shown in its panel. Splitting earns its place
// along a strip's many LEDs, while the outputs are few and cut one at a time between their lamps
export function splitTools(where, run) {
  var section = run.sections[run.picked];
  var wide = section ? widthOf(section) : 1;
  var ways = run.ways || 3;
  var parts = toolAct("stretches", wide < 2 || ways < 2, "split",
                      "split the selected stretch into " + ways + " equal parts");
  parts.onclick = function () { divide(run, Math.min(ways, wide)); };
  var lengths = toolAct("lights each", ways >= wide, "lengths",
                        "split the selected stretch every " + ways +
                        (ways === 1 ? " light" : " lights") + ", with a " +
                        "shorter last stretch if it does not divide evenly");
  lengths.onclick = function () { divideLengths(run, ways); };
  return h("span", {className: "stretchtools"},
           toolGroup("&#9986;", "Split into",
                     toolNumber(ways, 1, Math.max(2, wide), where + "-ways",
                                function (value) { run.ways = value; }, "Split into"),
                     parts, lengths));
}

// A run's stretches as its bar draws them, in order
export function barCells(run) {
  var bar = run.strip ? run.id + "Bar" : run === mono ? "monoBar" : "outBar";
  return Array.prototype.slice.call(document.querySelectorAll("#" + bar + " .bar > .sec"));
}

// One outlined group, its icon and words, then what is put inside it
function toolGroup(icon, words, ...inside) {
  return h("span", {className: "toolset"},
           h("span", {className: "toolsays"}, h("span", {"aria-hidden": "true", html: icon}),
             " " + words),
           inside);
}

// A button inside a group that does what the group says
function toolAct(words, off, act, title) {
  return h("button", {type: "button", className: "toolact", disabled: off, title: title,
                      "data-act": act}, words);
}

// Fit every bar to its scroller. A cut's label is centred on the cut and takes its room while
// hidden, so near either end it would overhang and make an unzoomed bar scroll. A label within
// 40px of an end is turned inward, and only a zoomed bar scrolls
function fitBars() {
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
stripDrawing.bar = renderStripBar;
stripDrawing.fit = fitBars;

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
