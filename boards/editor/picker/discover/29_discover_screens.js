
// ---- examples to discover, on the Screens tab ---------------------------------------------------
// The Screens tab's examples line, where its example drawings and pictures start, and the rules
// naming each kind where the drive has both. An example on the drive can be deleted, as it can be
// downloaded again, and carries its mark, Update or the firmware it needs. 28_discover.js does
// the rest. A board without screens has no Screens tab to add them to.

if (BOARD.screens) {
  assetSteps.push(function () {
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
}
