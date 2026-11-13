import {h, replace} from "../../00_dom.js";
import {OTHER_EXAMPLES, exampleSections, isExampleMedia} from "../../26_drive_files.js";
import {openingString} from "../../26_drive_programs.js";
import {
  discoverBar, discoverBin, discoverBinBeside, discoverDivider, discoverDrawings, discoverKinds,
  discoverPictureSaid, discoverPill, discoverThumbImage, discoverThumbs
} from "../28_discover.js";
import {galleryExamples, mediaNamed} from "../../screens/12_screens.js";
import {copyDrawing, drawingInk, drawingSaid} from "../../screens/16_screen_settings.js";

galleryExamples.offer = function (groupTitles) {
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
  return {bar: discoverBar("drawing"), dividers: dividers};
};

galleryExamples.addToTile = function (tile, name) {
  var media = mediaNamed(name);
  if (media && isExampleMedia(name))
    discoverBinBeside(tile, discoverBin(name, media.kind === "drawing" ? "drawing" : "picture"));
  var pill = discoverPill(name);
  if (pill) tile.appendChild(pill);
};

function discoverOfferFigure(face, title, said, hint) {
  return h("figure", {title: hint || null}, face,
    h("figcaption", {}, h("strong", {}, title), h("small", {}, said || "")));
}

function discoverDrawingFace(path) {
  if (discoverDrawings[path].kind === "picture") return discoverPictureFace(path);
  var drawing = discoverDrawings[path].drawing;
  var face = h("div");
  function made() {
    face.dataset.drawn = "";
    face.style.setProperty("--ink", drawingInk(drawing, path));
    replace(face, h("b", {}, drawing.icon || drawing.title[0]));
  }
  if (discoverThumbs[path]) {
    var picture = discoverThumbImage(path);
    picture.onerror = made;
    face.appendChild(picture);
  } else {
    made();
  }
  return discoverOfferFigure(face, drawing.title, drawing.description, drawing.description);
}

function discoverPictureFace(path) {
  var picture = discoverDrawings[path].picture;
  return discoverOfferFigure(
    h("div", {}, discoverThumbs[path] ? discoverThumbImage(path) : null,
      picture.slideshow ? h("small", {}, "slideshow") : null),
    picture.title, discoverPictureSaid(picture));
}

discoverKinds.drawing = {
  said: function (source) { return drawingSaid(openingString(source)); },
  copy: copyDrawing,
  onDrive: mediaNamed,
  face: discoverDrawingFace
};
discoverKinds.picture = discoverKinds.drawing;
