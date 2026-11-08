## Screens

### Naming screens

__SCREEN_NAMING__. The board cannot detect a screen's size,
so tell it:

```entry
board: __SCREEN__=1.54
```

That is a board entry, covered under [The board](#the-board).

The sizes are 2.8 and 1.54, in inches across the panel, and a screen shows
nothing until its size is set.

<!-- if hub -->
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
<!-- end -->

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
__SCREEN__ rotation=90: gif file="clock.gif"
__SCREEN__ offset=*|20 bg=black: image file=logo.png
__SCREEN__ tile=repeat: image file=bricks.png
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
__SCREEN__: gif file="clock.gif"
__SCREEN__: image file=logo.png
__SCREEN__: sequence folder=photos interval=30
```

`gif` plays an animated GIF at its saved frame delays, `image` shows one
picture, and `sequence` plays a folder of pictures in the order of the numbers
in their names. Pictures can be PNG, JPEG or GIF. `file` or `folder` must
always be given. The board looks for it in this drive's `pictures` folder, where
the picker adds pictures, then directly on the drive.

<!-- if examples -->
The example pictures are in the `examples/pictures` folder. To use one in an
entry, include the folder in its name, such as
`file=examples/pictures/medscan.gif`. The picker shows them on its Screens tab,
below your own pictures.
<!-- end -->

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
__SCREEN__: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the pause in seconds at each end, so a ping-pong rests before turning
back. One value sets both ends, or set each with a `|`:

```entry
__SCREEN__: gif file="wave.gif" ping_pong=yes hold=1
__SCREEN__: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

The board looks for a file on this drive first, then on the board itself, and
the name can include folders.

<!-- board screen_notes -->

### Drawing from code

**This section is for Python writers.** A screen can play a drawing instead of
a picture: a Python file with one function in it, drawn alongside everything
else in this file, so the lights keep their effects,
<!-- if two_screens -->
the other screen keeps its pictures,
<!-- end -->
and a scene shows and hides the drawing along with everything else in
it.

| Plays | Settings |
| --- | --- |
| `drawing` | `file` `fps` `interval` `width` `height` |

```entry
__SCREEN__: drawing file=rings.py
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

<!-- if examples -->
The examples under `examples/programs/screens/graphics` show what PicoVector can draw,
and a program that needs the whole board, not just one screen, is
<!-- end -->
<!-- if not examples -->
A program that needs the whole board, not just one screen, is
<!-- end -->
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
