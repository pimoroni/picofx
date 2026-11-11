
// ---- examples to discover, on the Sound tab -----------------------------------------------------
// The Sound tab's examples line, where its example sounds start. An example sound on the drive
// can be deleted, as it can be downloaded again, and carries its mark, Update or the firmware it
// needs. 28_discover.js does the rest. A board without sound has no Sound tab to add them to.

if (BOARD.sound) {
  soundTileSteps.push(function (tile, name) {
    if (!name) return;
    tile.dataset.name = name;
    if (isExampleMedia(name) && state.sounds.indexOf(name) >= 0)
      tile.appendChild(discoverBin(name, "sound"));
    var pill = discoverPill(name);
    if (pill) tile.appendChild(pill);
  });

  soundSteps.push(function () {
    var row = document.querySelector("#sound .sounds");
    if (row && state.fileHandle) discoverPlaceBar(row, "sound");
  });
}
