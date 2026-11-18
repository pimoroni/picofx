import {lampsMovable} from "./board.js";
import {h, replace} from "./dom.js";
import {PAINT_ORDER, addStep, draw, drawParts, paintSteps} from "./draw.js";
import {groupOpen, groupsOpen} from "./drive_files.js";
import {LOOK_GROUPS} from "./figures.js";
import {paletteMark, takesColour, targetFor} from "./lines.js";
import {LOOKS, canPlay, isBanked, lookNamed, whyNot} from "./looks.js";
import {
  CHANNEL_INKS, isChannel, kinOf, sameLamp, selectorFor, shortName, widthOf
} from "./outputs.js";
import {beat, livePlay, painters} from "./preview.js";
import {foldHead} from "./program.js";
import {
  CARD_LIGHTS, MIDDLING, active, canEdit, cardFaces, cardWalks, carrying_lamp, dragged, galleryRun,
  haveKind, inkAt, lampKey, landLook, mono, outs, pick, remember, setCarryingLamp, setHolding,
  setShowing, showing, stretchFor, uncut
} from "./runs.js";
import {state, stretchUnder, underSaid} from "./scenes.js";
import {carded, cellSays, cutPoint, washOf} from "./stretch_bar.js";
import {bringForward, crossing, moveLamp, showKin} from "./wiring.js";

// ---- the look gallery ---------------------------------------------------------------------------
// The cards of the looks the chosen stretch can play, in their groups and each lit as it plays,
// and the outputs' bars of stretches and their lamps.

function lookCard(isMono, look, on) {
  var cells = [];
  if (look.name) {
    for (var i = 0; i < CARD_LIGHTS; i++) cells.push(h("span"));
    cardFaces.push({cells: cells, look: look, mono: isMono,
                    key: (isMono ? "m" : "c") + "-" + look.name});
  }
  var coloured = !isMono && takesColour(lookNamed(look.name));
  // In a scene, a stretch playing nothing shows Always on's look or goes dark as the board decides,
  // so Nothing there is not the same as off
  return h("button", {
    type: "button", "aria-pressed": String(!!on), "data-look": look.name || "",
    className: "card" + (on ? " picked" : "") + (look.name ? "" : " nothing"),
    title: (look.name ? look.name + ": apply it to the selected stretch"
            : state.at >= 0 ? "Play nothing of this scene's own on the selected stretch"
            : "turn a stretch off") + (coloured ? ". You can choose its colour" : ""),
    onclick: function () {
      var run = galleryRun(isMono);
      landLook(run, stretchFor(run, isMono), look.name);
    }
  }, h("div", {className: "face"}, cells),
     h("div", {className: "name"}, look.name || "Nothing"),
     coloured ? paletteMark() : null);
}

// The looks a run of several lamps can play, a banked one dealing its banks along it
function spanning() {
  return LOOKS.filter(function (look) { return look.spans || isBanked(look); });
}

function paintCards() {
  cardFaces.forEach(function (one) {
    var store = cardWalks[one.key] || (cardWalks[one.key] = {});
    one.cells.forEach(function (cell, i) {
      var walk = store[i] || (store[i] = {});
      var lit = livePlay(one.look, MIDDLING, beat, i, CARD_LIGHTS, walk);
      cell.style.background = lit
        ? inkAt({level: lit.level, ink: one.mono ? "#ffd9a0" : lit.ink})
        : "#3a3f44";
    });
  });
}
addStep(paintSteps, PAINT_ORDER, "cards", paintCards);

// Draw the cards for whatever stretch was last picked, a shelf of what that stretch can play
function renderGalleries() {
  // Check if the board has none of the kind shown but some of the other, and show that, or the
  // cards would be for lights that are not there
  if (!haveKind(showing) && haveKind(!showing)) setShowing(!showing);

  var run = galleryRun(showing);
  var section = run.sections[run === active ? run.picked : stretchFor(run, showing)];
  var lamp = section && run.lamps[section.from];

  // What the stretch being worked on could actually be given. A look shaped to several
  // lamps has nothing to say on a stretch of one, and the model would clear it the moment
  // it landed, so the card says so and does not take it only to quietly drop it
  var target = section ? targetFor(run, section) : null;

  replace(document.getElementById("looks"),
          h("div", {className: "tabs sides"}),
          h("div", {className: "shelf bare"},
            h("div", {className: "gallery"}, spanning().concat([{name: null}]).map(function (look) {
              var can = !look.name || !target || canPlay(look, target);
              var on = can && lamp && lamp.colour === !showing && section.look === look.name;
              var card = lookCard(showing, look, on);
              if (!can) {
                card.className += " cannot";
                card.onclick = null;
                // Still reachable, so its tooltip can say why it cannot be chosen
                card.setAttribute("aria-disabled", "true");
                card.title = whyNot(look, target);
              }
              return card;
            }))));
  groupGallery();
}
drawParts.galleries = renderGalleries;

