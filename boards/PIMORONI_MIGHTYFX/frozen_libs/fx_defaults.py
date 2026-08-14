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

Deleting effects.txt restores the default. If something cannot be read, the
board writes errors.txt saying which line, and flashes red three times.


Writing an entry
----------------
  <outputs>: <effect> <setting=value> ...

  out1-7: rainbow_wave speed=0.3
  out3: pulse speed=0.6

Settings you leave out take their usual value. A '#' starts a comment. Spread a
entry over several lines if it reads better; indenting changes nothing.


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

  'level'           how bright, 0 to 1 or a percentage
  'colour'          a name or six-digit hex, for effects that bring no colour

  out1-7 level=50%: pulse
  out1-3 colour=warm: flicker
  out4 colour=ff8040: static
  out1 level=0.5, 2 level=0.8, 3-7: pulse_wave

Colours by name: red, yellow, green, cyan, blue, magenta, warm, white, cool,
black. Or the hex a colour picker gives you, with its '#' left off, as out4
above uses for a soft orange.


Effects
-------
For an output, or for one of its red, green and blue:

  none
  static            level
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

'rgb_blink' takes one colour, or several to blink through in turn:

  rgb: rgb_blink colour=red,warm,ff8040 speed=0.5

'speed' is cycles a second: 1 goes round once a second, 0.5 once every two, 2
twice a second.

The settings measured in seconds are 'interval', flicker's 'bright_min',
'bright_max', 'dim_min' and 'dim_max', and traffic_light's four intervals.
'length', 'flashes', 'steps', 'count' and 'step' are plain counts. The rest run
from 0 to 1 and take a percentage too, 'window' among them, being the share of a
cycle the flashes happen in.


This README is rebuilt by the board, so edits to it will not stick.
"""
