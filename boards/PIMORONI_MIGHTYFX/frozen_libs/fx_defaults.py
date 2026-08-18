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
#
# README is a card, and the manual it points at is fx_manual.py, generated from
# manual/MANUAL.md and not written by hand.

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
board applies the change straight away. One line per set of outputs:

  out1-7: rainbow_wave speed=0.3

MANUAL.html on this drive has the rest, and opens in a browser: every effect and
what it takes, the screens, running a program, and showing scenes in turn.

In a hurry? Save the file and press "Boot" once. The drive disappears and comes
straight back with the new effects running, so you can keep editing. Ejecting is
the surer way, since a computer does not always write the file out until then.
Press "Boot" twice to hide the drive, and twice again to bring it back.

Deleting effects.txt restores the default; emptying it leaves the board dark.

When something is wrong the lights say so, and the more flashes the worse it is:

  white, once         the computer was still writing, so the press did nothing;
                      try again in a moment
  blue, twice         something in effects.txt could not be read; errors.txt
                      says which line
  red, three times    there was no room to write errors.txt; this drive is full
                      or damaged, so free some space or let a computer repair it

While the computer is copying to this drive the effects stand aside for a dim
white travelling along the outputs, and come back a moment after it finishes.

This README is rebuilt by the board, so edits to it will not stick.
"""
