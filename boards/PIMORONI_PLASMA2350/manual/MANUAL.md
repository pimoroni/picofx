<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Plasma 2350

Two LED terminals, a screen connector on the 2350, and a text file that controls them. Edit `effects.txt` on this
drive and save it, and the board plays the change a few seconds later. No code
is needed, though you can write your own programs when you want to.

## Getting started

Edit `effects.txt` and save it to change what the lights do. A few seconds later
the drive disappears briefly, then comes back with the new effects running, so
you can keep editing.

If a save does not seem to work, press **Boot** once or eject this drive, as a
computer does not always write the file straight away. Double-press **Boot** to
hide the drive, and double-press it again to show it.

Deleting `effects.txt` restores the default file. Emptying it turns everything
off.

While the computer copies files to this drive, the effects pause and the board's
LED glows dim white with a brighter blink. The effects resume shortly after the
copy finishes.

**Prefer not to write the file by hand? `PICKER.html` on this drive writes it
for you. See [the picker](#the-picker). `EDITOR.html` helps you write it,
suggesting names as you type. See [the editor](#the-editor).**

## The picker

`PICKER.html` on this drive writes `effects.txt` for you. Open it in Chrome or
Edge, press **Open FX drive** and choose this drive, and the page loads the file
the board is playing, so you can carry on from there. A preview of the file it
will write is at the foot of the page.

The picker has two tabs, **Effects** and **Programs**. **Effects**
controls the strips, the board's LED and the screen: select a stretch of LEDs,
choose a look from the cards, and adjust its settings. A strip can be split into
stretches, each playing its own look. **Edit board**, at the end of the lights'
tabs, sets up your hardware: which strips are fitted, the number of LEDs on
each, and the screen's size. The Screens tab lists the pictures and drawings on
this drive, and can copy files onto the drive or delete them. Press **+** to
split your setup into scenes that play one after another, each with its own looks and
pictures. Anything on the **Always on** tab plays under every scene.

**Programs** lists your own programs on this drive, to run instead of the
effects.
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
fits: the strips, the board's LED and the screen at the start of a line, the effects after the colon,
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
<LEDs> <their settings>: <effect> <its settings>
```

```entry
stripDat: rainbow_wave speed=0.3 length=30
rgb level=50%: pulse speed=0.6
```

Each entry has one colon. Before it go the LEDs and their brightness or
colour. After it go the effect and its settings.

Settings you leave out use their defaults. A `#` starts a comment. An entry can
span several lines as long as the colon is on the first, and indentation does not
matter.

Screens are named the same way and play pictures. See [Screens](#screens).

## The board's LED

The RGB LED on the board is `rgb`, and takes any effect. The LEDs of a strip are
named under [LED strips](#led-strips).

```entry
rgb: rainbow speed=0.3
```

### Setting an LED

These go before the colon, separate from the effect:

| Setting | What it does | If omitted |
| --- | --- | --- |
| `level` | brightness, 0 to 1, such as 0.5 or 50% | 1 |
| `colour` | a colour name or six-digit hex code, for effects that bring no colour | white |
| `fade` | seconds to fade between changes, at a steady rate | changes instantly |
| `ease` | seconds to ease between changes, slowing at the end like a bulb | changes instantly |

```entry
stripDat level=50%: pulse
stripDat1-30 colour=warm: flicker
rgb colour=ff8040: static
stripDat ease=0.4: blink speed=0.5
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

An LED uses one or the other, so a line takes `fade` or `ease`, not
both. Two numbers separated by `|` set the rise and fall separately, for
example a light that comes on quickly and fades out slowly:

```entry
stripDat fade=0.8: blink speed=0.5
stripDat1-3 ease=0.05|1.2: blink speed=1
```

`fade` and `ease` belong to the LED, not the effect, so they work with any
effect, except effects that set their own colours.

## Effects

Every setting is optional. Left out, it uses the default shown below.

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
| `rgb_blink` | `colour=red` `speed=1` `phase=0` `duty=0.5` |

### Effects that travel

Effects ending in `_wave`, `_sequence` and `_counter`, and `sweep`, travel
across the LEDs you name. The others do the same thing on each one.

Effects ending in `_each` treat each LED separately: `flicker_each` dips
each one at its own moments, like flames, and `random_each` gives each its own
brightness. `flicker` and `random` affect them all together, like a single light:

```entry
stripDat colour=ff5a00: flicker_each dimness=0.6
```

`traffic_light` and `pelican_crossing` use their LEDs in the order given
below. With fewer, they light only the first ones. Naming more is an error,
reported in `errors.txt`.

### Traffic lights and crossings

`traffic_light` needs three LEDs, lit red, amber and green in that order.
It switches instantly, so add `ease` to look like a real signal's lamps:

```entry
stripDat1-3 ease=0.3: traffic_light
```

`pelican_crossing` needs five LEDs: the same three, then the pedestrian's
stop and walk figures. Instead of red and amber, it flashes amber and the walk
figure together, as a real pelican crossing does before it changes back. It
cycles on its own timer, as there is no button to press:

```entry
stripDat1-5 ease=0.3: pelican_crossing green_interval=20 red_interval=8
```

With three LEDs, `pelican_crossing` plays its traffic lights only:

```entry
stripDat1-3: pelican_crossing
```

### Sweep

`sweep` is a light that travels across the LEDs and turns back at each end,
like a scanner. `extent` sets how far its glow reaches either side, in LEDs,
and `speed` counts one crossing as one cycle, as the other travelling effects count
one pass. `hold` pauses at each end, in seconds, giving the trail time to fade
before the light returns:

```entry
stripDat ease=0.4: sweep speed=1 extent=1 hold=1
```

Give `extent` a whole number of LEDs, such as 1 or 2. A value in between
makes the light dim between LEDs and brighten on each, so it appears to
step. 1 is the smallest that travels smoothly.

### Blinking through colours

`rgb_blink` blinks one colour, or several in sequence separated by `|`. A comma
instead would give each LED its own colour. Without a colour it blinks red:

```entry
rgb: rgb_blink colour=red|warm|ff8040 speed=0.5
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

The two screw terminals are marked **DAT** and **CLK**. A WS2812 strip needs
only a data line, so one can go on each terminal: `stripDat` and `stripClk`. An
APA102 strip needs both data and clock, so it is the only strip on the board,
`stripApa`. A strip's LEDs take the same effects, colours and levels as the
board's LED. First tell the board how many LEDs each strip has, as it cannot
detect this:

```entry
board: stripDat=60
stripDat: rainbow_wave speed=0.3
```

| Written | Means |
| --- | --- |
| `stripDat` | every LED on the strip |
| `stripDat5` | one of them |
| `stripDat1-10` | the first ten |
| `stripDat60-1` | all sixty in reverse order, for a strip mounted backwards |

`stripClk` and `stripApa` are set the same way. An APA102 strip also has an overall
brightness, about half by default, set after its length on the board line, such as
`stripApa=144|75%`. The effects' own levels apply on top of it.

`stripApa` and the WS2812 strips cannot play at once, since they use the same
terminals. A file naming both plays the WS2812 strips and reports the
conflict in `errors.txt`.

Each LED is one colour light, so `stripDat5.r` is not valid. Set `colour` on the
LEDs instead, as the board's LED takes it.

Most strips take their colours in the order green, red, blue, and the board
sends them that way. If yours shows a different colour when you ask for red,
it uses another order: write the letters `r`, `g` and `b` after its length in
the order it needs, such as `stripDat=60|rgb`.

## Screens

### Naming screens

A screen on the SP/CE connector is named `screen`. The board cannot detect a screen's size,
so tell it:

```entry
board: screen=1.54
```

That is a board entry, covered under [The board](#the-board).

The sizes are 2.8 and 1.54, in inches across the panel, and a screen shows
nothing until its size is set.

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
screen rotation=90: gif file="clock.gif"
screen offset=*|20 bg=black: image file=logo.png
screen tile=repeat: image file=bricks.png
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
screen: gif file="clock.gif"
screen: image file=logo.png
screen: sequence folder=photos interval=30
```

`gif` plays an animated GIF at its saved frame delays, `image` shows one
picture, and `sequence` plays a folder of pictures in the order of the numbers
in their names. Pictures can be PNG, JPEG or GIF. `file` or `folder` must
always be given. The board looks for it in this drive's `pictures` folder, where
the picker adds pictures, then directly on the drive.

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
screen: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the pause in seconds at each end, so a ping-pong rests before turning
back. One value sets both ends, or set each with a `|`:

```entry
screen: gif file="wave.gif" ping_pong=yes hold=1
screen: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

The board looks for a file on this drive first, then on the board itself, and
the name can include folders.

The Plasma 2350 W has no SP/CE connector, so it takes no screen, and the picker
offers none.

A 2.8 inch panel is mounted upright, 240 wide by 320 tall, so a landscape
picture is cropped at the sides unless the line rotates it with
`rotation=90`.

### Drawing from code

**This section is for Python writers.** A screen can play a drawing instead of
a picture: a Python file with one function in it, drawn alongside everything
else in this file, so the lights keep their effects,
and a scene shows and hides the drawing along with everything else in
it.

| Plays | Settings |
| --- | --- |
| `drawing` | `file` `fps` `interval` `width` `height` `style` |

```entry
screen: drawing file=rings.py
```

```python
# rings.py
from picovector import color, shape

middle_x = canvas.width / 2
middle_y = canvas.height / 2

def draw():
    canvas.pen = color.black
    canvas.clear()
    canvas.pen = color.rgb(255, 160, 40)
    canvas.shape(shape.circle(middle_x, middle_y, 20 + (ticks % 3000) / 100))
```

`draw` is called for each frame, and the screen shows whatever it has drawn
when it returns. It can use three names the board provides. `canvas` is the
image to draw on, the size of the screen and kept between frames. `ticks` is
the milliseconds since the drawing started, so `ticks / 1000` is the time in
seconds, and `ticks_delta` is the milliseconds since the last frame. `fps` or
`interval` sets the frame rate, and leaving both out draws as fast as the
screen allows.

The rest of the file runs once, when the drawing starts, so set up anything
`draw` uses there. `canvas` is ready by then, so the setup can size things to
the screen, as `middle_x` and `middle_y` are here, or paint a background for
`draw` to build on.

`width` and `height` set the canvas size in pixels, overriding any other
setting. A small canvas draws faster and is placed like a small picture, so
`offset` positions it and `tile=repeat` fills the screen with it.

`style` passes a word to the drawing, which finds it as `style`, or `None`
where the entry sets none. A drawing drawn in several styles lists them in a
`Styles` line of its opening string, such as `Styles: cat, owl, goat`, the
first being the one it takes where none is set, and the picker offers them as
a choice. A drawing with more than one choice to make gives a `Styles` line
for each, and the entry joins its choices with a dash, such as
`style=ember-bare`.

In a scene, the drawing's clock pauses while another scene plays, and a scene
with `restart` runs the whole file again from a blank canvas. `rotation`,
`offset` and the other screen settings place a drawing as they do a picture,
and `pixel_double` also halves the canvas size, which draws faster and uses a
quarter of the memory.

The board looks for the drawing in this drive's `drawings` folder, where the
picker adds drawings, then directly on the drive. It can load pictures, such
as `picovector.image.load("/fx/pictures/faces.png")` for one in the `pictures`
folder. Do this once, in the setup. The drawing file itself is read once and
kept in memory.

A drawing can import `math`, `random`, `time` and `picovector`. The board's own
modules are reserved for the effects, so a pasted program that tries to use the
pins is refused, with a note in `errors.txt`. Any error in the file is reported
there too, with its line number, and a drawing that stops partway leaves its
last frame on the screen while everything else keeps running.

A program that needs the whole board, not just one screen, is
[a program](#running-your-own-program), not a drawing.

The picker lists a drawing on its Screens tab, not with its programs, when the
drawing's opening string has a `Drawing:` line with its name, and describes it
by the string's first sentence. It cannot run the drawing, so it shows an icon
for it instead, which two more lines can set:

```python
'''
Draw rings that grow and fade, in the four colours.

Drawing: Rings
Icon: *
Colour: orange
'''
```

`Icon` is any single character, including an emoji, and `Colour` is a colour
name or hex code. A drawing that sets neither shows its initial, on a colour
chosen from its name.

A `Defaults` line gives the screen settings the drawing is made for, written as
a program's `Args` line is, such as `Defaults: Rotation = 90 or 270, Pixel
double = true`. One rotation is where the drawing starts, and a list is the
only rotations it suits, the first being where it starts. When the drawing is
chosen, the picker turns the screen that way unless the drawing has been turned
on that screen before, and doubles its pixels on a half-size canvas only where
the line asks. `Pixel double = false` marks a drawing that needs the screen's
full resolution. While the drawing is turned or doubled otherwise than the line
says it suits, its Drawing settings say so, with a button to set it back.

## Scenes

A file can hold several sets of effects, called scenes, and play them one
after another. A heading in square brackets starts each scene and sets how
long it plays:

```entry
[Daytime: 30s]
stripDat: rainbow_wave speed=0.3

[Night: 2m]
stripDat colour=ff5a00: flicker_each
```

The name is everything before the `:` and can be anything, including spaces. The
time is in seconds, `30s`, or minutes, `10m`. Scenes play in the order written,
then repeat.

Entries before the first heading are always on, whichever scene is playing, so
put anything that should never change there:

```entry
rgb: static brightness=0.2
```

While a scene plays, an LED it does not name goes dark if another scene
uses it, and is left alone otherwise. A scene can name an always-on LED and
takes it over while the scene plays.

Screens behave the same way: the picture stays, but the backlight turns off
while another scene plays, and comes back when its own scene returns.

Add `restart` to a heading to restart that scene's effects each time it
plays, instead of resuming where they left off:

```entry
[Beacon: 5s restart]
stripDat1-3: flash_sequence flashes=3
```

The board entry goes before any scene heading. A single scene with no time plays
forever, and every reload, whether from a save, an eject or a press of **Boot**,
starts again from the first scene.

## The board

One entry sets up the board itself, and names no LED:

```entry
board: drive=manual program=fireplace.py
```

| Setting | What it does | If omitted |
| --- | --- | --- |
| `drive` | `manual` keeps the drive hidden until **Boot** is double-pressed | shown at boot |
| `reload` | `manual` plays a save only after an eject or a press of **Boot** | plays a few seconds after saving |
| `program` | a Python file to run instead of the effects | the effects play |
| `args` | arguments for that program, separated by `\|` | none |
| `screen` | the size of the screen on the SP/CE connector | no screen |
| `stripDat` | the number of LEDs on a WS2812 strip on **DAT**, then after a `\|` its colour order | no strip |
| `stripClk` | the same for **CLK** | no strip |
| `stripApa` | the number of LEDs on an APA102 strip across both terminals, then after a `\|` its brightness | no strip |

Saving `effects.txt` is all it takes: the board detects the save, briefly takes
the drive back, and plays the new effects, just as a single press of **Boot**
would. Only saving `effects.txt` triggers this, so copying pictures onto
the drive never interrupts anything. With `reload=manual`, a save waits for an
eject or a press of **Boot** instead.

### Running your own program

A program can be on this drive or on the board's own filesystem, and its name
can include folders. The board looks here first, then on the
board.
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

A program never sees `screen`, which sets up the screen for the entries in `effects.txt`. It sets up its own screens, so
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

The picker's **Programs** tab lists every Python file directly on this
drive and in its `programs` folder,
and describes each one from its opening string, the text in triple quotes that
opens the file. The first sentence says what the program does, and these lines
control how the picker shows it:

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

To delete one of your own programs from the drive, press the cross in the
corner of its card. One in `programs` takes its pictures with it.

A board with a wireless module keeps `secrets.py` directly on the drive for
your WiFi network's name and password, and restores an empty one if it is
deleted. Programs that go online, importing `network` or `requests`, are listed
only when the drive has that file.
A file whose opening string has a `Drawing:` line is [a
drawing](#drawing-from-code), so it is not listed.

## When something is wrong

The board's LED flashes to show a problem, and more flashes
means a more serious one:

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
