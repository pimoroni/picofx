
// ---- the hub's positions in groups -----------------------------------------------------------
// With a look beside every picture, two positions showing the same picture could differ in a
// setting no drawing makes plain, and so be sent apart. So positions are put in groups, and a
// group is set as one: one picture, one turn, one look, sent once to all of it. A group is the
// scene's, as what it shows is, so each scene can group the hub its own way.
//
// Groups are numbered 1 to 3, six positions holding at most three groups of two or more, and
// each has its colour. Under every position are the three numbers and which group it is in:
// pressing a number puts the position in that group, taking what the group shows, and pressing
// it again leaves the position on its own, keeping what it shows. Pressing a position picks its
// group for the strip, and a picture goes to a group or a position on its own, never to one
// member of a group. A group holds one panel size only, the two sizes being sent apart.

var GROUP_NUMBERS = ["1", "2", "3"];
var GROUP_INKS = {"1": "#d98a1a", "2": "#2f9e6a", "3": "#d0508a"};

// A position on its own is its own group, named by its letter
HUB_PLACES.forEach(function (place) { state.places[place].group = place; });

function groupOf(place) { return state.places[place].group; }

function inNumberedGroup(place) { return GROUP_NUMBERS.indexOf(groupOf(place)) >= 0; }

// The positions in a position's group, in the hub's order
function membersOf(place) {
  return placesThere().filter(function (other) { return groupOf(other) === groupOf(place); });
}

function membersOfGroup(number) {
  return placesThere().filter(function (place) { return groupOf(place) === number; });
}

// What a picture or the strip is sent to: each group with a member, in number order, then each
// position on its own, in the hub's order
function sendTargets() {
  var targets = GROUP_NUMBERS.filter(function (number) {
    return membersOfGroup(number).length;
  }).map(function (number) {
    return {name: number, places: membersOfGroup(number), ink: GROUP_INKS[number]};
  });
  placesThere().forEach(function (place) {
    if (!inNumberedGroup(place)) targets.push({name: place, places: [place], ink: null});
  });
  return targets;
}

// ---- each scene keeps its positions' looks and the hub's light --------------------------------

HUB_PLACES.forEach(function (place) { state.places[place].look = freshLook(); });
state.hubLight = 1;

// Each position keeps one look object for good, as a screen does
var placeLookHomes = {};
HUB_PLACES.forEach(function (place) { placeLookHomes[place] = state.places[place].look; });

bodyParts.push({
  capture: function (body) {
    HUB_PLACES.forEach(function (place) {
      body.places[place].look = Object.assign({}, state.places[place].look);
    });
    body.hubLight = state.hubLight;
  },
  apply: function (body) {
    HUB_PLACES.forEach(function (place) {
      var home = placeLookHomes[place];
      if (body.places && body.places[place].look) Object.assign(home, body.places[place].look);
      state.places[place].look = home;
    });
    if (body.hubLight !== undefined) state.hubLight = body.hubLight;
  }
});

// ---- each scene keeps its groups ---------------------------------------------------------------

bodyParts.push({
  capture: function (body) {
    HUB_PLACES.forEach(function (place) { body.places[place].group = groupOf(place); });
  },
  apply: function (body) {
    HUB_PLACES.forEach(function (place) {
      if (body.places && body.places[place].group)
        state.places[place].group = body.places[place].group;
    });
  }
});

// ---- joining, leaving, and a group set as one --------------------------------------------------

// Whether a position can join a group, which holds one panel size
function sizeFits(place, number) {
  var others = membersOfGroup(number).filter(function (other) { return other !== place; });
  return !others.length || state.hub.sizes[others[0]] === state.hub.sizes[place];
}

// Joining takes what the group shows, a first member setting it; leaving keeps what it shows
function joinOrLeave(place, number) {
  if (groupOf(place) === number) {
    state.places[place].group = place;
    placePicked = place;
    return;
  }
  var others = membersOfGroup(number).filter(function (other) { return other !== place; });
  state.places[place].group = number;
  placePicked = others.length ? others[0] : place;
}