// ---- the lamps, lit and put in place -------------------------------------------------------

// Light each lamp's face as it plays, where faces[at] is the face of the run's lamp at `at`. A lamp
// playing nothing of its own is marked unset, which its holder shows
function paintFaces(faces, all) {
  faces.forEach(function (face, at) {
    var one = all[at] || {level: 0, ink: "#e4e0d9"};
    face.style.background = one.nothing ? "#2a2d30" : inkAt(one);
    face.parentNode.classList.toggle("unset", !!one.unset);
    face.style.boxShadow = one.level > 0.05
      ? "inset 0 0 0 1px rgba(0,0,0,.2), 0 0 " + (3 + one.level * 8).toFixed(1) +
        "px rgba(255,217,160," + (one.level * 0.5).toFixed(2) + ")"
      : "inset 0 0 0 1px rgba(0,0,0,.2)";
  });
}

// Make a lamp a tile dragged to where it sits on the build. A colour output is one lamp so it
// moves whole, and a broken-out one moves a channel at a time, since its three LEDs are three
// separate things once the adapter is on
function takesPlace(node, lamp) {
  var me = {out: lamp.out, channel: lamp.colour ? null : lamp.channel};
  node.draggable = true;
  node.addEventListener("dragstart", function (event) {
    setCarryingLamp(me);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", shortName(lamp));
    node.classList.add("carried");
  });
  node.addEventListener("dragend", function () {
    setCarryingLamp(null);
    draw();
  });
  // Put down on a lamp's right half, the carried one goes after it, the only way to reach the end
  function after(event) {
    var box = node.getBoundingClientRect();
    return event.clientX > box.left + box.width / 2;
  }
  node.addEventListener("dragover", function (event) {
    if (!carrying_lamp || sameLamp(carrying_lamp, me)) return;
    event.preventDefault();
    node.classList.add("landing");
    node.classList.toggle("after", after(event));
  });
  node.addEventListener("dragleave", function () { node.classList.remove("landing", "after"); });
  node.addEventListener("drop", function (event) {
    event.preventDefault();
    node.classList.remove("landing", "after");
    if (!carrying_lamp || sameLamp(carrying_lamp, me)) return;
    var carried = carrying_lamp;
    setCarryingLamp(null);
    moveLamp({from: carried, to: me, after: after(event)});
  });
  if (!lampsMovable()) node.draggable = false;
  // Every lamp can be found by what it is, which is what the lines and the slide go by
  var key = lampKey(me);
  node.dataset.key = key;
  node.addEventListener("mouseenter", function () { bringForward([key], true); });
  node.addEventListener("mouseleave", function () { bringForward([key], false); });
}

