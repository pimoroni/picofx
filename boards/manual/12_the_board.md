## The board

One entry sets the board rather than the lights, and names no __OUTPUT__:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |
<!-- if screens -->
<!-- board screen_settings -->
<!-- end -->
<!-- if strips -->
<!-- board strip_settings -->
<!-- end -->

With `reload=auto`, saving `effects.txt` is enough on its own: the board notices
the save, takes the drive back for a moment, and plays the new effects, exactly
as a single press of **Boot** would. Only a save to `effects.txt` counts, so
copying __COPIED_FILES__ on never interrupts anything.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the
<!-- if examples -->
board, so `program=__EXAMPLE_PROGRAM__`
reaches one of the examples the board ships with.
<!-- end -->
<!-- if not examples -->
board.
<!-- end -->
Where the name is in both, this drive's copy runs.

If it is missing, or stops with an error, the effects run instead and
`errors.txt` says what happened, so a mistyped name never leaves you with a
board that does nothing.

Saving a file that names a program, while the effects play, restarts the board,
which then runs the program as it would from power on.

The effects stop while a program runs, and the board is busy with it, so
**Boot** and ejecting do nothing. The drive is shown anyway, even with `drive`
set to `manual`, so you can still edit `effects.txt`. With `reload=auto`, saving
it restarts the board, which then plays whatever it now says; without, press
**Reset** for the change to take. A program cannot read files from this drive
while it runs, so put anything it needs on the board's own filesystem.

<!-- if screens -->
__SCREEN_SETTINGS_UNSEEN__:
it sets its own up. Pass it the size in `args` if it
needs telling.
<!-- end -->

`args` passes a program whatever it needs to know, so one program can do
different things without being edited. Several are divided by `|`, and anything
with a space or a colon in it goes in quotes:

```entry
board: program=slideshow.py args=posters|3
board: program=clock.py args="07:30"
```

**If you are writing the program**, it reads them from `sys.argv`, the way any
Python program does, with the first being `sys.argv[1]`. Thonny passes none when
you run the same file from there, so give each one a value to fall back on and
the file works either way:

```python
args = sys.argv[1:]
FOLDER = args[0] if args else "posters"
```

### Your program in the picker

The picker's **A program** tab lists every Python file at the top of this
<!-- if examples -->
drive beside the examples in its `examples/python` folder,
<!-- end -->
<!-- if not examples -->
drive,
<!-- end -->
and describes each one by its opening string, the text in
triple quotes at the top of the file. Its first sentence says what the program
does, and these lines tell the picker how to show it:

```python
'''
Program: Big clock
Shows the time.
Args: Colour, Seconds
Picture: clock.png
Section: Signs and displays
'''
```

| Line | What the picker does with it |
| --- | --- |
| `Program: Big clock` | names the program, where it would use the file's name |
| `Args: Colour, Seconds` | gives each argument a box of its own, and writes `args=` from them |
| `Picture: clock.png` | shows the program by that picture, kept beside it |
| `Section: Signs and displays` | lists the program in that section, where it would be listed under **On the drive** |
| `Thumbnail: servo` | draws a servo for a program with no picture, or `motor`, or `outputs` and a pattern such as `outputs rainbow` |

Each is optional. Without `Picture`, the picker shows `clock.png` beside
`clock.py` where there is one, and `clock-2.png` beside it as a second screen's.
Without `Args`, a program that reads `sys.argv` is offered plain boxes to add
arguments to.

A board with a wireless module keeps `secrets.py` at the top of the drive for
your WiFi network's name and password, and puts an empty one back if it is
deleted. A program that goes online, importing `network` or `requests`, is listed
only where the drive holds that file.
<!-- if examples -->
An example is listed only in the section it names.
`examples/python/sections.txt` orders the sections, a line each with its name,
then a `|` and what it holds.
<!-- end -->
<!-- if screens -->
A file whose opening string starts `Drawing:` is [a drawing](#drawing-from-code),
so it is left out.
<!-- end -->

<!-- if examples -->
### What is already on the board

These come with the board, so `program=` reaches any of them with nothing to
download:

<!-- board examples_on_board -->

The full set, with what each one does, is on
[GitHub](https://github.com/pimoroni/picofx).
<!-- end -->
