## The board

One entry sets the board rather than the lights, and names no output:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |
| `screenA` | what size of screen is on SP/CE A, or `hub` for a Screen Hub | no screen |
| `screenB` | the same for SP/CE B | no screen |
| `hubA` to `hubF` | what size of screen is at each of a Screen Hub's positions | no screen there |
| `stripL` | how many LEDs are on a strip plugged into **L**, and after a `\|` the order it takes its colours in | no strip |
| `stripR` | the same for **R** | no strip |

With `reload=auto`, saving `effects.txt` is enough on its own: the board notices
the save, takes the drive back for a moment, and plays the new effects, exactly
as a single press of **Boot** would. Only a save to `effects.txt` counts, so
copying pictures on never interrupts anything.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the board, so
`program=examples/effects/colour/rainbow_wave.py` reaches one of the examples
the board ships with. Where the name is in both, this drive's copy runs.

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

`screenA` and `screenB` describe the screens this file's own entries play on, so
a program never sees them: it sets its own up. Pass it the size in `args` if it
needs telling.

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

The picker's **A program** tab lists every Python file at the top of this drive
beside the examples, and describes each one by its opening string, the text in
triple quotes at the top of the file. Its first plain line says what the program
does, and three more lines tell the picker how to show it:

```python
'''
Program: Big clock
Shows the time across both screens.
Args: Colour, Seconds
Picture: clock.png
'''
```

| Line | What the picker does with it |
| --- | --- |
| `Program: Big clock` | names the program, where it would use the file's name |
| `Args: Colour, Seconds` | gives each argument a box of its own, and writes `args=` from them |
| `Picture: clock.png` | shows the program by that picture from this drive |

Each is optional. Without `Args`, the picker offers plain boxes to add arguments
to, and without `Picture`, a plain tile. A file whose opening string starts
`Drawing:` is [a drawing](#drawing-from-code), so it is left out.

### What is already on the board

These come with the board, so `program=` reaches any of them with nothing to
download:

| Folder | What is in it |
| --- | --- |
| `examples/effects` | changing from one set of effects to another as time passes |
| `examples/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/effects/colour` | the same in colour, with traffic lights and crossings |
| `examples/screens/single` | one screen, its backlight, and finding what is attached |
| `examples/screens/playback` | animated GIFs and slideshows |
| `examples/screens/graphics` | drawing from code: text, colour wheels, a starfield |
| `examples/screens/images` | still pictures |
| `examples/screens/layout` | placing a picture on the screen |
| `examples/screens/pair` | two screens working together |
| `examples/screens/hub` | more than two, through a hub |
| `examples/audio` | playing a wav file |
| `examples/motors` | driving a pair of motors |
| `examples/servos` | sweeping a servo on the L connector |
| `examples/strips` | a rainbow along an LED strip |
| `examples/gpio` | using SP/CE pins as plain inputs and outputs |
| `examples/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/effects/colour/sweep_trail.py
board: program=examples/screens/playback/animated_gif.py
board: program=examples/showcase/flip_dot_sign.py
```

Anything under `screens`, `audio`, `motors`, `servos` or `strips` needs that
hardware attached, and some of the showcase ones want pictures or a network of
their own. The full set, with what each one does, is on
[GitHub](https://github.com/pimoroni/picofx).
