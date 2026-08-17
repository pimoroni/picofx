# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# What a fresh board starts from, one constant per file it fills. EFFECTS and README
# go on the FX drive and are rebuilt by fx_drive; MAIN goes to the filesystem root and
# is rebuilt by boot.py. Each board carries its own copy of this file.
#
# These are the only copies. Nothing ships main.py in the image, so a board writes its
# own on first boot and there is no second version to drift from.
#
# They live here rather than inside fx_drive.py so edits to the wording show up on
# their own in a diff. Ordinary quotes are fine inside these; only a literal triple
# quote would need escaping.

MAIN = '''\
from mighty_fx import MightyFX

import autofx
import fx_drive

"""
Play the effects described by effects.txt on the FX drive.

Plug the board into a computer and the drive appears. Edit effects.txt, eject the
drive, and the new effects start straight away. Press "Boot" once to try an edit
without putting the drive away, or twice to hide it and bring it back.

Replace this file with your own program if you would rather write code; deleting it
brings this one back, and an empty one leaves the board quiet.
"""

autofx.run(MightyFX(), volume=fx_drive)
'''

EFFECTS = """\
# MightyFX effects
# One entry per set of outputs: <outputs>: <effect> [setting=value ...]
# Omitted settings take the effect's own defaults. '#' starts a comment.
out1-7: rainbow_wave speed=0.3
"""

