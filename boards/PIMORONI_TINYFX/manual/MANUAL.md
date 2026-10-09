# Tiny FX

Six mono outputs, one RGB output, a speaker, and a text file that drives them.
Edit `effects.txt` on this drive, eject it, and the board applies the change
straight away. No code needed, though there is room for it when you want it.

## Getting started

Edit `effects.txt` to change what the lights do, then eject this drive and the
board applies the change straight away.

In a hurry? Save the file and press **Boot** once. The drive disappears and
comes straight back with the new effects running, so you can keep editing.
Ejecting is the surer way, since a computer does not always write the file out
until then. Press **Boot** twice to hide the drive, and twice again to bring it
back. A dim light runs along the outputs each time, one way as the computer
takes the drive and the other as the board takes it back, so a double press is
never mistaken for a single one.

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

While the computer is copying to this drive the effects stand aside for a dim
light travelling along the outputs, and come back a moment after it finishes.

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you. See [the picker](#the-picker). `EDITOR.html` beside it is a place to
write it with the names offered as you type.**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page reads the file
the board is playing, so you carry on from where it is. The file it will write
is shown at the foot of the page, so nothing about it is hidden.

Pick a stretch of outputs, tap a look from the cards to play on it, and slide its
settings until it suits. The outputs can be cut into stretches that each play a
look of their own. **Edit board** sets the order the lights are wired in, and
moving the RGB output across to the mono side breaks it into three plain lights.
The sounds on this drive are offered on the Sound tab. Press the plus to split
what you have into scenes that take turns.

**Save to board** writes the file, and the board picks it up a few seconds later.
**Check board** reads `errors.txt` back and shows what the board made of each
line. The page reaches the drive only in Chrome, Edge or another browser built
on Chromium; elsewhere it says so, and `effects.txt` can still be changed in any
text editor.

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
left off. A `#` always starts a comment, so one left on a colour hides the rest
of the line.

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms. Two numbers divided by `|` give the
rise and the fall their own lengths:

```entry
out1-3 ease=0.05|1.2: blink speed=1
```

## Effects

Every setting can be left out, and the board fills in the value shown against it
below.

### For any output

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
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour` `speed=1` `phase=0` `duty=0.5` |

### Which ones travel

The ones ending `_wave`, `_sequence` and `_counter`, and `sweep`, travel across
the outputs you name; the rest do the same thing on every one. The ones ending
`_each` give every output its own: `flicker_each` dips each at its own moments,
as flames do.

`traffic_light` wants three outputs, lit red, amber and green in that order, and
`pelican_crossing` five, the same three then the stop and walk figures:

```entry
out1-3 ease=0.3: traffic_light
out1-5 ease=0.3: pelican_crossing
```

`sweep` is a light that crosses the outputs and turns back at each end. Its
`extent` is how far it reaches from itself, in outputs, and `hold` waits at each
end, in seconds:

```entry
out1-6 ease=0.4: sweep speed=1 extent=1 hold=1
```

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|`:

```entry
rgb: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles a second: 1 goes round once a second, 0.5 once every two. A
negative speed runs the cycle backwards. `interval`, `hold` and the flicker and
signal timings are seconds. `length`, `flashes`, `steps`, `count` and `step` are
plain counts. The rest run from 0 to 1, written 0.5 or 50% as you prefer, and
`hue` takes degrees as well, written 180deg.

## Sound

The board plays a WAV file through its speaker, alongside whatever the lights
are doing:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

The file plays once as the board starts, or over and over with `loop`. The board
plays one sound at a time, so each scene takes one `audio` entry, and one more may
sit before any heading. Put the file on this drive beside `effects.txt`.

A file is looked for on this drive first, then on the board itself. While the
computer is copying to this drive the sound waits in silence with the effects.

An ordinary uncompressed WAV plays, mono or stereo; MP3 does not.

The drive is small, so a lower sample rate fits more: a minute of 22kHz mono
takes about 2.6MB, which is more than the drive holds, and 8kHz mono takes
under 1MB.

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

The time is in seconds, `30s`, or in minutes, `10m`. Scenes take turns in the
order they are written, then start again. Entries before the first heading are
always on, whatever is showing. Add `restart` to a heading and its effects begin
again every time it comes round.

## The board

One entry sets the board rather than the lights, and names no output:

```entry
board: reload=auto
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |

With `reload=auto`, saving `effects.txt` is enough on its own: the board notices
the save, takes the drive back for a moment, and plays the new effects, exactly
as a single press of **Boot** would. Only a save to `effects.txt` counts, so
copying sounds on never interrupts anything.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the board, so
`program=examples/effects/mono/sweep_trail.py` reaches one of the examples the
board ships with. Where the name is in both, this drive's copy runs. If it is
missing, or stops with an error, the effects run instead and `errors.txt` says
what happened.

Saving a file that names a program, while the effects play, restarts the board,
which then runs the program as it would from power on.

The effects stop while a program runs, and **Boot** and ejecting do nothing. The
drive is shown anyway, even with `drive` set to `manual`, so you can still edit
`effects.txt`. With `reload=auto`, saving it restarts the board, which then plays
whatever it now says; without, press **Reset** for the change to take.

### What is already on the board

| Folder | What is in it |
| --- | --- |
| `examples/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/effects/colour` | the RGB output |
| `examples/function` | the button, the sensor connector and the supply voltage |
| `examples/infrared` | effects chosen with an infrared remote |
| `examples/qwst` | light, tilt and weather from Qw/ST breakouts |
| `examples/comms` | several boards working together |
| `examples/showcase` | larger builds that put several of these together |

The audio examples' sounds are not on the board, to leave this drive its room.

## When something is wrong

The lights say so, and the more flashes the worse it is. The RGB output shows
the colour:

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press did nothing; try again in a moment |
| blue, twice | something in `effects.txt` could not be read; `errors.txt` says which line |
| red, three times | there was no room to write `errors.txt`; this drive is full or damaged, so free some space or let a computer repair it |

## More from Pimoroni

- [TinyFX](https://shop.pimoroni.com/products/tinyfx)
- [TinyFX W](https://shop.pimoroni.com/products/tiny-fx-w)
- [picofx on GitHub](https://github.com/pimoroni/picofx), the library these effects come from
