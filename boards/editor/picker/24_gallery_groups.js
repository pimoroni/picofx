
// ---- the looks in groups ------------------------------------------------------------------
// The gallery grouped by how the lights play together, each group a row of at most five, the
// width a row of cards has. The showiest come first: the travelling looks, Rainbow among them
// being what the board opens playing, then the ready-made ones, each a base look specialised
// or several of them together, then the plainest and the most specialised. The cards are the
// flat gallery's own, moved into their groups with everything they do, so a look no group
// names still shows, in a group of its own at the end. Nothing is no look of any group, so it
// is a card made small at the end of the first heading, where there is always room for it.

var LOOK_GROUPS = [
  {name: "Along the lights", says: "travelling from one end to the other",
   looks: ["Rainbow", "Wave", "Scanner", "Chase", "Marquee"]},
  {name: "Ready-made", says: "combinations of other looks",
   looks: ["Campfire", "Emergency", "Party"]},
  {name: "All together", says: "every light shows the same",
   looks: ["Solid", "Colour cycle", "Colour steps", "Breathe", "Blink"]},
  {name: "Individual", says: "each light plays its own part",
   looks: ["Sparkle", "Counter", "Traffic light", "Pelican crossing"]}
];

// The gallery's cards gathered under the groups' headings, in the groups' order
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