// What the picked position was given goes to the rest of its group before anything is drawn
// or written. Only the picked position's settings are shown, so it is the one changed
function settleGroups() {
  // A position of another size than its group's first leaves it for its own
  placesThere().forEach(function (place) {
    var first = membersOf(place)[0];
    if (state.hub.sizes[place] !== state.hub.sizes[first]) state.places[place].group = place;
  });
  if (!placeThere(placePicked)) return;
  // The picked position takes its starting turn for a new picture first, and the rest take
  // that turn with the picture, so none recalls a turn of its own from before it was grouped
  placeTurnForChosen(placePicked);
  var from = state.places[placePicked];
  membersOf(placePicked).forEach(function (place) {
    if (place === placePicked) return;
    var held = state.places[place];
    held.shows = from.shows;
    held.turn = from.turn;
    held.pingpong = from.pingpong;
    held.hold = from.hold;
    held.lastShows = from.shows;
    if (from.shows) held.turns[from.shows] = from.turn;
    Object.assign(held.look, from.look);
  });
}

drawSteps.before.push(settleGroups);

// ---- pictures go to groups ---------------------------------------------------------------------

// Under each picture, the groups and the positions on their own, then all. A picture on a
// group shows on every member, and pressing it again takes it off
assetSteps.push(function () {
  if (!state.hub.on) return;
  var targets = sendTargets();
  document.querySelectorAll("#assets .asset").forEach(function (cell, at) {
    var name = state.media[at].name;
    var pick = cell.querySelector(".pick");
    pick.textContent = "";
    targets.forEach(function (target) {
      var shown = target.places.every(function (place) {
        return state.places[place].shows === name;
      });
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = target.name;
      button.dataset.target = target.name;
      button.className = shown ? "lit" : "";
      if (shown && target.ink) button.style.background = target.ink;
      button.title = target.ink ? "Group " + target.name + ", " + placesSaid(target.places)
                                : target.name + ", on its own";
      button.onclick = function () {
        placePicked = target.places[0];
        state.places[placePicked].shows = shown ? null : name;
        draw();
      };
      pick.appendChild(button);
    });
    // Every group and every position on its own at once, the groups left as they are, or off
    // every one where it shows on all
    var everywhere = placesThere().length && placesThere().every(function (place) {
      return state.places[place].shows === name;
    });
    var all = document.createElement("button");
    all.type = "button";
    all.className = "all" + (everywhere ? " lit" : "");
    all.textContent = "all";
    all.title = "On every group and every position on its own, keeping the groups";
    all.disabled = !placesThere().length;
    all.onclick = function () {
      placesThere().forEach(function (place) {
        state.places[place].shows = everywhere ? null : name;
      });
      draw();
    };
    pick.appendChild(all);
  });
});

// ---- the hub's light ---------------------------------------------------------------------------

// The hub's one backlight is a row of its own across the top of the box, over all six
// positions and apart from whatever group is being set, since it lights every screen
hubHeadSteps.push(function () {
  var body = document.querySelector("#screensHead .hubbox .body");
  if (!body) return;
  // What each position shows, a slideshow named as its folder
  body.querySelectorAll(".place").forEach(function (tile) {
    var says = tile.querySelector(".placesays");
    var held = state.places[tile.dataset.place];
    if (says && held && held.shows) says.textContent = pictureSaid(held.shows);
  });
  var row = lightRow(state.hubLight, function (value) { state.hubLight = value; },
                     "backlight, every screen on the hub",
                     "How brightly the hub's screens are lit, all six together, in this scene");
  row.classList.add("hublightrow");
  row.querySelector(".lightopt").classList.add("hublight");
  body.insertBefore(row, body.firstChild);
});

// ---- drawing the groups -----------------------------------------------------------------------

