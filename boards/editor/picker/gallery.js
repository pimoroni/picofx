import {lampsMovable} from "./board.js";
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
import {beneath, carded, cutPoint, washOf} from "./stretch_bar.js";
import {bringForward, crossing, moveLamp, showKin} from "./wiring.js";

// ---- the look gallery ---------------------------------------------------------------------------
// The cards of the looks the chosen stretch can play, in their groups, each lit as it plays.

function lookCard(isMono, look, on) {
  var card = document.createElement("div");
  card.className = "card" + (on ? " picked" : "") + (look.name ? "" : " nothing");
  var face = document.createElement("div");
  face.className = "face";
  if (look.name) {
    var cells = [];
    for (var i = 0; i < CARD_LIGHTS; i++) {
      var cell = document.createElement("span");
      face.appendChild(cell);
      cells.push(cell);
    }
    cardFaces.push({cells: cells, look: look, mono: isMono,
                    key: (isMono ? "m" : "c") + "-" + look.name});
  }
  card.appendChild(face);
  var name = document.createElement("div");
  name.className = "name";
  name.textContent = look.name || "Nothing";
  card.appendChild(name);

  // In a scene, a stretch playing nothing shows Always on's look or goes dark as the board decides,
  // so Nothing there is not the same as off
  card.title = look.name ? look.name + ": apply it to the selected stretch"
             : state.at >= 0 ? "Play nothing of this scene's own on the selected stretch"
             : "turn a stretch off";
  card.onclick = function () {
    var run = galleryRun(isMono);
    landLook(run, stretchFor(run, isMono), look.name);
  };
  if (!isMono && takesColour(lookNamed(look.name))) {
    card.appendChild(paletteMark());
    card.title += ". You can choose its colour";
  }
  return card;
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

// The cards follow whatever stretch was last picked, so the gallery is a shelf of what that
// stretch can play
function renderGalleries() {
  // A kind the board has none of cannot be worked on, so the set goes back to the one it
  // has. Without this the cards would be for lights that are not there
  if (!haveKind(showing) && haveKind(!showing)) setShowing(!showing);

  var box = document.getElementById("looks");
  box.textContent = "";

  var tabs = document.createElement("div");
  tabs.className = "tabs sides";
  box.appendChild(tabs);

  var run = galleryRun(showing);
  var section = run.sections[run === active ? run.picked : stretchFor(run, showing)];
  var lamp = section && run.lamps[section.from];

  // What the stretch being worked on could actually be given. A look shaped to several
  // lamps has nothing to say on a stretch of one, and the model would clear it the moment
  // it landed, so the card says so and does not take it only to quietly drop it
  var target = section ? targetFor(run, section) : null;

  var shelf = document.createElement("div");
  shelf.className = "shelf bare";
  box.appendChild(shelf);

  var looks = document.createElement("div");
  looks.className = "gallery";
  spanning().concat([{name: null}]).forEach(function (look) {
    var can = !look.name || !target || canPlay(look, target);
    var on = can && lamp && lamp.colour === !showing && section.look === look.name;
    var card = lookCard(showing, look, on);
    if (!can) {
      card.className += " cannot";
      card.onclick = null;
      card.title = whyNot(look, target);
    }
    looks.appendChild(card);
  });
  shelf.appendChild(looks);
  groupGallery();
}
drawParts.galleries = renderGalleries;

// ---- the lamps, lit and put in place -------------------------------------------------------

// Light each lamp's face as it plays, faces[at] being the face of the run's lamp at `at`. A lamp
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

// A lamp is dragged to where it sits on the build. A colour output is one lamp so it
// moves whole, and a broken-out one moves a channel at a time, since its three LEDs are
// three separate things once the adapter is on
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
  // Put down on a lamp's right half, the carried one goes after it, which is the only way
  // to reach the far end of the run
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

  var holder = document.createElement("div");
  holder.className = "groupedlooks";
  groups.forEach(function (group, at) {
    // Each heading folds its group, all starting open. Nothing sits beside the first heading
    // and not in it, so it is never folded away
    var head = document.createElement("div");
    head.className = "gallery-head lookshead";
    var key = "looks:" + group.name;
    var open = groupOpen([key, "", [], false]);
    var fold = foldHead(group.name, group.says, open, function () {
      groupsOpen[key] = !open;
    });
    // The row is the heading here, the button only its part that folds
    fold.classList.remove("gallery-head");
    head.appendChild(fold);
    if (at === 0 && nothing) {
      nothing.classList.add("small");
      head.appendChild(nothing);
    }
    holder.appendChild(head);
    if (!open) return;
    var row = document.createElement("div");
    row.className = "gallery";
    row.dataset.group = group.name;
    group.looks.forEach(function (name) { row.appendChild(cards[name]); });
    holder.appendChild(row);
  });
  flat.parentNode.replaceChild(holder, flat);
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
drawParts.bars = function () {
  renderBar("outBar", outs);
  renderBar("monoBar", mono);
};

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