// Gather the gallery's cards under the groups' headings, in the groups' order
function groupGallery() {
  var flat = document.querySelector("#looks .gallery");
  if (!flat) return;
  var cards = {};
  var order = [];
  var nothing = null;
  Array.prototype.slice.call(flat.children).forEach(function (card) {
    if (card.classList.contains("nothing")) {
      nothing = card;
      return;
    }
    var name = card.querySelector(".name").textContent;
    cards[name] = card;
    order.push(name);
  });

  var named = [].concat.apply([], LOOK_GROUPS.map(function (group) { return group.looks; }));
  var groups = LOOK_GROUPS.map(function (group) {
    return {name: group.name, says: group.says,
            looks: group.looks.filter(function (name) { return cards[name]; })};
  });
  var rest = order.filter(function (name) { return named.indexOf(name) < 0; });
  if (rest.length) groups.push({name: "More", says: "", looks: rest});
  groups = groups.filter(function (group) { return group.looks.length; });

  flat.replaceWith(h("div", {className: "groupedlooks"}, groups.map(function (group, at) {
    // Each heading folds its group, and every group starts open. Nothing sits beside the first
    // heading and not in it, so it is never folded away
    var key = "looks:" + group.name;
    var open = groupOpen([key, "", [], false]);
    var fold = foldHead(group.name, group.says, open, function () {
      groupsOpen[key] = !open;
    });
    // The row is the heading here, the button only its part that folds
    fold.classList.remove("gallery-head");
    if (at === 0 && nothing) nothing.classList.add("small");
    return [h("div", {className: "gallery-head lookshead"}, fold, at === 0 ? nothing : null),
            open ? h("div", {className: "gallery", "data-group": group.name},
                     group.looks.map(function (name) { return cards[name]; }))
                 : null];
  })));
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

function renderBar(where, run) {
  var faces = [];
  replace(document.getElementById(where),
          h("div", {className: "scroller"},
            h("div", {className: "bar" + (carded(run) ? " carded" : "")},
              run.sections.map(function (section, at) {
                return [barCell(run, section, at, faces),
                        at < run.sections.length - 1 ? barEdge(run, at, where) : null];
              }))));
  if (carded(run)) painters.push({run: run, paint: function (all) { paintFaces(faces, all); }});
}

// A stretch of the outputs as a card, with its lamps where carded, its look's wash, name and cuts
function barCell(run, section, at, faces) {
  var first = run.lamps[section.from];
  var lamps = carded(run) ? cardLamps(run, section, faces) : null;
  var look = lookNamed(section.look);
  var under = look ? null : stretchUnder(run, section);
  var cuts = [];
  // Where this stretch can be cut, one place between each two lights
  for (var i = section.from; i < section.to; i++) {
    cuts.push(cutPoint(run, i, widthOf(section), section.from));
  }
  // A lamp is dragged out of its card while the wiring is set up, which a button would not let go
  return h(carded(run) && canEdit("outPanel") ? "div" : "button", {
    className: "sec" + (run === active && run.picked === at ? " picked" : ""),
    style: {flex: widthOf(section) + " 1 0"},
    title: under ? under.tip
                 : (first && first.colour ? "colour" : "mono") + ", " +
                   targetFor(run, section).selector,
    onclick: function () {
      if (dragged) return;
      pick(run, at);
      draw();
    }
  }, lamps, washOf(run, section, look, under), cellSays(look, widthOf(section), under),
     h("span", {className: "cuts"}, cuts));
}

// The cut a stretch shares with the next, dragged to move it or taken out to join the two stretches
function barEdge(run, at, where) {
  var edge = h("div", {
    className: "edge", title: "drag to move this cut, or click \u00d7 to remove it",
    onmousedown: function (event) {
      event.preventDefault();
      remember(run);
      // The stretch being resized is the one being worked on, whichever side it is on
      pick(run, at);
      // The bar is rebuilt on every move, so what is held onto is where the bar lives and not the
      // bar itself, which would be a node already thrown away
      setHolding({run: run, which: at, where: where, had: run.sections.length});
      edge.classList.add("holding");
    }
  }, // Taking the cut out is its own target, so it is never confused with moving it
     h("button", {
       className: "drop", title: "remove this cut and join the two stretches",
       onmousedown: function (event) { event.stopPropagation(); },
       onclick: function (event) {
         event.stopPropagation();
         uncut(run, at);
       }
     }, "\u00d7"));
  return edge;
}
drawParts.bars = function () {
  renderBar("outBar", outs);
  renderBar("monoBar", mono);
};

// A stretch's lamps, one for each light it holds, each face kept in faces by the lamp's place
// in the run so it can be lit as the run plays. While the wiring is set up, each lamp is a tile
// to drag to its place on the build, and an output that breaks out has its arrow on its tiles
function cardLamps(run, section, faces) {
  var wiring = canEdit("outPanel");
  var playing = lookNamed(section.look);
  var lamps = [];
  for (var at = section.from; at <= section.to; at++) {
    var lamp = run.lamps[at];
    var channel = !lamp.colour && isChannel(lamp);
    faces[at] = h("i");
    // A broken-out channel is marked in its channel's colour
    var one = h("span", {
      className: "cardlamp" + (channel ? " chan" : ""),
      style: {"--chan": channel ? CHANNEL_INKS[lamp.channel] : null},
      title: selectorFor(lamp) + (playing ? ", playing " + playing.name : underSaid(run, at))
    }, faces[at], h("b", {}, shortName(lamp)));
    if (wiring) setUpLamp(one, lamp, channel);
    lamps.push(one);
  }
  return h("span", {className: "cardlamps"}, lamps);
}