// Every group wears its colour on each member, its outline and letter, and under every position
// are the three numbers. The group being set is filled with a tint of its colour, which is the
// only mark of being picked
hubHeadSteps.push(function () {
  // How the groups are sent is said under the positions that make them, above what is set
  var pace = document.querySelector("#screensHead .hubpace");
  var strip = document.querySelector("#screensHead .hubsettings");
  if (pace && strip) strip.parentNode.insertBefore(pace, strip);
  // What is being set wears the colour of the group it is for, a position on its own the hub's
  if (strip && placeThere(placePicked) && inNumberedGroup(placePicked))
    strip.style.setProperty("--hub", GROUP_INKS[groupOf(placePicked)]);
  var picked = placeThere(placePicked) ? membersOf(placePicked) : [];
  // The screens each position goes out with, as the file writes them, so a position on its own
  // set just as others are can say it matches them
  var sentWith = {};
  placeGroups(capture()).forEach(function (send) {
    send.places.forEach(function (place) { sentWith[place] = send.places; });
  });
  document.querySelectorAll("#screensHead .place").forEach(function (tile) {
    var place = tile.dataset.place;
    if (!placeThere(place)) return;
    var ink = inNumberedGroup(place) ? GROUP_INKS[groupOf(place)] : null;
    tile.classList.toggle("grouped", !!ink);
    if (ink) {
      tile.querySelector(".placename").style.color = ink;
      tile.style.setProperty("--group", ink);
    }
    tile.classList.toggle("picked", picked.indexOf(place) >= 0);

    var numbers = document.createElement("span");
    numbers.className = "groupseg";
    GROUP_NUMBERS.forEach(function (number) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = number;
      var inIt = groupOf(place) === number;
      button.className = inIt ? "on" : "";
      if (inIt) button.style.background = GROUP_INKS[number];
      var fits = sizeFits(place, number);
      button.disabled = !fits;
      button.title = !fits ? "Group " + number + " holds " +
                             state.hub.sizes[membersOfGroup(number)[0]] + "\" panels, and " +
                             place + " is " + state.hub.sizes[place] + "\""
                   : inIt ? "Take " + place + " out of group " + number + ", keeping what it shows"
                          : "Put " + place + " in group " + number +
                            (membersOfGroup(number).length ? ", showing what it shows" : "");
      button.onclick = function (event) {
        event.stopPropagation();
        joinOrLeave(place, number);
        draw();
      };
      numbers.appendChild(button);
    });
    tile.appendChild(numbers);
    // Which screens it shares a group with, as a range the way the file names them, so a full
    // group still fits: "grouped with B-F". A group of one says so, its number being lit. A
    // position on its own says which it matches, being sent with them until a setting differs
    var others = membersOf(place).filter(function (other) { return other !== place; });
    var matching = (sentWith[place] || []).filter(function (other) { return other !== place; });
    var said = document.createElement("small");
    said.className = "groupsaid";
    said.textContent = ink ? (others.length ? "grouped with " + placesSaid(others)
                                            : "alone in group " + groupOf(place))
                     : matching.length ? "matches " + placesSaid(matching) : "on its own";
    if (ink) said.style.color = ink;
    said.title = said.textContent;
    tile.appendChild(said);
  });
});

// How fast the hub plays what it shows. A still picture is sent once and costs nothing after, so
// only the animations share the frames between them: one plays as fast as a single screen,
// sent at once to every screen of its group, and several share the speed, each slower than
// it would be alone. A group showing nothing costs nothing and is not named
// Screens named in the note are bold, so "A plays" reads as the screen and not as a word. The
// letters and their commas and dashes are all the markup holds
function screensBold(places) { return "<b>" + placesSaid(places) + "</b>"; }

function namesSaid(sends) {
  var names = sends.map(function (send) { return screensBold(send.places); });
  return names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1]
                          : names[0];
}

