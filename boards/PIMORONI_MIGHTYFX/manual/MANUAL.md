# MightyFX

Seven outputs, two screen connectors, and a text file that drives them. Edit
`effects.txt` on this drive, eject it, and the board applies the change straight
away. No code needed, though there is room for it when you want it.

## Getting started

Edit `effects.txt` to change what the lights do, then eject this drive and the
board applies the change straight away.

In a hurry? Save the file and press **Boot** once. The drive disappears and
comes straight back with the new effects running, so you can keep editing.
Ejecting is the surer way, since a computer does not always write the file out
until then. Press **Boot** twice to hide the drive, and twice again to bring it
back. A dim white light runs along the outputs each time, towards the USB
connector as the computer takes the drive and away from it as the board takes it
back, so a double press is never mistaken for a single one.

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

While the computer is copying to this drive the effects stand aside for a dim
white travelling along the outputs, and come back a moment after it finishes.

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you. See [the picker](#the-picker). `EDITOR.html` beside it is a place to
write it with the names offered as you type. See [the editor](#the-editor).**

**The board also carries programs that run as they are, from single effects to
whole builds, and one line in `effects.txt` starts any of them. See
[what is already on the board](#what-is-already-on-the-board).**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, pick a look, and slide until it suits. It shows the file it is writing as
you go, so nothing about it is hidden.

Screens, strips and sound are set up there too. Say how many LEDs a strip has and
which size each screen is, pick a picture from this drive for a screen to show,
and tap any of the board's own seven lights to leave it out of the effect, or
drag them into the order your build has them. Pictures and sounds can be copied
onto the drive, and deleted from it, without leaving the page. Press the plus to
split what you have into scenes that take turns.

"Put it on the board" writes the file, and the board picks it up a few seconds
later. Untick "play it as soon as I save" and it waits instead until this drive
is ejected, or **Boot** is pressed once. "Did it work?" reads `errors.txt` back
and shows what the board made of each line.

A page cannot write to a drive in Firefox or Safari, so the picker needs Chrome or
Edge. What it writes is an ordinary `effects.txt`: anything it makes can be edited
by hand afterwards, and it asks before replacing a file it did not write itself.

## The editor

`EDITOR.html` on this drive is `effects.txt` in a window that knows the format.
Every word is coloured by the part it plays, and as you type it offers what fits
where you are: the outputs and screens at the start of a line, the effects after
the colon, then that effect's own settings and the values each one takes. A line
underneath says what shape a value wants. Tab or Enter takes what is offered,
Escape leaves it, and Ctrl+Space asks for it again.

A name it does not know is underlined, an effect that is not one or a setting the
effect does not take. Values are left alone, since a percentage, a colour and a
list all live there and the board is the one that reads them. "Put it on the
board" writes the file and "Did it work?" reads `errors.txt` back, as the picker
does.

It offers only what this board provides, so anything the firmware gains appears
without the page changing. Like the picker it needs Chrome or Edge, and it needs
`catalogue.js` beside it, which is why both live on this drive together.

## Writing an entry

```shape
<outputs> <their settings>: <effect> <its settings>
```

```entry
out1-7: rainbow_wave speed=0.3
out3 level=50%: pulse speed=0.6
```

There is one colon in an entry. Which outputs, and how bright or what colour
they are, go before it. The effect and its own settings go after.

Settings you leave out take their usual value. A `#` starts a comment. An entry
can run on over several lines so long as the colon is on the first; indenting
changes nothing.

A screen is named the same way and plays pictures instead of lighting up. See
[Screens](#screens).

## Outputs

### Naming outputs

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-7` | all seven |
| `out7-1` | all seven, the other way round |
| `out2,1,5-7` | mixed, and in the order you write them |

An output shows colour. Its red, green and blue can be driven separately as
three plain lights instead:

| Written | Means |
| --- | --- |
| `out3.r` | just the red |
| `out3.*` | all three of them |
| `out1-7.*` | all 21 |

Order matters for the effects that travel: they move in the order you write the
outputs, so list them in the order they appear in your model, which need not be
number order.

### Setting an output

Before the colon, and separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | how bright, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a name or six-digit hex, for effects that bring no colour | white |
| `fade` | seconds to follow the effect, at a steady rate | follows at once |
| `ease` | seconds to follow it, settling in as a bulb does | follows at once |

```entry
out1-7 level=50%: pulse
out1-3 colour=warm: flicker
out4 colour=ff8040: static
out1 level=0.5, 2 level=0.8, 3-7: pulse_wave
out1-7 ease=0.4: blink speed=0.5
```

Colours by name: red, yellow, green, cyan, blue, magenta, warm, white, cool,
black. Or the hex a colour picker gives you, with its `#` left off, as `out4`
above uses for a soft orange. A `#` always starts a comment, so one left on a
colour hides the rest of the line.

### Fade and ease

`fade` and `ease` take the seconds a change takes to get there. `fade` crosses
evenly, which is what a stage light does; `ease` goes quickly at first and slows
as it arrives, which is how a bulb warms and is the one that looks natural on a
light switching on and off.

An output follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
out1-7 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the output, not to the effect, so it works on any effect.

## Effects

Every setting can be left out, and the board fills in the value shown against it
below. The few with none shown have nothing to fall back on, and each is covered
where its effect is.

### For an output, or for one of its red, green and blue

| Effect | Settings |
| --- | --- |
| `none` | |
| `static` | `brightness=1` |
| `blink` | `speed=1` `phase=0` `duty=0.5` |
| `blink_wave` | `speed=1` `length=1` `phase=0` `duty=0.5` |
| `flash` | `speed=1` `flashes=2` `window=0.5` `phase=0` `duty=0.5` |
| `flash_sequence` | `speed=1` `length=1` `flashes=1` `window=1` `phase=0` `duty=0.5` |
| `flicker` | `brightness=1` `dimness=0.5` `bright_min=0.05` `bright_max=0.1` `dim_min=0.02` `dim_max=0.04` |
| `pulse` | `speed=1` `phase=0` |
| `pulse_wave` | `speed=1` `length=1` `phase=0` |
| `sweep` | `speed=1` `length=1` `extent=1` `hold=0` |
| `random` | `interval=0.05` `brightness_min=0` `brightness_max=1` |
| `binary_counter` | `interval=0.1` `count=0` `step=1` |
| `traffic_light` | `red_interval=10` `red_amber_interval=5` `green_interval=10` `amber_interval=5` |
| `pelican_crossing` | `red_interval=8` `flashing_interval=6` `green_interval=20` `amber_interval=3` |

### For an output only, since these bring their own colour

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
out1-7 ease=0.4: sweep speed=1 length=7 extent=1 hold=1
```

Give `extent` a whole number of outputs, such as 1 or 2. In between it dims as
the light passes between two outputs and brightens as it lands on one, which
reads as stepping. 1 is the tightest that travels smoothly.

### Blinking through colours

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|` since a comma would mean one colour for each output. It has no colour of its
own, so give it at least one:

```entry
out1: rgb_blink colour=red|warm|ff8040 speed=0.5
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

## LED strips

A strip of WS2812 LEDs plugs into the connector marked **L** or **R**, and its
LEDs take the same effects, colours and levels the outputs do. Tell the board
how long it is first, since that is the one thing it cannot work out for itself:

```entry
board: stripL=60
stripL: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `stripL` | every LED on the strip |
| `stripL5` | one of them |
| `stripL1-10` | the first ten |
| `stripL60-1` | all sixty, the other way round, for a strip mounted backwards |

`stripR` is the same for the other connector. Both share one power supply, so a
strip on either lights the small LED between them, and anything plugged into the
one you are not using is powered too.

Each LED shows a colour of its own, so `stripL5.r` is not a thing to write; set
`colour` on the LEDs instead, as an output takes it.

## Screens

### Naming screens

A screen on either SP/CE connector is named `screenA` or `screenB`. A screen
cannot say what size it is, so tell the board:

```entry
board: screenA=1.54
```

That is a board entry, which sets the board rather than the lights and is one of
a handful covered under [The board](#the-board).

The sizes are 2.8 and 1.54, and 2.8 is used if you say nothing. Changing it
needs the board turned off and on again before the new size takes.

### Setting a screen

Before the colon, and separate from what it plays:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `rotation` | 0, 90, 180 or 270, for how the screen is mounted | 0 |
| `backlight` | how brightly it is lit, 0 to 1, such as 0.5 or 50% | 1 |
| `mirror` | true to flip the picture left to right | no |
| `offset` | where to put the picture, as `x\|y` | centred |
| `background` | the colour around it, or `bg` for short | black |
| `pixel_double` | true to draw each pixel twice as wide and tall, so a half size picture fills the screen | no |
| `tile` | `repeat` or `mirror` to fill the screen with copies of the picture, as `across\|down` | off |

```entry
screenA rotation=90: gif file="clock.gif"
screenA offset=*|20 bg=black: image file=logo.png
screenA tile=repeat: image file=bricks.png
```

A picture is centred unless `offset` puts it somewhere, and a `*` in place of
either number centres that side.

`tile` fills the screen with a small picture instead of leaving a background
around it. `repeat` lays copies side by side, so a picture drawn to join up at
its edges makes a pattern with no seam in it, and `mirror` turns every other
copy round, which joins any picture up whether it was drawn to or not. One
value covers both directions and two set them apart, `tile=mirror|off`
spreading a picture across the screen and leaving its height alone.

### Pictures

| Plays | Settings |
| --- | --- |
| `gif` | `file` `fps` `interval` `loop=yes` `ping_pong=no` `first_as_last=no` `hold=0` |
| `image` | `file` |
| `sequence` | `folder` `fps` `interval` `loop=yes` `ping_pong=no` `first_as_last=no` `hold=0` |

```entry
screenA: gif file="clock.gif"
screenA: image file=logo.png
screenA: sequence folder=photos interval=30
```

`gif` plays an animated GIF at the delays it was saved with, `image` holds one
picture, and `sequence` plays a folder of them in the order their names number
them. Pictures can be PNG, JPEG or GIF. There is nothing to play without `file`
or `folder`, so those two always have to be given.

`fps` is frames a second and `interval` is the seconds between them, so use
whichever suits: `fps=12` for an animation, `interval=30` for a slideshow.
Either one replaces the delays the file was saved with, and leaving out both
keeps them. `loop` is true unless you set it false, which stops on the last
frame. `ping_pong` plays back and forth instead of starting over, which suits an
animation with two ends, such as an arm flexing.

An animation drawn to loop has no such ends, its last frame leading back into
its first. Add `first_as_last=yes` for one of those and the whole loop is played
in each direction, so a spinning coin winds all the way round and back:

```entry
screenA: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the seconds to wait where it turns around, so a ping-pong pauses at
each end instead of bouncing straight off. One value serves both ends, or write
each with a `|`:

```entry
screenA: gif file="wave.gif" ping_pong=yes hold=1
screenA: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

A file is looked for on this drive first, then on the board itself, and the name
may include folders. There is little room here, so pictures usually live on the
board.

A screen draws about twenty frames a second at best, and effects on the outputs
take time from it, so a file asking for more keeps its timing by dropping
frames. Ask for twenty or fewer and it plays every one.

### Drawing from code

**This one is for Python writers.** A screen can play a drawing instead of a
picture: a Python file with one function in it, drawn beside everything else in
this file, so the lights keep their effects, the other screen keeps its
pictures, and a scene puts the drawing on and off with everything else it holds.

| Plays | Settings |
| --- | --- |
| `graphics` | `file` `fps` `interval` `width` `height` |

```entry
screenA: graphics file=rings.py
```

```python
# rings.py
from picovector import color, shape

def draw(canvas, elapsed):
    canvas.pen = color.black
    canvas.clear()
    canvas.pen = color.rgb(255, 160, 40)
    canvas.shape(shape.circle(120, 160, 20 + 10 * (elapsed % 3)))
```

`draw` is called with a canvas the size of the screen, kept between calls, and
the seconds since the drawing started; whatever it has drawn when it returns is
what the screen shows. The rest of the file runs once, when the drawing starts,
so that is the place to build anything `draw` uses. `fps` or `interval` sets the
pace, and leaving both out draws as often as the screen takes a frame.

`width` and `height` size the canvas by hand, in pixels, and are honoured as
written whatever else is set. A small canvas draws faster and is placed like a
small picture, so `offset` puts it somewhere and `tile=repeat` fills the screen
with it.

In a scene, the drawing's clock stops while the scene is away, and a scene with
`restart` runs the whole file again from a blank canvas. The rotation, offset
and other screen settings place a drawing as they place a picture, with
`pixel_double` also making the canvas half size, which draws faster and uses a
quarter of the memory; a stated `width` or `height` is still used as written.

A drawing can load pictures, `picovector.image.load("/faces.png")`, best done
once in the setup. Name them from the board's own filesystem, with the leading
`/`: this drive comes and goes with the computer, so a picture kept here may be
missing just when a scene's `restart` runs the file again. The drawing itself is
safe wherever it lives, read once and kept.

A drawing may import `math`, `random`, `time` and `picovector`. The board's own
modules stay with the effects running around it, so a program pasted in that
reaches for the pins is refused, with a note in `errors.txt`. A mistake anywhere
in the file lands there too, with its line, and a drawing that stops partway
keeps its last frame on the screen while everything else carries on.

The examples under `examples/screens/graphics` show what PicoVector can draw,
and a program that wants the whole board instead of one screen is
[a program](#running-your-own-program), not a drawing.

## Sound

The board plays a WAV file through its onboard amplifier, alongside whatever the
lights and screens are doing:

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

A file is looked for on this drive first, then on the board itself, as a picture
is. The board opens it before this drive is shown, so a computer taking the drive
does not stop the sound. While the computer is copying to this drive the sound
waits in silence with the effects, and a file replaced under a playing sound ends
it quietly.

An ordinary uncompressed WAV plays, mono or stereo; MP3 does not.

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
out1-7: rainbow_wave speed=0.3

[Night: 10s]
out1-7 colour=warm: pulse
```

The name is everything before the `:` and may be anything you like, spaces
included. Scenes take turns in the order they are written, then start again.

Entries before the first heading are always on, whatever is showing, so anything
that should never change goes there:

```entry
out1: static brightness=0.2
```

While a scene shows, an output it does not name goes dark if any other scene
uses it, and is left alone if none of them do. A scene may name an output that
is always on, and takes it over for as long as it shows.

A screen behaves the same way: its picture stays put but the light goes out
while another scene has the board, and comes back when its own returns.

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
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |
| `screenA` | what size of screen is on SP/CE A, if you have one | 2.8 |
| `screenB` | the same for SP/CE B | 2.8 |
| `stripL` | how many LEDs are on a strip plugged into **L** | no strip |
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

The effects stop while a program runs, and the board is busy with it, so
**Boot** and ejecting do nothing. The drive is shown anyway, even with `drive`
set to `manual`, so you can still edit `effects.txt`; unplug and plug back in
for the change to take. A program cannot read files from this drive while it
runs, so put anything it needs on the board's own filesystem.

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

## When something is wrong

The lights say so, and the more flashes the worse it is:

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
- [Everything in the range](https://shop.pimoroni.com/collections/tiny-fx)

### Going further

- [picofx on GitHub](https://github.com/pimoroni/picofx), the library these effects come from
- [The PicoVector drawing API](https://badgewa.re/docs), for programs that draw on a screen
