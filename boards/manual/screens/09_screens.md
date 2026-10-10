## Screens

### Naming screens

__SCREEN_NAMING__. A screen
cannot say what size it is, so tell the board:

```entry
board: __SCREEN__=1.54
```

That is a board entry, which sets the board rather than the lights and is one of
a handful covered under [The board](#the-board).

The sizes are 2.8 and 1.54, and a screen plays nothing until its size is given.
Changing it needs the board turned off and on again before the new size takes.

<!-- if hub -->
### A Screen Hub

A Screen Hub takes both connectors and carries up to six screens, at the
positions its board letters A to F. Say which connector its screens come through
with `hub`, the other taking its selects, then the size at each position fitted:

```entry
board: screenA=hub hubA-D,F=2.8 hubE=1.54
hubA-C: gif file=flames.gif
hubD,F: image file=badge.png
```

Positions are named as outputs are, `hubB` alone or `hubA-C,E` for several.
Several positions showing the same picture are sent it once, so a picture across
all six moves as smoothly as it does on one. A picture goes only to screens of
one size, so give 2.8 and 1.54 positions entries of their own. A position with
nothing to show in a scene is black.

All six share one backlight, so `backlight` is for the whole hub: the first
entry to set it decides, and `errors.txt` says where two entries showing at once
ask for different ones. In scenes, each scene can set its own.
<!-- end -->

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
__SCREEN__ rotation=90: gif file="clock.gif"
__SCREEN__ offset=*|20 bg=black: image file=logo.png
__SCREEN__ tile=repeat: image file=bricks.png
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
__SCREEN__: gif file="clock.gif"
__SCREEN__: image file=logo.png
__SCREEN__: sequence folder=photos interval=30
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
__SCREEN__: gif file="coin.gif" ping_pong=yes first_as_last=yes
```

`hold` is the seconds to wait where it turns around, so a ping-pong pauses at
each end instead of bouncing straight off. One value serves both ends, or write
each with a `|`:

```entry
__SCREEN__: gif file="wave.gif" ping_pong=yes hold=1
__SCREEN__: gif file="wave.gif" ping_pong=yes hold=1.5|0.5
```

A file is looked for on this drive first, then on the board itself, and the name
may include folders. There is little room here, so pictures usually live on the
board.

<!-- board screen_notes -->

### Drawing from code

**This one is for Python writers.** A screen can play a drawing instead of a
picture: a Python file with one function in it, drawn beside everything else in
this file, so the lights keep their effects,
<!-- if two_screens -->
the other screen keeps its pictures,
<!-- end -->
and a scene puts the drawing on and off with everything else it holds.

| Plays | Settings |
| --- | --- |
| `graphics` | `file` `fps` `interval` `width` `height` |

```entry
__SCREEN__: graphics file=rings.py
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

<!-- if examples -->
The examples under `examples/python/screens/graphics` show what PicoVector can draw,
and a program that wants the whole board instead of one screen is
<!-- end -->
<!-- if not examples -->
A program that wants the whole board instead of one screen is
<!-- end -->
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
