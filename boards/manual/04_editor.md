## The editor

`EDITOR.html` on this drive is `effects.txt` in a window that knows the format.
Every word is coloured by the part it plays, and as you type it offers what fits
where you are:
__ENTRY_TARGETS__
at the start of a line, the effects after the colon, then that effect's own settings and the values each one takes. A line
underneath says what shape a value wants. Tab or Enter takes what is offered,
Escape leaves it, and Ctrl+Space asks for it again.

A name it does not know is underlined, an effect that is not one or a setting the
effect does not take. Values are left alone, since a percentage, a colour and a
list all live there and the board is the one that reads them. "Put it on the
board" writes the file and "Did it work?" reads `errors.txt` back, as the picker
does.

It offers only what this board provides, so anything the firmware gains appears
without the page changing. It saves the way the picker does, in one click from a
Chromium browser and by download from Safari or Firefox, and it needs
`catalogue.js` beside it, which is why both live on this drive together.
