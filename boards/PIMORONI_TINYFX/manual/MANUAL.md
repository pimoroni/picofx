<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Tiny FX

Six mono outputs, one RGB output, a speaker, and a text file that drives them.
Edit `effects.txt` on this drive and save it, and the board plays the change a
few seconds later. No code needed, though there is room for it when you want it.

## Getting started

Edit `effects.txt` to change what the lights do and save it, and the board plays
the change a few seconds later. The drive disappears for a moment and comes back
with the new effects running, so you can keep editing.

If a save does not seem to take, press **Boot** once or eject this drive, since
a computer does not always write the file out straight away. Press **Boot** twice
to hide the drive, and twice again to bring it back.
A dim light runs along the outputs each time, towards the USB
connector as the computer takes the drive and away from it as the board takes it
back, so a double press is never mistaken for a single one.

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

While the computer is copying to this drive the effects stand aside for a
dim light travelling along the outputs, and come back a moment after
it finishes.

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you. See [the picker](#the-picker). `EDITOR.html` beside it is a place to
write it with the names offered as you type. See [the editor](#the-editor).**

**The board also carries programs that run as they are, from single effects to
whole builds, and one line in `effects.txt` starts any of them. See
[what is already on the board](#what-is-already-on-the-board).**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page reads the file
the board is playing, so you carry on from where it is. The file it will write
is shown at the foot of the page, so nothing about it is hidden.

Two tabs sit under the page's header. **The effects** sets the lights and
sound: pick a stretch of outputs, tap a look from the cards to play on it, and
slide its settings until it suits. A run can be cut into stretches that each
play a look of their own. **Edit board** sets the order the lights are wired in,
and moving the RGB output across to the mono side breaks it into three plain
lights. The sounds on this drive are offered on the Sound tab, where files can
be copied onto the drive and deleted from it. Press the plus to split what you
have into scenes that take turns, each with its own looks and sound; what
**Always on** holds plays under every scene.

**A program** runs one of the board's programs in place of the effects:
what a remote, a sensor or a speaker brings,
beside any programs of your own on this drive.
Pick one and save, and the board restarts to run it. [Your program in the picker](#your-program-in-the-picker)
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

## The editor

`EDITOR.html` on this drive is `effects.txt` in a window that knows the format.
Every word is coloured by the part it plays, and as you type it offers what fits
where you are:
the outputs
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

## Writing an entry

```shape
<outputs> <their settings>: <effect> <its settings>
```

```entry
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.5
out3 level=50%: pulse speed=0.6
```

There is one colon in an entry. Which outputs, and how bright or what colour
they are, go before it. The effect and its own settings go after.

Settings you leave out take their usual value. A `#` starts a comment. An entry
can run on over several lines so long as the colon is on the first; indenting
changes nothing.

## Outputs

### Naming outputs

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-6` | all six |
| `out6-1` | all six, the other way round |
| `out2,1,5-6` | mixed, and in the order you write them |
| `rgb` | the RGB output |

The RGB output shows colour. Its red, green and blue can be driven separately as
three plain lights instead, and named alongside the others:

| Written | Means |
| --- | --- |
| `rgb.r` | just the red |
| `rgb.*` | all three of them, red, green then blue |
| `out1-6,rgb.*` | all nine plain lights |

Order matters for the effects that travel: they move in the order you write the
outputs, so list them in the order they appear in your model, which need not be
number order.

### Setting an output

Before the colon, and separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | how bright, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a name or six-digit hex, for the RGB output when its effect brings no colour | white |
| `fade` | seconds to follow the effect, at a steady rate | follows at once |
| `ease` | seconds to follow it, settling in as a bulb does | follows at once |

```entry
out1-6 level=50%: pulse
rgb colour=warm: flicker
out1-6 ease=0.4: blink speed=0.5
```

Colours by name: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or the hex a colour picker gives you, with its `#`
left off, such as ff8040 for an orange paler than the named one. A `#` always
starts a comment, so one left on a colour hides the rest of the line.

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms and is the one that looks natural on a
light switching on and off.

An output follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
out1-6 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the output, not to the effect, so it works on any effect.

## Effects

Every setting can be left out, and the board fills in the value shown against it
below. The few with none shown have nothing to fall back on, and each is covered
where its effect is.

### For any output, or for one of the RGB output's red, green and blue

| Effect | Settings |
| --- | --- |
| `none` | |
| `static` | `brightness=1` |
| `blink` | `speed=1` `phase=0` `duty=0.5` |
| `blink_wave` | `speed=1` `length=1` `phase=0` `duty=0.5` |
| `flash` | `speed=1` `flashes=2` `window=0.5` `phase=0` `duty=0.5` |
| `flash_sequence` | `speed=1` `length=1` `flashes=1` `window=1` `phase=0` `duty=0.5` |
| `flicker` | `brightness=1` `dimness=0.5` `bright_min=0.05` `bright_max=0.1` `dim_min=0.02` `dim_max=0.04` |
| `flicker_each` | as `flicker` |
| `pulse` | `speed=1` `phase=0` |
| `pulse_wave` | `speed=1` `length=1` `phase=0` |
| `sweep` | `speed=1` `length=1` `extent=1` `hold=0` |
| `random` | `interval=0.05` `brightness_min=0` `brightness_max=1` |
| `random_each` | as `random` |
| `binary_counter` | `interval=0.1` `count=0` `step=1` |
| `traffic_light` | `red_interval=10` `red_amber_interval=5` `green_interval=10` `amber_interval=5` |
| `pelican_crossing` | `red_interval=8` `flashing_interval=6` `green_interval=20` `amber_interval=3` |

### For the RGB output only, since these bring their own colour

| Effect | Settings |
| --- | --- |
| `rgb` | `red=255` `green=255` `blue=255` |
| `hsv` | `hue=0` `sat=1` `val=1` |
| `rainbow` | `speed=1` `sat=1` `val=1` |
| `rainbow_wave` | `speed=1` `length=1` `sat=1` `val=1` |
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour` `speed=1` `phase=0` `duty=0.5` |

### Which ones travel

The ones ending `_wave`, `_sequence` and `_counter`, and `sweep`, travel across
the outputs you name; the rest do the same thing on every one.

The ones ending `_each` give every output its own: `flicker_each` dips each at
its own moments, as flames do, and `random_each` gives each its own brightness.
`flicker` and `random` do the same to all of them at once, as one light would:

```entry
out1-6: flicker_each dimness=0.6
```

An effect that drives several outputs takes them in the order given in its own
section below, so naming fewer than it drives lights the first of them and
leaves the rest out. Naming more than it drives is a mistake, and `errors.txt`
says so.

### Traffic lights and crossings

`traffic_light` wants three outputs, and lights them red, amber and green in
that order. It switches instantly, so add `ease` for the lamps of a real signal:

```entry
out1-3 ease=0.3: traffic_light
```

`pelican_crossing` wants five outputs: the same three, then the two figures a
pedestrian reads, stop and walk. In place of red and amber it flashes the amber
and the walking figure together, as a pelican does while a crossing ends. It
comes round on its own clock, there being no button to press:

```entry
out1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

Three outputs on `pelican_crossing` is its traffic lights on their own:

```entry
out1-3: pelican_crossing
```

### Sweep

`sweep` is a light that crosses the outputs and turns back at each end, the back
and forth a scanner does. Its `extent` is how far it reaches from itself, in
outputs, and its `speed` counts one crossing as the travelling effects count one
pass. Its `hold` waits at each end, in seconds, giving a trail time to clear
before the light comes back over it:

```entry
out1-6 ease=0.4: sweep speed=1 length=6 extent=1 hold=1
```

Give `extent` a whole number of outputs, such as 1 or 2. In between it dims as
the light passes between two outputs and brightens as it lands on one, which
reads as stepping. 1 is the tightest that travels smoothly.

### Blinking through colours

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|` since a comma would mean one colour for each output. It has no colour of its
own, so give it at least one:

```entry
rgb: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles a second: 1 goes round once a second, 0.5 once every two, 2
twice a second. A negative speed runs the cycle backwards.

The settings measured in seconds are `interval`, `hold`, flicker's `bright_min`,
`bright_max`, `dim_min` and `dim_max`, and the four intervals `traffic_light`
and `pelican_crossing` each take. `length`, `flashes`, `steps`, `count` and
`step` are plain counts, and a negative `step` counts down.

The rest run from 0 to 1, written 0.5 or 50% as you prefer. `window` is one of
them, being the share of a cycle the flashes happen in. `hue` takes degrees as
well, written 180deg, which is what a colour picker gives you.

**If you write Python**, an effect of your own can join this list and be written
here like any other. The library reference on
[GitHub](https://github.com/pimoroni/picofx/blob/main/picofx/README.md) says how,
under Effects System.

## Sound

The board plays a WAV file through its speaker, alongside whatever
else it is doing:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

| Plays | Settings |
| --- | --- |
| `wav` | `file` `loop=no` |

The file plays once as the board starts, or over and over with `loop`. The board
plays one sound at a time, so each scene takes one `audio` entry, and one more may
sit before any heading.

A file is looked for on this drive first, then on the board itself. The board
opens it before this drive is shown, so a computer taking the drive does not stop
the sound. While the computer is copying to this drive the sound waits in silence
with the effects, and a file replaced under a playing sound stays silent until
the next reload.

An ordinary uncompressed WAV plays, mono or stereo; MP3 does not. This drive
holds 2.5MB, so a lower sample rate fits more: a minute of 16-bit 22kHz
mono takes about 2.6MB, and the same at 8kHz under 1MB.

An `audio` entry inside a scene plays while that scene shows, and one before any
heading plays whenever the showing scene brings no sound of its own. A sound
put aside by a scene change picks up where it left off when its turn comes back,
and one that had already finished starts again from the top. A scene with
`restart` starts its sound from the top every time, along with everything else
it holds.

## Scenes

A file can hold several sets of effects and show them one after another. A
heading in square brackets begins one, and says how long it shows for:

```entry
[Evening: 30s]
out1-6: pulse_wave speed=0.3
rgb: rainbow speed=0.2

[Night: 10s]
out1-6: flicker_each
rgb colour=warm: pulse
```

The name is everything before the `:` and may be anything you like, spaces
included. The time is in seconds, `30s`, or in minutes, `10m`. Scenes take turns
in the order they are written, then start again.

Entries before the first heading are always on, whatever is showing, so anything
that should never change goes there:

```entry
out1: static brightness=0.2
```

While a scene shows, an output it does not name goes dark if any other scene
uses it, and is left alone if none of them do. A scene may name an output that
is always on, and takes it over for as long as it shows.

Add `restart` to a heading and its effects begin again every time it comes
round, instead of carrying on from where they were left:

```entry
[Beacon: 5s restart]
out1-3: flash_sequence flashes=3
```

The board entry belongs outside every scene. A single scene with no time simply
shows for ever, and ejecting this drive always starts again at the first scene.

## The board

One entry sets the board rather than the lights, and names no output:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `manual` waits for an eject or **Boot** before playing a save | played the moment it is saved |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |

Saving `effects.txt` is enough on its own: the board notices the save, takes the
drive back for a moment, and plays the new effects, exactly as a single press of
**Boot** would. Only a save to `effects.txt` counts, so copying
sounds on never interrupts anything. With `reload=manual` a save waits
for an eject or **Boot** instead.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the
board, so `program=examples/python/effects/mono/sweep_trail.py`
reaches one of the examples the board ships with.
Where the name is in both, this drive's copy runs.

If it is missing, or stops with an error, the effects run instead and
`errors.txt` says what happened, so a mistyped name never leaves you with a
board that does nothing.

Saving a file that names a program, while the effects play, restarts the board,
which then runs the program as it would from power on.

The effects stop while a program runs, and the board is busy with it, so
**Boot** and ejecting do nothing. The drive is shown anyway, even with `drive`
set to `manual`, so you can still edit `effects.txt`. Saving it restarts the
board, which then plays whatever it now says; with `reload=manual`, press
**Reset** for the change to take. A program reads its files from this drive even
while it is shown, so its pictures and sounds can sit beside it here.

When the program ends, the board goes back to the effects the rest of the file
describes.

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
drive beside the examples in its `examples/python` folder,
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
An example is listed only in the section it names.
`examples/python/sections.txt` orders the sections, a line each with its name,
then a `|` and what it holds.

### What is already on the board

These come with the board, so `program=` reaches any of them with nothing to
download:

| Folder | What is in it |
| --- | --- |
| `examples/python/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/python/effects/colour` | the RGB output |
| `examples/python/function` | the button, the sensor connector and the supply voltage |
| `examples/python/infrared/mono` | effects chosen with an infrared remote |
| `examples/python/infrared/colour` | the same on the RGB output |
| `examples/python/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/python/audio` | sound alongside the lights |
| `examples/python/comms` | several boards working together |
| `examples/python/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/python/effects/mono/sweep_trail.py
board: program=examples/python/effects/colour/rainbow.py
board: program=examples/python/showcase/ship_thrusters.py
```

Anything under `infrared` or `qwst` needs that hardware attached, and `comms`
wants a second board. The audio examples' sounds are not on the board, to leave
this drive its room.

The full set, with what each one does, is on
[GitHub](https://github.com/pimoroni/picofx).

## When something is wrong

The lights say so, and the more flashes the worse it is. The RGB output
shows the colour:

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press did nothing; try again in a moment |
| blue, twice | something in `effects.txt` could not be read; `errors.txt` says which line |
| red, three times | there was no room to write `errors.txt`; this drive is full or damaged, so free some space or let a computer repair it |

A setting whose value is not what it takes is ignored, with a note in
`errors.txt`, and the effect runs on its usual value for it.

## More from Pimoroni

### Boards and accessories

- [MightyFX](https://shop.pimoroni.com/products/mightyfx)
- [TinyFX](https://shop.pimoroni.com/products/tinyfx)
- [TinyFX W](https://shop.pimoroni.com/products/tiny-fx-w)
- [Plasma 2350](https://shop.pimoroni.com/products/plasma-2350)
- [Plasma 2350 W](https://shop.pimoroni.com/products/plasma-2350-w)
- [Everything in the range](https://shop.pimoroni.com/collections/tiny-fx)

### Going further

- [picofx on GitHub](https://github.com/pimoroni/picofx), the library these effects come from
