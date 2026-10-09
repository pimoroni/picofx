## When something is wrong

The lights say so, and the more flashes the worse it is. __FLASH_COLOUR_ON__
shows the colour:

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press did nothing; try again in a moment |
| blue, twice | something in `effects.txt` could not be read; `errors.txt` says which line |
| red, three times | there was no room to write `errors.txt`; this drive is full or damaged, so free some space or let a computer repair it |

A setting whose value is not what it takes is ignored, with a note in
`errors.txt`, and the effect runs on its usual value for it.
