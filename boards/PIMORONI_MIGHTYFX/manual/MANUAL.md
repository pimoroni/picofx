<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Mighty FX

Seven outputs, two screen connectors, and a text file that controls them. Edit `effects.txt` on this
drive and save it, and the board plays the change a few seconds later. No code
is needed, though you can write your own programs when you want to.

## Getting started

Edit `effects.txt` and save it to change what the lights do. A few seconds later
the drive disappears briefly, then comes back with the new effects running, so
you can keep editing.

If a save does not seem to work, press **Boot** once or eject this drive, as a
computer does not always write the file straight away. Double-press **Boot** to
hide the drive, and double-press it again to show it.
Each double press runs a dim white light along the outputs, towards the
USB connector when the drive is shown and away from it when it is hidden.

Deleting `effects.txt` restores the default file. Emptying it turns everything
off.

While the computer copies files to this drive, the effects pause and a
dim white light travels along the outputs. The effects resume shortly
after the copy finishes.

**Prefer not to write the file by hand? `PICKER.html` on this drive writes it
for you. See [the picker](#the-picker). `EDITOR.html` helps you write it,
suggesting names as you type. See [the editor](#the-editor).**

**The board also comes with ready-made programs, from single effects to whole
builds, and one line in `effects.txt` runs any of them. See [what is already
on the board](#what-is-already-on-the-board).**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page loads the file
the board is playing, so you can carry on from there. A preview of the file it
will write is at the foot of the page.

The picker has two tabs, **The effects** and **A program**. **The effects**
controls the lights, screens and sound: select a stretch of outputs or LEDs,
choose a look from the cards, and adjust its settings. A run can be split into
stretches, each playing its own look. **Edit board**, at the end of the lights'
tabs, sets up your hardware: the order the lights are wired in, the number of
LEDs on each strip, each screen's size, and a Screen Hub. The Screens and Sound
tabs list the pictures, drawings and sounds on this drive, and can copy files
onto the drive or delete them. Press **+** to split your setup into scenes that
play in turn, each with its own looks, pictures and sound. Anything on the
**Always on** tab plays under every scene.

**A program** runs one of the board's programs instead of the effects:
the showcase signs, screen pieces, and what a remote, a sensor, a speaker or a motor brings, as well as any of your own programs on this
drive.
Choose one and save, and the board restarts to run it. [Your program in the
picker](#your-program-in-the-picker) explains how your own programs appear there.

**Save to board** writes the file, and the board loads it a few seconds later.
The arrow beside it opens the save settings. Untick "Play saves without an eject"
and the board waits for an eject or a single press of **Boot**, which is
`reload=manual`. "Keep the drive hidden at start" is `drive=manual`. **Check
board** reads `errors.txt` and shows any problems the board found with each line.
On a Mac, each save shows "Disk Not Ejected Properly" once and closes any Finder
window on this drive. The drive comes back a few seconds later and the page
continues.

The page can only reach the drive in Chrome, Edge or another Chromium-based
browser. Safari and Firefox cannot write to a drive from a web page, so the
picker says so there, but `effects.txt` can still be edited in any text
editor.

The picker writes an ordinary `effects.txt`, so anything it makes can be edited
by hand afterwards. Lines the picker cannot edit are kept unchanged, and it asks
before replacing a file it has not read.

## The editor

`EDITOR.html` on this drive is a text editor for `effects.txt` that understands
its format. Each word is coloured by its role, and as you type it suggests what
fits: the outputs and screens at the start of a line, the effects after the colon,
then that effect's settings and their values. A hint below the text describes
the value expected. Tab or Enter accepts a suggestion, Escape dismisses it, and
Ctrl+Space shows suggestions again.

It underlines names it does not recognise, such as a misspelt effect or a setting
the effect does not take. Values are not checked, as the board reads them itself.
**Save to board** writes the file and **Check board** reads `errors.txt`, as in
the picker.

It suggests only what this board's firmware provides, so new firmware features
appear without the page changing. It saves in one click from a Chromium browser,
as the picker does, and from Safari or Firefox as a download you then copy onto
this drive. It needs `catalogue.js`, which sits beside it on this drive.

## Writing an entry

```shape
<outputs> <their settings>: <effect> <its settings>
```

```entry
out1-7: rainbow_wave speed=0.3
out3 level=50%: pulse speed=0.6
```

Each entry has one colon. Before it go the outputs and their brightness or
colour. After it go the effect and its settings.

Settings you leave out use their defaults. A `#` starts a comment. An entry can
span several lines as long as the colon is on the first, and indentation does not
matter.

Screens are named the same way and play pictures. See [Screens](#screens).

## Outputs

### Naming outputs

| Written | Means |
| --- | --- |
| `out1` | one output |
| `out1,3,5` | three of them |
| `out1-7` | all seven |
| `out7-1` | all seven, in reverse order |
| `out2,1,5-7` | a mix, played in the order written |

Each output is a colour light. Its red, green and blue channels can also be
driven separately, as three mono lights:

| Written | Means |
| --- | --- |
| `out3.r` | the red channel only |
| `out3.*` | all three channels, in the order red, green, blue |
| `out1-7.*` | all 21, from 1's red to 7's blue |
| `out7-1.*` | all 21 in reverse order, from 7's blue to 1's red |

Order matters for effects that travel: they move through the outputs in the
order you write them, so list them in the order they appear in your build,
which need not be number order.

### Setting an output

These go before the colon, separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | brightness, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a colour name or six-digit hex code, for effects that bring no colour | white |
| `fade` | seconds to fade between changes, at a steady rate | changes instantly |
| `ease` | seconds to ease between changes, slowing at the end like a bulb | changes instantly |

```entry
out1-7 level=50%: pulse
out1-3 colour=warm: flicker
out4 colour=ff8040: static
out1 level=0.5, 2 level=0.8, 3-7: pulse_wave
out1-7 ease=0.4: blink speed=0.5
```

Colour names: red, orange, yellow, green, cyan, blue, purple, magenta, pink,
warm, white, cool, black. Or a hex code from a colour picker, without its `#`,
such as ff8040 for a paler orange. A `#` always starts a comment, so leaving it
on a colour hides the rest of the line.

### Fade and ease

`fade` and `ease` set how many seconds a change takes. `fade` changes at a
steady rate, like a stage light. `ease` changes quickly at first and slows
towards the end, like a warming bulb, and looks more natural on a light
switching on and off.

An output uses one or the other, so a line takes `fade` or `ease`, not
both. Two numbers separated by `|` set the rise and fall separately, for
example a light that comes on quickly and fades out slowly:

```entry
out1-7 fade=0.8: blink speed=0.5
out1-3 ease=0.05|1.2: blink speed=1
```

`fade` and `ease` belong to the output, not the effect, so they work with any
effect, except effects that set their own colours.

## Effects

Every setting is optional. Left out, it uses the default shown below.

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
| `flicker_each` | as `flicker` |
| `pulse` | `speed=1` `phase=0` |
| `pulse_wave` | `speed=1` `length=1` `phase=0` |
| `sweep` | `speed=1` `length=1` `extent=1` `hold=0` |
| `random` | `interval=0.05` `brightness_min=0` `brightness_max=1` |
| `random_each` | as `random` |
| `binary_counter` | `interval=0.1` `count=0` `step=1` |
| `traffic_light` | `red_interval=10` `red_amber_interval=5` `green_interval=10` `amber_interval=5` |
| `pelican_crossing` | `red_interval=8` `flashing_interval=6` `green_interval=20` `amber_interval=3` |

### For a whole output or a strip's LEDs, since these bring their own colour

| Effect | Settings |
| --- | --- |
| `rgb` | `red=255` `green=255` `blue=255` |
| `hsv` | `hue=0` `sat=1` `val=1` |
| `rainbow` | `speed=1` `sat=1` `val=1` |
| `rainbow_wave` | `speed=1` `length=1` `sat=1` `val=1` |
| `hue_step` | `interval=1` `hue=0` `sat=1` `val=1` `steps=6` |
| `rgb_blink` | `colour=red` `speed=1` `phase=0` `duty=0.5` |

### Effects that travel

Effects ending in `_wave`, `_sequence` and `_counter`, and `sweep`, travel
across the outputs you name. The others do the same thing on each one.

Effects ending in `_each` treat each output separately: `flicker_each` dips
each one at its own moments, like flames, and `random_each` gives each its own
brightness. `flicker` and `random` affect them all together, like a single light:

```entry
out1-7 colour=ff5a00: flicker_each dimness=0.6
```

`traffic_light` and `pelican_crossing` use their outputs in the order given
below. With fewer, they light only the first ones. Naming more is an error,
reported in `errors.txt`.

### Traffic lights and crossings

`traffic_light` needs three outputs, lit red, amber and green in that order.
It switches instantly, so add `ease` to look like a real signal's lamps:

```entry
out1-3 ease=0.3: traffic_light
```

`pelican_crossing` needs five outputs: the same three, then the pedestrian's
stop and walk figures. Instead of red and amber, it flashes amber and the walk
figure together, as a real pelican crossing does before it changes back. It
cycles on its own timer, as there is no button to press:

```entry
out1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

With three outputs, `pelican_crossing` plays its traffic lights only:

```entry
out1-3: pelican_crossing
```

### Sweep

`sweep` is a light that travels across the outputs and turns back at each end,
like a scanner. `extent` sets how far its glow reaches either side, in outputs,
and `speed` counts one crossing as one cycle, as the other travelling effects count
one pass. `hold` pauses at each end, in seconds, giving the trail time to fade
before the light returns:

```entry
out1-7 ease=0.4: sweep speed=1 extent=1 hold=1
```

Give `extent` a whole number of outputs, such as 1 or 2. A value in between
makes the light dim between outputs and brighten on each, so it appears to
step. 1 is the smallest that travels smoothly.

### Blinking through colours

`rgb_blink` blinks one colour, or several in turn separated by `|`, as a comma
would give each output its own colour. Without a colour it blinks red:

```entry
out1: rgb_blink colour=red|warm|ff8040 speed=0.5
```

### What the settings mean

`speed` is cycles per second: 1 is once a second, 0.5 once every two seconds,
2 twice a second. A negative speed runs the cycle backwards.

The settings measured in seconds are `interval`, `hold`, flicker's `bright_min`,
`bright_max`, `dim_min` and `dim_max`, and the four intervals `traffic_light`
and `pelican_crossing` each take. `length`, `flashes`, `steps`, `count` and
`step` are whole numbers, and a negative `step` counts down.

`red`, `green` and `blue` run from 0 to 255. The rest run from 0 to 1, written as
0.5 or 50%. These include `window`, the share of each cycle the flashes happen in.
`hue` also takes degrees, such as 180deg, as a colour picker shows them.

**If you write Python**, you can add your own effect to this list and use it like
any other. The library reference on
[GitHub](https://github.com/pimoroni/picofx/blob/main/picofx/README.md) explains
how, under Effects System.

## LED strips

A WS2812 LED strip plugs into the connector marked **L** or **R**, and its LEDs
take the same effects, colours and levels as the outputs. First tell the board
how many LEDs the strip has, as it cannot detect this:

```entry
board: stripL=60
stripL: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `stripL` | every LED on the strip |
| `stripL5` | one of them |
| `stripL1-10` | the first ten |
| `stripL60-1` | all sixty in reverse order, for a strip mounted backwards |

`stripR` does the same for the other connector. Both connectors share one power
supply, so a strip on either lights the small LED between them, and the unused
connector is powered too.

Each LED is one colour light, so `stripL5.r` is not valid. Set `colour` on the
LEDs instead, as an output takes it.

Most strips take their colours in the order green, red, blue, and the board
sends them that way. If yours shows a different colour when you ask for red,
it uses another order: write the letters `r`, `g` and `b` after its length in
the order it needs, such as `stripL=60|rgb`.

## Screens

### Naming screens

A screen on either SP/CE connector is named `screenA` or `screenB`. The board cannot detect a screen's size,
so tell it:

```entry
board: screenA=1.54
```

That is a board entry, covered under [The board](#the-board).

The sizes are 2.8 and 1.54, in inches across the panel, and a screen shows
nothing until its size is set.

### A Screen Hub

A Screen Hub uses both connectors and holds up to six screens, at positions
labelled A to F on the hub. Use `hub` to say which connector carries the hub's
SPI, the other carrying its Selects, then give the size at each fitted position:

```entry
board: screenA=hub hubA-D,F=2.8 hubE=1.54
hubA-C: gif file=flames.gif
hubD,F: image file=badge.png
```

Positions are named like outputs, `hubB` alone or `hubA-C,E` for several. A
picture shown on several positions is sent once, so it plays as smoothly on all
six as on one. A picture can only go to screens of one size, so give 2.8 and
1.54 positions separate entries. A position with nothing to show in a scene
stays black.

All six share one backlight, so `backlight` applies to the whole hub. The first
entry to set it wins, and `errors.txt` reports any conflict between entries
playing at once. Each scene can set its own.

### Setting a screen

These go before the colon, separate from what it plays:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `rotation` | 0, 90, 180 or 270, for how the screen is mounted | 0 |
| `backlight` | backlight brightness, 0 to 1, such as 0.5 or 50% | 1 |
| `mirror` | true to flip the picture left to right | no |
| `offset` | the picture's position, as `x\|y` | centred |
| `background` | the colour behind the picture, or `bg` for short | black |
| `pixel_double` | true to draw each pixel at double size, so a half size picture fills the screen | no |
| `tile` | `repeat` or `mirror` copies to fill the screen, as `across\|down` | off |

```entry
screenA rotation=90: gif file="clock.gif"
screenA offset=*|20 bg=black: image file=logo.png
screenA tile=repeat: image file=bricks.png
```

A picture is centred unless `offset` places it, and a `*` in place of either
number centres it on that axis.

`tile` fills the screen with copies of a small picture instead of a
background. `repeat` lays copies side by side, so a picture drawn to join up
at its edges makes a seamless pattern. `mirror` flips every other copy, so the
edges always join up. One value sets both directions, and two set them
separately: `tile=mirror|off` tiles across the screen only.

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

`gif` plays an animated GIF at its saved frame delays, `image` shows one
picture, and `sequence` plays a folder of pictures in the order of the numbers
in their names. Pictures can be PNG, JPEG or GIF. `file` or `folder` must
always be given. The board looks for it in this drive's `pictures` folder, where
the picker adds pictures, then at the top of the drive.

The example pictures are in the `examples/pictures` folder. To use one in an
entry, include the folder in its name, such as
`file=examples/pictures/medscan.gif`. The picker shows them on its Screens tab,
below your own pictures.

`fps` is frames per second and `interval` is seconds per frame, so use whichever
suits: `fps=12` for an animation, `interval=30` for a slideshow. Either replaces
the file's saved delays, and leaving both out keeps them. `loop` is true unless
set to false, which stops on the last frame. `ping_pong` plays forwards then
backwards instead of starting over, which suits an animation with two ends, such
as an arm flexing.

An animation drawn as a loop has no such ends, as its last frame leads back into
its first. Add `first_as_last=yes` to repeat the first frame at the end, so the
whole loop plays in each direction and a spinning coin turns all the way round
and back:

```entry
screenA: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the pause in seconds at each end, so a ping-pong rests before turning
back. One value sets both ends, or set each with a `|`:

```entry
screenA: gif file="wave.gif" ping_pong=yes hold=1
screenA: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

The board looks for a file on this drive first, then on the board itself, and
the name can include folders.

A screen updates less often than the lights, and effects on the outputs take
time from it. If a file asks for more frames than the screen can draw, it drops
frames to keep its timing.

### Drawing from code

**This section is for Python writers.** A screen can play a drawing instead of
a picture: a Python file with one function in it, drawn alongside everything
else in this file, so the lights keep their effects,
the other screen keeps its pictures,
and a scene shows and hides the drawing along with everything else in
it.

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
the seconds since the drawing started. The screen shows whatever it has drawn
when it returns. The rest of the file runs once, when the drawing starts, so set
up anything `draw` uses there. `fps` or `interval` sets the frame rate, and
leaving both out draws as fast as the screen allows.

`width` and `height` set the canvas size in pixels, overriding any other
setting. A small canvas draws faster and is placed like a small picture, so
`offset` positions it and `tile=repeat` fills the screen with it.

In a scene, the drawing's clock pauses while another scene plays, and a scene
with `restart` runs the whole file again from a blank canvas. `rotation`,
`offset` and the other screen settings place a drawing as they do a picture,
and `pixel_double` also halves the canvas size, which draws faster and uses a
quarter of the memory.

The board looks for the drawing in this drive's `drawings` folder, where the
picker adds drawings, then at the top of the drive. It can load pictures, such
as `picovector.image.load("/fx/pictures/faces.png")` for one in the `pictures`
folder. Do this once, in the setup. The drawing file itself is read once and
kept in memory.

A drawing can import `math`, `random`, `time` and `picovector`. The board's own
modules are reserved for the effects, so a pasted program that tries to use the
pins is refused, with a note in `errors.txt`. Any error in the file is reported
there too, with its line number, and a drawing that stops partway leaves its
last frame on the screen while everything else keeps running.

The examples under `examples/programs/screens/graphics` show what PicoVector can draw,
and a program that needs the whole board, not just one screen, is
[a program](#running-your-own-program), not a drawing.

The picker lists a drawing on its Screens tab, not with its programs, when the
drawing's opening string starts with `Drawing:` and its name. It cannot run the
drawing, so it shows an icon for it instead, which two more lines can set:

```python
'''
Drawing: Rings
Rings that grow and fade, in the four colours.
Icon: *
Colour: orange
'''
```

`Icon` is any single character, including an emoji, and `Colour` is a colour
name or hex code. A drawing that sets neither shows its initial, on a colour
chosen from its name.

## Sound

The board plays a WAV file through its onboard amplifier, alongside
everything else:

```entry
audio: wav file=chimes.wav
audio: wav file=ambience.wav loop=yes
```

| Plays | Settings |
| --- | --- |
| `wav` | `file` `loop=no` |

The file plays once each time the effects start, or repeatedly with `loop`.

The board looks for the file in this drive's `sounds` folder, where the picker
adds sounds, then at the top of the drive, then on the board itself. It
opens the file before this drive is shown, so the sound keeps playing when the
drive appears on a computer. While the computer copies files to this drive, the
sound pauses with the effects, and replacing a file while it plays silences it
until the next reload.

Use an uncompressed WAV file, mono or stereo. MP3 is not supported. This drive
holds nearly 13MB, so a lower sample rate fits more. A minute of 16-bit mono
takes about 2.6MB at 22kHz and under 1MB at 8kHz.

The board plays one sound at a time, so each scene takes one `audio` entry, and
one more can go before the first heading. An `audio` entry in a scene plays
while that scene plays, and one before the first heading plays in any scene
without its own sound. A sound paused by a scene change resumes where it left
off when its scene returns, and one that had finished starts again from the
beginning. A scene with `restart` starts its sound from the beginning every
time, along with everything else in it.

## Scenes

A file can hold several sets of effects, called scenes, and play them one
after another. A heading in square brackets starts each scene and sets how
long it plays:

```entry
[Evening: 30s]
out1-7: rainbow_wave speed=0.3

[Night: 10s]
out1-7 colour=warm: pulse
```

The name is everything before the `:` and can be anything, including spaces. The
time is in seconds, `30s`, or minutes, `10m`. Scenes play in the order written,
then repeat.

Entries before the first heading are always on, whichever scene is playing, so
put anything that should never change there:

```entry
out1: static brightness=0.2
```

While a scene plays, an output it does not name goes dark if another scene
uses it, and is left alone otherwise. A scene can name an always-on output and
takes it over while the scene plays.

Screens behave the same way: the picture stays, but the backlight turns off
while another scene plays, and comes back when its own scene returns.

Add `restart` to a heading to restart that scene's effects each time it
plays, instead of resuming where they left off:

```entry
[Beacon: 5s restart]
out1-3: flash_sequence flashes=3
```

The board entry goes before any scene heading. A single scene with no time plays
forever, and every reload, whether from a save, an eject or a press of **Boot**,
starts again from the first scene.

## The board

One entry sets up the board itself, and names no output:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until **Boot** is double-pressed | shown at boot |
| `reload` | `manual` plays a save only after an eject or a press of **Boot** | plays a few seconds after saving |
| `program` | a Python file to run instead of the effects | the effects play |
| `args` | arguments for that program, separated by `\|` | none |
| `screenA` | the size of the screen on SP/CE A, or `hub` for a Screen Hub | no screen |
| `screenB` | the size of the screen on SP/CE B | no screen |
| `hubA` to `hubF` | the size of the screen at each Screen Hub position | no screen there |
| `stripL` | the number of LEDs on the strip plugged into **L**, then after a `\|` its colour order | no strip |
| `stripR` | the same for **R** | no strip |

Saving `effects.txt` is all it takes: the board detects the save, briefly takes
the drive back, and plays the new effects, just as a single press of **Boot**
would. Only saving `effects.txt` triggers this, so copying pictures onto
the drive never interrupts anything. With `reload=manual`, a save waits for an
eject or a press of **Boot** instead.

### Running your own program

A program can be on this drive or on the board's own filesystem, and its name
can include folders. The board looks here first, then on the
board, so `program=examples/programs/effects/colour/rainbow_wave.py` runs one of the
examples the board comes with.
If both have a file with that name, the one on this drive
runs.

If the program is missing or stops with an error, the effects play instead
and `errors.txt` explains why, so a mistyped name never leaves the board
doing nothing.

Saving a file that names a program while the effects are playing restarts the
board, which then runs the program as it would at power-on.

The effects stop while a program runs, and **Boot** and ejecting do nothing. The
drive is always shown, even with `drive=manual`, so you can still edit
`effects.txt`. Saving it restarts the board with the new file. With
`reload=manual`, press **Reset** to apply the change. A program can read files
from this drive while it is shown, so its pictures and sounds can sit beside it
here.

When the program ends, the board plays the effects in the rest of the file.

A program never sees `screenA` and `screenB`, which set up the screens for this file's own entries. It sets up its own screens, so
pass it the size in `args` if it needs it.

`args` passes values to a program, so one program can behave differently
without being edited. Separate several with `|`, and put anything containing a
space or a colon in quotes:

```entry
board: program=slideshow.py args=posters|3
board: program=clock.py args="07:30"
```

**If you are writing the program**, read them from `sys.argv` as in any Python
program, starting at `sys.argv[1]`. Thonny passes none when you run the file
from there, so give each one a default and the file works either way:

```python
args = sys.argv[1:]
FOLDER = args[0] if args else "posters"
```

### Your program in the picker

The picker's **A program** tab lists every Python file at the top of this
drive and in its `programs` folder,
beside the examples in its `examples/programs` folder,
and describes each one from its opening string, the text in triple quotes at
the top of the file. The first sentence says what the program does, and these
lines control how the picker shows it:

```python
'''
Program: Big clock
Shows the time.
Args: Colour, Seconds = 10
Picture: clock.png
Section: Signs and displays
'''
```

| Line | What the picker does with it |
| --- | --- |
| `Program: Big clock` | names the program, in place of its file name |
| `Args: Colour, Seconds = 10` | gives each argument a box of its own, and writes `args=` from them |
| `Picture: clock.png` | shows that picture for the program, kept beside it |
| `Section: Signs and displays` | lists the program in that section, not under **On the drive** |
| `Thumbnail: servo` | draws a servo for a program with no picture, `servo pair` two of them, or `motor`, or `outputs` and a pattern such as `outputs rainbow` |

Each is optional. Without `Picture`, the picker shows `clock.png` for `clock.py`
if it exists, and `clock-2.png` as a second screen's picture. Without `Args`, a
program that reads `sys.argv` gets empty boxes for adding arguments.

A value after `=` in `Args` is the program's default, so the box starts with it,
and `args=` is left out while every argument keeps its default. An argument
named `Screen size` offers the sizes the firmware knows, and one named
`Rotation` offers 0, 90, 180 and 270, or the values it lists, such as `Rotation
= 90 or 270`, the first being the default. The picture always shows the program
at its defaults.

To change an example, choose it and press **Customise**. The picker copies it
and its pictures into `programs`, under a new name if that one is taken, and
chooses the copy. Open the copy from the drive in Thonny or another editor, then
press **Save to board** to run it.

To delete one of your own programs from the drive, press the cross in the
corner of its card. One in `programs` takes its pictures with it.

A board with a wireless module keeps `secrets.py` at the top of the drive for
your WiFi network's name and password, and restores an empty one if it is
deleted. Programs that go online, importing `network` or `requests`, are listed
only when the drive has that file.
An example is listed only in the section it names.
`examples/programs/sections.txt` sets the order of the sections, one per line:
its name, then a `|` and a description.
A file whose opening string starts with `Drawing:` is [a
drawing](#drawing-from-code), so it is not listed.

### What is already on the board

These come with the board, so `program=` can run any of them with nothing to
download:

| Folder | What is in it |
| --- | --- |
| `examples/programs/effects/mono` | one output at a time, and the effects that travel across several |
| `examples/programs/effects/colour` | the same in colour, with traffic lights and crossings |
| `examples/programs/function` | the Boot button, the sensor connector and the supply voltage |
| `examples/programs/infrared/mono` | effects chosen with an infrared remote |
| `examples/programs/infrared/colour` | the same in colour |
| `examples/programs/qwst` | light, tilt and temperature from Qw/ST breakouts |
| `examples/programs/screens/single` | one screen, its backlight, and finding what is attached |
| `examples/programs/screens/playback` | animated GIFs and slideshows |
| `examples/programs/screens/graphics` | drawing from code: text, colour wheels, a starfield |
| `examples/programs/screens/images` | still pictures |
| `examples/programs/screens/layout` | placing a picture on the screen |
| `examples/programs/screens/pair` | two screens working together |
| `examples/programs/screens/hub` | more than two, through a hub |
| `examples/programs/audio` | playing a wav file |
| `examples/programs/motors` | driving a pair of motors |
| `examples/programs/servos` | servos on the L and R connectors, alone, in a pair and steered by remote |
| `examples/programs/strips` | a rainbow along an LED strip, and filling one an LED at a time |
| `examples/programs/gpio` | using SP/CE pins as plain inputs and outputs, and fading LEDs on them |
| `examples/programs/wireless` | colours fetched over WiFi |
| `examples/programs/comms` | several boards working together |
| `examples/programs/showcase` | larger builds that put several of these together |

Three to start with:

```entry
board: program=examples/programs/effects/colour/sweep_trail.py
board: program=examples/programs/screens/playback/animated_gif.py
board: program=examples/programs/showcase/flip_dot_sign.py
```

Examples under `screens`, `audio`, `motors`, `servos`, `strips`, `gpio`,
`infrared` or `qwst` need that hardware attached. `wireless` needs a WiFi
network, `comms` needs a second board, and some showcase examples need their
own pictures or network.

The full list, with a description of each, is in the
[examples README on GitHub](https://github.com/pimoroni/picofx/tree/main/examples/mighty_fx).

## When something is wrong

The lights flash to show a problem, and more flashes means a more serious
one. Every output shows the colour:

| Flashes | What happened |
| --- | --- |
| white, once | the computer was still writing, so the press was ignored. Try again in a moment |
| blue, twice | a line in `effects.txt` could not be read, or a drawing failed. `errors.txt` names the line. A drawing's error appears there once the board has the drive back |
| red, three times | there was no room to write `errors.txt`. This drive is full or damaged, so free some space or repair it from a computer |

A setting with an invalid value is ignored and noted in `errors.txt`,
and the effect uses its default instead.

## More from Pimoroni

### Boards and accessories

- [Mighty FX](https://shop.pimoroni.com/products/mightyfx)
- [Tiny FX](https://shop.pimoroni.com/products/tinyfx)
- [Tiny FX W](https://shop.pimoroni.com/products/tiny-fx-w)
- [Plasma 2350](https://shop.pimoroni.com/products/plasma-2350)
- [Plasma 2350 W](https://shop.pimoroni.com/products/plasma-2350-w)
- [Everything in the range](https://shop.pimoroni.com/collections/tiny-fx)

### Going further

- [picofx on GitHub](https://github.com/pimoroni/picofx), the library these effects come from
- [The PicoVector drawing API](https://badgewa.re/docs), for programs that draw on a screen
