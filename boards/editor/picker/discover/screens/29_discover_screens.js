import {h} from "../../00_dom.js";
import {escapeHtml} from "../../03_runs.js";
import {OTHER_EXAMPLES, exampleSections, isExampleMedia} from "../../26_drive_files.js";
import {openingString} from "../../26_drive_programs.js";
import {
  discoverBin, discoverBinBeside, discoverDivider, discoverDrawings, discoverElement,
  discoverKinds, discoverPictureSaid, discoverPill, discoverPlaceBar, discoverThumbImage,
  discoverThumbs
} from "../28_discover.js";
import {galleryExamples, mediaNamed} from "../../screens/12_screens.js";
import {copyDrawing, drawingInk, drawingSaid} from "../../screens/16_screen_settings.js";

// ---- examples to discover, on the Screens tab ---------------------------------------------------
// The Screens tab's examples line, where its example drawings and pictures start, and the rules
// naming each kind where the drive has both. An example on the drive can be deleted, as it can be
// downloaded again, and carries its mark, Update or the firmware it needs. 28_discover.js does
// the rest. A board without screens has no Screens tab to add them to.

galleryExamples.offer = function (groupTitles) {
  var holder = h("div");
  discoverPlaceBar(holder, "drawing");
  function firstOf(kind) {
    var groups = (exampleSections[kind] || []).map(function (one) { return one[0]; })
      .concat([OTHER_EXAMPLES[kind]]);
    return groupTitles.filter(function (title) { return groups.indexOf(title) >= 0; })[0];
  }
  var drawings = firstOf("drawings");
  var pictures = firstOf("pictures");
  var dividers = {};
  if (drawings && pictures) {
    dividers[drawings] = discoverDivider("Drawings", true);
    dividers[pictures] = discoverDivider("Pictures", true);
  }
  return {bar: holder.firstChild, dividers: dividers};
};

galleryExamples.addToTile = function (tile, name) {
  var media = mediaNamed(name);
  if (media && isExampleMedia(name))
    discoverBinBeside(tile, discoverBin(name, media.kind === "drawing" ? "drawing" : "picture"));
  var pill = discoverPill(name);
  if (pill) tile.appendChild(pill);
};

// A drawing as the Screens tab shows it, its thumbnail whole, or its icon or initial on its colour
// where it has none, in a face the shape of a program card's, so every card in a row is one height
function discoverDrawingFace(path) {
  if (discoverDrawings[path].kind === "picture") return discoverPictureFace(path);
  var drawing = discoverDrawings[path].drawing;
  var card = discoverElement("div", "asset discoveroffer");
  card.title = drawing.description || "";
  var face = discoverElement("div", "face");
  // Its icon or initial on its colour, where it has no thumbnail or the thumbnail will not load
  function made() {
    face.className = "face drawingface";
    face.style.background = drawingInk(drawing, path);
    face.innerHTML = drawing.icon
      ? "<span class='drawingicon'>" + escapeHtml(drawing.icon) + "</span>"
      : "<span class='drawingletter'>" + escapeHtml(drawing.title[0]) + "</span>";
  }
  if (discoverThumbs[path]) {
    var picture = discoverThumbImage(path);
    picture.onerror = made;
    face.appendChild(picture);
  } else {
    made();
  }
  card.appendChild(face);
  // Its name and what it does under the picture, as a program card has them
  card.appendChild(discoverElement("span", "progname", drawing.title));
  card.appendChild(discoverElement("span", "discoverdoes", drawing.description || ""));
  return card;
}

// A picture as a drawing's card has it, the picture itself in the face, a GIF playing, a slideshow
// by its first picture and tagged as one, its file or folder name and what it is under it
function discoverPictureFace(path) {
  var picture = discoverDrawings[path].picture;
  var card = discoverElement("div", "asset discoveroffer");
  var face = discoverElement("div", "face");
  if (discoverThumbs[path]) face.appendChild(discoverThumbImage(path));
  if (picture.slideshow) face.appendChild(discoverElement("span", "discoverkind", "slideshow"));
  card.appendChild(face);
  card.appendChild(discoverElement("span", "progname", picture.title));
  card.appendChild(discoverElement("span", "discoverdoes", discoverPictureSaid(picture)));
  return card;
}

discoverKinds.drawing = {
  said: function (source) { return drawingSaid(openingString(source)); },
  copy: copyDrawing,
  onDrive: mediaNamed,
  face: discoverDrawingFace
};
discoverKinds.picture = discoverKinds.drawing;
