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
| white, once | the computer was still writing, so the press was ignored. Try again in a moment |
<!-- if screens -->
| blue, twice | a line in `effects.txt` could not be read, or a drawing failed. `errors.txt` names the line. A drawing's error appears there once the board has the drive back |
<!-- end -->
<!-- if not screens -->
| blue, twice | a line in `effects.txt` could not be read. `errors.txt` names the line |
<!-- end -->
<!-- if sound -->
| blue, twice | a sound could not be played. `errors.txt` names the line. A sound's error appears there once the board has the drive back |
<!-- end -->
| red, three times | there was no room to write `errors.txt`. This drive is full or damaged, so free some space or repair it from a computer |

A setting with an invalid value is ignored and noted in `errors.txt`,
and the effect uses its default instead.

A drive that cannot be repaired can be returned to how it shipped by
installing the board's `-full` firmware from the
[picofx releases](https://github.com/pimoroni/picofx/releases/latest).
This erases everything on the drive, so copy off anything you want to
keep first.
