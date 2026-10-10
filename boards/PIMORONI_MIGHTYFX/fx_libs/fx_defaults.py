# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT

# What a fresh board starts from, one constant per file it fills. EFFECTS, README and
# SECRETS go on the FX drive and are rebuilt by fx_drive, SECRETS only by firmware with
# networking; MAIN goes to the filesystem root and is rebuilt by boot.py. Each board
# carries its own copy of this file.
#
# These are the only copies a drive build has. Nothing ships main.py or secrets.py in
# its image, so a board writes its own on first boot. The builds without the drive ship
# the examples' secrets.py, which holds the same settings as SECRETS.
#
# They live here rather than inside fx_drive.py so edits to the wording show up on
# their own in a diff. Ordinary quotes are fine inside these; only a literal triple
# quote would need escaping.
#
# README is a card, and the manual it points at is fx_manual.py, generated from
# manual/MANUAL.md and not written by hand.

MAIN = '''\
from mighty_fx import MightyFX

# Light the outputs first: importing the effects machinery below takes a few
# seconds, and this says the board is alive while it happens
MightyFX.wake()

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

autofx.run(MightyFX, volume=fx_drive)
'''

# Exactly what the picker writes for its Rainbow look on the outputs, so a fresh board's
# file opens in the picker as that look. Change it with the picker's own output, or the
# picker reads it as a file written by hand
EFFECTS = """\
# Written by the FX picker. Everything here can be edited by hand;
# MANUAL.html on this drive explains every line.

out1-7: rainbow_wave speed=-0.39 length=9
"""

README = """\
MightyFX
========
Edit effects.txt to change what the lights do and save it, and the board plays
the change a few seconds later. One line per set of outputs:

  out1-7: rainbow_wave speed=0.3

MANUAL.html on this drive has the rest, and opens in a browser: every effect and
what it takes, the screens, playing sound, running a program, and showing scenes
in turn.

If a save does not seem to take, press "Boot" once or eject this drive, since a
computer does not always write the file out straight away. Press "Boot" twice to
hide the drive, and twice again to bring it back.

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

# Empty, for the user to fill in. Written only where the drive has none, so their edits stay
SECRETS = '''\
# Your WiFi network's name and password, for the programs that go online
WIFI_SSID = ""
WIFI_PASSWORD = ""
'''
