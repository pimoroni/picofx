## Getting started

Edit `effects.txt` to change what the lights do and save it, and the board plays
the change a few seconds later. The drive disappears for a moment and comes back
with the new effects running, so you can keep editing.

If a save does not seem to take, press **Boot** once or eject this drive, since
a computer does not always write the file out straight away. Press **Boot** twice
to hide the drive, and twice again to bring it back.
<!-- if outputs -->
A __TRAVELLING_LIGHT__ runs along the outputs each time, towards the USB
connector as the computer takes the drive and away from it as the board takes it
back, so a double press is never mistaken for a single one.
<!-- end -->

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

<!-- if outputs -->
While the computer is copying to this drive the effects stand aside for a
__TRAVELLING_LIGHT__ travelling along the outputs, and come back a moment after
it finishes.
<!-- end -->
<!-- if not outputs -->
While the computer is copying to this drive the effects stand aside, the board's
LED glowing a dim white with a brighter blink, and come back a moment after it
finishes.
<!-- end -->

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you. See [the picker](#the-picker). `EDITOR.html` beside it is a place to
write it with the names offered as you type. See [the editor](#the-editor).**

<!-- if examples -->
**The board also carries programs that run as they are, from single effects to
whole builds, and one line in `effects.txt` starts any of them. See
[what is already on the board](#what-is-already-on-the-board).**
<!-- end -->
