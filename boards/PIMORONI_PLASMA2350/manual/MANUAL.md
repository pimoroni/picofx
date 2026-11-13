<!-- Generated from boards/manual/ and this board's own parts by tools/build_manual.py. Edit those and rebuild; edits here are lost. -->

# Plasma 2350

Two LED terminals, a screen connector on the 2350, and a page on this drive that sets them all up for you. Open the
picker, choose your looks and save, and you'll see them play a few seconds
later. No code is needed, though you can write your own programs whenever you
want to.

## Getting started

The quickest way to start is the picker. Open it in Chrome or Edge, with
[[Picker]] at the top of this page or `PICKER.html` on this drive, then press
[[Open FX drive]] and choose this drive. Choose a look from the cards and press
[[Save to board]]. A few seconds later the drive disappears briefly, then comes
back with your changes playing. [The picker](#the-picker) shows you everything
else it can do.

While the board starts up or loads your changes, its LED blinks slowly between
dim and bright white until the effects begin.

If a save does not seem to work, press **Boot** once or eject this drive, as a
computer does not always finish writing to a drive straight away.

You can hide the drive when you don't need it. Double-press **Boot** to hide it,
and double-press again to bring it back.

While the computer copies files to this drive, the effects pause and the board's
LED glows dim white with a brighter blink. The effects resume shortly after the
copy finishes.

## The picker

The picker is where you choose what your board plays, from the looks on its
lights to a whole program. You'll be greeted with whatever the board is playing
right now, so you can carry on from there. Nothing reaches the board until you
press [[Save to board]], so feel free to try things out.

### The page: Getting around

Along the top are [[Open FX drive]], [[Save to board]] and [[Check board]]. Below
them are two large tabs. **Effects** is where you'll spend most of your time, and
**Programs** runs a program instead.

```picker
header: Plasma 2350 Picker
pages: *Effects, Programs
tabs: *DAT strip, CLK strip, ~APA102 strip, LED=Rainbow, Screens=2.8"
```

Under **Effects** you'll find **DAT strip**, **CLK strip** and **APA102 strip**
for the strips, **LED** for the board's own light, and **Screens**. Each tab
shows a small preview of what it's playing, and [[Edit board]] sits at the end
of the row.

### Lights: Choosing a look

On a strip's tab or **LED** you'll see your lights, and below them a bar showing what each
stretch of them plays.

When your board is new, the picker opens on **DAT strip** with all 66 LEDs as one
stretch, playing nothing yet. The board's own LED, on the **LED** tab, plays
Rainbow.

```picker
badge strip: Strip, 66 LEDs, GRB
strip: *Nothing 66
tools:
settings: Nothing, on LEDs 1 to 66 of the strip on DAT
cards Along the lights: Rainbow, Wave, Scanner, Chase, Marquee, *Nothing
```

Click the bar, or any light, to select that stretch. Then click a card in the
gallery to play that look there.

The cards are grouped by how they play. **Along the lights** travel from one end
to the other, **Ready-made** looks combine several others, **All together** shows
the same on every light, and **Individual** gives each light its own part. Cards
with a small palette let you choose the colour, and [[Nothing]] turns the stretch
off.

The selected stretch's settings sit just above the gallery. Every look has a
brightness, and most also have a speed and a setting of their own. A look that
takes a colour shows a row of colours to choose from, with [[custom]] for any
other. [[Reverse]] changes which end a travelling look starts from. If you want
an exact figure, the arrow at the right of the sliders opens a drawer to type it
in.

### Lights: Cutting into stretches

To play more than one look, cut the bar into stretches. Hover over the bar where
you want a cut, between two lights, and click.

Choose Rainbow first, then try a cut about halfway along. You'll have two
stretches, both playing Rainbow. Click the right-hand one and choose Scanner, and
a light starts sweeping along that half.

```picker
badge strip: Strip, 66 LEDs, GRB
strip: Rainbow 33, *Scanner 33
tools:
settings: Scanner, on LEDs 34 to 66 of the strip on DAT, colour red, Brightness 100, Speed 50
cards Along the lights: Rainbow, Wave, *Scanner, Chase, Marquee
```

Drag a cut to move it, or click the cross on it to remove it.

The tools under the bar do the same in one go. [[Split into]] cuts the selected
stretch into a number of equal [[stretches]], or into stretches of so many
[[lights each]]. [[Join all]] puts the bar back to one stretch. [[Repeat]] takes
the number of stretches you set, starting with the selected one, and repeats
them to the end. The arrows above the bar undo and redo.
On a long strip, the magnifier buttons zoom in so each LED is easier to reach.

### Board: Setting up your hardware

Press [[Edit board]] to tell the picker about your hardware. Everything else
fades while you're there, and [[Done]] takes you back.

Look out for the chip icon on [[Edit board]]. The picker marks every board
setting with it, such as the order your lights are wired in. These settings
describe your hardware, so they're shared by every scene.

```picker
tabs editing: *DAT strip, CLK strip, ~APA102 strip, LED=Rainbow, Screens=2.8"
stripsetup: 66
```

Choose which strips are fitted, then set how many LEDs each has and its colour
order, which needs changing if red shows as another colour. An APA102 strip uses
both terminals, so it replaces the other two. On **Screens**, set the size of
the screen.

### Screens: Showing a picture

Once the drive is open, the pictures and drawings on it appear on the
**Screens** tab, under the screen. Press the button under a picture to show it
there. Each screen has its own settings for the picture it shows, such as its
backlight, rotation and position, and the timing of an animation.

```picker
screen: 2.8 inch, logo.png
pictures: logo.png=A, sunset.jpg, waves.gif
```

To add your own, drop GIF, PNG or JPEG files or drawings onto the **add pictures
or drawings** tile, and the picker copies them onto the drive. Each picture has a
button to delete it from the drive.

### Scenes: Playing one after another

Press [[+ split into scenes]] to have the board play one setup after another.
What you've set up so far becomes Scene 1, and a tray of cards appears above
the tabs, one for each scene. A card shows the scene's name, an icon for each
part of the board it sets, and how it ends, such as "10s" or "45s, then Day".
Click a card to work on that scene, and drag it by the grip beside its name to
change the order. [[+ another scene]] adds one, and when the cards fill their
last row it becomes a thin bar under them.

```picker
pages: *Effects, Programs
scenes: Always on, *Scene 1 10s
```

Each scene takes the colour of its place, matching the number buttons on the
Aye Arr Remote, so the first scene is red like button 1 and the tenth takes the
rainbow of button 0. A scene you move takes the colour of its new place.

Everything below the tray sits in a frame of the chosen scene's colour, with the
scene's settings on a tab at its top left: its name, whether it "shows for" a
number of seconds or "waits", and the scene after it. That's the next scene
unless you choose another, or "itself" to repeat it. Tick "restart each time" to
have a scene start its effects from the beginning each time it plays, instead of
carrying on where they left off. A scene that goes back to itself always
restarts, so its tick stays on. With only one scene, "shows for" repeats it
after that many seconds, and "waits" keeps it showing.

Beside the tab, the page says where the scene comes, such as "Scene 2 of 4, then
Day", and [[Remove scene]] takes it away.

Each scene needs a name of its own. While its name is empty, "Always on" or
another scene's, the name is outlined and the words beside the tab say why.
Leave it that way and the scene goes back to its last name that worked.

### Scenes: Playing over Always on

The first card, **Always on**, runs down the left of the tray. Anything on it
plays under every scene. A scene that plays on the same part of the board takes
over from it while that scene shows.

With a scene chosen, the page shows what the board plays where the scene sets
nothing. Those lights play Always on's look, on tiles striped inside a dashed
outline. A light that only another scene uses is dark, as the board turns it
off, and the bar names the scene that lights it. In a scene, [[Nothing]] means
the scene sets nothing of its own there, so Always on can still play.

A screen the scene leaves to Always on shows Always on's picture in the same
striped frame, with its settings greyed, as they're set on Always on. To turn a
screen off in a scene, press its button on the small black [[Off]] card at the
end of the first heading on **Screens**. The screen then shows black.

### Programs: Running a program

**Programs** lists your own programs on this drive, to run instead of the
effects.
Choose one and save, and the board restarts to run it. The **With** buttons above
the list name the hardware the programs use, so turn off anything you don't have
and you'll only see programs that work without it. [[Choose none]] goes back to
the effects. [Your program in the picker](#your-program-in-the-picker) explains
how your own programs appear there.

```picker
pages: Effects, *Programs=My lights
note: my_lights.py
programs On the drive | your own programs: *My lights
```

### Saving: Sending to the board

[[Save to board]] writes your changes, and the board loads them a few seconds
later. The picker tells you when the board is playing your save, and whether it
found any problems. [[Check board]] asks the board again at any time.

The arrow beside [[Save to board]] opens the save settings. Untick "Play saves
without an eject" and the board waits for an eject or a single press of
**Boot**. Tick "Keep the drive hidden at start" and the drive stays hidden until
**Boot** is double-pressed.

```picker
header: Plasma 2350 Picker | Playing on the board. No problems reported.
savemenu:
```

On a Mac, each save shows "Disk Not Ejected Properly" once and closes any Finder
window on this drive. Don't worry, the drive comes back a few seconds later and
the page carries on.

The page can only reach the drive in Chrome, Edge or another Chromium-based
browser. Safari and Firefox cannot write to a drive from a web page, so the
picker says so there. [The editor](#the-editor) can still save from them, as a
download.

<!-- contents fold -->

## The editor

The picker saves everything into one text file on this drive, `effects.txt`, and
shows the file it will write at the foot of the page. The file can also be edited
by hand in any text editor, and [writing an entry](#writing-an-entry) and the
sections after it describe its format. The picker keeps lines it cannot edit
unchanged, and asks before replacing a file it has not read.

Deleting `effects.txt` restores the default file. Emptying it turns everything
off.

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

### Brightness effects

These work for any LED.

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

### Colour effects

These bring their own colour, and work for any LED.

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

A drawing with nothing new to show can return `False` from `draw`, and the
board then sends no frame. A clock that changes once a second can check what
it last drew and return `False` the rest of the time, leaving the board free
for the lights and the other screen.

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

Each scene needs a name of its own. A heading with no name, or with a name
another scene already has, even in different capitals, is reported in
`errors.txt`. The picker also keeps the name "Always on" for the entries before
the first heading.

Entries before the first heading are always on, whichever scene is playing, so
put anything that should never change there:

```entry
rgb: static brightness=0.2
```

While a scene plays, an LED it does not name plays its always-on entry.
Where there is none, it goes dark if another scene uses it, and is left alone
otherwise. A scene can name an always-on LED and takes it over while the
scene plays, and `none` turns it off for that scene:

```entry
[Night: 10m]
rgb: none
```

Screens behave the same way. A screen the scene does not name shows its
always-on picture, even where the always-on entry names both screens, as
`screenA,B`, and the scene takes only one. Where there is none, the picture
stays but the backlight turns off while another scene plays, and comes back
when its own scene returns.
`none` turns a screen off for a scene, showing black, or its `background`
colour, at the backlight set before the colon:

```entry
[Night: 10m]
screen backlight=0%: none
```

Add `restart` to a heading to restart that scene's effects each time it
plays, instead of resuming where they left off:

```entry
[Beacon: 5s restart]
stripDat1-3: flash_sequence flashes=3
```

A scene hands over to the next one in order. The picker can choose another,
which it writes after `then` at the end of the heading. `then` ends the
heading's settings, so everything after it is the next scene's name, spaces and
all, and `restart` goes before it:

```entry
[Night: 45s restart then Day]
```

A scene can also go back to itself, to begin its effects again each time its
time is up. That needs `restart`, as does a file's only scene when it has a
time, since otherwise nothing changes when the time is up, and `errors.txt`
says so:

```entry
[Storm: 30s restart then Storm]
```

The board entry goes before any scene heading. A scene with no time, such as
`[Welcome]`, waits, and the board stays on it. Put one last to play the scenes
before it once and then hold, such as an opening effect after the board starts.
A scene that no other scene goes on to never shows, and `errors.txt` says so.
Every reload, whether from a save, an eject or a press of **Boot**, starts again
from the first scene.

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

The picker's save settings write the first two. "Keep the drive hidden at start"
is `drive=manual`, and unticking "Play saves without an eject" is `reload=manual`.
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

<!-- contents Help -->

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

A drive that cannot be repaired can be returned to how it shipped by
installing the board's `-full` firmware from the
[picofx releases](https://github.com/pimoroni/picofx/releases/latest).
This erases everything on the drive, so copy off anything you want to
keep first.

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
