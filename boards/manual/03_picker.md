## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page reads the file
the board is playing, so you carry on from where it is. The file it will write
is shown at the foot of the page, so nothing about it is hidden.

<!-- board picker_tabs -->

**A program** runs one of the board's programs in place of the effects:
__PROGRAMS_OFFERED__,
beside any programs of your own on this drive. Pick one and save, and the board
restarts to run it. [Your program in the picker](#your-program-in-the-picker)
says how a program of yours describes itself there.

**Save to board** writes the file, and the board picks it up a few seconds later.
Its arrow opens the save's settings: untick "Play saves without an eject" and the
board waits instead until this drive is ejected, or **Boot** is pressed once, and
"Keep the drive hidden at start" is `drive=manual`. **Check board** reads
`errors.txt` back and shows what the board made of each line. On a Mac each save
shows "Disk Not Ejected Properly" once and a Finder window on this drive closes;
the drive comes back on its own a few seconds later and the page carries on.

The page reaches the drive only in Chrome, Edge or another browser built on
Chromium. Safari and Firefox cannot write to a drive from a page, so there it
says so, and `effects.txt` can still be changed in any text editor.

What the picker writes is an ordinary `effects.txt`: anything it makes can be
edited by hand afterwards. A line it cannot write itself is kept as it is, and it
asks before replacing a file it has not read.
