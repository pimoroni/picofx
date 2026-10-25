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
