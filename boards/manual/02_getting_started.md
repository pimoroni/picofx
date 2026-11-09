## Getting started

Edit `effects.txt` and save it to change what the lights do. A few seconds later
the drive disappears briefly, then comes back with the new effects running, so
you can keep editing.

If a save does not seem to work, press **Boot** once or eject this drive, as a
computer does not always write the file straight away. Double-press **Boot** to
hide the drive, and double-press it again to show it.
<!-- if outputs -->
Each double press runs a __TRAVELLING_LIGHT__ along the outputs, towards the
USB connector when the drive is shown and away from it when it is hidden.
<!-- end -->

Deleting `effects.txt` restores the default file. Emptying it turns everything
off.

<!-- if outputs -->
While the computer copies files to this drive, the effects pause and a
__TRAVELLING_LIGHT__ travels along the outputs. The effects resume shortly
after the copy finishes.
<!-- end -->
<!-- if not outputs -->
While the computer copies files to this drive, the effects pause and the board's
LED glows dim white with a brighter blink. The effects resume shortly after the
copy finishes.
<!-- end -->

**Prefer not to write the file by hand? `PICKER.html` on this drive writes it
for you. See [the picker](#the-picker). `EDITOR.html` helps you write it,
suggesting names as you type. See [the editor](#the-editor).**

<!-- if examples -->
**The board also comes with ready-made programs, from single effects to whole
builds, and one line in `effects.txt` runs any of them. See [what is already
on the board](#what-is-already-on-the-board).**
<!-- end -->
