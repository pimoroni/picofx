import {
  discoverBin, discoverBinBeside, discoverDivider, discoverDrawings, discoverKinds,
  discoverPictureSaid, discoverPill, discoverPlaceBar, discoverThumbImage, discoverThumbs
} from "../discover.js";
import {h, replace} from "../../dom.js";
import {addStep} from "../../draw.js";
import {OTHER_EXAMPLES, exampleSections, isExampleMedia} from "../../drive_files.js";
import {openingString} from "../../drive_programs.js";
import {state} from "../../scenes.js";
import {drawingInk} from "../../screens/screen_art.js";
import {copyDrawing} from "../../screens/screen_settings.js";
import {ASSET_ORDER, assetSteps, drawingSaid, mediaNamed} from "../../screens/screens.js";

// ---- examples to discover, on the Screens tab ---------------------------------------------------
// The Screens tab's examples line, where its example drawings and pictures start, and the rules
// naming each kind where the drive has both. An example on the drive can be deleted, as it can be
// downloaded again, and carries its mark, Update or the firmware it needs. discover.js does
// the rest. build_editor.py takes this folder only for a board with screens.

addStep(assetSteps, ASSET_ORDER, "discover", function () {
  var box = document.getElementById("assets");
  if (!state.fileHandle) return;
  discoverPlaceBar(box, "drawing");
  // The user's own group heads the gallery and is neither kind
  var heads = Array.from(box.querySelectorAll(".foldhead")).slice(1);
  function firstOf(kind) {
    var groups = (exampleSections[kind] || []).map(function (one) { return one[0]; })
      .concat([OTHER_EXAMPLES[kind]]);
    return heads.filter(function (head) {
      return groups.indexOf(head.firstChild.textContent) >= 0;
    })[0];
  }
  var drawings = firstOf("drawings"), pictures = firstOf("pictures");
  if (drawings && pictures) {
    box.insertBefore(discoverDivider("Drawings", true), drawings);
    box.insertBefore(discoverDivider("Pictures", true), pictures);
  }
  box.querySelectorAll(".asset").forEach(function (cell) {
    var name = cell.dataset.name;
    var media = mediaNamed(name);
    if (media && isExampleMedia(name))
      discoverBinBeside(cell, discoverBin(name, media.kind === "drawing" ? "drawing" : "picture"));
    var pill = discoverPill(name);
    if (pill) cell.appendChild(pill);
  });
});

// A drawing as the Screens tab shows it, its thumbnail whole, or its icon or initial on its colour
// where it has none, in a face the shape of a program card's, so every card in a row is one height
function discoverDrawingFace(path) {
  if (discoverDrawings[path].kind === "picture") return discoverPictureFace(path);
  var drawing = discoverDrawings[path].drawing;
  var face = h("div", {className: "face"});
  // Its icon or initial on its colour, where it has no thumbnail or the thumbnail will not load
  function made() {
    face.className = "face drawingface";
    face.style.background = drawingInk(drawing, path);
    replace(face, drawing.icon ? h("span", {className: "drawingicon"}, drawing.icon)
                               : h("span", {className: "drawingletter"}, drawing.title[0]));
  }
  if (discoverThumbs[path]) {
    var picture = discoverThumbImage(path);
    picture.onerror = made;
    face.appendChild(picture);
  } else {
    made();
  }
  // Its name and what it does under the picture, as a program card has them
  return h("div", {className: "asset discoveroffer", title: drawing.description || ""},
           face,
           h("span", {className: "progname"}, drawing.title),
           h("span", {className: "discoverdoes"}, drawing.description || null));
}

// A picture as a drawing's card has it, the picture itself in the face, a GIF playing, a slideshow
// by its first picture and tagged as one, its file or folder name and what it is under it
function discoverPictureFace(path) {
  var picture = discoverDrawings[path].picture;
  return h("div", {className: "asset discoveroffer"},
           h("div", {className: "face"},
             discoverThumbs[path] ? discoverThumbImage(path) : null,
             picture.slideshow ? h("span", {className: "discoverkind"}, "slideshow") : null),
           h("span", {className: "progname"}, picture.title),
           h("span", {className: "discoverdoes"}, discoverPictureSaid(picture)));
}

discoverKinds.drawing = {
  said: function (source) { return drawingSaid(openingString(source)); },
  copy: copyDrawing,
  onDrive: mediaNamed,
  face: discoverDrawingFace
};
discoverKinds.picture = discoverKinds.drawing;