README = """\
MightyFX
========
Edit effects.txt to change what the lights do, then eject this drive and the
board applies the change straight away.

In a hurry? Save the file and press "Boot" once. The drive disappears and comes
straight back with the new effects running, so you can keep editing. Ejecting is
the surer way, since a computer does not always write the file out until then.
Press "Boot" twice to put the drive away, and twice again to bring it back.

Deleting effects.txt restores the default; emptying it leaves the board dark.

When something is wrong the lights say so, and the more flashes the worse it is:

  white, once         the computer was still writing, so the press did nothing;
                      try again in a moment
  blue, twice         something in effects.txt could not be read; errors.txt
                      says which line
  red, three times    there was no room to write errors.txt; this drive is full
                      or damaged, so free some space or let a computer repair it

While the computer is copying to this drive the effects stand aside and a dim
white travels along the outputs, coming back a moment after it finishes.


Writing an entry
----------------
  <outputs> <their settings>: <effect> <its settings>

  out1-7: rainbow_wave speed=0.3
  out3 level=50%: pulse speed=0.6

There is one colon in an entry. Which outputs, and how bright or what colour
they are, go before it. The effect and its own settings go after.

Settings you leave out take their usual value. A '#' starts a comment. An entry
can run on over several lines so long as the colon is on the first; indenting
changes nothing.

A screen is named the same way and plays pictures instead of lighting up. See
"Screens" below.


The board itself
----------------
One entry sets the board rather than the lights, and names no output:

  board: drive=manual program=fireplace.py

  'drive'           'manual' keeps the drive hidden until you ask for it
  'program'         a Python file to run instead of the effects
  'screenA'         what size of screen is on SP/CE A, if you have one
  'screenB'         the same for SP/CE B

A program can sit on this drive or on the board's own filesystem: a name is
looked for here first, then on the board, and it may include folders. So
'program=fireplace.py' finds one of that name in either place, and
'program=examples/effects/colour/rainbow_wave.py' reaches one of the examples
the board ships with. Where the name is in both, this drive's copy runs.

If it is missing, or stops with an error, the effects run instead and
errors.txt says what happened, so a mistyped name never leaves you with a board
that does nothing.

The effects stop while a program runs, and the board is busy with it, so "Boot"
and ejecting do nothing. The drive is put up first so you can still edit
effects.txt; unplug and plug back in for the change to take. That happens even
with 'drive' set to 'manual', since hiding it would leave no way to change
either setting back. It also means a program cannot read files from this drive
while it runs, so put anything it needs on the board's own filesystem.


Naming outputs
--------------
  out1              one output
  out1,3,5          three of them
  out1-7            all seven
  out7-1            all seven, the other way round
  out2,1,5-7        mixed, and in the order you write them

An output shows colour. Its red, green and blue can be driven separately as
three plain lights instead:

  out3.r            just the red
  out3.*            all three of them
  out1-7.*          all 21

Order matters for the effects that travel: they move in the order you write the
outputs, so list them in the order they appear in your build, which need not be
number order.


Setting an output
-----------------
Before the colon, and separate from the effect:

  'level'           how bright, 0 to 1, such as 0.5 or 50%
  'colour'          a name or six-digit hex, for effects that bring no colour

  out1-7 level=50%: pulse
  out1-3 colour=warm: flicker
  out4 colour=ff8040: static
  out1 level=0.5, 2 level=0.8, 3-7: pulse_wave

Colours by name: red, yellow, green, cyan, blue, magenta, warm, white, cool,
black. Or the hex a colour picker gives you, with its '#' left off, as out4
above uses for a soft orange. A '#' always starts a comment, so one left on a
colour hides the rest of the line.


Effects
-------
For an output, or for one of its red, green and blue:

  none
  static            brightness
  blink             speed phase duty
  blink_wave        speed length phase duty
  flash             speed flashes window phase duty
  flash_sequence    speed length flashes window phase duty
  flicker           brightness dimness bright_min bright_max
                    dim_min dim_max
  pulse             speed phase
  pulse_wave        speed length phase
  random            interval brightness_min brightness_max
  binary_counter    interval count step
  traffic_light     red_interval red_amber_interval green_interval
                    amber_interval fade_rate amber_flashing

For an output only, since these bring their own colour:

  rgb               red green blue
  hsv               hue sat val
  rainbow           speed sat val
  rainbow_wave      speed length sat val
  hue_step          interval hue sat val steps
  rgb_blink         colour speed phase duty

The ones ending '_wave', '_sequence' and '_counter' travel across the outputs
you name; the rest do the same on every one. 'traffic_light' wants three
outputs, and lights them red, amber and green in that order.

'rgb_blink' takes one colour, or several to blink through in turn, divided by
'|' because they are parts of one setting rather than one each for the outputs:

  out1: rgb_blink colour=red|warm|ff8040 speed=0.5

'speed' is cycles a second: 1 goes round once a second, 0.5 once every two, 2
twice a second. A negative speed runs the cycle backwards.

The settings measured in seconds are 'interval', flicker's 'bright_min',
'bright_max', 'dim_min' and 'dim_max', and traffic_light's four intervals.
'length', 'flashes', 'steps', 'count' and 'step' are plain counts, and a
negative 'step' counts down.
'amber_flashing' is true or false, and takes yes, on and 1 too. 'fade_rate' is
how fast a traffic light's colours come up, per millisecond, so the usual 0.01
reaches full in a tenth of a second and much above that looks instant.

The rest run from 0 to 1, written 0.5 or 50% as you prefer, 'window' among them,
being the share of a cycle the flashes happen in. 'hue' takes degrees as well,
written 180deg, which is what a colour picker gives you.

A setting whose value is not what it takes is ignored, with a note in
errors.txt, and the effect runs on its usual value for it.


Screens
-------
A screen on either SP/CE connector is named screenA or screenB. A screen
cannot say what size it is, so tell the board:

  board: screenA=1.54

The sizes are 2.8 and 1.54, and 2.8 is used if you say nothing. Changing it
needs the board turned off and on again before the new size takes.

What a screen plays:

  gif               file fps interval loop ping_pong
  image             file
  sequence          folder fps interval loop ping_pong

  screenA: gif file="clock.gif"
  screenA: image file=logo.png
  screenA: sequence folder=photos interval=30

'gif' plays an animated GIF at the delays it was saved with, 'image' holds
one picture, and 'sequence' plays a folder of them in the order their names
number them. Pictures can be PNG, JPEG or GIF.

'fps' is frames a second and 'interval' is the seconds between them, so use
whichever suits: 'fps=12' for an animation, 'interval=30' for a slideshow.
Either one replaces the delays the file was saved with. 'loop' is true
unless you set it false, which stops on the last frame. 'ping_pong' plays
back and forth instead of starting over.

A file is looked for on this drive first, then on the board itself, and the
name may include folders. There is little room here, so pictures usually
live on the board.

A screen draws about twenty frames a second at best, and effects on the
outputs take time from it, so a file asking for more gets its speed and not
its smoothness.


Setting a screen
----------------
Before the colon, and separate from what it plays:

  'rotation'        0, 90, 180 or 270, for how the screen is mounted
  'backlight'       how brightly it is lit, 0 to 1, such as 0.5 or 50%
  'mirror'          true to flip the picture left to right
  'offset'          where to put the picture, as x|y
  'background'      the colour around it, or 'bg' for short
  'pixel_double'    true to draw each pixel twice as wide and tall, so a
                    half size picture fills the screen

  screenA rotation=90: gif file="clock.gif"
  screenA offset=*|20 bg=black: image file=logo.png

A picture is centred unless 'offset' puts it somewhere, and a '*' in place
of either number centres that side. The '|' is there because a comma always
means one value per output, where these two are parts of one value.


This README is rebuilt by the board, so edits to it will not stick.
"""
