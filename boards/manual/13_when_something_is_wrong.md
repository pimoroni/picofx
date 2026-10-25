<!-- contents Help -->

## When something is wrong

<!-- if outputs -->
The lights flash to show a problem, and more flashes means a more serious
one. __FLASH_COLOUR_ON__ shows the colour:
<!-- end -->
<!-- if not outputs -->
The board's LED flashes to show a problem, and more flashes
means a more serious one:
<!-- end -->

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press did nothing; try again in a moment |
| blue, twice | something in `effects.txt` could not be read; `errors.txt` says which line |
| red, three times | there was no room to write `errors.txt`; this drive is full or damaged, so free some space or let a computer repair it |

A setting with an invalid value is ignored and noted in `errors.txt`,
and the effect uses its default instead.

If the FX drive doesn't appear on your computer, double-press **Boot** to show
it. This can happen on a Mac that was locked when the board was plugged in or
restarted. The Mac ejects the drive, and it stays hidden after you log in.

A drive that cannot be repaired can be returned to how it shipped by
installing the board's `-full` firmware from the
[picofx releases](https://github.com/pimoroni/picofx/releases/latest).
This erases everything on the drive, so copy off anything you want to
keep first.

For anything else, the foot of the picker, the editor and this page has two
links. **Help** opens the Support section of the Pimoroni forum, the best place
to ask how to do something. **Report a problem** opens a form on GitHub for
something that isn't working as it should, with the board and its firmware
version filled in.
