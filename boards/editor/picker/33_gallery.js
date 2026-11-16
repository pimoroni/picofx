import {draw} from "./00_draw.js";
import {LOOKS, isBanked, lookNamed} from "./01_looks.js";
import {beat, livePlay} from "./02_preview.js";
import {paletteMark, takesColour} from "./03_lines.js";
import {sameLamp, shortName} from "./03_outputs.js";
import {
  CARD_LIGHTS, MIDDLING, cardFaces, cardWalks, carrying_lamp, galleryRun, inkAt, lampKey, landLook,
  stretchFor
} from "./03_runs.js";
import {state} from "./04_scenes.js";
import {lampsMovable} from "./07_board.js";
import {bringForward, moveLamp} from "./09_wiring.js";
import {foldHead} from "./22_program.js";
import {LOOK_GROUPS} from "./25_figures.js";
import {groupOpen, groupsOpen} from "./26_drive_files.js";

// ---- the look gallery ---------------------------------------------------------------------------
// The cards of the looks the chosen stretch can play, in their groups, each lit as it plays.

export function lookCard(isMono, look, on) {
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
export function spanning() {
  return LOOKS.filter(function (look) { return look.spans || isBanked(look); });
}

export function paintCards() {
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

// ---- the lamps, lit and put in place -------------------------------------------------------

// Light each lamp's face as it plays, faces[at] being the face of the run's lamp at `at`. A lamp
// playing nothing of its own is marked unset, which its holder shows
export function paintFaces(faces, all) {
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
export function takesPlace(node, lamp) {
  var me = {out: lamp.out, channel: lamp.colour ? null : lamp.channel};
  node.draggable = true;
  node.addEventListener("dragstart", function (event) {
    carrying_lamp = me;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", shortName(lamp));
    node.classList.add("carried");
  });
  node.addEventListener("dragend", function () {
    carrying_lamp = null;
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
    carrying_lamp = null;
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
export function groupGallery() {
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
