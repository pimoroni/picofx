<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Plasma 2350

Two LED terminals, a screen connector, and a text file that drives them.
Edit `effects.txt` on this drive, eject it, and the board applies the change
straight away. No code needed, though there is room for it when you want it.

## Getting started

Edit `effects.txt` to change what the lights do, then eject this drive and the
board applies the change straight away.

In a hurry? Save the file and press **Boot** once. The drive disappears and
comes straight back with the new effects running, so you can keep editing.
Ejecting is the surer way, since a computer does not always write the file out
until then. Press **Boot** twice to hide the drive, and twice again to bring it
back.

Deleting `effects.txt` restores the default; emptying it leaves the board dark.

While the computer is copying to this drive the effects stand aside, the board's
LED glowing a dim white with a brighter blink, and come back a moment after it
finishes.

**Would you rather not write the file at all? `PICKER.html` on this drive writes
it for you. See [the picker](#the-picker). `EDITOR.html` beside it is a place to
write it with the names offered as you type. See [the editor](#the-editor).**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page reads the file
the board is playing, so you carry on from where it is. The file it will write
is shown at the foot of the page, so nothing about it is hidden.

Two tabs sit under the page's header. **The effects** sets the strips, the
board's LED and the screen: pick a stretch of LEDs, tap a look from the cards to
play on it, and slide its settings until it suits. A strip can be cut into
stretches that each play a look of their own. **Edit board** sets up what is
built: which strips are fitted, how many LEDs each has, and which size the
screen is. The pictures and drawings on this drive are offered on the Screens
tab, where files can be copied onto the drive and deleted from it. Press the plus
to split what you have into scenes that take turns, each with its own looks and
pictures; what **Always on** holds plays under every scene.

**A program** runs one of your own programs on this drive in place of the
effects.
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
the strips, the board's LED and the screen
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
<LEDs> <their settings>: <effect> <its settings>
```

```entry
stripDat: rainbow_wave speed=0.3 length=30
rgb level=50%: pulse speed=0.6
```

There is one colon in an entry. Which LEDs, and how bright or what colour
they are, go before it. The effect and its own settings go after.

Settings you leave out take their usual value. A `#` starts a comment. An entry
can run on over several lines so long as the colon is on the first; indenting
changes nothing.

A screen is named the same way and plays pictures instead of lighting up. See
[Screens](#screens).

## The board's LED

The RGB LED on the board is `rgb`, and takes any effect. The LEDs of a strip are
named under [LED strips](#led-strips).

```entry
rgb: rainbow speed=0.3
```

### Setting an LED

Before the colon, and separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | how bright, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a name or six-digit hex, for effects that bring no colour | white |
| `fade` | seconds to follow the effect, at a steady rate | follows at once |
| `ease` | seconds to follow it, settling in as a bulb does | follows at once |

```entry
stripDat level=50%: pulse
stripDat1-30 colour=warm: flicker
rgb colour=ff8040: static
stripDat ease=0.4: blink speed=0.5
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

An LED follows one way or the other, so a line takes one of them and not
both. Two numbers divided by `|` give the rise and the fall their own lengths,
a light that comes on quickly and fades out slowly being the usual reason:

```entry
stripDat fade=0.8: blink speed=0.5
stripDat1-3 ease=0.05|1.2: blink speed=1
```

Softening belongs to the LED, not to the effect, so it works on any effect.

## Effects

Every setting can be left out, and the board fills in the value shown against it
below. The few with none shown have nothing to fall back on, and each is covered
where its effect is.

### For any LED

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

### For any LED, bringing their own colour

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
the LEDs you name; the rest do the same thing on every one.

The ones ending `_each` give every LED its own: `flicker_each` dips each at
its own moments, as flames do, and `random_each` gives each its own brightness.
`flicker` and `random` do the same to all of them at once, as one light would:

```entry
stripDat colour=ff5a00: flicker_each dimness=0.6
```

An effect that drives several LEDs takes them in the order given in its own
section below, so naming fewer than it drives lights the first of them and
leaves the rest out. Naming more than it drives is a mistake, and `errors.txt`
says so.

### Traffic lights and crossings

`traffic_light` wants three LEDs, and lights them red, amber and green in
that order. It switches instantly, so add `ease` for the lamps of a real signal:

```entry
stripDat1-3 ease=0.3: traffic_light
```

`pelican_crossing` wants five LEDs: the same three, then the two figures a
pedestrian reads, stop and walk. In place of red and amber it flashes the amber
and the walking figure together, as a pelican does while a crossing ends. It
comes round on its own clock, there being no button to press:

```entry
stripDat1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

Three LEDs on `pelican_crossing` is its traffic lights on their own:

```entry
stripDat1-3: pelican_crossing
```

### Sweep

`sweep` is a light that crosses the LEDs and turns back at each end, the back
and forth a scanner does. Its `extent` is how far it reaches from itself, in
LEDs, and its `speed` counts one crossing as the travelling effects count one
pass. Its `hold` waits at each end, in seconds, giving a trail time to clear
before the light comes back over it:

```entry
stripDat ease=0.4: sweep speed=1 length=60 extent=1 hold=1
```

Give `extent` a whole number of LEDs, such as 1 or 2. In between it dims as
the light passes between two LEDs and brightens as it lands on one, which
reads as stepping. 1 is the tightest that travels smoothly.

### Blinking through colours

`rgb_blink` takes one colour, or several to blink through in turn, divided by
`|` since a comma would mean one colour for each LED. It has no colour of its
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

## LED strips

The two screw terminals are marked **DAT** and **CLK**. A WS2812 strip needs
only a data line, so one can go on each terminal: `stripDat` and `stripClk`. An
APA102 strip needs both, data and clock, so it is the one strip on the board,
`stripApa`. A strip's LEDs take the same effects, colours and levels the board's
LED does. Tell the board how long a strip is first, since that is the one thing
it cannot work out for itself:

```entry
board: stripDat=60
stripDat: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `stripDat` | every LED on the strip |
| `stripDat5` | one of them |
| `stripDat1-10` | the first ten |
| `stripDat60-1` | all sixty, the other way round, for a strip mounted backwards |

`stripClk` and `stripApa` are named the same way. An APA102 strip has a
brightness of its own for the whole strip, at 50% unless the board line says
otherwise, such as `stripApa=144|75%`. The effects' own levels apply on top of
it.

`stripApa` and the WS2812 strips cannot play at once, since they use the same
terminals. A file naming both plays the WS2812 strips and says so in
`errors.txt`.

Each LED shows a colour of its own, so `stripDat5.r` is not a thing to write; set
`colour` on the LEDs instead, as the board's LED takes it.

Most strips take their colours as green, red, then blue, and the board sends
them that way. If yours shows another colour where you asked for red, it takes
them in another order: write the letters `r`, `g` and `b` after its length in
the order it wants them, such as `stripDat=60|rgb`.

## Screens

### Naming screens

A screen on the SP/CE connector is named `screen`. A screen
cannot say what size it is, so tell the board:

```entry
board: screen=1.54
```

That is a board entry, which sets the board rather than the lights and is one of
a handful covered under [The board](#the-board).

The sizes are 2.8 and 1.54, and a screen plays nothing until its size is given.
Changing it needs the board turned off and on again before the new size takes.

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
screen rotation=90: gif file="clock.gif"
screen offset=*|20 bg=black: image file=logo.png
screen tile=repeat: image file=bricks.png
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
screen: gif file="clock.gif"
screen: image file=logo.png
screen: sequence folder=photos interval=30
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
screen: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the seconds to wait where it turns around, so a ping-pong pauses at
each end instead of bouncing straight off. One value serves both ends, or write
each with a `|`:

```entry
screen: gif file="wave.gif" ping_pong=yes hold=1
screen: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

A file is looked for on this drive first, then on the board itself, and the name
may include folders. There is little room here, so pictures usually live on the
board.

The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker
offers none.

The panel is mounted upright, 240 wide by 320 tall, so a landscape picture is
cropped at its sides unless the line turns it, with `rotation=90`.

**A limit for now.** The board's memory is small, and what the last file showed
can keep its room until a restart. Saving a change from one full-size picture
to another is refused with a note in `errors.txt`; turn the board off and on
with the new file saved and it plays. Animations under about 60KB of frames,
small pictures, and drawings with `pixel_double=true` change over without a
restart. The lights are never affected.

### Drawing from code

**This one is for Python writers.** A screen can play a drawing instead of a
picture: a Python file with one function in it, drawn beside everything else in
this file, so the lights keep their effects,
and a scene puts the drawing on and off with everything else it holds.

| Plays | Settings |
| --- | --- |
| `graphics` | `file` `fps` `interval` `width` `height` |

```entry
screen: graphics file=rings.py
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

A program that wants the whole board instead of one screen is
[a program](#running-your-own-program), not a drawing.

The picker offers a drawing on its Screens tab where the drawing's opening string
starts with `Drawing:` and its name, and keeps it out of its programs. It cannot
run the drawing, so it shows it by a face instead, which two more lines can set:

```python
'''
Drawing: Rings
Rings that grow and fade, in the four colours.
Icon: *
Colour: orange
'''
```

`Icon` is any one character, an emoji included, and `Colour` one of the colour
words or a hex. A drawing naming neither is shown by its initial, on a colour
taken from its name.

## Scenes

A file can hold several sets of effects and show them one after another. A
heading in square brackets begins one, and says how long it shows for:

```entry
[Daytime: 30s]
stripDat: rainbow_wave speed=0.3

[Night: 2m]
stripDat colour=ff5a00: flicker_each
```

The name is everything before the `:` and may be anything you like, spaces
included. The time is in seconds, `30s`, or in minutes, `10m`. Scenes take turns
in the order they are written, then start again.

Entries before the first heading are always on, whatever is showing, so anything
that should never change goes there:

```entry
rgb: static brightness=0.2
```

While a scene shows, an LED it does not name goes dark if any other scene
uses it, and is left alone if none of them do. A scene may name an LED that
is always on, and takes it over for as long as it shows.

A screen behaves the same way: its picture stays put but the light goes out
while another scene has the board, and comes back when its own returns.

Add `restart` to a heading and its effects begin again every time it comes
round, instead of carrying on from where they were left:

```entry
[Beacon: 5s restart]
stripDat1-3: flash_sequence flashes=3
```

The board entry belongs outside every scene. A single scene with no time simply
shows for ever, and ejecting this drive always starts again at the first scene.

## The board

One entry sets the board rather than the lights, and names no LED:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until you ask for it | shown at boot |
| `reload` | `auto` plays the file the moment it is saved | wait for an eject or **Boot** |
| `program` | a Python file to run instead of the effects | the effects run |
| `args` | what to pass that program, divided by `\|` | it is given none |
| `screen` | what size of screen is on the SP/CE connector | no screen |
| `stripDat` | how many LEDs are on a WS2812 strip on **DAT**, and after a `\|` the order it takes its colours in | no strip |
| `stripClk` | the same for **CLK** | no strip |
| `stripApa` | how many LEDs are on an APA102 strip across both terminals, and after a `\|` its brightness | no strip |

With `reload=auto`, saving `effects.txt` is enough on its own: the board notices
the save, takes the drive back for a moment, and plays the new effects, exactly
as a single press of **Boot** would. Only a save to `effects.txt` counts, so
copying pictures on never interrupts anything.

### Running your own program

A program can sit on this drive or on the board's own filesystem, and its name
may include folders: it is looked for here first, then on the
board.
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

`screen` describes the screen this file's own entries play on, so a program never sees it:
it sets its own up. Pass it the size in `args` if it
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

The picker's **A program** tab lists every Python file at the top of this
drive,
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
A file whose opening string starts `Drawing:` is [a drawing](#drawing-from-code),
so it is left out.

## When something is wrong

The board's LED says so, and the more flashes the worse it is:

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
- [The PicoVector drawing API](https://badgewa.re/docs), for programs that draw on a screen