// What makes a send differ from another showing the same picture, in the words the settings
// use, so it is plain why they are sent apart
function differences(send, from) {
  var one = send.playing;
  var other = from.playing;
  var look = one.look || LOOK_START;
  var base = other.look || LOOK_START;
  var words = [];
  if (state.hub.sizes[send.places[0]] !== state.hub.sizes[from.places[0]])
    words.push("a " + state.hub.sizes[send.places[0]] + "\" panel");
  if (Number(one.turn || 0) !== Number(other.turn || 0))
    words.push(Number(one.turn || 0) ? "turned " + one.turn + "\u00b0" : "not turned");
  if (look.mirror !== base.mirror) words.push(look.mirror ? "mirrored" : "not mirrored");
  if (look.anchor !== base.anchor || look.x !== base.x || look.y !== base.y)
    words.push(look.anchor !== null && look.anchor !== undefined
               ? "placed " + ANCHOR_NAMES[look.anchor]
               : "placed at " + (look.x === "" ? "centre" : look.x) + ", " +
                 (look.y === "" ? "centre" : look.y));
  // Tiling said for the sides it fills: across, down, or both
  var across = look.tile;
  var down = look.tileDown || "off";
  if (across !== base.tile || down !== (base.tileDown || "off")) {
    var sides = across !== "off" && down !== "off" ? "" : across !== "off" ? " across" : " down";
    var mirrored = across === "mirror" || down === "mirror" ? ", mirrored" : "";
    words.push(across === "off" && down === "off" ? "not tiled" : "tiled" + sides + mirrored);
  }
  if (look.double !== base.double) words.push(look.double ? "pixel doubled" : "not doubled");
  if (look.bg !== base.bg) words.push("on " + groundSaid(look.bg));
  // Playback as the file writes it, which a still picture takes none of
  var kind = kindOf(one.shows);
  var played = playingTokens(one, look, kind, state.hub.sizes[send.places[0]]);
  var basePlayed = playingTokens(other, base, kind, state.hub.sizes[from.places[0]]);
  function paced(tokens) { return tokens.filter(function (t) { return /^(fps|interval)=/.test(t); }); }
  function sized(tokens) { return tokens.filter(function (t) { return /^(width|height)=/.test(t); }); }
  function looped(tokens) {
    return tokens.filter(function (t) { return !/^(fps|interval|width|height)=/.test(t); });
  }
  if (paced(played).join() !== paced(basePlayed).join()) words.push("paced differently");
  if (sized(played).join() !== sized(basePlayed).join()) words.push("drawn on another canvas");
  if (looped(played).join() !== looped(basePlayed).join()) words.push("played differently");
  return words;
}

function listSaid(words) {
  return words.length > 1 ? words.slice(0, -1).join(", ") + " and " + words[words.length - 1]
                          : words[0];
}

// Where one picture goes out in several sends, which happens when some of its screens are set
// differently, a sentence naming how, against the plainest of them: the one least changed from
// how a screen starts, the one on most screens where that is a tie
function plainness(send) {
  return differences(send, {places: send.places,
                            playing: {turn: 0, pingpong: false, hold: "", look: LOOK_START}}).length;
}

function apartSaid(sends) {
  var byPicture = {};
  sends.forEach(function (send) {
    (byPicture[send.playing.shows] = byPicture[send.playing.shows] || []).push(send);
  });
  var told = [];
  var bases = [];
  Object.keys(byPicture).forEach(function (picture) {
    var group = byPicture[picture];
    if (group.length < 2) return;
    var base = group.slice().sort(function (a, b) {
      return plainness(a) - plainness(b) || b.places.length - a.places.length;
    })[0];
    group.forEach(function (send) {
      if (send === base) return;
      var words = differences(send, base);
      if (words.length)
        told.push(screensBold(send.places) + (send.places.length > 1 ? " are " : " is ") +
                  listSaid(words));
    });
    bases.push(screensBold(base.places));
  });
  if (!told.length) return "";
  var several = told.length > 1 || sends.some(function (send) {
    return told[0].indexOf(screensBold(send.places) + " are ") === 0;
  });
  return listSaid(told) + ", so " + (told.length > 1 ? "each is" : several ? "they are" : "it is") +
         " sent apart from " + listSaid(bases) + ".";
}
