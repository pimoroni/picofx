## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page loads the file
the board is playing, so you can carry on from there. A preview of the file it
will write is at the foot of the page.

<!-- board picker_tabs -->

<!-- if examples -->
**Programs** lists the board's programs, __PROGRAMS_OFFERED__, and any of
your own programs on this drive, to run instead of the effects.
<!-- end -->
<!-- if not examples -->
**Programs** lists your own programs on this drive, to run instead of the
effects.
<!-- end -->
Choose one and save, and the board restarts to run it. [Your program in the
picker](#your-program-in-the-picker) explains how your own programs appear there.

**Save to board** writes the file, and the board loads it a few seconds later.
The arrow beside it opens the save settings. Untick "Play saves without an eject"
and the board waits for an eject or a single press of **Boot**, which is
`reload=manual`. "Keep the drive hidden at start" is `drive=manual`. **Check
board** reads `errors.txt` and shows any problems the board found with each line.
On a Mac, each save shows "Disk Not Ejected Properly" once and closes any Finder
window on this drive. The drive comes back a few seconds later and the page
continues.

The page can only reach the drive in Chrome, Edge or another Chromium-based
browser. Safari and Firefox cannot write to a drive from a web page, so the
picker says so there, but `effects.txt` can still be edited in any text
editor.

The picker writes an ordinary `effects.txt`, so anything it makes can be edited
by hand afterwards. Lines the picker cannot edit are kept unchanged, and it asks
before replacing a file it has not read.
